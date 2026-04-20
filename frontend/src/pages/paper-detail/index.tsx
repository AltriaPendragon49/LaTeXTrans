import { useParams } from "react-router-dom"

import { PaperDetailScreen } from "@/features/community-paper/components/PaperDetailScreen"

export default function PaperDetailPage() {
  const { paperId } = useParams<{ paperId: string }>()
  return <PaperDetailScreen paperId={paperId ?? null} />
}
