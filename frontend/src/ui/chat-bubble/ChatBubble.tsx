import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const chatBubbleVariants = cva(
  "w-full whitespace-pre-wrap border px-5 py-4 text-[15px] leading-relaxed",
  {
    variants: {
      speaker: {
        assistant:
          "rounded-[22px] rounded-bl-none border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-[0_4px_20px_rgba(27,28,28,0.03)]",
        user:
          "rounded-[22px] rounded-br-none border-[color:var(--px-shell-accent)]/20 bg-[linear-gradient(135deg,var(--px-shell-accent),var(--px-shell-accent-strong))] text-white shadow-[0_8px_24px_rgba(182,23,34,0.15)]",
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
