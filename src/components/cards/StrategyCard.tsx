import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import BaseCard from "./BaseCard"
import { t } from "../../i18n"

interface StrategyCardProps {
  content: string | null
  loading?: boolean
  actions?: {
    label: string
    type: "confirm" | "redo" | "rollback"
    onClick: (feedback?: string) => void
  }[]
  showFeedback?: boolean
}

export default function StrategyCard({ content, loading, actions, showFeedback }: StrategyCardProps) {
  return (
    <BaseCard
      title={t("card.strategy")}
      agent="chief_strategist"
      loading={loading}
      actions={actions}
      showFeedback={showFeedback}
    >
      {content ? (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {content}
        </ReactMarkdown>
      ) : (
        <p className="text-[var(--color-text-muted)] italic">
          {loading ? t("status.generating") : "—"}
        </p>
      )}
    </BaseCard>
  )
}
