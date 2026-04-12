import DOMPurify from "dompurify"
import { forwardRef, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { getCommunityPaperPreview } from "@/lib/community-api"
import { enhancePaperPreviewElement, preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaperPreviewResponse } from "@/types/community"

interface PaperPreviewReaderProps {
  paperId: string
  initialPreview?: CommunityPaperPreviewResponse | null
  readerState?: "ready" | "warming" | "unavailable"
}

function getPreviewIdentity(preview: CommunityPaperPreviewResponse | null | undefined): string | null {
  if (!preview) {
    return null
  }

  return [
    preview.asset.id,
    preview.generated_at ?? preview.asset.created_at ?? "",
    preview.fetch_url ?? "",
  ].join("::")
}

function getPreviewSignature(preview: CommunityPaperPreviewResponse | null | undefined): string | null {
  if (!preview) {
    return null
  }

  return [
    getPreviewIdentity(preview),
    preview.html_content ?? "",
  ].join("::")
}

function normalizePreviewHtml(rawHtml: string): string {
  if (!rawHtml) {
    return ""
  }

  let normalized = rawHtml

  normalized = normalized.replace(
    /<pre class="paper-preview__latex">([\s\S]*?)<\/pre>/g,
    (_match, source: string) => {
      const cleanedSource = String(source || "").trim()
      if (!cleanedSource) {
        return ""
      }

      const isMathLike =
        /\\begin\{(?:equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD)\}/.test(
          cleanedSource,
        ) ||
        /\\\[/.test(cleanedSource) ||
        /\$\$/.test(cleanedSource)

      if (isMathLike) {
        return `<div class="paper-preview__math-block">${cleanedSource}</div>`
      }

      const prose = cleanedSource
        .replace(/\\begin\{(?:quote|snugshade\*?)\}/g, " ")
        .replace(/\\end\{(?:quote|snugshade\*?)\}/g, " ")
        .replace(/\\flushright\{([^}]*)\}/g, "$1")
        .replace(/\\lettrine(?:\[[^\]]*\])?\{([^}]*)\}\{([^}]*)\}/g, "$1$2")
        .replace(/\s+/g, " ")
        .trim()

      return prose ? `<p>${prose}</p>` : ""
    },
  )

  normalized = normalized.replace(
    /<p>\s*\\flushright\{([^}]*)\}(?:\s*\\n)?\s*\\end\{quote\}\s*<\/p>/g,
    "<p>$1</p>",
  )
  normalized = normalized.replace(
    /<p>\s*\\(?:begin|end)\{(?:quote|snugshade\*?)\}\s*<\/p>/g,
    "",
  )
  normalized = normalized.replace(
    /<p>\s*\\flushright\{([^}]*)\}\s*<\/p>/g,
    "<p>$1</p>",
  )
  normalized = normalized.replace(
    /<p>\s*\\lettrine(?:\[[^\]]*\])?\{([^}]*)\}\{([^}]*)\}\s*<\/p>/g,
    "<p>$1$2</p>",
  )
  normalized = normalized.replace(
    /<p>\s*\\end\{(?:quote|snugshade\*?)\}\s*<\/p>/g,
    "",
  )

  return normalized
}

export const PaperPreviewReader = forwardRef<HTMLDivElement, PaperPreviewReaderProps>(
  function PaperPreviewReader({ paperId, initialPreview = null, readerState = "unavailable" }, ref) {
    const { t } = useTranslation()
    const contentRef = useRef<HTMLDivElement | null>(null)
    const preparedPreviewRef = useRef<{ signature: string; html: string } | null>(null)
    const [preview, setPreview] = useState<CommunityPaperPreviewResponse | null>(initialPreview)
    const [loading, setLoading] = useState(
      (!initialPreview || !initialPreview.html_content) && readerState !== "warming",
    )
    const [error, setError] = useState<string | null>(null)
    const [expandedTable, setExpandedTable] = useState<{ caption: string | null; html: string } | null>(null)

    useEffect(() => {
      if (initialPreview?.html_content) {
        const nextSignature = getPreviewSignature(initialPreview)
        setPreview((current) => {
          if (nextSignature && nextSignature === getPreviewSignature(current)) {
            return current
          }
          return initialPreview
        })
        setLoading(false)
        setError(null)
        return
      }

      if (initialPreview) {
        const nextIdentity = getPreviewIdentity(initialPreview)
        setPreview((current) => {
          if (
            current?.html_content &&
            nextIdentity &&
            nextIdentity === getPreviewIdentity(current)
          ) {
            return current
          }
          return initialPreview
        })
      }

      if (readerState === "warming") {
        setPreview(initialPreview ?? null)
        setLoading(false)
        setError(null)
        return
      }

      let cancelled = false
      setLoading(true)
      setError(null)

      void (async () => {
        try {
          const response = await getCommunityPaperPreview(paperId)
          if (cancelled) {
            return
          }
          const nextSignature = getPreviewSignature(response)
          setPreview((current) => {
            if (nextSignature && nextSignature === getPreviewSignature(current)) {
              return current
            }
            return response
          })
          setLoading(false)
        } catch (fetchError) {
          if (cancelled) {
            return
          }
          setPreview((current) => current?.html_content ? current : null)
          setLoading(false)
          setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
        }
      })()

      return () => {
        cancelled = true
      }
    }, [initialPreview, paperId, readerState])

    const previewSignature = useMemo(() => getPreviewSignature(preview), [preview])
    const previewAssetId = preview?.asset.id

    const sanitizedHtml = useMemo(() => {
      if (!preview?.html_content || !previewSignature) {
        return ""
      }

      if (preparedPreviewRef.current?.signature === previewSignature) {
        return preparedPreviewRef.current.html
      }

      const normalized = normalizePreviewHtml(preview.html_content)
      const sanitized = DOMPurify.sanitize(normalized)
      preparedPreviewRef.current = {
        signature: previewSignature,
        html: sanitized,
      }
      return sanitized
    }, [preview?.html_content, previewSignature])

    useEffect(() => {
      if (!previewSignature) {
        return
      }

      void preloadPaperPreviewEnhancer()
    }, [previewSignature])

    useEffect(() => {
      if (!previewSignature) {
        setExpandedTable(null)
      }
    }, [previewSignature])

    useEffect(() => {
      if (!sanitizedHtml || !contentRef.current || !previewSignature) {
        return
      }

      let cancelled = false
      const target = contentRef.current
      void (async () => {
        const fallbackRenderMathBlocks = async () => {
          const katexModule = await import("katex")
          const katex = katexModule.default
          target.querySelectorAll<HTMLElement>(".paper-preview__math-block").forEach((block) => {
            const source = (block.textContent || "").trim()
            if (!source) {
              return
            }
            block.innerHTML = katex.renderToString(source, {
              displayMode: true,
              strict: "ignore",
              throwOnError: false,
            })
          })
        }

        try {
          await enhancePaperPreviewElement(target, {
            previewAssetId,
            previewSignature,
          })
        } catch {
          if (!cancelled) {
            await fallbackRenderMathBlocks()
          }
          return
        }

        if (cancelled) {
          return
        }

        const hasMathBlocks = target.querySelector(".paper-preview__math-block") !== null
        const hasKaTeX = target.querySelector(".katex, .katex-display") !== null
        if (hasMathBlocks && !hasKaTeX) {
          await fallbackRenderMathBlocks()
        }
      })()

      return () => {
        cancelled = true
      }
    }, [previewAssetId, previewSignature, sanitizedHtml])

    useEffect(() => {
      if (!contentRef.current || !previewSignature) {
        return
      }

      contentRef.current.querySelectorAll<HTMLElement>(".paper-preview__figure--table").forEach((figure) => {
        if (figure.querySelector("[data-paper-preview-expand-table='true']")) {
          return
        }

        const toolbar = document.createElement("div")
        toolbar.className = "paper-preview__table-toolbar"

        const button = document.createElement("button")
        button.type = "button"
        button.className = "paper-preview__table-expand"
        button.dataset.paperPreviewExpandTable = "true"
        button.textContent = t("community.reader.expandTable")

        toolbar.append(button)
        figure.prepend(toolbar)
      })
    }, [previewSignature, sanitizedHtml, t])

    useEffect(() => {
      if (!contentRef.current || !previewSignature) {
        return
      }

      const root = contentRef.current
      const handleClick = (event: MouseEvent) => {
        const target = event.target
        if (!(target instanceof Element)) {
          return
        }

        const expandButton = target.closest<HTMLButtonElement>("[data-paper-preview-expand-table='true']")
        if (expandButton) {
          const tableFigure = expandButton.closest<HTMLElement>(".paper-preview__figure--table")
          if (!tableFigure) {
            return
          }

          event.preventDefault()
          const clone = tableFigure.cloneNode(true) as HTMLElement
          clone.querySelector(".paper-preview__table-toolbar")?.remove()
          setExpandedTable({
            caption: clone.querySelector<HTMLElement>(".paper-preview__caption")?.textContent?.trim() ?? null,
            html: clone.outerHTML,
          })
          return
        }

        const anchor = target.closest<HTMLAnchorElement>("a[href^='#']")
        const href = anchor?.getAttribute("href")
        if (!anchor || !href || href === "#") {
          return
        }

        const linkedTarget = root.querySelector<HTMLElement>(href)
        if (!linkedTarget) {
          return
        }

        event.preventDefault()
        linkedTarget.scrollIntoView({
          behavior: "smooth",
          block: "center",
        })
      }

      root.addEventListener("click", handleClick)
      return () => {
        root.removeEventListener("click", handleClick)
      }
    }, [previewSignature])

    function attachRootRef(node: HTMLDivElement | null) {
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
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-[320px] items-center rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] p-6 text-sm text-[var(--shell-text-muted)]"
        >
          {t("community.reader.loading")}
        </div>
      )
    }

    if (readerState === "warming") {
      return (
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-[320px] items-center rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] p-6 text-sm text-[var(--shell-text-soft)]"
        >
          <div>
            <p className="font-medium text-[var(--shell-heading)]">{t("community.reader.warmingTitle")}</p>
            <p className="mt-2 text-[var(--shell-text-muted)]">{t("community.reader.warmingDescription")}</p>
          </div>
        </div>
      )
    }

    if (!preview || error) {
      return (
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-[320px] items-center rounded-[24px] border border-dashed border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] p-6 text-sm text-[var(--shell-text-soft)]"
        >
          <div>
            <p className="font-medium text-[var(--shell-heading)]">{t("community.reader.emptyTitle")}</p>
            <p className="mt-2 text-[var(--shell-text-muted)]">{t("community.reader.emptyDescription")}</p>
          </div>
        </div>
      )
    }

    return (
      <>
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-0 flex-col text-[var(--shell-text)]"
        >
          <div
            data-testid="paper-preview-viewport"
            className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-6 py-5 xl:px-8 xl:py-6"
          >
            <div
              ref={contentRef}
              data-testid="paper-preview-content"
              data-reader-layout="scholarly"
              className="paper-preview-shell prose max-w-none text-[var(--shell-text)] [&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold [&_h4]:mt-5 [&_h4]:text-lg [&_h4]:font-semibold [&_img]:rounded-2xl [&_img]:shadow-sm [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:border [&_pre]:p-4 [&_table]:w-full [&_td]:align-top [&_th]:align-bottom"
              dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
            />
          </div>
        </div>

        <Sheet open={Boolean(expandedTable)} onOpenChange={(open) => !open && setExpandedTable(null)}>
          <SheetContent
            side="right"
            className="w-[min(96vw,1160px)] border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-6 text-[var(--shell-text)] sm:max-w-none"
          >
            <SheetHeader className="pr-10">
              <SheetTitle className="text-[var(--shell-heading)]">
                {expandedTable?.caption || t("community.reader.expandedTableTitle")}
              </SheetTitle>
              <SheetDescription className="text-[var(--shell-text-muted)]">
                {t("community.reader.expandedTableDescription")}
              </SheetDescription>
            </SheetHeader>

            <div
              data-testid="paper-preview-expanded-table"
              className="mt-6 h-[calc(100vh-8rem)] overflow-auto rounded-[20px] border border-[color:var(--shell-border-strong)] bg-[var(--shell-surface-strong)] p-4"
            >
              <div
                className="paper-preview-shell prose max-w-none text-[var(--shell-text)]"
                dangerouslySetInnerHTML={{ __html: expandedTable?.html ?? "" }}
              />
            </div>
          </SheetContent>
        </Sheet>
      </>
    )
  },
)
