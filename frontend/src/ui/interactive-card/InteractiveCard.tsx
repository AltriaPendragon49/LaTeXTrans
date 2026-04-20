import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const interactiveCardVariants = cva(
  "group w-full rounded-[24px] border text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      tone: {
        panel:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-line-strong)] hover:bg-[color:var(--px-shell-panel-strong)] hover:shadow-[0_14px_34px_rgba(15,23,42,0.06)]",
        strong:
          "border-[color:var(--px-shell-line)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel-strong)_94%,white),color-mix(in_srgb,var(--px-shell-accent-soft)_38%,white))] text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-line-strong)] hover:shadow-[0_18px_46px_rgba(15,23,42,0.08)]",
        selected:
          "border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-[0_16px_40px_rgba(15,23,42,0.06)]",
        ghost:
          "border-transparent bg-transparent text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel)]",
      },
      size: {
        sm: "px-4 py-3",
        md: "px-4 py-4",
        lg: "px-6 py-6",
      },
    },
    defaultVariants: {
      tone: "panel",
      size: "md",
    },
  },
)

export interface InteractiveCardProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof interactiveCardVariants> {
  element?: "button" | "div"
}

export const InteractiveCard = React.forwardRef<HTMLButtonElement, InteractiveCardProps>(
  ({ className, tone, size, type = "button", element = "button", ...props }, ref) => {
    if (element === "div") {
      return (
        <div
          className={cn(interactiveCardVariants({ tone, size }), className)}
          {...(props as React.HTMLAttributes<HTMLDivElement>)}
        />
      )
    }

    return (
      <button
        ref={ref}
        type={type}
        className={cn(interactiveCardVariants({ tone, size }), className)}
        {...props}
      />
    )
  },
)

InteractiveCard.displayName = "InteractiveCard"
