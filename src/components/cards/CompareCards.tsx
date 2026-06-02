import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import { t } from "../../i18n"

interface CompareCardsProps {
  oldContent: string
  newContent: string
  loading?: boolean
  onAcceptNew: () => void
  onKeepOld: () => void
  onReviseAgain: (feedback?: string) => void
}

export default function CompareCards({ oldContent, newContent, loading, onAcceptNew, onKeepOld, onReviseAgain }: CompareCardsProps) {
  const [chosen, setChosen] = useState<"new" | "old" | null>(null)
  const [feedback, setFeedback] = useState("")
  const zh = t("action.confirm") === "确认"

  const handleAcceptNew = () => {
    setChosen("new")
    setTimeout(onAcceptNew, 400)
  }
  const handleKeepOld = () => {
    setChosen("old")
    setTimeout(onKeepOld, 400)
  }

  return (
    <div className="space-y-3 animate-fade-in">
      <div className="flex items-center gap-2">
        <span className="text-xs text-[var(--color-primary)] bg-[var(--color-primary)]/10 px-2 py-0.5 rounded font-medium">
          {zh ? "方案对比" : "Comparing"}
        </span>
      </div>

      {/* 并排卡片 */}
      <div className="flex gap-3">
        {/* 旧方案 */}
        <div className={`card !p-4 transition-all duration-400 ease-out ${
          chosen === "old" ? "compare-win" :
          chosen === "new" ? "compare-lose" :
          "compare-old"
        } ${chosen === "old" ? "!border-[var(--color-success)]" : "!border-[var(--color-border)]"}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">
              {zh ? "原方案" : "Original"}
            </span>
            {chosen === "old" && (
              <svg className="w-4 h-4 text-[var(--color-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
          <div className="card-content text-sm">
            {oldContent ? (
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                {oldContent}
              </ReactMarkdown>
            ) : <p className="text-[var(--color-text-muted)]">—</p>}
          </div>
        </div>

        {/* 新方案 */}
        <div className={`card !p-4 transition-all duration-400 ease-out ${
          chosen === "new" ? "compare-win" :
          chosen === "old" ? "compare-lose" :
          "compare-new"
        } ${chosen === "new" ? "!border-[var(--color-success)]" : "!border-[var(--color-primary)]"}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-[var(--color-primary)] uppercase">
              {zh ? "✨ 新方案" : "✨ New"}
            </span>
            {loading && (
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.3s" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse-dot" style={{ animationDelay: "0.6s" }} />
              </div>
            )}
            {chosen === "new" && (
              <svg className="w-4 h-4 text-[var(--color-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
          <div className="card-content text-sm">
            {newContent ? (
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                {newContent}
              </ReactMarkdown>
            ) : loading ? (
              <p className="text-[var(--color-text-muted)] italic">{zh ? "生成中..." : "Generating..."}</p>
            ) : <p className="text-[var(--color-text-muted)]">—</p>}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      {!loading && !chosen && newContent && (
        <div className="flex items-center gap-2 pt-2">
          <button onClick={handleAcceptNew} className="btn btn-primary cursor-pointer">
            {zh ? "采用新方案" : "Use new"}
          </button>
          <button onClick={handleKeepOld} className="btn btn-outline cursor-pointer">
            {zh ? "保留原方案" : "Keep original"}
          </button>
          <div className="flex-1" />
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder={zh ? "给修改意见..." : "Feedback..."}
            className="px-3 py-1.5 text-sm border border-[var(--color-border)] rounded-[var(--radius-sm)] outline-none focus:border-[var(--color-primary)] w-48 transition-colors"
          />
          <button onClick={() => onReviseAgain(feedback || undefined)} className="btn btn-ghost cursor-pointer text-sm">
            {zh ? "再改一版" : "Revise"}
          </button>
        </div>
      )}
    </div>
  )
}
