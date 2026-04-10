import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { preloadPaperDetailRoute, prefetchCommunityPaperDetail } from "@/lib/community-api"
import { preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaper } from "@/types/community"
import { API_BASE_URL } from "@/api-base"

import { PaperStatusBadge } from "./PaperStatusBadge"
import { Document, Page, pdfjs } from "react-pdf"
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url"

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker

const PDF_PREVIEW_OPTIONS_BASE = Object.freeze({
  cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
  cMapPacked: true,
})

const PDF_PREVIEW_OPTIONS_SOURCE = Object.freeze({
  ...PDF_PREVIEW_OPTIONS_BASE,
  disableStream: true,
  disableAutoFetch: true,
  rangeChunkSize: 128 * 1024,
})

interface PaperCardProps {
  paper: CommunityPaper
}

interface PdfPreviewFrameProps {
  label: string
  pdfUrl: string | null
  unavailableIcon: string
  placeholderTone: "neutral" | "accent"
  pdfOptions: Record<string, unknown>
}

function PdfPreviewFrame({
  label,
  pdfUrl,
  unavailableIcon,
  placeholderTone,
  pdfOptions,
}: PdfPreviewFrameProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [containerHeight, setContainerHeight] = useState(0)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    const element = containerRef.current
    if (!element) {
      return
    }

    const refresh = () => {
      setContainerHeight(Math.max(120, Math.floor(element.clientHeight)))
    }

    refresh()

    if (typeof ResizeObserver === "undefined") {
      return
    }

    const observer = new ResizeObserver(() => refresh())
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    setLoaded(false)
  }, [pdfUrl])

  const pageHeight = Math.max(120, containerHeight - 8)
  const canRenderPdf = Boolean(pdfUrl && containerHeight > 0)

  return (
    <div
      ref={containerRef}
      className="w-full aspect-[3/4] bg-white rounded-lg shadow-md border border-outline-variant/20 overflow-hidden relative transition-transform duration-300 z-10 hover:z-50 hover:scale-[1.5] origin-center"
    >
      {canRenderPdf ? (
        <Document
          file={pdfUrl}
          className="absolute inset-0 z-20 overflow-hidden flex items-center justify-center pointer-events-none bg-white"
          loading={null}
          error={
            <div className="absolute inset-0 bg-white/95 flex flex-col items-center justify-center text-slate-400 p-2 z-30">
              <span className="material-symbols-outlined text-2xl mb-1 opacity-50">description</span>
              <span className="text-[8px] font-bold uppercase tracking-widest text-center">Unavailable</span>
            </div>
          }
          onLoadSuccess={() => setLoaded(true)}
          onLoadError={(error) => console.error(`${label} PDF Load Error:`, error)}
          options={pdfOptions}
        >
          <Page
            pageNumber={1}
            height={pageHeight}
            renderTextLayer={false}
            renderAnnotationLayer={false}
            className="h-full w-full flex items-center justify-center bg-white [&>canvas]:!h-full [&>canvas]:!w-auto [&>canvas]:!max-w-full"
          />
        </Document>
      ) : null}

      <div
        className={`absolute inset-0 z-10 p-3 pointer-events-none transition-opacity duration-300 ${
          loaded ? "opacity-0" : "opacity-100"
        }`}
      >
        <div className={`h-2 w-3/4 mb-2 ${placeholderTone === "accent" ? "bg-blue-100" : "bg-slate-200"}`}></div>
        <div className="h-1 w-full bg-slate-100 mb-1.5"></div>
        <div className="h-1 w-full bg-slate-100 mb-1.5"></div>
        <div className="h-1 w-5/6 bg-slate-100 mb-5"></div>
        <div className={`h-24 w-full rounded mt-auto ${placeholderTone === "accent" ? "bg-blue-50/50" : "bg-slate-50"}`}></div>
      </div>

      {!pdfUrl && (
        <div className="absolute inset-0 bg-primary/5 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center z-30 pointer-events-none">
          <span className="material-symbols-outlined text-primary scale-125">{unavailableIcon}</span>
        </div>
      )}
    </div>
  )
}

function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .slice(0, 3)
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

export function PaperCard({ paper }: PaperCardProps) {
  const { t } = useTranslation()
  const [showTranslatedAbstract, setShowTranslatedAbstract] = useState(true)

  function prefetchDetailNavigation() {
    void preloadPaperDetailRoute()
    void prefetchCommunityPaperDetail(paper.id)
    void preloadPaperPreviewEnhancer()
  }

  const sourcePdfUrl =
    paper.source === "arxiv" || Boolean(paper.assets?.source_archive) || Boolean(paper.community_selected_task_id)
      ? `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`
      : null
  const transPdfUrl =
    paper.trans_status === "completed" &&
    (Boolean(paper.assets?.translated_pdf) || Boolean(paper.community_selected_task_id))
      ? `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf`
      : null

  const authorsLabel = useMemo(
    () => formatAuthors(paper.authors, t("community.card.authorsUnavailable")),
    [paper.authors, t],
  )

  return (
    <Link
      to={`/paper/${paper.id}`}
      onMouseEnter={prefetchDetailNavigation}
      onFocus={prefetchDetailNavigation}
      onPointerDown={prefetchDetailNavigation}
      className="group bg-surface-container-lowest rounded-2xl p-6 md:p-8 flex flex-col md:flex-row gap-6 md:gap-10 transition-all hover:border-primary/30 border border-outline-variant/10 cursor-pointer shadow-sm hover:shadow-xl hover:shadow-primary/5 select-none"
    >
      <div className="flex-1 flex flex-col justify-between order-2 md:order-1">
        <div>
          <div className="flex justify-between items-start mb-6">
            <div className="flex flex-wrap gap-2">
              {paper.categories.slice(0, 3).map((cat) => (
                <span key={cat} className="bg-surface-container-low text-primary text-[11px] font-extrabold tracking-widest px-4 py-1.5 rounded-full uppercase border border-primary/10">
                  {cat}
                </span>
              ))}
              {paper.categories.length === 0 && (
                <span className="bg-surface-container-low text-primary text-[11px] font-extrabold tracking-widest px-4 py-1.5 rounded-full uppercase border border-primary/10">
                  Uncategorized
                </span>
              )}
            </div>
            <span className="material-symbols-outlined text-slate-300 group-hover:text-primary transition-colors">bookmark</span>
          </div>
          <h3 className="text-xl md:text-2xl font-bold text-on-surface leading-tight mb-4 md:mb-5 group-hover:text-primary transition-colors">
            {paper.title}
          </h3>
          <div className="mb-4 flex items-center justify-between">
            <PaperStatusBadge kind="translation" value={paper.trans_status} />
            {paper.abstract_translated && (
              <button
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setShowTranslatedAbstract(!showTranslatedAbstract)
                }}
                className={`text-xs font-semibold px-2.5 py-1 rounded transition-colors flex items-center gap-1 border ${
                  showTranslatedAbstract
                    ? "text-primary hover:text-primary bg-primary/10 hover:bg-primary/20 border-primary/20 dark:bg-primary/20 dark:text-primary/90"
                    : "text-slate-500 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 border-slate-200 dark:bg-surface-container-high dark:text-on-surface-variant dark:border-outline-variant/20 dark:hover:bg-surface-container-highest"
                }`}
                title={showTranslatedAbstract ? "Switch to English" : "Switch to Chinese"}
              >
                <span className="material-symbols-outlined text-[14px]">translate</span>
                切换语言(switch)
              </button>
            )}
          </div>
          <p className="text-on-surface-variant text-sm md:text-base mb-6 md:mb-8 leading-relaxed line-clamp-3">
            {showTranslatedAbstract && paper.abstract_translated
              ? paper.abstract_translated
              : paper.abstract_raw || paper.abstract_translated || "No abstract available for this paper."}
          </p>
        </div>

        <div className="flex items-center justify-between pt-6 border-t border-outline-variant/10 mt-auto">
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              <div className="w-8 h-8 rounded-full border border-outline-variant/20 bg-surface-container-high flex items-center justify-center text-xs font-bold text-tertiary">
                {formatAuthors(paper.authors, "?").charAt(0).toUpperCase()}
              </div>
            </div>
            <span className="text-xs md:text-sm font-bold text-tertiary">{authorsLabel}</span>
          </div>
          <div className="flex items-center gap-5 text-tertiary text-xs md:text-sm">
            <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-lg">visibility</span> {paper.view_count || 0}</span>
            <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-lg">comment</span> {paper.comment_count || 0}</span>
          </div>
        </div>
      </div>

      <div className="md:w-2/5 flex gap-5 bg-slate-50/50 p-6 rounded-2xl items-center justify-center border border-slate-100 dark:bg-surface-container-low dark:border-outline-variant/5 order-1 md:order-2 shrink-0">
        <div className="flex-1 flex flex-col items-center gap-3">
          <PdfPreviewFrame
            label="Source"
            pdfUrl={sourcePdfUrl}
            unavailableIcon="picture_as_pdf"
            placeholderTone="neutral"
            pdfOptions={PDF_PREVIEW_OPTIONS_SOURCE}
          />
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{paper.source === "arxiv" ? "Original" : "Source"}</span>
        </div>

        <div className="flex-1 flex flex-col items-center gap-3">
          <PdfPreviewFrame
            label="Translated"
            pdfUrl={transPdfUrl}
            unavailableIcon="translate"
            placeholderTone="accent"
            pdfOptions={PDF_PREVIEW_OPTIONS_BASE}
          />
          <span className="text-[10px] font-black text-primary uppercase tracking-[0.2em] bg-blue-50 px-2 py-0.5 rounded-sm dark:bg-blue-900/30 dark:text-blue-300">ZH-CN</span>
        </div>
      </div>
    </Link>
  )
}
