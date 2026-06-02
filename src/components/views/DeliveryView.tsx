import { useState, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { t } from "../../i18n"
import type { CardData, CardType } from "../../types"
import { exportCampaignMarkdown, downloadMarkdown } from "../../utils/export"

interface DeliveryViewProps {
  cards: CardData
  onContinue: () => void
  onFinish: () => void
  isDone?: boolean
}

interface AccordionItem {
  key: CardType
  title: string
  summary: string
  content: string
}

function getItems(cards: CardData): AccordionItem[] {
  const audienceContent = (cards.audience as Record<string, unknown>)?.content as string || ""
  const brandRaw = ((cards.brand_creative as Record<string, unknown>)?.creatives as Record<string, unknown>[])?.[0]?.raw as string
    || (cards.brand_creative as Record<string, unknown>)?.raw as string || ""
  const channelRaw = ((cards.channel_plan as Record<string, unknown>)?.plan as Record<string, unknown>)?.raw as string
    || (cards.channel_plan as Record<string, unknown>)?.raw as string || ""
  const strategyContent = (cards.strategy as Record<string, unknown>)?.content as string
    || (cards.strategy as Record<string, unknown>)?.raw as string || ""
  const copyRaw = ((cards.copywriting as Record<string, unknown>)?.content as Record<string, unknown>)?.raw as string
    || (cards.copywriting as Record<string, unknown>)?.raw as string || ""

  const summarize = (text: string, maxLen = 60) => {
    if (!text) return "—"
    const first = text.replace(/[#*\n]/g, " ").trim().slice(0, maxLen)
    return first + (text.length > maxLen ? "..." : "")
  }

  return [
    { key: "audience", title: t("card.audience"), summary: summarize(audienceContent), content: audienceContent },
    { key: "brand_creative", title: t("card.brand_creative"), summary: summarize(brandRaw), content: brandRaw },
    { key: "channel_plan", title: t("card.channel_plan"), summary: summarize(channelRaw), content: channelRaw },
    { key: "strategy", title: t("card.strategy"), summary: summarize(strategyContent), content: strategyContent },
    { key: "copywriting", title: t("card.copywriting"), summary: summarize(copyRaw), content: copyRaw },
  ]
}

export default function DeliveryView({ cards, onContinue, onFinish, isDone }: DeliveryViewProps) {
  const [expanded, setExpanded] = useState<CardType | null>(null)
  const items = getItems(cards)

  const handleExport = useCallback(() => {
    const md = exportCampaignMarkdown(cards)
    downloadMarkdown(md, `campaign-${Date.now()}.md`)
  }, [cards])

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold font-[var(--font-heading)]">
          {isDone ? t("phase.done") : t("phase.delivery")}
        </h2>
        {!isDone && (
          <div className="flex gap-2">
            <button onClick={handleExport} className="btn btn-ghost cursor-pointer">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {t("action.confirm") === "确认" ? "导出方案" : "Export"}
            </button>
            <button onClick={onContinue} className="btn btn-outline cursor-pointer">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              {t("action.continue_edit")}
            </button>
            <button onClick={onFinish} className="btn btn-primary cursor-pointer">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {t("action.finish")}
            </button>
          </div>
        )}
        {isDone && (
          <button onClick={handleExport} className="btn btn-primary cursor-pointer">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {t("action.confirm") === "确认" ? "导出方案" : "Export"}
          </button>
        )}
      </div>

      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.key} className="card !p-0 overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === item.key ? null : item.key)}
              className="w-full flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-[var(--color-bg)] transition-colors text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <svg
                  className={`w-4 h-4 text-[var(--color-text-muted)] transition-transform duration-200 flex-shrink-0 ${expanded === item.key ? "rotate-90" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                <span className="font-semibold text-sm font-[var(--font-heading)]">{item.title}</span>
                {expanded !== item.key && (
                  <span className="text-xs text-[var(--color-text-muted)] truncate">{item.summary}</span>
                )}
              </div>
              <svg className="w-4 h-4 text-[var(--color-success)] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </button>

            {expanded === item.key && (
              <div className="px-5 pb-4 pt-0 border-t border-[var(--color-border)] animate-fade-in">
                <div className="card-content text-sm mt-3">
                  {item.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                      {item.content}
                    </ReactMarkdown>
                  ) : (
                    <p className="text-[var(--color-text-muted)] italic">—</p>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
