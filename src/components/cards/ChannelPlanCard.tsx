import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import BaseCard from "./BaseCard"
import { t } from "../../i18n"

interface ChannelPlanCardProps {
  data: { plan: Record<string, unknown> } | null
  loading?: boolean
  actions?: {
    label: string
    type: "confirm" | "redo" | "rollback"
    onClick: (feedback?: string) => void
  }[]
  showFeedback?: boolean
}

export default function ChannelPlanCard({ data, loading, actions, showFeedback }: ChannelPlanCardProps) {
  const raw = (data as Record<string, unknown>)?.raw as string | undefined
  const plan = data?.plan

  return (
    <BaseCard
      title={t("card.channel_plan")}
      agent="channel_planner"
      loading={loading}
      actions={actions}
      showFeedback={showFeedback}
    >
      {raw ? (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {raw}
        </ReactMarkdown>
      ) : plan ? (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {String((plan as Record<string, unknown>).raw || JSON.stringify(plan, null, 2))}
        </ReactMarkdown>
      ) : (
        <p className="text-[var(--color-text-muted)] italic">
          {loading ? t("status.generating") : "—"}
        </p>
      )}
    </BaseCard>
  )
}
