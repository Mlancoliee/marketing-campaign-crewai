import type { CardData } from "../types"
import { t } from "../i18n"

function getRaw(data: Record<string, unknown> | null, ...paths: string[]): string {
  if (!data) return ""
  for (const path of paths) {
    const parts = path.split(".")
    let cur: unknown = data
    for (const p of parts) {
      if (cur && typeof cur === "object") {
        cur = (cur as Record<string, unknown>)[p]
      } else {
        cur = undefined
        break
      }
    }
    if (typeof cur === "string" && cur) return cur
  }
  return ""
}

export function exportCampaignMarkdown(cards: CardData, campaignName?: string): string {
  const audience = getRaw(cards.audience as Record<string, unknown>, "content")
  const brand = getRaw(cards.brand_creative as Record<string, unknown>, "creatives.0.raw", "raw")
  const channel = getRaw(cards.channel_plan as Record<string, unknown>, "plan.raw", "raw")
  const strategy = getRaw(cards.strategy as Record<string, unknown>, "content", "raw")
  const copy = getRaw(cards.copywriting as Record<string, unknown>, "content.raw", "raw")

  const title = campaignName || t("app.title")
  const now = new Date().toLocaleDateString()

  return `# ${title}

> ${t("action.finish") === "全部完成" ? "生成时间" : "Generated"}: ${now}

---

## ${t("card.audience")}

${audience || "—"}

---

## ${t("card.brand_creative")}

${brand || "—"}

---

## ${t("card.channel_plan")}

${channel || "—"}

---

## ${t("card.strategy")}

${strategy || "—"}

---

## ${t("card.copywriting")}

${copy || "—"}
`
}

export function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
