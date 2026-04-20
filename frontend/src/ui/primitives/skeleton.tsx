import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[color:color-mix(in_srgb,var(--px-shell-accent)_10%,transparent)]",
        className,
      )}
      {...props}
    />
  )
}

export { Skeleton }
