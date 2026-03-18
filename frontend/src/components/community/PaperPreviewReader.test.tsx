import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import { PaperPreviewReader } from "@/components/community/PaperPreviewReader"

const getCommunityPaperPreviewMock = vi.fn()
const renderMathInElementMock = vi.fn()

vi.mock("@/lib/community-api", () => ({
  getCommunityPaperPreview: (...args: unknown[]) => getCommunityPaperPreviewMock(...args),
}))

vi.mock("dompurify", () => ({
  default: {
    sanitize: (value: string) => value,
  },
}))

vi.mock("katex/contrib/auto-render", () => ({
  default: (...args: unknown[]) => renderMathInElementMock(...args),
}))

describe("PaperPreviewReader", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("renders inline translated html and triggers math rendering", async () => {
    getCommunityPaperPreviewMock.mockResolvedValue({
      paper_id: "paper-1",
      task_id: "task-1",
      asset: {
        id: "asset-preview",
        task_id: "task-1",
        asset_type: "preview_html",
        file_name: "preview.html",
        mime_type: "text/html",
        created_at: "2026-03-18T02:00:00Z",
      },
      html_content: "<h2>引言</h2><p>中文段落 $E=mc^2$。</p>",
      generated_at: "2026-03-18T02:00:00Z",
    })

    render(<PaperPreviewReader paperId="paper-1" />)

    expect(await screen.findByText("引言")).toBeInTheDocument()
    expect(screen.getByText("中文段落 $E=mc^2$。")).toBeInTheDocument()
    await waitFor(() => {
      expect(renderMathInElementMock).toHaveBeenCalled()
    })
  })

  it("renders an empty state when the preview is unavailable", async () => {
    getCommunityPaperPreviewMock.mockRejectedValue(new Error("404"))

    render(<PaperPreviewReader paperId="paper-1" />)

    expect(await screen.findByText("Translated reader not available")).toBeInTheDocument()
  })
})
