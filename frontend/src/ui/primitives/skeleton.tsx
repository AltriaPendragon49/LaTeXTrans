/**
 * 骨架屏组件
 * 渲染脉动画效果的占位块，用于内容加载时的占位展示
 */
import { cn } from "@/lib/utils"

/** 骨架屏组件，带脉动动画的占位容器 */
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
