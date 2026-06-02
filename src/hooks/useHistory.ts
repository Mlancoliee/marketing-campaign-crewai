import type { HistoryItem, Phase } from "../types"

const HISTORY_KEY = "marketing-campaign-history"
const MAX_ITEMS = 20

export function getHistory(): HistoryItem[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]")
  } catch {
    return []
  }
}

export function saveHistory(id: string, campaignName: string, phase: Phase) {
  const list = getHistory()
  const existing = list.findIndex((h) => h.id === id)
  if (existing >= 0) {
    list[existing].phase = phase
    list[existing].timestamp = Date.now()
  } else {
    list.unshift({ id, campaignName: campaignName.slice(0, 50), timestamp: Date.now(), phase })
  }
  if (list.length > MAX_ITEMS) list.pop()
  localStorage.setItem(HISTORY_KEY, JSON.stringify(list))
}

export function removeHistory(id: string) {
  const list = getHistory().filter((h) => h.id !== id)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(list))
}
