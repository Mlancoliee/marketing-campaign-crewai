import { useState, useCallback } from "react"
import type { AgentId } from "../../types"
import { t } from "../../i18n"

interface BaseCardProps {
  title: string
  agent: AgentId
  loading?: boolean
  active?: boolean
  children: React.ReactNode
  actions?: {
    label: string
    type: "confirm" | "redo" | "rollback"
    onClick: (feedback?: string) => void
  }[]
  showFeedback?: boolean
}

export default function BaseCard({
  title,
  agent,
  loading,
  active,
  children,
  actions,
  showFeedback,
}: BaseCardProps) {
  const [feedback, setFeedback] = useState("")

  const handleAction = useCallback((onClick: (feedback?: string) => void) => {
    onClick(feedback.trim() || undefined)
    setFeedback("")
  }, [feedback])

  return (
    <div className={`card ${loading ? "loading" : ""} ${active ? "active" : ""} animate-fade-in`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-[var(--color-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <span className="text-xs text-[var(--color-text-muted)]">{t(`agent.${agent}`)}</span>
        </div>
        <h3 className="text-sm font-semibold font-[var(--font-heading)]">{title}</h3>
        {loading && (
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
          </div>
        )}
      </div>

      <div className="card-content text-sm leading-relaxed">{children}</div>

      {(actions?.length || showFeedback) && !loading && (
        <div className="mt-4 pt-3 border-t border-[var(--color-border)]">
          {showFeedback && (
            <input
              type="text"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={t("input.feedback_placeholder")}
              className="w-full px-3 py-2 text-sm border border-[var(--color-border)] rounded-[var(--radius-sm)] outline-none focus:border-[var(--color-primary)] mb-2 transition-colors"
            />
          )}
          {actions && actions.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {actions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAction(action.onClick)}
                  className={`btn cursor-pointer ${
                    action.type === "confirm"
                      ? "btn-primary"
                      : action.type === "redo"
                      ? "btn-outline"
                      : "btn-ghost"
                  }`}
                >
                  {action.type === "confirm" && (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                  {action.type === "redo" && (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  )}
                  {action.type === "rollback" && (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                    </svg>
                  )}
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
