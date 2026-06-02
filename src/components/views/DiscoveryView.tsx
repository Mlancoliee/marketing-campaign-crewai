import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { t } from "../../i18n"
import type { ChatMessage, AgentId } from "../../types"

interface DiscoveryViewProps {
  messages: ChatMessage[]
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  onSkip: () => void
  suggestions?: string[]
  onSuggestionClick?: (suggestion: string) => void
}

export default function DiscoveryView({ messages, streaming, activeAgents, onSkip, suggestions, onSuggestionClick }: DiscoveryViewProps) {
  const discoveryMessages = messages.filter((m) => m.phase === "discovery")
  const isAgentActive = activeAgents.some((a) => a.agent === "market_analyst")

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="sticky -top-4 z-10 bg-[var(--color-bg)] pt-4 pb-2 -mx-6 px-6 flex items-center justify-between mb-2 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold font-[var(--font-heading)]">
          {t("phase.discovery")}
        </h2>
        <button
          onClick={onSkip}
          disabled={streaming}
          className="btn btn-outline text-xs cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
          {t("action.skip_discovery")}
        </button>
      </div>

      {discoveryMessages.map((msg, idx) => (
        <div
          key={idx}
          className={`animate-fade-in ${
            msg.role === "user" ? "flex justify-end" : ""
          }`}
        >
          {msg.role === "user" ? (
            <div className="max-w-[80%] bg-[var(--color-primary)] text-white px-4 py-2.5 rounded-2xl rounded-br-sm text-sm">
              {msg.content}
            </div>
          ) : (
            <div className="card">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center">
                  <svg className="w-3.5 h-3.5 text-[var(--color-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {t(`agent.${msg.role}`)}
                </span>
              </div>
              <div className="card-content text-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      ))}

      {isAgentActive && (
        <div className="card animate-fade-in">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-[var(--color-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <span className="text-xs text-[var(--color-text-muted)]">{t("agent.market_analyst")}</span>
            <div className="flex gap-1 ml-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
            </div>
          </div>
        </div>
      )}

      {/* 推荐回答按钮 */}
      {suggestions && suggestions.length > 0 && !streaming && !isAgentActive && onSuggestionClick && (
        <div className="flex flex-wrap gap-2 pt-2 animate-fade-in">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSuggestionClick(s)}
              className="btn btn-outline text-xs cursor-pointer hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
