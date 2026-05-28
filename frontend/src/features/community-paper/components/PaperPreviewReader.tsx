import DOMPurify from "dompurify"
import { forwardRef, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/ui/primitives/sheet"
import { getCommunityPaperPreview } from "@/features/community-paper/services/community-paper-api"
import { stripLeadingDuplicatePaperHeaderHtml, type PaperReaderMetadata } from "@/lib/paper-reader-html"
import { enhancePaperPreviewElement, preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaperPreviewResponse } from "@/types/community"
import { StatePanel } from "@/ui/state-panel/StatePanel"

/** 论文预览阅读器的 Props */
interface PaperPreviewReaderProps {
  /** 论文 ID */
  paperId: string
  /** 论文元数据（用于去除重复标题） */
  paperMetadata?: PaperReaderMetadata | null
  /** 初始预览数据（可选，用于缓存） */
  initialPreview?: CommunityPaperPreviewResponse | null
  /** 阅读器状态：就绪/预热中/不可用 */
  readerState?: "ready" | "warming" | "unavailable"
}

/** 获取预览数据唯一标识（基于资源 ID 和生成时间） */
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

/** 获取预览数据完整签名（包含 HTML 内容） */
function getPreviewSignature(preview: CommunityPaperPreviewResponse | null | undefined): string | null {
  if (!preview) {
    return null
  }

  return [
    getPreviewIdentity(preview),
    preview.html_content ?? "",
  ].join("::")
}

/**
 * 规范化预览 HTML，将 LaTeX 环境转换为适合展示的 HTML 结构
 */
function normalizePreviewHtml(rawHtml: string): string {
  if (!rawHtml) {
    return ""
  }

  let normalized = rawHtml

  // 处理 LaTeX 代码块
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

  // 各种 LaTeX 命令清理
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

/**
 * 论文预览阅读器组件
 * 加载并渲染社区论文的结构化 HTML 预览内容，支持：
 * - LaTeX 数学公式渲染（KaTeX 引擎）
 * - 表格展开查看（Sheet 弹出）
 * - 数学块回退渲染
 * - 锚点平滑滚动
 *
 * 调用 GET /api/papers/{paperId}/preview 获取 HTML 预览数据
 */
export const PaperPreviewReader = forwardRef<HTMLDivElement, PaperPreviewReaderProps>(
  function PaperPreviewReader({ paperId, paperMetadata = null, initialPreview = null, readerState = "unavailable" }, ref) {
    const { t } = useTranslation()
    const contentRef = useRef<HTMLDivElement | null>(null)
    const preparedPreviewRef = useRef<{ signature: string; html: string } | null>(null)
    const [preview, setPreview] = useState<CommunityPaperPreviewResponse | null>(initialPreview)
    const [loading, setLoading] = useState(
      (!initialPreview || !initialPreview.html_content) && readerState !== "warming",
    )
    const [error, setError] = useState<string | null>(null)
    const [expandedTable, setExpandedTable] = useState<{ caption: string | null; html: string } | null>(null)

    // 加载或更新预览数据
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

    // HTML 净化：规范化 → 去除重复标题 → DOMPurify 清理
    const sanitizedHtml = useMemo(() => {
      if (!preview?.html_content || !previewSignature) {
        return ""
      }

      if (preparedPreviewRef.current?.signature === previewSignature) {
        return preparedPreviewRef.current.html
      }

      const normalized = normalizePreviewHtml(preview.html_content)
      const stripped = stripLeadingDuplicatePaperHeaderHtml(normalized, paperMetadata) ?? normalized
      const sanitized = DOMPurify.sanitize(stripped)
      preparedPreviewRef.current = {
        signature: previewSignature,
        html: sanitized,
      }
      return sanitized
    }, [paperMetadata, preview?.html_content, previewSignature])

    // 预加载预览增强器
    useEffect(() => {
      if (!previewSignature) {
        return
      }
      void preloadPaperPreviewEnhancer()
    }, [previewSignature])

    // 签名变更时清除展开的表格状态
    useEffect(() => {
      if (!previewSignature) {
        setExpandedTable(null)
      }
    }, [previewSignature])

    // 增强预览元素：渲染数学公式
    useEffect(() => {
      if (!sanitizedHtml || !contentRef.current || !previewSignature) {
        return
      }

      let cancelled = false
      const target = contentRef.current
      void (async () => {
        // KaTeX 数学块回退渲染
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

    // 为表格元素添加展开按钮
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

    // 处理点击事件：展开表格、锚点平滑滚动
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

    /** 附加 ref 回调 */
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
          className="flex h-full min-h-[320px] items-center rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-6 text-sm text-[color:var(--px-shell-muted)]"
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
          className="h-full min-h-[320px]"
        >
          <StatePanel
            className="h-full rounded-[24px] bg-[color:var(--px-shell-panel-strong)] shadow-none"
            title={t("community.reader.warmingTitle")}
            description={t("community.reader.warmingDescription")}
          />
        </div>
      )
    }

    if (!preview || error) {
      return (
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="h-full min-h-[320px]"
        >
          <StatePanel
            className="h-full rounded-[24px] border-dashed bg-[color:var(--px-shell-panel-strong)] shadow-none"
            title={t("community.reader.emptyTitle")}
            description={t("community.reader.emptyDescription")}
          />
        </div>
      )
    }

    return (
      <>
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-0 flex-col text-[color:var(--px-shell-ink)]"
        >
          <div
            data-testid="paper-preview-viewport"
            className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-6 py-5 xl:px-8 xl:py-6"
          >
            <div
              ref={contentRef}
              data-testid="paper-preview-content"
              data-reader-layout="scholarly"
              className="paper-preview-shell prose max-w-none text-[color:var(--px-shell-ink)] [&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold [&_h4]:mt-5 [&_h4]:text-lg [&_h4]:font-semibold [&_img]:rounded-2xl [&_img]:shadow-sm [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:border [&_pre]:p-4 [&_table]:w-full [&_td]:align-top [&_th]:align-bottom"
              dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
            />
          </div>
        </div>

        {/* 展开表格的 Sheet 弹出层 */}
        <Sheet open={Boolean(expandedTable)} onOpenChange={(open) => !open && setExpandedTable(null)}>
          <SheetContent
            side="right"
            className="w-[min(96vw,1160px)] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6 text-[color:var(--px-shell-ink)] sm:max-w-none"
          >
            <SheetHeader className="pr-10">
              <SheetTitle className="text-[color:var(--px-shell-ink)]">
                {expandedTable?.caption || t("community.reader.expandedTableTitle")}
              </SheetTitle>
              <SheetDescription className="text-[color:var(--px-shell-muted)]">
                {t("community.reader.expandedTableDescription")}
              </SheetDescription>
            </SheetHeader>

            <div
              data-testid="paper-preview-expanded-table"
              className="mt-6 h-[calc(100vh-8rem)] overflow-auto rounded-[20px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_82%,rgba(23,20,17,0.2))] bg-[color:var(--px-shell-panel-strong)] p-4"
            >
              <div
                className="paper-preview-shell prose max-w-none text-[color:var(--px-shell-ink)]"
                dangerouslySetInnerHTML={{ __html: expandedTable?.html ?? "" }}
              />
            </div>
          </SheetContent>
        </Sheet>
      </>
    )
  },
)
