import { t } from "../i18n"
import type { Locale } from "../types"

interface HeaderProps {
  locale: Locale
  onLocaleChange: (locale: Locale) => void
  onNew: () => void
  onHistory: () => void
}

export default function Header({ locale, onLocaleChange, onNew, onHistory }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--color-border)] bg-white">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h1 className="text-lg font-semibold font-[var(--font-heading)] text-[var(--color-text)]">
          {t("app.title")}
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onNew}
          className="btn btn-ghost text-sm cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          {t("app.new")}
        </button>

        <button
          onClick={onHistory}
          className="btn btn-ghost text-sm cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {t("app.history")}
        </button>

        <button
          onClick={() => onLocaleChange(locale === "zh" ? "en" : "zh")}
          className="btn btn-outline text-xs px-3 py-1.5 cursor-pointer"
        >
          {locale === "zh" ? "EN" : "中"}
        </button>
      </div>
    </header>
  )
}
