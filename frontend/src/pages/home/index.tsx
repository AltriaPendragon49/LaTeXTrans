import CommunityFeedSurface from "@/features/community-paper/components/CommunityFeedSurface"

/** 首页组件：展示社区论文信息流 */
export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-2 md:px-6 md:py-3">
      <CommunityFeedSurface />
    </div>
  )
}
