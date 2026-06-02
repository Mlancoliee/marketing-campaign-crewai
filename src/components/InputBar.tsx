import { useState, useCallback, useEffect } from "react"
import { t } from "../i18n"

interface InputBarProps {
  onSend: (message: string) => void
  disabled: boolean
  placeholder?: string
  prefill?: string
}

export default function InputBar({ onSend, disabled, placeholder, prefill }: InputBarProps) {
  const [value, setValue] = useState("")

  // 当 prefill 变化时填入
  useEffect(() => {
    if (prefill) {
      setValue(prefill)
    }
  }, [prefill])

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const msg = value.trim()
    if (!msg || disabled) return
    onSend(msg)
    setValue("")
  }, [value, disabled, onSend])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }, [handleSubmit])

  return (
    <form onSubmit={handleSubmit} className="input-bar flex items-center gap-3">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || t("input.placeholder")}
        disabled={disabled}
        className="flex-1"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="btn btn-primary disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
        </svg>
        {t("action.send")}
      </button>
    </form>
  )
}
