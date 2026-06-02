import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import BaseCard from "./BaseCard"
import { t } from "../../i18n"

interface BrandCreativeCardProps {
  data: { creatives: Record<string, unknown>[] } | null
  loading?: boolean
  actions?: {
    label: string
    type: "confirm" | "redo" | "rollback"
    onClick: (feedback?: string) => void
  }[]
  showFeedback?: boolean
}

export default function BrandCreativeCard({ data, loading, actions, showFeedback }: BrandCreativeCardProps) {
  const [activeTab, setActiveTab] = useState(0)

  const creatives = data?.creatives || []
  const raw = (data as Record<string, unknown>)?.raw as string | undefined

  return (
    <BaseCard
      title={t("card.brand_creative")}
      agent="brand_creative_director"
      loading={loading}
      actions={actions}
      showFeedback={showFeedback}
    >
      {creatives.length > 1 && (
        <div className="flex gap-1 mb-3 border-b border-[var(--color-border)]">
          {creatives.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTab(idx)}
              className={`px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer border-b-2 ${
                activeTab === idx
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {t("action.confirm")} {idx + 1}
            </button>
          ))}
        </div>
      )}

      {raw ? (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {raw}
        </ReactMarkdown>
      ) : creatives.length > 0 ? (
        <div className="space-y-2">
          <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
            {String(creatives[activeTab]?.raw || JSON.stringify(creatives[activeTab], null, 2))}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="text-[var(--color-text-muted)] italic">
          {loading ? t("status.generating") : "—"}
        </p>
      )}
    </BaseCard>
  )
}
