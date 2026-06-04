import { t } from "../i18n"
import type { Phase } from "../types"

interface PhaseProgressProps {
  phase: Phase
  progress: number
}

const PHASES: { key: Phase; label: string }[] = [
  { key: "discovery", label: "phase.discovery" },
  { key: "planning", label: "phase.planning" },
  { key: "integration", label: "phase.integration" },
  { key: "content", label: "phase.content" },
  { key: "finalize", label: "phase.finalize" },
]

const PHASE_ORDER: Phase[] = PHASES.map((p) => p.key)

export default function PhaseProgress({ phase }: PhaseProgressProps) {
  const currentIdx = PHASE_ORDER.indexOf(phase)

  return (
    <div className="px-6 py-3 bg-white border-b border-[var(--color-border)]">
      <div className="flex items-center max-w-2xl mx-auto">
        {PHASES.map((p, idx) => {
          const isActive = p.key === phase
          const isCompleted = idx < currentIdx

          return (
            <div key={p.key} className="flex items-center flex-1 last:flex-none">
              {/* 节点 */}
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
              {/* 连线（最后一个不显示） */}
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
    </div>
  )
}
