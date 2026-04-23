import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const chatBubbleVariants = cva(
  "w-full whitespace-pre-wrap border px-5 py-4 text-[15px] leading-relaxed backdrop-blur-sm transition-colors duration-200",
  {
    variants: {
      speaker: {
        assistant:
          "rounded-[24px] rounded-bl-[8px] border-[color:color-mix(in_srgb,var(--px-shell-line)_78%,white_22%)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--px-shell-panel)_88%,white_12%),color-mix(in_srgb,var(--px-shell-panel-strong)_92%,white_8%))] text-[color:var(--px-shell-ink)] shadow-[0_18px_40px_-34px_rgba(15,23,42,0.45)]",
        user:
          "rounded-[24px] rounded-br-[8px] border-[color:var(--px-shell-accent)]/30 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent)_92%,white_8%),var(--px-shell-accent-strong))] text-white shadow-[0_20px_44px_-30px_rgba(0,55,176,0.62)]",
      },
    },
    defaultVariants: {
      speaker: "assistant",
    },
  },
)

interface ChatBubbleProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof chatBubbleVariants> {}

export function ChatBubble({
  speaker,
  className,
  ...props
}: ChatBubbleProps) {
  return (
    <div
      className={cn(chatBubbleVariants({ speaker }), className)}
      {...props}
    />
  )
}
