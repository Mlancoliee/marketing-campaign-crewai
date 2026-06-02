interface StatusBarProps {
  message: string
}

export default function StatusBar({ message }: StatusBarProps) {
  return (
    <div className="status-bar flex items-center gap-2">
      <svg className="w-4 h-4 text-[var(--color-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
      <span>{message}</span>
    </div>
  )
}
