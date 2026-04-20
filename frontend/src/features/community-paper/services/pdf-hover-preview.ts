import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist/types/src/display/api"

export interface PdfHoverPreviewImage {
  dataUrl: string
  width: number
  height: number
}

const PDF_HOVER_RENDER_CACHE = new Map<string, Promise<PdfHoverPreviewImage>>()
const PDF_HOVER_TARGET_WIDTH = 1280

let pdfjsLoaderPromise: Promise<typeof import("react-pdf").pdfjs> | null = null

async function loadPdfJs() {
  if (!pdfjsLoaderPromise) {
    pdfjsLoaderPromise = import("react-pdf").then(({ pdfjs }) => {
      pdfjs.GlobalWorkerOptions.workerSrc = new URL(
        "pdfjs-dist/build/pdf.worker.min.mjs",
        import.meta.url,
      ).toString()
      return pdfjs
    })
  }

  return pdfjsLoaderPromise
}

export function preloadPdfHoverPreviewRenderer() {
  if (typeof window === "undefined") {
    return Promise.resolve(null)
  }

  return loadPdfJs()
}

async function renderPdfFirstPageToImageDataUrl(url: string): Promise<PdfHoverPreviewImage> {
  if (typeof window === "undefined") {
    throw new Error("PDF hover previews require a browser environment")
  }

  const pdfjs = await loadPdfJs()
  const loadingTask = pdfjs.getDocument(url)

  let pdfDocument: PDFDocumentProxy | null = null
  let page: PDFPageProxy | null = null

  try {
    pdfDocument = await loadingTask.promise
    page = await pdfDocument.getPage(1)

    const baseViewport = page.getViewport({ scale: 1 })
    const renderScale = PDF_HOVER_TARGET_WIDTH / baseViewport.width
    const renderViewport = page.getViewport({ scale: renderScale })

    const canvas = document.createElement("canvas")
    canvas.width = Math.round(renderViewport.width)
    canvas.height = Math.round(renderViewport.height)

    const context = canvas.getContext("2d", { alpha: false })
    if (!context) {
      throw new Error("Unable to create canvas context for PDF hover preview")
    }

    await page.render({
      canvas,
      canvasContext: context,
      viewport: renderViewport,
    }).promise

    return {
      dataUrl: canvas.toDataURL("image/png"),
      width: canvas.width,
      height: canvas.height,
    }
  } finally {
    page?.cleanup()
    await pdfDocument?.destroy()
  }
}

export function loadPdfHoverPreview(url: string): Promise<PdfHoverPreviewImage> {
  const normalizedUrl = String(url || "").trim()
  if (!normalizedUrl) {
    return Promise.reject(new Error("PDF hover preview URL is required"))
  }

  const cached = PDF_HOVER_RENDER_CACHE.get(normalizedUrl)
  if (cached) {
    return cached
  }

  const renderPromise = renderPdfFirstPageToImageDataUrl(normalizedUrl).catch((error) => {
    PDF_HOVER_RENDER_CACHE.delete(normalizedUrl)
    throw error
  })

  PDF_HOVER_RENDER_CACHE.set(normalizedUrl, renderPromise)
  return renderPromise
}
