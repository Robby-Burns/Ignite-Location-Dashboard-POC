"""Multi-provider LLM Client for Facility Operational Decision Support.

Supports:
- OpenRouter API (Access to Gemini 2.0/2.5, Claude 3.5/3.7, GPT-4o, Llama 3.3, DeepSeek via unified API)
- Real Google Gemini API (via Gemini REST endpoint or OpenAI-compatible endpoint)
- Real OpenAI API (GPT-4o / GPT-4o-mini)
- Configurable Custom Endpoints (via LLM_BASE_URL / LLM_API_KEY)
- Offline Dynamic Reasoning Synthesizer when external API keys are unavailable (for offline tests/demos)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import httpx
from pydantic import BaseModel, Field


class LLMExecutionReceipt(BaseModel):
    """Execution receipt for an LLM generation call."""

    receipt_id: str = Field(
        ..., description="Unique receipt identifier, e.g. 'REC-LLM-...'"
    )
    provider: str = Field(
        ...,
        description="LLM provider name (e.g. 'openrouter', 'google-gemini', 'openai', 'deterministic-fallback')",
    )
    model: str = Field(
        ...,
        description="Model identifier used (e.g. 'google/gemini-2.0-flash-001', 'gemini-2.0-flash', 'gpt-4o')",
    )
    latency_ms: float = Field(..., ge=0.0, description="Call duration in milliseconds")
    is_live_call: bool = Field(
        ..., description="Whether a live external HTTP call was performed"
    )
    prompt_chars: int = Field(default=0, description="Number of characters in prompt")
    completion_chars: int = Field(
        default=0, description="Number of characters in completion"
    )


class LLMClient:
    """Async client for executing LLM operational decision prompts with structured JSON output."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        provider: str | None = None,
    ):
        # Determine explicit or inferred provider
        explicit_provider = (provider or os.getenv("LLM_PROVIDER", "")).lower().strip()
        env_openrouter_key = os.getenv("OPENROUTER_API_KEY")
        env_gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        env_openai_key = os.getenv("OPENAI_API_KEY")
        env_generic_key = os.getenv("LLM_API_KEY")

        if explicit_provider in ("openrouter", "open-router"):
            self.effective_provider = "openrouter"
            self.openrouter_key = api_key or env_openrouter_key
            self.gemini_key = env_gemini_key
            self.openai_key = env_openai_key
        elif explicit_provider in ("gemini", "google"):
            self.effective_provider = "gemini"
            self.gemini_key = api_key or env_gemini_key
            self.openrouter_key = env_openrouter_key
            self.openai_key = env_openai_key
        elif explicit_provider == "openai":
            self.effective_provider = "openai"
            self.openai_key = api_key or env_openai_key
            self.openrouter_key = env_openrouter_key
            self.gemini_key = env_gemini_key
        elif model and "/" in model:
            # Model identifiers like 'google/gemini-2.0-flash-001' or 'anthropic/claude-3.5-haiku'
            self.effective_provider = "openrouter"
            self.openrouter_key = api_key or env_openrouter_key
            self.gemini_key = env_gemini_key
            self.openai_key = env_openai_key
        elif model and "gemini" in model.lower():
            self.effective_provider = "gemini"
            self.gemini_key = api_key or env_gemini_key
            self.openrouter_key = env_openrouter_key
            self.openai_key = env_openai_key
        elif model and any(k in model.lower() for k in ("gpt", "o1", "o3")):
            self.effective_provider = "openai"
            self.openai_key = api_key or env_openai_key
            self.openrouter_key = env_openrouter_key
            self.gemini_key = env_gemini_key
        elif api_key:
            self.effective_provider = "gemini"
            self.gemini_key = api_key
            self.openrouter_key = api_key
            self.openai_key = api_key
        elif env_openrouter_key:
            self.effective_provider = "openrouter"
            self.openrouter_key = env_openrouter_key
            self.gemini_key = env_gemini_key
            self.openai_key = env_openai_key
        elif env_gemini_key:
            self.effective_provider = "gemini"
            self.gemini_key = env_gemini_key
            self.openrouter_key = None
            self.openai_key = env_openai_key
        elif env_openai_key:
            self.effective_provider = "openai"
            self.openai_key = env_openai_key
            self.openrouter_key = None
            self.gemini_key = None
        else:
            self.effective_provider = "none"
            self.openrouter_key = None
            self.gemini_key = None
            self.openai_key = None

        self.generic_key = api_key or env_generic_key
        self.base_url = base_url or os.getenv("LLM_BASE_URL")

        # Resolve model name
        raw_model = (
            model
            or (
                os.getenv("OPENROUTER_MODEL")
                if self.effective_provider == "openrouter"
                else None
            )
            or os.getenv("LLM_MODEL")
            or (
                "google/gemini-2.5-flash"
                if self.effective_provider == "openrouter"
                else (
                    "gemini-2.0-flash"
                    if self.effective_provider == "gemini"
                    else "gpt-4o-mini"
                )
            )
        )

        # Normalize OpenRouter model aliases
        if self.effective_provider == "openrouter":
            if raw_model in (
                "google/gemini-2.0-flash-001",
                "google/gemini-2.0-flash",
                "gemini-2.0-flash",
            ):
                raw_model = "google/gemini-2.5-flash"
            elif raw_model == "gpt-4o-mini":
                raw_model = "openai/gpt-4o-mini"
            elif raw_model == "claude-3.5-haiku":
                raw_model = "anthropic/claude-3.5-haiku"

        self.model = raw_model

    @property
    def has_live_credentials(self) -> bool:
        """Return whether external LLM API credentials are configured."""
        return bool(
            self.openrouter_key
            or self.gemini_key
            or self.openai_key
            or self.generic_key
        )

    async def generate_structured_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema_name: str = "FacilityStateAnalysis",
        fallback_data: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, LLMExecutionReceipt]:
        """Execute LLM call requesting structured JSON or return None when AI is unavailable (Spec §8)."""
        start_time = time.perf_counter()
        receipt_id = f"REC-LLM-{int(time.time())}-{uuid.uuid4().hex[:6]}"

        # 1. OpenRouter Provider
        if self.effective_provider == "openrouter" and (
            self.openrouter_key or self.generic_key
        ):
            try:
                result_json = await self._call_openrouter_api(
                    system_prompt, user_prompt
                )
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                receipt = LLMExecutionReceipt(
                    receipt_id=receipt_id,
                    provider="openrouter",
                    model=self.model,
                    latency_ms=elapsed_ms,
                    is_live_call=True,
                    prompt_chars=len(system_prompt) + len(user_prompt),
                    completion_chars=len(json.dumps(result_json)),
                )
                return result_json, receipt
            except Exception:  # noqa: BLE001, S110
                pass

        # 2. Native Google Gemini Provider
        if self.gemini_key and self.effective_provider in ("gemini", "none"):
            try:
                result_json = await self._call_gemini_api(system_prompt, user_prompt)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                receipt = LLMExecutionReceipt(
                    receipt_id=receipt_id,
                    provider="google-gemini",
                    model=self.model,
                    latency_ms=elapsed_ms,
                    is_live_call=True,
                    prompt_chars=len(system_prompt) + len(user_prompt),
                    completion_chars=len(json.dumps(result_json)),
                )
                return result_json, receipt
            except Exception:  # noqa: BLE001, S110
                pass

        # 3. Native OpenAI Provider or Generic OpenAI-compatible
        if (self.openai_key or self.generic_key) and self.effective_provider in (
            "openai",
            "generic",
            "none",
        ):
            try:
                result_json = await self._call_openai_api(system_prompt, user_prompt)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                receipt = LLMExecutionReceipt(
                    receipt_id=receipt_id,
                    provider="openai" if self.openai_key else "openai-compatible",
                    model=self.model,
                    latency_ms=elapsed_ms,
                    is_live_call=True,
                    prompt_chars=len(system_prompt) + len(user_prompt),
                    completion_chars=len(json.dumps(result_json)),
                )
                return result_json, receipt
            except Exception:  # noqa: BLE001, S110
                pass

        # Per Spec §8 & INV-001: When AI is unavailable, do not substitute hard-coded AI conclusions.
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        receipt = LLMExecutionReceipt(
            receipt_id=receipt_id,
            provider="deterministic-fallback",
            model="none",
            latency_ms=elapsed_ms,
            is_live_call=False,
            prompt_chars=len(system_prompt) + len(user_prompt),
            completion_chars=0,
        )
        return None, receipt

    async def _call_openrouter_api(
        self, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        """Execute OpenRouter API call using chat completions standard."""
        base = (
            os.getenv("OPENROUTER_BASE_URL")
            or self.base_url
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        url = f"{base}/chat/completions"
        key = self.openrouter_key or self.generic_key
        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": os.getenv(
                "OPENROUTER_REFERER", "https://github.com/Ignite-Medical-Resorts"
            ),
            "X-Title": os.getenv(
                "OPENROUTER_APP_TITLE", "Ignite Facility Decision Agent"
            ),
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            # Clean markdown codeblocks if wrapped
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            return json.loads(raw_text)

    async def _call_gemini_api(
        self, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        """Execute real Gemini API call via Generative Language REST API using header auth."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.gemini_key,
            "Content-Type": "application/json",
        }
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            return json.loads(raw_text)

    async def _call_openai_api(
        self, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        """Execute call to OpenAI or OpenAI-compatible endpoint."""
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"
        key = self.openai_key or self.generic_key
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            return json.loads(raw_text)
