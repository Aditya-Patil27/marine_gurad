export default function Logo({ className = '' }) {
  return (
    <span className={`grid h-10 w-10 place-items-center rounded-[11px] bg-navy ${className}`} title="SamudraSense">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
        <path d="M3 15c2.2-1.6 4.4-1.6 6.6 0s4.4 1.6 6.6 0 3.6-1.2 4.8-.6" />
        <path d="M3 19c2.2-1.6 4.4-1.6 6.6 0s4.4 1.6 6.6 0 3.6-1.2 4.8-.6" />
        <circle cx="12" cy="8" r="3" />
      </svg>
      <span className="sr-only">SamudraSense</span>
    </span>
  )
}
