import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  MessageCircle,
  Send,
  Sparkles,
  ShieldCheck,
  ChevronRight,
  RotateCw,
  User,
  Loader2,
} from "lucide-react";
import type {
  FollowUpQuestionReport,
  FollowUpQuestion,
  ChatMessage,
  ChatResponse,
} from "../types";
import { scenarioById } from "../config";

interface ExploreAnalysisProps {
  facilityId: string;
  scenario: string;
  questionsData: FollowUpQuestionReport | null;
  questionsLoading: boolean;
  questionsError: string | null;
  onRefreshQuestions: () => void;
}

export const ExploreAnalysis: React.FC<ExploreAnalysisProps> = ({
  facilityId,
  scenario,
  questionsData,
  questionsLoading,
  questionsError,
  onRefreshQuestions,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  const accent = scenarioById(scenario);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isSending]);

  useEffect(() => {
    setMessages([]);
    setChatError(null);
  }, [facilityId, scenario]);

  const sendMessage = async (questionText: string) => {
    if (!questionText.trim() || isSending) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: questionText.trim(),
    };
    const updated = [...messages, userMessage];
    setMessages(updated);
    setInputValue("");
    setIsSending(true);
    setChatError(null);

    try {
      const res = await axios.post<ChatResponse>("/api/agent/chat", {
        facility_id: facilityId,
        scenario,
        question: questionText.trim(),
        conversation_history: updated.slice(-6),
      });
      setMessages([...updated, { role: "assistant", content: res.data.answer }]);
    } catch (err: any) {
      setChatError(
        err.response?.data?.detail || err.message || "Failed to get a response.",
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  return (
    <aside className="relative">
      <div
        className={`bg-surface border border-line rounded-[14px] shadow-card flex flex-col overflow-hidden ${
          collapsed ? "" : "max-h-[calc(100vh-40px)] xl:h-[calc(100vh-104px)]"
        }`}
      >
        {/* Head */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-line-soft">
          <div className="flex items-center gap-2 min-w-0">
            <MessageCircle className="w-[17px] h-[17px] flex-shrink-0" style={{ color: accent.accent }} />
            <h3 className="text-sm font-bold text-ink">Explore the analysis</h3>
          </div>
          <button
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? "Expand panel" : "Collapse panel"}
            className="w-[26px] h-[26px] rounded-md border border-line bg-surface flex items-center justify-center text-muted hover:bg-line-soft flex-shrink-0"
          >
            <ChevronRight
              className="w-[13px] h-[13px] transition-transform duration-200"
              style={{
                transform: collapsed ? "rotate(180deg)" : "rotate(0deg)",
              }}
            />
          </button>
        </div>

        {!collapsed && (
          <>
            {/* Body */}
            <div
              ref={bodyRef}
              className="flex-1 overflow-y-auto px-4 py-4 space-y-3.5 min-h-0 max-h-[440px] xl:max-h-none"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-muted">
                    Suggested questions
                  </p>
                  <button
                    onClick={onRefreshQuestions}
                    aria-label="Refresh suggested questions"
                    className="text-muted hover:text-flame transition-colors"
                  >
                    <RotateCw
                      className={`w-3.5 h-3.5 ${questionsLoading ? "animate-spin" : ""}`}
                    />
                  </button>
                </div>

                {questionsLoading && (
                  <div className="flex items-center gap-2 text-[12.5px] text-muted py-1">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Generating from current analysis…
                  </div>
                )}

                {!questionsLoading && questionsError && (
                  <p className="text-[12px] text-critical">{questionsError}</p>
                )}

                {!questionsLoading &&
                  questionsData &&
                  questionsData.questions.length > 0 && (
                    <div className="space-y-1.5">
                      {questionsData.questions.map((q: FollowUpQuestion) => (
                        <button
                          key={q.question_id}
                          onClick={() => sendMessage(q.question_text)}
                          disabled={isSending}
                          className="block w-full text-left bg-paper border border-line rounded-[9px] px-3 py-2 text-[12.5px] text-ink-soft font-medium hover:border-flame hover:text-ink hover:bg-white transition-colors disabled:opacity-50"
                        >
                          {q.question_text}
                        </button>
                      ))}
                    </div>
                  )}

                {!questionsLoading && questionsData && questionsData.questions.length === 0 && (
                  <p className="text-[12px] text-muted">
                    No suggested questions available.
                  </p>
                )}
              </div>

              {/* Conversation */}
              {messages.length > 0 && (
                <div className="pt-2 space-y-3 border-t border-line-soft">
                  {messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {msg.role === "assistant" && (
                        <span className="w-7 h-7 rounded-full overflow-hidden bg-line-soft flex items-center justify-center flex-shrink-0">
                          <img
                            src="/avatar.jpg"
                            alt="Ignite assistant"
                            className="w-full h-full object-cover"
                          />
                        </span>
                      )}
                      <div
                        className={`max-w-[85%] rounded-xl px-3 py-2 text-[12.5px] leading-relaxed ${
                          msg.role === "user"
                            ? "text-white rounded-br-md"
                            : "bg-paper text-ink rounded-bl-md border border-line"
                        }`}
                        style={
                          msg.role === "user"
                            ? { backgroundColor: accent.accent }
                            : undefined
                        }
                      >
                        {msg.content}
                      </div>
                      {msg.role === "user" && (
                        <span className="w-7 h-7 rounded-full bg-line-soft flex items-center justify-center flex-shrink-0">
                          <User className="w-3.5 h-3.5 text-ink-soft" />
                        </span>
                      )}
                    </div>
                  ))}

                  {isSending && (
                    <div className="flex gap-2.5 justify-start">
                      <span className="w-7 h-7 rounded-full overflow-hidden bg-line-soft flex items-center justify-center flex-shrink-0">
                        <img
                          src="/avatar.jpg"
                          alt="Ignite assistant"
                          className="w-full h-full object-cover"
                        />
                      </span>
                      <div className="bg-paper border border-line rounded-xl rounded-bl-md px-3 py-2 flex items-center gap-2">
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-muted" />
                        <span className="text-[12px] text-muted">Analyzing facility data…</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {chatError && (
                <p className="text-[12px] text-critical">{chatError}</p>
              )}
            </div>

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="flex gap-2 px-3.5 py-3 border-t border-line-soft"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your question…"
                disabled={isSending}
                className="flex-1 min-w-0 border border-line rounded-[9px] px-3 py-2 text-[12.5px] font-sans bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-flame disabled:opacity-50"
              />
              <button
                type="submit"
                aria-label="Send"
                disabled={!inputValue.trim() || isSending}
                className="w-[34px] h-[34px] rounded-[9px] flex items-center justify-center flex-shrink-0 disabled:opacity-50 text-white"
                style={{ backgroundColor: accent.accent }}
              >
                <Send className="w-[15px] h-[15px]" />
              </button>
            </form>

            {/* Trust footer */}
            <div className="flex gap-2 px-4 py-3 text-[11px] text-muted">
              <ShieldCheck className="w-3.5 h-3.5 text-good flex-shrink-0 mt-0.5" />
              <span>
                Answers are grounded in facility data. The agent does not make
                clinical or administrative decisions.
              </span>
            </div>
          </>
        )}

        {collapsed && (
          <div className="flex flex-col items-center gap-4 py-4 text-muted">
            <Sparkles className="w-[18px] h-[18px]" />
          </div>
        )}
      </div>
    </aside>
  );
};

export default ExploreAnalysis;
