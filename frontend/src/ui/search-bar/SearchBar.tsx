import type { FormEvent, KeyboardEvent, ReactNode } from "react"
import { Search } from "lucide-react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"
import { Input } from "@/ui/input/Input"
import { Textarea } from "@/ui/input/Textarea"

const searchBarVariants = cva(
  "border border-[color:var(--px-shell-line)] text-[color:var(--px-shell-ink)] shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      variant: {
        inline:
          "rounded-[20px] bg-[color:var(--px-shell-panel)] px-4 py-3",
        feature:
          "rounded-[20px] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel-strong)_96%,white),color-mix(in_srgb,var(--px-shell-accent-soft)_18%,white))] px-4 py-4 md:px-5 md:py-5",
      },
    },
    defaultVariants: {
      variant: "inline",
    },
  },
)

interface SearchBarProps extends VariantProps<typeof searchBarVariants> {
  value: string
  onValueChange: (value: string) => void
  onSubmit: (value: string) => void
  placeholder: string
  ariaLabel: string
  actionLabel: string
  actionIcon?: ReactNode
  auxiliaryAction?: ReactNode
  meta?: ReactNode
  disabled?: boolean
  multiline?: boolean
  className?: string
  inputClassName?: string
}

export function SearchBar({
  value,
  onValueChange,
  onSubmit,
  placeholder,
  ariaLabel,
  actionLabel,
  actionIcon,
  auxiliaryAction,
  meta,
  disabled = false,
  multiline = false,
  variant,
  className,
  inputClassName,
}: SearchBarProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit(value)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!multiline) {
      return
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSubmit(value)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(searchBarVariants({ variant }), className)}
    >
      <div className={cn("flex gap-3", variant === "feature" ? "items-start" : "items-center")}>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[14px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-accent)] shadow-sm">
          <Search className="h-4 w-4" />
        </div>

        <div className="min-w-0 flex-1 space-y-2.5">
          {multiline ? (
            <Textarea
              aria-label={ariaLabel}
              value={value}
              onChange={(event) => onValueChange(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              className={cn("min-h-[108px] border-none bg-transparent px-0 py-0 shadow-none focus-visible:ring-0", inputClassName)}
            />
          ) : (
            <Input
              aria-label={ariaLabel}
              value={value}
              onChange={(event) => onValueChange(event.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className={cn("min-h-9 border-none bg-transparent px-0 py-0 text-[15px] shadow-none focus-visible:ring-0", inputClassName)}
            />
          )}

          <div className="flex flex-col gap-2 border-t border-[color:var(--px-shell-line)]/75 pt-2.5 md:flex-row md:items-center md:justify-between">
            {meta ? (
              <div className="min-w-0">{meta}</div>
            ) : (
              <div />
            )}

            <div className="flex flex-wrap items-center justify-end gap-2">
              {auxiliaryAction}
              <Button
                type="submit"
                disabled={disabled}
                className={cn(variant === "feature" ? "px-7" : "px-5")}
              >
                {actionIcon}
                {actionLabel}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </form>
  )
}
