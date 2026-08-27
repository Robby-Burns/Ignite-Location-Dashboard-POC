"""FastAPI application entrypoint for Ignite Facility Operational Decision Agent POC."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown tasks."""
    # Initialize database tables
    init_db()
    yield


app = FastAPI(
    title="Ignite Facility Operational Decision Agent API",
    description="Proof of concept operational decision support agent for Ignite Medical Resorts.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for local frontend and Railway deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
