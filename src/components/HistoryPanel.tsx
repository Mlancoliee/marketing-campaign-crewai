import { useState, useCallback, useEffect } from "react"
import { t } from "../i18n"
import { getHistory, removeHistory } from "../hooks/useHistory"
import type { HistoryItem } from "../types"

interface HistoryPanelProps {
  open: boolean
  onClose: () => void
  onSelect: (id: string) => void
  currentId?: string
}

function formatTime(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 60_000) return t("app.history") === "历史" ? "刚刚" : "Just now"
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return new Date(ts).toLocaleDateString()
}

export default function HistoryPanel({ open, onClose, onSelect, currentId }: HistoryPanelProps) {
  const [items, setItems] = useState<HistoryItem[]>(getHistory)

  // 每次打开时刷新列表
  useEffect(() => {
    if (open) setItems(getHistory())
  }, [open])

  const handleRemove = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    removeHistory(id)
    setItems(getHistory())
    // 同时删除服务端数据
    fetch("/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json", "makers-conversation-id": id },
      body: JSON.stringify({ conversation_id: id }),
    }).catch(() => {})
  }, [])

  const handleSelect = useCallback((id: string) => {
    onSelect(id)
    onClose()
  }, [onSelect, onClose])

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-80 bg-white shadow-xl z-50 flex flex-col animate-fade-in">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
          <h3 className="font-semibold text-sm font-[var(--font-heading)]">{t("app.history")}</h3>
          <button onClick={onClose} className="btn btn-ghost p-1 cursor-pointer">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {items.length === 0 ? (
            <p className="text-sm text-[var(--color-text-muted)] text-center py-8">
              {t("app.history") === "历史" ? "暂无历史会话" : "No history yet"}
            </p>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              {items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleSelect(item.id)}
                  className={`px-4 py-3 cursor-pointer transition-colors flex items-center justify-between group ${
                    item.id === currentId
                      ? "bg-[var(--color-primary)]/5 border-l-2 border-[var(--color-primary)]"
                      : "hover:bg-[var(--color-bg)]"
                  }`}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{item.campaignName}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">{formatTime(item.timestamp)}</p>
                  </div>
                  <button
                    onClick={(e) => handleRemove(item.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity btn btn-ghost p-1 cursor-pointer"
                  >
                    <svg className="w-4 h-4 text-[var(--color-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
