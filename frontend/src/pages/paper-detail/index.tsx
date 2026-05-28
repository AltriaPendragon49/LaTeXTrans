import { useParams } from "react-router-dom"

import { PaperDetailScreen } from "@/features/community-paper/components/PaperDetailScreen"

/** 论文详情页面组件：根据路由参数 paperId 展示论文详情 */
export default function PaperDetailPage() {
  const { paperId } = useParams<{ paperId: string }>()
  return <PaperDetailScreen paperId={paperId ?? null} />
}
