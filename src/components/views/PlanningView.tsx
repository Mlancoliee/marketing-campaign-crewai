import { useState, useCallback, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { t } from "../../i18n"
import type { CardData, AgentId } from "../../types"
import CompareCards from "../cards/CompareCards"

interface PlanningViewProps {
  cards: CardData
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  parallelActive: boolean
  onCardAction: (target: "brand" | "channel", type: "confirm" | "redo" | "keep_old", options?: { selected_index?: number; feedback?: string; previous_data?: Record<string, unknown> }) => void
  onRestoreCard?: (card: "brand_creative" | "channel_plan", data: Record<string, unknown>) => void
  onNext: () => void
}

type PlanningTab = "brand" | "channel"

export default function PlanningView({ cards, streaming, activeAgents, onCardAction, onRestoreCard, onNext }: PlanningViewProps) {
  const [activeTab, setActiveTab] = useState<PlanningTab>("brand")
  const [previousBrand, setPreviousBrand] = useState<Record<string, unknown> | null>(null)
  const [previousChannel, setPreviousChannel] = useState<Record<string, unknown> | null>(null)

  const brandLoading = activeAgents.some((a) => a.agent === "brand_creative_director")
  const channelLoading = activeAgents.some((a) => a.agent === "channel_planner")

  const brandData = cards.brand_creative as Record<string, unknown> | null
  const channelData = cards.channel_plan as Record<string, unknown> | null

  // 流式输出时自动切到正在生成的 tab
  useEffect(() => {
    if (brandLoading) setActiveTab("brand")
    else if (channelLoading) setActiveTab("channel")
  }, [brandLoading, channelLoading])

  // 品牌创意完成后自动切到渠道
  useEffect(() => {
    if (!brandLoading && channelLoading) {
      setActiveTab("channel")
    }
  }, [brandLoading, channelLoading])

  const getRaw = (data: Record<string, unknown> | null, type: "brand" | "channel") => {
    if (!data) return ""
    if (type === "brand") {
      const creatives = data.creatives as Record<string, unknown>[] | undefined
      return creatives?.[0]?.raw as string || data.raw as string || ""
    }
    const plan = data.plan as Record<string, unknown> | undefined
    return plan?.raw as string || data.raw as string || ""
  }

  const handleRedo = useCallback((feedback?: string) => {
    if (activeTab === "brand") {
      if (brandData) setPreviousBrand(brandData)
      onCardAction("brand", "redo", { feedback })
    } else {
      if (channelData) setPreviousChannel(channelData)
      onCardAction("channel", "redo", { feedback })
    }
  }, [activeTab, brandData, channelData, onCardAction])

  const handleKeepOld = useCallback(() => {
    if (activeTab === "brand" && previousBrand) {
      if (onRestoreCard) onRestoreCard("brand_creative", previousBrand)
      onCardAction("brand", "keep_old", { previous_data: previousBrand })
      setPreviousBrand(null)
    } else if (activeTab === "channel" && previousChannel) {
      if (onRestoreCard) onRestoreCard("channel_plan", previousChannel)
      onCardAction("channel", "keep_old", { previous_data: previousChannel })
      setPreviousChannel(null)
    }
  }, [activeTab, previousBrand, previousChannel, onRestoreCard, onCardAction])

  const handleAcceptNew = useCallback(() => {
    if (activeTab === "brand") setPreviousBrand(null)
    else setPreviousChannel(null)
  }, [activeTab])

  const isLoading = brandLoading || channelLoading || streaming
  const hasContent = !!brandData && !!channelData
  const currentPrevious = activeTab === "brand" ? previousBrand : previousChannel
  const currentData = activeTab === "brand" ? brandData : channelData
  const currentRaw = getRaw(currentData, activeTab)
  const currentLoading = activeTab === "brand" ? brandLoading : channelLoading

  const zh = t("action.confirm") === "确认"

  return (
    <div className="max-w-3xl mx-auto">
      {/* Sticky 头部：标题 + Tab + 导航按钮 */}
      <div className="sticky -top-4 z-10 bg-[var(--color-bg)] pt-4 -mx-6 px-6 mb-4">
        <div className="flex items-center justify-between pb-2">
          <h2 className="text-lg font-semibold font-[var(--font-heading)]">
            {t("phase.planning")}
          </h2>
          <div className="flex gap-2">
            {hasContent && !isLoading && !previousBrand && !previousChannel && (
              <button onClick={onNext} className="btn btn-cta cursor-pointer text-xs">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
                {zh ? "进入策略整合" : "Next"}
              </button>
            )}
          </div>
        </div>
        {/* Tab 切换 */}
        <div className="flex border-b border-[var(--color-border)]">
        <div className="flex">
          <button
            onClick={() => setActiveTab("brand")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 cursor-pointer transition-colors flex items-center gap-1.5 ${
              activeTab === "brand"
                ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            {t("card.brand_creative")}
            {brandLoading && <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />}
            {brandData && !brandLoading && <svg className="w-3.5 h-3.5 text-[var(--color-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
          </button>
          <button
            onClick={() => setActiveTab("channel")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 cursor-pointer transition-colors flex items-center gap-1.5 ${
              activeTab === "channel"
                ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            {t("card.channel_plan")}
            {channelLoading && <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />}
            {channelData && !channelLoading && <svg className="w-3.5 h-3.5 text-[var(--color-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
          </button>
        </div>
        </div>
      </div>

      {/* Tab 内容 */}
      {currentPrevious ? (
        <CompareCards
          oldContent={getRaw(currentPrevious, activeTab)}
          newContent={currentRaw}
          loading={currentLoading}
          onAcceptNew={handleAcceptNew}
          onKeepOld={handleKeepOld}
          onReviseAgain={(fb) => handleRedo(fb)}
        />
      ) : (
        <div className="card animate-fade-in">
          {currentLoading && !currentRaw ? (
            <div className="flex items-center gap-2 py-8 justify-center">
              <span className="text-sm text-[var(--color-text-muted)]">{zh ? "生成中..." : "Generating..."}</span>
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
              </div>
            </div>
          ) : currentRaw ? (
            <div className="card-content text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                {currentRaw}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="text-[var(--color-text-muted)] text-sm text-center py-8">
              {zh ? "等待生成..." : "Waiting..."}
            </p>
          )}

          {/* 重做按钮（内嵌在卡片底部） */}
          {!isLoading && currentRaw && !currentPrevious && (
            <div className="mt-4 pt-3 border-t border-[var(--color-border)]">
              <RedobBar onRedo={handleRedo} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** 内嵌重做输入框 */
function RedobBar({ onRedo }: { onRedo: (feedback?: string) => void }) {
  const [feedback, setFeedback] = useState("")
  const zh = t("action.confirm") === "确认"

  return (
    <div className="flex gap-2">
      <input
        type="text"
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && feedback.trim()) { onRedo(feedback.trim()); setFeedback("") } }}
        placeholder={zh ? "给修改意见（可选）..." : "Feedback (optional)..."}
        className="flex-1 px-3 py-2 text-sm border border-[var(--color-border)] rounded-[var(--radius-sm)] outline-none focus:border-[var(--color-primary)] transition-colors"
      />
      <button
        onClick={() => { onRedo(feedback.trim() || undefined); setFeedback("") }}
        className="btn btn-outline cursor-pointer"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {t("action.redo")}
      </button>
    </div>
  )
}
