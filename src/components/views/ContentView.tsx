import { useState, useCallback } from "react"
import { t } from "../../i18n"
import type { CardData, AgentId } from "../../types"
import CopywritingCard from "../cards/CopywritingCard"
import CompareCards from "../cards/CompareCards"

interface ContentViewProps {
  cards: CardData
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  onAction: (type: "confirm" | "redo" | "rollback" | "keep_old", feedback?: string) => void
}

export default function ContentView({ cards, streaming, activeAgents, onAction }: ContentViewProps) {
  const isLoading = activeAgents.some((a) => a.agent === "copywriter")
  const [previousCopy, setPreviousCopy] = useState<string | null>(null)

  const raw = (cards.copywriting as Record<string, unknown>)?.raw as string | undefined
    || ((cards.copywriting as Record<string, unknown>)?.content as Record<string, unknown>)?.raw as string | undefined
    || null

  const handleRedo = useCallback((feedback?: string) => {
    if (raw) setPreviousCopy(raw)
    onAction("redo", feedback)
  }, [onAction, raw])

  const handleConfirm = useCallback((feedback?: string) => {
    setPreviousCopy(null)
    onAction("confirm", feedback)
  }, [onAction])

  const handleKeepOld = useCallback(() => {
    if (previousCopy) {
      onAction("keep_old", previousCopy)
    }
    setPreviousCopy(null)
  }, [previousCopy, onAction])

  const actions = !isLoading && !streaming && !previousCopy && cards.copywriting ? [
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
        {t("phase.content")}
      </h2>

      {previousCopy ? (
        <CompareCards
          oldContent={previousCopy}
          newContent={raw || ""}
          loading={isLoading}
          onAcceptNew={() => handleConfirm()}
          onKeepOld={handleKeepOld}
          onReviseAgain={(fb) => handleRedo(fb)}
        />
      ) : (
        <CopywritingCard
          data={cards.copywriting}
          loading={isLoading || (streaming && !cards.copywriting)}
          actions={actions}
          showFeedback={!!actions}
        />
      )}
    </div>
  )
}
