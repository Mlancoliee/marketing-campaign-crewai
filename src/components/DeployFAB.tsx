import { useState, useEffect } from "react"
import { getLocale } from "../i18n"

/**
 * One-click deploy floating action button.
 * Syncs with template locale and theme colors.
 */
export default function DeployFAB() {
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    // Show after 2s delay (same as reference template)
    const timer = setTimeout(() => setVisible(true), 2000)
    return () => clearTimeout(timer)
  }, [])

  if (dismissed || !visible) return null

  const zh = getLocale() === "zh"

  const handleDeploy = () => {
    const hostname = window.location.hostname
    const parts = hostname.split(".")
    const projectName = 'crewai-marketing-campaign'
    const domain = parts.slice(1).join(".")

    if (domain === "edgeone.app") {
      window.open(`https://edgeone.ai/makers/new?template=${projectName}&from=github`, "_blank")
    } else {
      window.open(`https://console.cloud.tencent.com/edgeone/makers/new?from=github&template=${projectName}`, "_blank")
    }
  }

  return (
    <div
      className="fixed z-[9999] right-5 bottom-5 rounded-xl shadow-lg p-4 w-[280px] text-center animate-fade-in"
      style={{
        backgroundColor: "rgba(30, 27, 75, 0.92)",
        backdropFilter: "blur(8px)",
        fontFamily: "var(--font-body, system-ui, sans-serif)",
      }}
    >
      {/* Close button */}
      <button
        onClick={() => setDismissed(true)}
        className="absolute top-2.5 right-2.5 p-1 cursor-pointer opacity-60 hover:opacity-100 transition-opacity"
        style={{ background: "none", border: "none" }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M16 8L8 16" stroke="white" strokeWidth="2" strokeLinecap="round" />
          <path d="M8 8L16 16" stroke="white" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      {/* Deploy button */}
      <button
        onClick={handleDeploy}
        className="cursor-pointer font-semibold text-sm text-white border-none rounded-full px-5 py-2.5 mt-1 mb-3 inline-block transition-colors"
        style={{ backgroundColor: "var(--color-cta)", lineHeight: "20px" }}
        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--color-cta-hover)")}
        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "var(--color-cta)")}
      >
        {zh ? "🚀 免费一键部署" : "🚀 Deploy Now - Free!"}
      </button>

      {/* Description */}
      <p className="text-xs leading-relaxed text-left" style={{ color: "rgba(255,255,255,0.85)", margin: 0 }}>
        {zh ? (
          <>
            使用 <a href="https://edgeone.ai/products/pages" target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-primary-light)", fontWeight: 600, textDecoration: "none" }}>EdgeOne Makers</a> 部署你自己的 AI 营销策划助手，全球加速，完全免费
          </>
        ) : (
          <>
            Deploy your own AI marketing planner with <a href="https://edgeone.ai/products/pages" target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-primary-light)", fontWeight: 600, textDecoration: "none" }}>EdgeOne Makers</a> — global CDN, completely free
          </>
        )}
      </p>
    </div>
  )
}
