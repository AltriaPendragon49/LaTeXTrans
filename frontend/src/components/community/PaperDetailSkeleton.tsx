import { Skeleton } from "@/components/ui/skeleton"

export function PaperDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-28 rounded-xl bg-[var(--shell-border)]" />
      <div className="rounded-[32px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-8">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Skeleton className="h-7 w-28 rounded-full bg-[var(--shell-border)]" />
            <Skeleton className="h-7 w-24 rounded-full bg-[var(--shell-border)]" />
          </div>
          <Skeleton className="h-10 w-4/5 rounded-xl bg-[var(--shell-border)]" />
          <Skeleton className="h-5 w-2/3 rounded-xl bg-[var(--shell-border)]" />
        </div>
        <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.8fr)]">
          <div className="space-y-4">
            <Skeleton className="h-48 rounded-[28px] bg-[var(--shell-border)]" />
            <Skeleton className="h-36 rounded-[28px] bg-[var(--shell-border)]" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-36 rounded-[28px] bg-[var(--shell-border)]" />
            <Skeleton className="h-52 rounded-[28px] bg-[var(--shell-border)]" />
          </div>
        </div>
      </div>
    </div>
  )
}
