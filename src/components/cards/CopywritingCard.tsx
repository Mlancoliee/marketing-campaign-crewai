import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import BaseCard from "./BaseCard"
import { t } from "../../i18n"

interface CopywritingCardProps {
  data: { content: Record<string, unknown> } | null
  loading?: boolean
  actions?: {
    label: string
    type: "confirm" | "redo" | "rollback"
    onClick: (feedback?: string) => void
  }[]
  showFeedback?: boolean
}

export default function CopywritingCard({ data, loading, actions, showFeedback }: CopywritingCardProps) {
  // data 可能是 {raw: "..."} 或 {content: {raw: "..."}} 或 {content: {headline, body, cta}}
  const raw = (data as Record<string, unknown>)?.raw as string | undefined
    || ((data?.content as Record<string, unknown>)?.raw as string | undefined)

  return (
    <BaseCard
      title={t("card.copywriting")}
      agent="copywriter"
      loading={loading}
      actions={actions}
      showFeedback={showFeedback}
    >
      {raw ? (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {raw}
        </ReactMarkdown>
      ) : data?.content ? (
        (() => {
          const c = data.content as Record<string, unknown>
          return (
            <div className="space-y-3">
              {c.headline ? (
                <div>
                  <span className="text-xs font-semibold text-[var(--color-primary)] uppercase tracking-wide">Headline</span>
                  <p className="text-lg font-bold mt-0.5">{String(c.headline)}</p>
                </div>
              ) : null}
              {c.body ? (
                <div>
                  <span className="text-xs font-semibold text-[var(--color-primary)] uppercase tracking-wide">Body</span>
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                    {String(c.body)}
                  </ReactMarkdown>
                </div>
              ) : null}
              {c.cta ? (
                <div>
                  <span className="text-xs font-semibold text-[var(--color-primary)] uppercase tracking-wide">CTA</span>
                  <p className="font-semibold text-[var(--color-cta)] mt-0.5">{String(c.cta)}</p>
                </div>
              ) : null}
            </div>
          )
        })()
      ) : (
        <p className="text-[var(--color-text-muted)] italic">
          {loading ? t("status.generating") : "—"}
        </p>
      )}
    </BaseCard>
  )
}
