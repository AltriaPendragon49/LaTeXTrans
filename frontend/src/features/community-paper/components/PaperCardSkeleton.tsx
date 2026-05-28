import { Skeleton } from "@/ui/primitives/skeleton"

/**
 * 论文卡片骨架屏组件
 * 在论文列表加载过程中展示占位动画，模拟卡片的分类标签、标题、摘要和操作按钮布局
 */
export function PaperCardSkeleton() {
  return (
    <div className="rounded-[28px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6">
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-7 w-28 rounded-full bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-7 w-24 rounded-full bg-[color:var(--px-shell-line)]" />
      </div>
      <div className="mt-5 space-y-3">
        <Skeleton className="h-7 w-4/5 rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-2/3 rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-full rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-full rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-4/5 rounded-xl bg-[color:var(--px-shell-line)]" />
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <Skeleton className="h-11 rounded-full bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-11 rounded-full bg-[color:var(--px-shell-line)]" />
      </div>
    </div>
  )
}
