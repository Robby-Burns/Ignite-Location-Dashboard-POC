import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  MessageCircle,
  Send,
  Sparkles,
  AlertOctagon,
  ShieldCheck,
  HelpCircle,
  ChevronRight,
  RotateCw,
  Bot,
  User,
} from "lucide-react";
import {
  FollowUpQuestionReport,
  FollowUpQuestion,
  ChatMessage,
  ChatResponse,
} from "../types";

interface ChatViewProps {
  facilityId: string;
  scenario: string;
}

export const ChatView: React.FC<ChatViewProps> = ({
  facilityId,
  scenario,
}) => {
  const [questionsData, setQuestionsData] =
    useState<FollowUpQuestionReport | null>(null);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [questionsError, setQuestionsError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchQuestions = async () => {
    setQuestionsLoading(true);
    setQuestionsError(null);
    try {
      const res = await axios.get<FollowUpQuestionReport>(
        `/api/agent/follow-up-questions?facility_id=${facilityId}&scenario=${scenario}`
      );
      setQuestionsData(res.data);
    } catch (err: any) {
      setQuestionsError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to fetch suggested questions."
      );
    } finally {
      setQuestionsLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
    setMessages([]);
  }, [facilityId, scenario]);

  const sendMessage = async (questionText: string) => {
    if (!questionText.trim() || isSending) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: questionText.trim(),
    };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputValue("");
    setIsSending(true);
    setChatError(null);

    try {
      const res = await axios.post<ChatResponse>("/api/agent/chat", {
        facility_id: facilityId,
        scenario: scenario,
        question: questionText.trim(),
        conversation_history: updatedMessages.slice(-6),
      });

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: res.data.answer,
      };
      setMessages([...updatedMessages, assistantMessage]);
    } catch (err: any) {
      setChatError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to get a response."
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleSuggestedQuestion = (q: FollowUpQuestion) => {
    sendMessage(q.question_text);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const getPriorityColor = (priority: string) => {
    if (priority === "HIGH") return "bg-red-100 text-red-800 border-red-200";
    if (priority === "MEDIUM")
      return "bg-amber-100 text-amber-800 border-amber-200";
    return "bg-slate-100 text-slate-700 border-slate-200";
  };

  const getDomainLabel = (domain: string) => {
    const labels: Record<string, string> = {
      census: "Census",
      staffing: "Staffing",
      therapy: "Therapy",
      payer_auth: "Authorizations",
      hospital_transfers: "Transfers",
      hospitality: "Hospitality",
      length_of_stay: "Length of Stay",
      admissions_discharges: "Admissions",
    };
    return labels[domain] || domain;
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-br from-teal-900 to-emerald-950 text-white shadow-md border border-emerald-800/40">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 text-xs font-extrabold uppercase tracking-wider rounded-full bg-teal-600 text-white shadow-xs">
              Interactive
            </span>
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-700 text-emerald-100">
              Story 4.3
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <MessageCircle className="w-8 h-8" />
            Ask the Facility
          </h2>
          <p className="text-base sm:text-lg leading-relaxed text-emerald-100">
            Investigate the facility analysis with dynamic follow-up questions.
            Select a suggested question or type your own.
          </p>
        </div>
      </div>

      {/* Suggested Questions */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 sm:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-500" />
            Suggested Questions
          </h3>
          <button
            onClick={fetchQuestions}
            className="p-1.5 text-slate-400 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
            title="Refresh questions"
          >
            <RotateCw
              className={`w-4 h-4 ${questionsLoading ? "animate-spin" : ""}`}
            />
          </button>
        </div>

        {questionsLoading && (
          <div className="flex items-center gap-3 py-4">
            <div className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-slate-500 animate-pulse">
              Generating questions from current analysis...
            </p>
          </div>
        )}

        {questionsError && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm flex items-start gap-2">
            <AlertOctagon className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            {questionsError}
          </div>
        )}

        {questionsData && questionsData.questions.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {questionsData.questions.map((q) => (
              <button
                key={q.question_id}
                onClick={() => handleSuggestedQuestion(q)}
                disabled={isSending}
                className="text-left p-4 rounded-xl border border-slate-200 hover:border-teal-300 hover:bg-teal-50/50 transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1.5 flex-1">
                    <p className="text-sm font-semibold text-slate-800 group-hover:text-teal-800 transition-colors">
                      {q.question_text}
                    </p>
                    <p className="text-xs text-slate-500 line-clamp-2">
                      {q.context_summary}
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-teal-600 flex-shrink-0 mt-1 transition-colors" />
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getPriorityColor(q.priority)}`}
                  >
                    {q.priority}
                  </span>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase">
                    {getDomainLabel(q.related_domain)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {questionsData &&
          questionsData.analysis_state === "AI_ANALYSIS_UNAVAILABLE" && (
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5" />
              Questions generated deterministically (AI interpretation offline).
            </p>
          )}
      </div>

      {/* Chat Area */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col">
        {/* Chat Header */}
        <div className="p-4 border-b border-slate-100 flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-teal-600" />
          <h3 className="text-sm font-bold text-slate-800">Facility Chat</h3>
          {messages.length > 0 && (
            <span className="text-xs text-slate-400 ml-auto">
              {messages.filter((m) => m.role === "user").length} question
              {messages.filter((m) => m.role === "user").length !== 1
                ? "s"
                : ""}
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 p-4 space-y-4 max-h-[500px] overflow-y-auto min-h-[200px]">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400 space-y-3">
              <Bot className="w-12 h-12 text-slate-300" />
              <p className="text-sm font-medium">
                Ask a question about the facility operations
              </p>
              <p className="text-xs text-slate-400">
                Select a suggested question above or type your own
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-teal-700" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-teal-600 text-white rounded-br-md"
                    : "bg-slate-100 text-slate-800 rounded-bl-md"
                }`}
              >
                {msg.content}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-slate-600" />
                </div>
              )}
            </div>
          ))}

          {isSending && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-teal-700" />
              </div>
              <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
                <span className="text-xs text-slate-500">
                  Analyzing facility data...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error */}
        {chatError && (
          <div className="mx-4 mb-2 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-start gap-2">
            <AlertOctagon className="w-3.5 h-3.5 text-rose-600 flex-shrink-0 mt-0.5" />
            {chatError}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="p-4 border-t border-slate-100 flex gap-3"
        >
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a question about the facility..."
            disabled={isSending}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isSending}
            className="px-4 py-2.5 bg-teal-600 text-white rounded-xl hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline text-sm font-semibold">Ask</span>
          </button>
        </form>
      </div>

      {/* Governance Footer */}
      <div className="p-4 rounded-2xl bg-slate-100/80 border border-slate-200 text-xs text-slate-600 flex items-start gap-2">
        <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-slate-800">Decision Support</span>{" "}
          — All responses are grounded in verified facility data and are
          intended for human leadership review. The agent does not execute
          actions or replace human clinical or administrative judgment.
          Numerical calculations are deterministic and traceable. The Domo
          connection is simulated for this POC.
        </div>
      </div>
    </div>
  );
};
