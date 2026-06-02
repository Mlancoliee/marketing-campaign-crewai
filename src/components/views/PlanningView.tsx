import { useRef, useCallback, useState } from "react"
import { t } from "../../i18n"
import type { CardData, AgentId } from "../../types"
import BrandCreativeCard from "../cards/BrandCreativeCard"
import ChannelPlanCard from "../cards/ChannelPlanCard"
import CompareCards from "../cards/CompareCards"

interface PlanningViewProps {
  cards: CardData
  streaming: boolean
  activeAgents: { agent: AgentId; lane?: string }[]
  parallelActive: boolean
  onCardAction: (target: "brand" | "channel", type: "confirm" | "redo" | "keep_old", options?: { selected_index?: number; feedback?: string; previous_data?: Record<string, unknown> }) => void
  onRestoreCard?: (card: "brand_creative" | "channel_plan", data: Record<string, unknown>) => void
}

export default function PlanningView({ cards, streaming, activeAgents, onCardAction, onRestoreCard }: PlanningViewProps) {
  const channelRef = useRef<HTMLDivElement>(null)
  const brandRef = useRef<HTMLDivElement>(null)
  const [brandConfirmed, setBrandConfirmed] = useState(false)
  const [channelConfirmed, setChannelConfirmed] = useState(false)
  const [previousBrand, setPreviousBrand] = useState<Record<string, unknown> | null>(null)
  const [previousChannel, setPreviousChannel] = useState<Record<string, unknown> | null>(null)
  const [activeNav, setActiveNav] = useState<"brand" | "channel">("brand")

  const brandLoading = activeAgents.some((a) => a.agent === "brand_creative_director")
  const channelLoading = activeAgents.some((a) => a.agent === "channel_planner")

  const brandData = cards.brand_creative as Record<string, unknown> | null
  const channelData = cards.channel_plan as Record<string, unknown> | null

  const handleBrandConfirm = useCallback((feedback?: string) => {
    setBrandConfirmed(true)
    setPreviousBrand(null)
    onCardAction("brand", "confirm", { selected_index: 0, feedback })
    if (!channelConfirmed) {
      setActiveNav("channel")
      setTimeout(() => channelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 300)
    }
  }, [onCardAction, channelConfirmed])

  const handleBrandRedo = useCallback((feedback?: string) => {
    if (brandData) setPreviousBrand(brandData)
    onCardAction("brand", "redo", { feedback })
    // 保持在品牌卡片位置
    setTimeout(() => brandRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100)
  }, [onCardAction, brandData])

  const handleBrandKeepOld = useCallback(() => {
    if (previousBrand) {
      if (onRestoreCard) onRestoreCard("brand_creative", previousBrand)
      // 通知后端恢复旧数据
      onCardAction("brand", "keep_old", { previous_data: previousBrand })
    }
    setPreviousBrand(null)
  }, [previousBrand, onRestoreCard, onCardAction])

  const handleChannelConfirm = useCallback((feedback?: string) => {
    setChannelConfirmed(true)
    setPreviousChannel(null)
    onCardAction("channel", "confirm", { feedback })
    if (!brandConfirmed) {
      setTimeout(() => brandRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 300)
    }
  }, [onCardAction, brandConfirmed])

  const handleChannelRedo = useCallback((feedback?: string) => {
    if (channelData) setPreviousChannel(channelData)
    onCardAction("channel", "redo", { feedback })
  }, [onCardAction, channelData])

  const handleChannelKeepOld = useCallback(() => {
    if (previousChannel) {
      if (onRestoreCard) onRestoreCard("channel_plan", previousChannel)
      onCardAction("channel", "keep_old", { previous_data: previousChannel })
    }
    setPreviousChannel(null)
  }, [previousChannel, onRestoreCard, onCardAction])

  const getBrandRaw = (data: Record<string, unknown> | null) => {
    if (!data) return ""
    const creatives = data.creatives as Record<string, unknown>[] | undefined
    return creatives?.[0]?.raw as string || data.raw as string || ""
  }
  const getChannelRaw = (data: Record<string, unknown> | null) => {
    if (!data) return ""
    const plan = data.plan as Record<string, unknown> | undefined
    return plan?.raw as string || data.raw as string || ""
  }

  // 目录导航
  const scrollTo = (ref: React.RefObject<HTMLDivElement | null>) => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="sticky -top-4 z-10 bg-[var(--color-bg)] pt-4 pb-2 -mx-6 px-6 flex items-center justify-between mb-4 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold font-[var(--font-heading)]">
          {t("phase.planning")}
        </h2>
        {/* 目录导航 */}
        <nav className="flex gap-3 text-xs">
          <button
            onClick={() => { scrollTo(brandRef); setActiveNav("brand") }}
            className={`cursor-pointer transition-colors ${
              brandConfirmed ? "text-[var(--color-success)]"
              : activeNav === "brand" ? "text-[var(--color-primary)] font-medium"
              : "text-[var(--color-text-muted)]"
            }`}
          >
            {brandConfirmed && "✓ "}{t("card.brand_creative")}
          </button>
          <span className="text-[var(--color-border)]">|</span>
          <button
            onClick={() => { scrollTo(channelRef); setActiveNav("channel") }}
            className={`cursor-pointer transition-colors ${
              channelConfirmed ? "text-[var(--color-success)]"
              : activeNav === "channel" ? "text-[var(--color-primary)] font-medium"
              : "text-[var(--color-text-muted)]"
            }`}
          >
            {channelConfirmed && "✓ "}{t("card.channel_plan")}
          </button>
        </nav>
      </div>

      <div className="space-y-6">
        {/* 品牌创意 */}
        <div ref={brandRef} className={`transition-all duration-500 ease-out ${brandConfirmed ? "opacity-50 scale-[0.98]" : ""}`}>
          {brandConfirmed && (
            <div className="flex items-center gap-2 mb-2 text-[var(--color-success)] text-sm font-medium animate-fade-in">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {t("card.brand_creative")} — {t("action.confirm")}
            </div>
          )}

          {/* 对比模式：并排卡片 + 动画 */}
          {previousBrand ? (
            <CompareCards
              oldContent={getBrandRaw(previousBrand)}
              newContent={getBrandRaw(brandData)}
              loading={brandLoading}
              onAcceptNew={() => handleBrandConfirm()}
              onKeepOld={handleBrandKeepOld}
              onReviseAgain={(fb) => handleBrandRedo(fb)}
            />
          ) : (
            <BrandCreativeCard
              data={cards.brand_creative}
              loading={brandLoading || (streaming && !cards.brand_creative)}
              actions={!brandLoading && !brandConfirmed && !streaming && cards.brand_creative ? [
                { label: t("action.confirm"), type: "confirm" as const, onClick: handleBrandConfirm },
                { label: t("action.redo"), type: "redo" as const, onClick: handleBrandRedo },
              ] : undefined}
              showFeedback={!brandLoading && !brandConfirmed && !streaming && !!cards.brand_creative}
            />
          )}
        </div>

        {/* 渠道策略 */}
        <div ref={channelRef} className={`transition-all duration-500 ease-out ${channelConfirmed ? "opacity-50 scale-[0.98]" : ""}`}>
          {channelConfirmed && (
            <div className="flex items-center gap-2 mb-2 text-[var(--color-success)] text-sm font-medium animate-fade-in">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {t("card.channel_plan")} — {t("action.confirm")}
            </div>
          )}

          {previousChannel ? (
            <CompareCards
              oldContent={getChannelRaw(previousChannel)}
              newContent={getChannelRaw(channelData)}
              loading={channelLoading}
              onAcceptNew={() => handleChannelConfirm()}
              onKeepOld={handleChannelKeepOld}
              onReviseAgain={(fb) => handleChannelRedo(fb)}
            />
          ) : (
            <ChannelPlanCard
              data={cards.channel_plan}
              loading={channelLoading || (streaming && !cards.channel_plan)}
              actions={!channelLoading && !channelConfirmed && !streaming && cards.channel_plan ? [
                { label: t("action.confirm"), type: "confirm" as const, onClick: handleChannelConfirm },
                { label: t("action.redo"), type: "redo" as const, onClick: handleChannelRedo },
              ] : undefined}
              showFeedback={!channelLoading && !channelConfirmed && !streaming && !!cards.channel_plan}
            />
          )}
        </div>
      </div>
    </div>
  )
}
