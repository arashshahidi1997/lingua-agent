// Small presentational primitives shared by every view.

import { useEffect, useId, useRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { ArrowLeft, ChevronRight, X } from 'lucide-react'
import { friendlyError } from '../lib/hooks'

// ---- buttons ---------------------------------------------------------------

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'quiet-danger'
  size?: 'sm' | 'md' | 'lg'
  block?: boolean
}

export function Button({ variant = 'primary', size = 'md', block, className = '', type = 'button', ...rest }: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45 select-none'
  const sizes = { sm: 'h-9 px-3 text-sm', md: 'h-11 px-4 text-[15px]', lg: 'h-13 px-6 text-base' }
  const variants = {
    primary: 'bg-accent text-accent-ink hover:bg-accent-strong',
    secondary: 'border border-line-strong bg-surface text-ink hover:bg-surface-2',
    ghost: 'text-ink-2 hover:bg-surface-2 hover:text-ink',
    'quiet-danger': 'text-danger hover:bg-danger-soft',
  }
  return (
    <button
      type={type}
      className={`${base} ${sizes[size]} ${variants[variant]} ${block ? 'w-full' : ''} ${className}`}
      {...rest}
    />
  )
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  size?: 'sm' | 'md'
  tone?: 'plain' | 'accent' | 'solid'
}

export function IconButton({ label, size = 'md', tone = 'plain', className = '', children, type = 'button', ...rest }: IconButtonProps) {
  const sizes = { sm: 'h-8 w-8', md: 'h-10 w-10' }
  const tones = {
    plain: 'text-ink-2 hover:bg-surface-2 hover:text-ink',
    accent: 'text-accent hover:bg-accent-soft',
    solid: 'bg-accent text-accent-ink hover:bg-accent-strong',
  }
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={`inline-flex shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 ${sizes[size]} ${tones[tone]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}

// ---- layout ----------------------------------------------------------------

export function Page({ children, wide = false, className = '' }: { children: ReactNode; wide?: boolean; className?: string }) {
  return (
    <div className={`mx-auto w-full ${wide ? 'max-w-3xl' : 'max-w-2xl'} px-4 sm:px-6 ${className}`}>
      {children}
    </div>
  )
}

export function PageTitle({ title, subtitle, action }: { title: string; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4 pt-2">
      <div className="min-w-0">
        <h1 className="text-[1.65rem] font-semibold leading-tight tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-[15px] text-ink-2">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function SectionLabel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <h2 className={`mb-2 text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3 ${className}`}>{children}</h2>
}

/** A quiet list row: icon, title, detail, chevron. Renders as a real button. */
export function Row({ icon, title, detail, onClick, disabled, trailing }: {
  icon?: ReactNode
  title: ReactNode
  detail?: ReactNode
  onClick?: () => void
  disabled?: boolean
  trailing?: ReactNode
}) {
  const inner = (
    <>
      {icon && <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-ink-2">{icon}</span>}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] text-ink">{title}</span>
        {detail && <span className="mt-0.5 block truncate text-[13px] text-ink-3">{detail}</span>}
      </span>
      {trailing ?? (onClick && <ChevronRight size={18} className="shrink-0 text-ink-3 rtl:rotate-180" aria-hidden />)}
    </>
  )
  const cls = 'flex w-full items-center gap-3 px-1 py-3 text-start'
  if (!onClick) return <div className={cls}>{inner}</div>
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${cls} rounded-xl transition-colors hover:bg-surface-2/70 disabled:opacity-50`}>
      {inner}
    </button>
  )
}

export function List({ children }: { children: ReactNode }) {
  return <div className="divide-y divide-line border-y border-line">{children}</div>
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-surface ${className}`}>{children}</div>
}

// ---- feedback ----------------------------------------------------------------

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-ink-3">
      <span className="dot-pulse inline-flex gap-1" aria-hidden>
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      <span className="text-sm">{label}</span>
    </span>
  )
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return <div className="py-10 text-center"><Spinner label={label} /></div>
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-line-strong px-5 py-8 text-center">
      <p className="text-[15px] font-medium text-ink">{title}</p>
      {children && <div className="mx-auto mt-1.5 max-w-sm text-sm text-ink-2">{children}</div>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}

export function ErrorNote({ error, onRetry }: { error: string | null | undefined; onRetry?: () => void }) {
  if (!error) return null
  return (
    <div role="alert" className="flex items-start justify-between gap-3 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
      <span className="min-w-0">{friendlyError(error)}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="shrink-0 font-medium underline underline-offset-2">
          Try again
        </button>
      )}
    </div>
  )
}

export function ProgressLine({ value, className = '', label }: { value: number; className?: string; label?: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={`h-1 w-full overflow-hidden rounded-full bg-line ${className}`}
    >
      <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${pct}%` }} />
    </div>
  )
}

// ---- inputs ------------------------------------------------------------------

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex max-w-full overflow-x-auto rounded-xl bg-surface-2 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`h-8 shrink-0 whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
            value === o.value ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--line)]' : 'text-ink-2 hover:text-ink'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Toggle({ checked, onChange, label, description }: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  description?: string
}) {
  const id = useId()
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <label htmlFor={id} className="min-w-0">
        <span className="block text-[15px] text-ink">{label}</span>
        {description && <span className="block text-[13px] text-ink-3">{description}</span>}
      </label>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-10 shrink-0 rounded-full transition-colors ${checked ? 'bg-accent' : 'bg-line-strong'}`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-surface transition-[left] ${checked ? 'left-[18px]' : 'left-0.5'}`}
        />
      </button>
    </div>
  )
}

export const inputCls =
  'block w-full rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none'

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-2">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-[13px] text-ink-3">{hint}</span>}
    </label>
  )
}

// ---- overlays ----------------------------------------------------------------

/** Full-screen view above the tabs (hides the tab bar). */
export function Screen({ title, onBack, backIcon = 'back', actions, children, footer, label }: {
  title?: ReactNode
  onBack: () => void
  backIcon?: 'back' | 'close'
  actions?: ReactNode
  children: ReactNode
  footer?: ReactNode
  label?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.focus() }, [])
  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={label ?? (typeof title === 'string' ? title : undefined)}
      className="fixed inset-0 z-40 flex flex-col bg-canvas outline-none"
    >
      <header className="pt-safe shrink-0 border-b border-line bg-canvas">
        <div className="mx-auto flex h-14 w-full max-w-3xl items-center gap-2 px-2 sm:px-4">
          <IconButton label={backIcon === 'close' ? 'Close' : 'Back'} onClick={onBack}>
            {backIcon === 'close' ? <X size={20} /> : <ArrowLeft size={20} className="rtl:rotate-180" />}
          </IconButton>
          <div className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">{title}</div>
          {actions}
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
      {footer && <div className="pb-safe shrink-0 border-t border-line bg-canvas">{footer}</div>}
    </div>
  )
}

/** Bottom sheet on phones, centred dialog on wider screens. */
export function Sheet({ onClose, children, label, footer }: {
  onClose: () => void
  children: ReactNode
  label: string
  footer?: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6">
      <div className="absolute inset-0 bg-black/35" onClick={onClose} aria-hidden />
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className="anim-in relative flex max-h-[88vh] w-full max-w-xl flex-col rounded-t-3xl border border-line bg-surface outline-none sm:rounded-3xl"
      >
        <div className="flex justify-end px-3 pt-3">
          <IconButton label="Close" size="sm" onClick={onClose}><X size={18} /></IconButton>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 sm:px-7">{children}</div>
        {footer && <div className="pb-safe border-t border-line px-5 py-4 sm:px-7">{footer}</div>}
      </div>
    </div>
  )
}
