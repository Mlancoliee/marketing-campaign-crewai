import { useState, useCallback } from "react"
import { t } from "../../i18n"
import type { CardData, AgentId } from "../../types"
import StrategyCard from "../cards/StrategyCard"
import CompareCards from "../cards/CompareCards"

interface IntegrationViewProps {
  cards: CardData
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  onAction: (type: "confirm" | "redo" | "rollback" | "keep_old", feedback?: string) => void
}

export default function IntegrationView({ cards, streaming, activeAgents, onAction }: IntegrationViewProps) {
  const isLoading = activeAgents.some((a) => a.agent === "chief_strategist")
  const [previousStrategy, setPreviousStrategy] = useState<string | null>(null)

  const content = (cards.strategy as Record<string, unknown>)?.content as string | undefined
    || (cards.strategy as Record<string, unknown>)?.raw as string | undefined
    || null

  const handleRedo = useCallback((feedback?: string) => {
    if (content) setPreviousStrategy(content)
    onAction("redo", feedback)
  }, [onAction, content])

  const handleConfirm = useCallback((feedback?: string) => {
    setPreviousStrategy(null)
    onAction("confirm", feedback)
  }, [onAction])

  const handleAcceptNew = useCallback(() => {
    // Just accept the new version (clear compare mode), don't advance
    setPreviousStrategy(null)
  }, [])

  const handleKeepOld = useCallback(() => {
    if (previousStrategy) {
      onAction("keep_old", previousStrategy)
    }
    setPreviousStrategy(null)
  }, [previousStrategy, onAction])

  const actions = !isLoading && !streaming && !previousStrategy && content ? [
    {
      label: t("action.redo"),
      type: "redo" as const,
      onClick: (feedback?: string) => handleRedo(feedback),
    },
  ] : undefined

  return (
    <div className="max-w-3xl mx-auto">
      <div className="sticky -top-4 z-10 bg-[var(--color-bg)] pt-4 pb-2 -mx-6 px-6 flex items-center justify-between mb-4 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold font-[var(--font-heading)]">
          {t("phase.integration")}
        </h2>
        <div className="flex gap-2">
          {!isLoading && !streaming && !previousStrategy && content && (
            <>
              <button onClick={() => onAction("rollback")} className="btn btn-ghost cursor-pointer text-xs">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                </svg>
                {t("action.rollback")}
              </button>
              <button onClick={() => handleConfirm()} className="btn btn-cta cursor-pointer text-xs">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
                {t("action.confirm") === "确认" ? "进入内容产出" : "Next"}
              </button>
            </>
          )}
        </div>
      </div>

      {previousStrategy ? (
        <CompareCards
          oldContent={previousStrategy}
          newContent={content || ""}
          loading={isLoading}
          onAcceptNew={handleAcceptNew}
          onKeepOld={handleKeepOld}
          onReviseAgain={(fb) => handleRedo(fb)}
        />
      ) : (
        <StrategyCard
          content={content}
          loading={isLoading || (streaming && !content)}
          actions={actions}
          showFeedback={!!actions}
        />
      )}
    </div>
  )
}
