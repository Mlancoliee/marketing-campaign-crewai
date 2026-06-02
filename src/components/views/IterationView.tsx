import { useState, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { t } from "../../i18n"
import type { CardData, AgentId, CardType } from "../../types"

interface IterationViewProps {
  cards: CardData
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  onFinish: () => void
  onIterationFeedback?: (feedback: string) => void
}

interface AccordionItem {
  key: CardType
  title: string
  summary: string
  content: string
  agent: AgentId
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
    { key: "audience", title: t("card.audience"), summary: summarize(audienceContent), content: audienceContent, agent: "market_analyst" },
    { key: "brand_creative", title: t("card.brand_creative"), summary: summarize(brandRaw), content: brandRaw, agent: "brand_creative_director" },
    { key: "channel_plan", title: t("card.channel_plan"), summary: summarize(channelRaw), content: channelRaw, agent: "channel_planner" },
    { key: "strategy", title: t("card.strategy"), summary: summarize(strategyContent), content: strategyContent, agent: "chief_strategist" },
    { key: "copywriting", title: t("card.copywriting"), summary: summarize(copyRaw), content: copyRaw, agent: "copywriter" },
  ]
}

export default function IterationView({ cards, streaming, activeAgents, onFinish, onIterationFeedback }: IterationViewProps) {
  const [expanded, setExpanded] = useState<CardType | null>(null)
  const [feedback, setFeedback] = useState("")
  const items = getItems(cards)

  const isCardLoading = (agent: AgentId) => activeAgents.some((a) => a.agent === agent)

  const handleSendFeedback = useCallback(() => {
    if (!feedback.trim() || !onIterationFeedback) return
    onIterationFeedback(feedback.trim())
    setFeedback("")
  }, [feedback, onIterationFeedback])

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold font-[var(--font-heading)]">
          {t("phase.iteration")}
        </h2>
        <button onClick={onFinish} disabled={streaming} className="btn btn-primary cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          {t("action.finish")}
        </button>
      </div>

      <div className="space-y-2">
        {items.map((item) => {
          const loading = isCardLoading(item.agent)
          const isExpanded = expanded === item.key

          return (
            <div key={item.key} className={`card !p-0 overflow-hidden transition-all ${loading ? "ring-2 ring-[var(--color-primary)]/30" : ""}`}>
              <button
                onClick={() => setExpanded(isExpanded ? null : item.key)}
                className="w-full flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-[var(--color-bg)] transition-colors text-left"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <svg
                    className={`w-4 h-4 text-[var(--color-text-muted)] transition-transform duration-200 flex-shrink-0 ${isExpanded ? "rotate-90" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="font-semibold text-sm font-[var(--font-heading)]">{item.title}</span>
                  {!isExpanded && (
                    <span className="text-xs text-[var(--color-text-muted)] truncate">{item.summary}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {loading && (
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
                    </div>
                  )}
                  {!loading && (
                    <svg className="w-4 h-4 text-[var(--color-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </button>

              {isExpanded && (
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

                  {/* 内嵌修改输入框 */}
                  {onIterationFeedback && !loading && (
                    <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex gap-2">
                      <input
                        type="text"
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSendFeedback()}
                        placeholder={t("input.feedback_placeholder")}
                        disabled={streaming}
                        className="flex-1 px-3 py-2 text-sm border border-[var(--color-border)] rounded-[var(--radius-sm)] outline-none focus:border-[var(--color-primary)] transition-colors"
                      />
                      <button
                        onClick={handleSendFeedback}
                        disabled={streaming || !feedback.trim()}
                        className="btn btn-cta disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                      >
                        {t("action.redo")}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
