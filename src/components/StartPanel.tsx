import { useState, useCallback } from "react"
import { t } from "../i18n"

interface StartPanelProps {
  onStart: (name: string, brief: string) => void
  disabled?: boolean
}

const EXAMPLES = [
  { name: "start.example1", brief: "start.brief1" },
  { name: "start.example2", brief: "start.brief2" },
  { name: "start.example3", brief: "start.brief3" },
]

export default function StartPanel({ onStart, disabled }: StartPanelProps) {
  const [name, setName] = useState("")
  const [brief, setBrief] = useState("")

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !brief.trim() || disabled) return
    onStart(name.trim(), brief.trim())
  }, [name, brief, onStart, disabled])

  const handleExample = useCallback((idx: number) => {
    const ex = EXAMPLES[idx]
    setName(t(ex.name))
    setBrief(t(ex.brief))
  }, [])

  return (
    <div className="max-w-xl mx-auto mt-16 animate-fade-in">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-2xl bg-[var(--color-primary)] flex items-center justify-center mx-auto mb-4">
          <svg className="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold font-[var(--font-heading)] text-[var(--color-text)]">
          {t("start.title")}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-4">
        <div>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("start.name_placeholder")}
            className="w-full px-4 py-3 border border-[var(--color-border)] rounded-[var(--radius-sm)] text-sm outline-none focus:border-[var(--color-primary)] transition-colors"
          />
        </div>
        <div>
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder={t("start.brief_placeholder")}
            rows={4}
            className="w-full px-4 py-3 border border-[var(--color-border)] rounded-[var(--radius-sm)] text-sm outline-none focus:border-[var(--color-primary)] transition-colors resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={!name.trim() || !brief.trim() || disabled}
          className="btn btn-cta w-full justify-center py-3 text-base font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          {t("action.start")}
        </button>
      </form>

      <div className="mt-6">
        <p className="text-xs text-[var(--color-text-muted)] mb-2">{t("start.examples")}</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex, idx) => (
            <button
              key={idx}
              onClick={() => handleExample(idx)}
              className="btn btn-ghost text-xs cursor-pointer"
            >
              {t(ex.name)}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
