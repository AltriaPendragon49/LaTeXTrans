import type { CommunityPaperReaderMode } from "@/types/community"

/**
 * 判断论文是否拥有翻译后的 PDF 资源
 * 综合检查 assets.translated_pdf、reader.translated.kind、latest_asset 和 trans_status
 */
function hasTranslatedPdfResource(
  paper: {
    assets?: { translated_pdf?: unknown } | null
    latest_asset?: { asset_type?: string | null } | null
    trans_status?: string | null
  } | null | undefined,
  reader: {
    translated?: { kind?: string | null } | null
  } | null | undefined,
) {
  return Boolean(
    paper?.assets?.translated_pdf ||
      reader?.translated?.kind === "translated_pdf" ||
      paper?.latest_asset?.asset_type === "translated_pdf" ||
      paper?.trans_status === "completed",
  )
}

/**
 * 判断论文是否拥有源 PDF 资源
 * 检查 reader.source.kind 或 arxiv_id
 */
function hasSourcePdfResource(
  paper: {
    arxiv_id?: string | null
  } | null | undefined,
  reader: {
    source?: { kind?: string | null } | null
  } | null | undefined,
) {
  return Boolean(reader?.source?.kind === "source_pdf" || paper?.arxiv_id)
}

/**
 * 根据论文资源和阅读器状态，解析出当前可用的阅读模式列表
 * 可用模式：source（原文）、translated_pdf（翻译 PDF）、bilingual_compare（双语对比）
 */
export function resolveAvailableModes(
  paper: {
    arxiv_id?: string | null
    trans_status?: string | null
    assets?: { translated_pdf?: unknown } | null
    latest_asset?: { asset_type?: string | null } | null
  } | null | undefined,
  preview: { html_content?: string | null } | null | undefined,
  reader: {
    available_modes?: CommunityPaperReaderMode[] | null
    source?: { kind?: string | null } | null
    translated?: { kind?: string | null; html_content?: string | null } | null
  } | null | undefined,
): CommunityPaperReaderMode[] {
  void preview
  const modes: CommunityPaperReaderMode[] = ["source"]
  const rawModes = reader?.available_modes ?? []
  const allowTranslatedPdf =
    rawModes.includes("translated_pdf") ||
    (rawModes.includes("translated") && hasTranslatedPdfResource(paper, reader)) ||
    hasTranslatedPdfResource(paper, reader)

  if (allowTranslatedPdf) {
    modes.push("translated_pdf")
  }
  if (allowTranslatedPdf && hasSourcePdfResource(paper, reader)) {
    modes.push("bilingual_compare")
  }

  return modes
}

/**
 * 根据用户偏好、可用模式和设备类型，确定首选的阅读模式
 * 移动端优先 translated_pdf → source
 * 桌面端优先级：用户偏好 → bilingual_compare → source → translated_pdf
 */
export function resolvePreferredMode(
  preferredMode: CommunityPaperReaderMode | undefined,
  availableModes: CommunityPaperReaderMode[],
  options?: { isMobile?: boolean },
): CommunityPaperReaderMode {
  if (options?.isMobile) {
    if (availableModes.includes("translated_pdf")) {
      return "translated_pdf"
    }
    if (availableModes.includes("source")) {
      return "source"
    }
  }

  if (preferredMode === "translated") {
    if (availableModes.includes("bilingual_compare")) {
      return "bilingual_compare"
    }
    if (availableModes.includes("translated_pdf")) {
      return "translated_pdf"
    }
    if (availableModes.includes("source")) {
      return "source"
    }
  }
  if (preferredMode && availableModes.includes(preferredMode)) {
    return preferredMode
  }
  if (availableModes.includes("bilingual_compare")) {
    return "bilingual_compare"
  }
  if (availableModes.includes("source")) {
    return "source"
  }
  if (availableModes.includes("translated_pdf")) {
    return "translated_pdf"
  }
  return "source"
}

/**
 * 根据翻译状态和阅读器状态返回对应的中文阶段标签
 */
export function resolveStageLabel(
  transStatus: string | undefined,
  readerState: "ready" | "warming" | "unavailable",
  hasTranslatedMode: boolean,
  t: (key: string) => string,
) {
  if (hasTranslatedMode && readerState === "ready") {
    return t("community.detail.stage.translatedReady")
  }
  if (transStatus === "queued" || transStatus === "processing" || readerState === "warming") {
    return t("community.detail.stage.generating")
  }
  if (readerState === "ready") {
    return t("community.detail.stage.sourceReady")
  }
  return t("community.detail.stage.unavailable")
}
