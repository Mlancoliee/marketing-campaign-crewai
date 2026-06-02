import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import BaseCard from "./BaseCard"
import { t } from "../../i18n"

interface AudienceCardProps {
  content: string
  loading?: boolean
}

export default function AudienceCard({ content, loading }: AudienceCardProps) {
  return (
    <BaseCard
      title={t("card.audience")}
      agent="market_analyst"
      loading={loading}
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
