import { useState, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { t } from "../../i18n"
import type { CardData, AgentId, CardType } from "../../types"

interface FinalizeViewProps {
  cards: CardData
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  finalDocument: string
  onGenerateDocument: () => void
  onEditDocument: (feedback: string) => void
  onGoBackToContent: () => void
  onGoBackToOverview: () => void
  onExportCards: () => void
  onExportDocument: () => void
}

interface AccordionItem {
  key: CardType
  title: string
  summary: string
  content: string
}

function getItems(cards: CardData): AccordionItem[] {
  const getRaw = (data: unknown): string => {
    if (!data) return ""
    const d = data as Record<string, unknown>
    // 直接 raw 字段
    if (typeof d.raw === "string") return d.raw
    // content 字段（可能是 string 或 {raw: string}）
    if (d.content) {
      if (typeof d.content === "string") return d.content
      if (typeof d.content === "object" && (d.content as Record<string, unknown>).raw) {
        return (d.content as Record<string, unknown>).raw as string
      }
    }
    // creatives 数组
    if (Array.isArray(d.creatives) && d.creatives[0]?.raw) {
      return d.creatives[0].raw as string
    }
    // plan 嵌套
    if (d.plan && typeof d.plan === "object") {
      return (d.plan as Record<string, unknown>).raw as string || ""
    }
    return ""
  }
  const summarize = (text: string, maxLen = 60) => {
    if (!text) return "—"
    return text.replace(/[#*\n]/g, " ").trim().slice(0, maxLen) + (text.length > maxLen ? "..." : "")
  }
  return [
    { key: "audience", title: t("card.audience"), summary: summarize(getRaw(cards.audience)), content: getRaw(cards.audience) },
    { key: "brand_creative", title: t("card.brand_creative"), summary: summarize(getRaw(cards.brand_creative)), content: getRaw(cards.brand_creative) },
    { key: "channel_plan", title: t("card.channel_plan"), summary: summarize(getRaw(cards.channel_plan)), content: getRaw(cards.channel_plan) },
    { key: "strategy", title: t("card.strategy"), summary: summarize(getRaw(cards.strategy)), content: getRaw(cards.strategy) },
    { key: "copywriting", title: t("card.copywriting"), summary: summarize(getRaw(cards.copywriting)), content: getRaw(cards.copywriting) },
  ]
}

function extractHeadings(md: string): { level: number; text: string; id: string }[] {
  const headings: { level: number; text: string; id: string }[] = []
  for (const line of md.split("\n")) {
    const match = line.match(/^(#{1,3})\s+(.+)/)
    if (match) {
      const text = match[2].replace(/\*\*/g, "").trim()
      const id = text.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "")
      headings.push({ level: match[1].length, text, id })
    }
  }
  return headings
}

export default function FinalizeView({
  cards, streaming, activeAgents, finalDocument,
  onGenerateDocument, onEditDocument, onGoBackToContent, onGoBackToOverview, onExportCards, onExportDocument,
}: FinalizeViewProps) {
  const [expanded, setExpanded] = useState<CardType | null>(null)
  const [feedback, setFeedback] = useState("")
  const [waitingForDocument, setWaitingForDocument] = useState(false)
  const items = getItems(cards)
  const isGenerating = activeAgents.some((a) => a.agent === "chief_strategist")
  const zh = t("action.confirm") === "确认"

  // Clear waitingForDocument once content starts arriving or streaming ends
  if (waitingForDocument && (finalDocument || (!streaming && !isGenerating))) {
    setWaitingForDocument(false)
  }

  const handleEditSubmit = useCallback(() => {
    if (!feedback.trim()) return
    setWaitingForDocument(true)
    onEditDocument(feedback.trim())
    setFeedback("")
  }, [feedback, onEditDocument])

  // ═══════════════════════════════════════════════════════════
  // 方案调整阶段：完整方案文档 + 右侧目录 + 修改输入
  // ═══════════════════════════════════════════════════════════
  if (finalDocument || isGenerating || waitingForDocument) {
    const headings = extractHeadings(finalDocument)

    return (
      <div className="max-w-5xl mx-auto">
        <div className="sticky -top-4 z-10 bg-[var(--color-bg)] pt-4 pb-2 -mx-6 px-6 flex items-center justify-between mb-4 border-b border-[var(--color-border)]">
          <div>
            <h2 className="text-lg font-semibold font-[var(--font-heading)]">
              {zh ? "方案调整" : "Plan Refinement"}
            </h2>
            <p className="text-xs text-[var(--color-text-muted)]">
              {zh ? "基于完整方案进行修改" : "Edit the final plan document"}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={onGoBackToOverview} disabled={streaming} className="btn btn-ghost cursor-pointer text-xs disabled:opacity-40 disabled:cursor-not-allowed">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
              </svg>
              {zh ? "返回方案总览" : "Back to overview"}
            </button>
            <button onClick={onExportDocument} disabled={streaming} className="btn btn-primary cursor-pointer text-xs disabled:opacity-40 disabled:cursor-not-allowed">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {zh ? "导出完整方案" : "Export Plan"}
            </button>
          </div>
        </div>

        <div className="flex gap-6">
          {/* 左侧：文档内容 */}
          <div className="flex-1 min-w-0">
            <div className="card overflow-hidden">
              <div className="card-content text-sm overflow-x-auto">
                {finalDocument ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkBreaks]}
                    components={{
                      h1: ({ children }) => {
                        const id = String(children).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "")
                        return <h1 id={id}>{children}</h1>
                      },
                      h2: ({ children }) => {
                        const id = String(children).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "")
                        return <h2 id={id}>{children}</h2>
                      },
                      h3: ({ children }) => {
                        const id = String(children).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-").replace(/^-|-$/g, "")
                        return <h3 id={id}>{children}</h3>
                      },
                    }}
                  >
                    {finalDocument}
                  </ReactMarkdown>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 gap-3 w-full">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
                      <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.2s" }} />
                      <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.4s" }} />
                    </div>
                    <p className="text-sm text-[var(--color-text-muted)]">
                      {zh ? "\u6b63\u5728\u751f\u6210\u65b9\u6848..." : "Generating plan..."}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* 修改输入 */}
            <div className="mt-4 flex gap-2">
              <input
                type="text"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleEditSubmit()}
                placeholder={zh ? "对方案提出修改意见..." : "Suggest changes..."}
                disabled={streaming}
                className="flex-1 px-4 py-3 border border-[var(--color-border)] rounded-[var(--radius-sm)] text-sm outline-none focus:border-[var(--color-primary)] transition-colors"
              />
              <button
                onClick={handleEditSubmit}
                disabled={streaming || !feedback.trim()}
                className="btn btn-cta cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot" />
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
                  </div>
                ) : (zh ? "修改" : "Revise")}
              </button>
            </div>
          </div>

          {/* 右侧：目录导航（始终占位保持宽度一致） */}
          <nav className="hidden lg:block w-48 flex-shrink-0">
            {headings.length > 0 && (
              <div className="sticky top-16">
                <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">
                  {zh ? "目录" : "Contents"}
                </p>
                <ul className="space-y-1 text-xs">
                  {headings.map((h, idx) => (
                    <li key={idx} style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>
                      <a
                        href={`#${h.id}`}
                        onClick={(e) => {
                          e.preventDefault()
                          document.getElementById(h.id)?.scrollIntoView({ behavior: "smooth", block: "start" })
                        }}
                        className="block py-0.5 text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors truncate cursor-pointer"
                      >
                        {h.text}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </nav>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════
  // 方案总览阶段：手风琴查看各模块 + 操作按钮
  // ═══════════════════════════════════════════════════════════
  return (
    <div className="max-w-3xl mx-auto">
      <div className="sticky -top-4 z-10 bg-[var(--color-bg)] pt-4 pb-2 -mx-6 px-6 flex items-center justify-between mb-4 border-b border-[var(--color-border)]">
        <div>
          <h2 className="text-lg font-semibold font-[var(--font-heading)]">
            {zh ? "方案总览" : "Plan Overview"}
          </h2>
          <p className="text-xs text-[var(--color-text-muted)]">
            {zh ? "确认各模块内容后生成完整方案" : "Review modules, then generate full plan"}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={onGoBackToContent} disabled={streaming} className="btn btn-ghost cursor-pointer text-xs disabled:opacity-40 disabled:cursor-not-allowed">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
            </svg>
            {zh ? "返回修改" : "Go back"}
          </button>
          <button onClick={onExportCards} className="btn btn-outline cursor-pointer text-xs">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {zh ? "导出" : "Export"}
          </button>
          <button
            onClick={() => { setWaitingForDocument(true); onGenerateDocument() }}
            disabled={streaming}
            className="btn btn-cta cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            {zh ? "生成完整方案" : "Generate Plan"}
          </button>
        </div>
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
                <span className="font-semibold text-sm">{item.title}</span>
                {expanded !== item.key && (
                  <span className="text-xs text-[var(--color-text-muted)] truncate">{item.summary}</span>
                )}
              </div>
              <svg className="w-4 h-4 text-[var(--color-success)] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </button>
            {expanded === item.key && (
              <div className="px-5 pb-4 border-t border-[var(--color-border)] animate-fade-in">
                <div className="card-content text-sm mt-3">
                  {item.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{item.content}</ReactMarkdown>
                  ) : <p className="text-[var(--color-text-muted)]">—</p>}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {isGenerating && (
        <div className="mt-4 card animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="text-sm text-[var(--color-text-muted)]">{zh ? "策略总监正在整合生成完整方案..." : "Generating full plan..."}</span>
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
