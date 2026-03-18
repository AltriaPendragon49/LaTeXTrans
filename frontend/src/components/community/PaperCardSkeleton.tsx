import { Skeleton } from "@/components/ui/skeleton"

export function PaperCardSkeleton() {
  return (
    <div className="rounded-[28px] border border-white/10 bg-slate-950/65 p-6">
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-7 w-28 rounded-full bg-white/10" />
        <Skeleton className="h-7 w-24 rounded-full bg-white/10" />
      </div>
      <div className="mt-5 space-y-3">
        <Skeleton className="h-7 w-4/5 rounded-xl bg-white/10" />
        <Skeleton className="h-4 w-2/3 rounded-xl bg-white/10" />
        <Skeleton className="h-4 w-full rounded-xl bg-white/10" />
        <Skeleton className="h-4 w-full rounded-xl bg-white/10" />
        <Skeleton className="h-4 w-4/5 rounded-xl bg-white/10" />
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <Skeleton className="h-11 rounded-full bg-white/10" />
        <Skeleton className="h-11 rounded-full bg-white/10" />
      </div>
    </div>
  )
}
