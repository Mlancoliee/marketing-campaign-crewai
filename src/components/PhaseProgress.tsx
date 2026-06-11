import { t } from "../i18n"
import type { Phase } from "../types"

interface PhaseProgressProps {
  phase: Phase
  progress: number
  onNew: () => void
  onHistory: () => void
}

const PHASES: { key: Phase; label: string }[] = [
  { key: "discovery", label: "phase.discovery" },
  { key: "planning", label: "phase.planning" },
  { key: "integration", label: "phase.integration" },
  { key: "content", label: "phase.content" },
  { key: "finalize", label: "phase.finalize" },
]

const PHASE_ORDER: Phase[] = PHASES.map((p) => p.key)

export default function PhaseProgress({ phase, onNew, onHistory }: PhaseProgressProps) {
  const currentIdx = PHASE_ORDER.indexOf(phase)

  return (
    <div className="px-6 py-3 bg-white border-b border-[var(--color-border)]">
      <div className="flex items-center">
        {/* 阶段进度 */}
        <div className="flex items-center flex-1 max-w-2xl mx-auto">
          {PHASES.map((p, idx) => {
            const isActive = p.key === phase
            const isCompleted = idx < currentIdx

            return (
              <div key={p.key} className="flex items-center flex-1 last:flex-none">
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={`w-3 h-3 rounded-full transition-all flex-shrink-0 ${
                      isCompleted
                        ? "bg-[var(--color-success)]"
                        : isActive
                        ? "bg-[var(--color-primary)] ring-4 ring-[var(--color-primary)]/20"
                        : "bg-[var(--color-border)]"
                    }`}
                  />
                  <span
                    className={`text-xs whitespace-nowrap transition-colors ${
                      isActive
                        ? "text-[var(--color-primary)] font-semibold"
                        : isCompleted
                        ? "text-[var(--color-success)]"
                        : "text-[var(--color-text-muted)]"
                    }`}
                  >
                    {t(p.label)}
                  </span>
                </div>
                {idx < PHASES.length - 1 && (
                  <div
                    className="flex-1 h-0.5 mx-2"
                    style={{
                      backgroundColor: idx < currentIdx
                        ? "var(--color-success)"
                        : "var(--color-border)",
                    }}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* 新建 + 历史 */}
        <div className="flex items-center gap-1 ml-4 flex-shrink-0">
          <button onClick={onNew} className="btn btn-ghost text-xs cursor-pointer px-2 py-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            {t("app.new")}
          </button>
          <button onClick={onHistory} className="btn btn-ghost text-xs cursor-pointer px-2 py-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t("app.history")}
          </button>
        </div>
      </div>
    </div>
  )
}
