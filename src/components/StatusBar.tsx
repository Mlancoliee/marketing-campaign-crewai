interface StatusBarProps {
  message: string
}

export default function StatusBar({ message }: StatusBarProps) {
  const isError = message.startsWith("Error")

  return (
    <div className={`status-bar flex items-center gap-2 ${isError ? "!bg-red-50 !border-red-200" : ""}`}>
      {isError ? (
        <svg className="w-4 h-4 text-[var(--color-error)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.07 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      ) : (
        <svg className="w-4 h-4 text-[var(--color-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      )}
      <span className={isError ? "text-[var(--color-error)]" : ""}>{message}</span>
    </div>
  )
}
