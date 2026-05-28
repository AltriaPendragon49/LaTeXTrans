/**
 * 论文预览增强器
 * 使用 KaTeX 对论文预览 HTML 中的 LaTeX 数学公式进行渲染
 */
type KatexModule = typeof import("katex")
type RenderMathInElement = typeof import("katex/contrib/auto-render").default

/** 论文预览增强上下文 */
export interface PaperPreviewEnhancementContext {
  previewAssetId?: string
  previewSignature: string
}

/** 论文预览增强器接口 */
interface PaperPreviewEnhancer {
  enhance: (element: HTMLElement, context: PaperPreviewEnhancementContext) => void
}

let paperPreviewEnhancerPromise: Promise<PaperPreviewEnhancer> | null = null
let paperPreviewEnhancerStylesPromise: Promise<unknown> | null = null

/** KaTeX 渲染时的 LaTeX 宏定义 */
const READER_MATH_MACROS = {
  "\\mean": "\\operatorname{mean}",
  "\\argmax": "\\operatorname*{arg\\,max}",
  "\\argmin": "\\operatorname*{arg\\,min}",
  "\\trilerp": "\\operatorname{trilerp}",
  "\\softmax": "\\operatorname{softmax}",
  "\\Re": "\\mathbb{R}",
} as const

/**
 * 规范化块级数学公式的源码，去除外围 $$ 定界符
 */
function normalizeDisplayMathSource(source: string): string {
  const trimmed = source.trim()
  if (trimmed.startsWith("$$") && trimmed.endsWith("$$")) {
    return trimmed.slice(2, -2).trim()
  }
  return trimmed
}

/** 获取 auto-render 渲染配置，包括各种 LaTeX 环境定界符 */
function getPaperPreviewEnhancerOptions() {
  return {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\begin{equation}", right: "\\end{equation}", display: true },
      { left: "\\begin{equation*}", right: "\\end{equation*}", display: true },
      { left: "\\begin{align}", right: "\\end{align}", display: true },
      { left: "\\begin{align*}", right: "\\end{align*}", display: true },
      { left: "\\begin{alignat}", right: "\\end{alignat}", display: true },
      { left: "\\begin{alignat*}", right: "\\end{alignat*}", display: true },
      { left: "\\begin{gather}", right: "\\end{gather}", display: true },
      { left: "\\begin{gather*}", right: "\\end{gather*}", display: true },
      { left: "\\begin{multline}", right: "\\end{multline}", display: true },
      { left: "\\begin{multline*}", right: "\\end{multline*}", display: true },
      { left: "\\begin{eqnarray}", right: "\\end{eqnarray}", display: true },
      { left: "\\begin{eqnarray*}", right: "\\end{eqnarray*}", display: true },
      { left: "\\begin{split}", right: "\\end{split}", display: true },
      { left: "\\begin{CD}", right: "\\end{CD}", display: true },
    ],
    ignoredClasses: ["paper-preview__math-block"],
    macros: READER_MATH_MACROS,
    strict: "ignore",
    throwOnError: false,
  } as Parameters<RenderMathInElement>[1]
}

/** 懒加载 KaTeX 并构建增强器 */
async function loadPaperPreviewEnhancer(): Promise<PaperPreviewEnhancer> {
  if (!paperPreviewEnhancerStylesPromise) {
    paperPreviewEnhancerStylesPromise = import("katex/dist/katex.min.css")
  }

  if (!paperPreviewEnhancerPromise) {
    paperPreviewEnhancerPromise = Promise.all([
      import("katex") as Promise<KatexModule>,
      import("katex/contrib/auto-render"),
      paperPreviewEnhancerStylesPromise,
    ]).then(([katexModule, autoRenderModule]) => {
      const katex = katexModule.default
      const renderMathInElement = autoRenderModule.default
      const options = getPaperPreviewEnhancerOptions()

      return {
        enhance(element: HTMLElement) {
          // 先渲染预先标记的块级数学公式
          element.querySelectorAll<HTMLElement>(".paper-preview__math-block").forEach((block) => {
            const source = normalizeDisplayMathSource(block.textContent || "")
            if (!source) {
              return
            }

            block.innerHTML = katex.renderToString(source, {
              displayMode: true,
              macros: READER_MATH_MACROS,
              strict: "ignore",
              throwOnError: false,
            })
          })
          // 再使用 auto-render 扫描内联和标准定界符公式
          renderMathInElement(element, options)
        },
      }
    })
  }

  return paperPreviewEnhancerPromise
}

/**
 * 预加载论文预览增强器（KaTeX 和样式表），提前启动加载
 * @returns 返回一个解析为 PaperPreviewEnhancer 的 Promise
 */
export function preloadPaperPreviewEnhancer(): Promise<PaperPreviewEnhancer> {
  return loadPaperPreviewEnhancer()
}

/**
 * 对指定 DOM 元素中的 LaTeX 数学公式进行渲染增强
 * @param element - 包含 LaTeX 公式的 DOM 元素
 * @param context - 增强上下文（asset ID 和签名等）
 */
export async function enhancePaperPreviewElement(
  element: HTMLElement,
  context: PaperPreviewEnhancementContext,
): Promise<void> {
  const enhancer = await loadPaperPreviewEnhancer()
  enhancer.enhance(element, context)
}
