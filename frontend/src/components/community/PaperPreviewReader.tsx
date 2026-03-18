import DOMPurify from "dompurify"
import renderMathInElement from "katex/contrib/auto-render"
import { forwardRef, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { getCommunityPaperPreview } from "@/lib/community-api"
import type { CommunityPaperPreviewResponse } from "@/types/community"

interface PaperPreviewReaderProps {
  paperId: string
}

export const PaperPreviewReader = forwardRef<HTMLDivElement, PaperPreviewReaderProps>(
  function PaperPreviewReader({ paperId }, ref) {
    const { t } = useTranslation()
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [preview, setPreview] = useState<CommunityPaperPreviewResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
      let cancelled = false
      setLoading(true)
      setError(null)

      void (async () => {
        try {
          const response = await getCommunityPaperPreview(paperId)
          if (cancelled) {
            return
          }
          setPreview(response)
          setLoading(false)
        } catch (fetchError) {
          if (cancelled) {
            return
          }
          setPreview(null)
          setLoading(false)
          setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
        }
      })()

      return () => {
        cancelled = true
      }
    }, [paperId])

    const sanitizedHtml = useMemo(() => {
      if (!preview?.html_content) {
        return ""
      }
      return DOMPurify.sanitize(preview.html_content)
    }, [preview])

    useEffect(() => {
      if (!sanitizedHtml || !containerRef.current) {
        return
      }
      renderMathInElement(containerRef.current, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
      })
    }, [sanitizedHtml])

    function attachRef(node: HTMLDivElement | null) {
      containerRef.current = node
      if (!ref) {
        return
      }
      if (typeof ref === "function") {
        ref(node)
        return
      }
      ref.current = node
    }

    if (loading) {
      return (
        <div
          ref={attachRef}
          id="paper-preview-reader"
          className="rounded-[24px] border border-white/10 bg-[#202020] p-6 text-sm text-slate-400"
        >
          {t("community.reader.loading")}
        </div>
      )
    }

    if (!preview || error) {
      return (
        <div
          ref={attachRef}
          id="paper-preview-reader"
          className="rounded-[24px] border border-dashed border-white/10 bg-[#202020] p-6 text-sm text-slate-300"
        >
          <p className="font-medium text-slate-100">{t("community.reader.emptyTitle")}</p>
          <p className="mt-2 text-slate-400">{t("community.reader.emptyDescription")}</p>
        </div>
      )
    }

    return (
      <div
        ref={attachRef}
        id="paper-preview-reader"
        className="rounded-[24px] border border-white/10 bg-[#202020] p-6 text-slate-100 shadow-none"
      >
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
          <span>{t("community.reader.sectionTitle")}</span>
          <span>·</span>
          <span>{preview.asset.file_name}</span>
        </div>
        <div
          className="paper-preview prose prose-invert max-w-none text-slate-100 [&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold [&_h4]:mt-5 [&_h4]:text-lg [&_h4]:font-semibold [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:border [&_pre]:border-white/10 [&_pre]:bg-[#171717] [&_pre]:p-4 [&_pre]:text-slate-200"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
      </div>
    )
  },
)
