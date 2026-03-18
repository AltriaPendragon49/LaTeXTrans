import { Skeleton } from "@/components/ui/skeleton"

export function PaperDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-28 rounded-xl bg-white/10" />
      <div className="rounded-[32px] border border-white/10 bg-slate-950/65 p-8">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Skeleton className="h-7 w-28 rounded-full bg-white/10" />
            <Skeleton className="h-7 w-24 rounded-full bg-white/10" />
          </div>
          <Skeleton className="h-10 w-4/5 rounded-xl bg-white/10" />
          <Skeleton className="h-5 w-2/3 rounded-xl bg-white/10" />
        </div>
        <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.8fr)]">
          <div className="space-y-4">
            <Skeleton className="h-48 rounded-[28px] bg-white/10" />
            <Skeleton className="h-36 rounded-[28px] bg-white/10" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-36 rounded-[28px] bg-white/10" />
            <Skeleton className="h-52 rounded-[28px] bg-white/10" />
          </div>
        </div>
      </div>
    </div>
  )
}
