type KatexModule = typeof import("katex")
type RenderMathInElement = typeof import("katex/contrib/auto-render").default

export interface PaperPreviewEnhancementContext {
  previewAssetId?: string
  previewSignature: string
}

interface PaperPreviewEnhancer {
  enhance: (element: HTMLElement, context: PaperPreviewEnhancementContext) => void
}

let paperPreviewEnhancerPromise: Promise<PaperPreviewEnhancer> | null = null
let paperPreviewEnhancerStylesPromise: Promise<unknown> | null = null

const READER_MATH_MACROS = {
  "\\mean": "\\operatorname{mean}",
  "\\argmax": "\\operatorname*{arg\\,max}",
  "\\argmin": "\\operatorname*{arg\\,min}",
  "\\trilerp": "\\operatorname{trilerp}",
  "\\softmax": "\\operatorname{softmax}",
  "\\Re": "\\mathbb{R}",
} as const

function normalizeDisplayMathSource(source: string): string {
  const trimmed = source.trim()
  if (trimmed.startsWith("$$") && trimmed.endsWith("$$")) {
    return trimmed.slice(2, -2).trim()
  }
  return trimmed
}

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
          renderMathInElement(element, options)
        },
      }
    })
  }

  return paperPreviewEnhancerPromise
}

export function preloadPaperPreviewEnhancer(): Promise<PaperPreviewEnhancer> {
  return loadPaperPreviewEnhancer()
}

export async function enhancePaperPreviewElement(
  element: HTMLElement,
  context: PaperPreviewEnhancementContext,
): Promise<void> {
  const enhancer = await loadPaperPreviewEnhancer()
  enhancer.enhance(element, context)
}
