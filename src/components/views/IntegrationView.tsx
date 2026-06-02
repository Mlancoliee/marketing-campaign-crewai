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

  const handleKeepOld = useCallback(() => {
    if (previousStrategy) {
      onAction("keep_old", previousStrategy)
    }
    setPreviousStrategy(null)
  }, [previousStrategy, onAction])

  const actions = !isLoading && !streaming && !previousStrategy && content ? [
    {
      label: t("action.confirm"),
      type: "confirm" as const,
      onClick: (feedback?: string) => handleConfirm(feedback),
    },
    {
      label: t("action.redo"),
      type: "redo" as const,
      onClick: (feedback?: string) => handleRedo(feedback),
    },
    {
      label: t("action.rollback"),
      type: "rollback" as const,
      onClick: () => onAction("rollback"),
    },
  ] : undefined

  return (
    <div className="max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold font-[var(--font-heading)] mb-4">
        {t("phase.integration")}
      </h2>

      {previousStrategy ? (
        <CompareCards
          oldContent={previousStrategy}
          newContent={content || ""}
          loading={isLoading}
          onAcceptNew={() => handleConfirm()}
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
