/**
 * 论文阅读器 HTML 处理工具
 * 从 HTML 中剥离重复的论文头部信息（标题+作者），避免在正文预览中出现重复
 */

/** 从作者数组中提取作者姓名列表 */
function extractAuthorNames(authors: unknown[]): string {
  return authors
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

/** 将文本标准化为可比较的格式（去空白、小写） */
function normalizeComparableText(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, " ").trim().toLowerCase()
}

/** 判断某个 DOM 元素是否包含重复的论文标题和作者信息 */
function isDuplicatePaperHeaderElement(
  element: Element,
  normalizedTitle: string,
  normalizedAuthors: string,
) {
  const normalizedText = normalizeComparableText(element.textContent)
  if (!normalizedText) {
    return false
  }

  const containsTitle = Boolean(normalizedTitle) && normalizedText.includes(normalizedTitle)
  const containsAuthors = Boolean(normalizedAuthors) && normalizedText.includes(normalizedAuthors)
  if (containsTitle && containsAuthors) {
    return true
  }

  // 检查子元素是否分别匹配标题和作者
  const childTexts = Array.from(element.children).map((child) => normalizeComparableText(child.textContent))
  const hasTitleChild = Boolean(normalizedTitle) && childTexts.some((text) => text === normalizedTitle)
  const hasAuthorChild = Boolean(normalizedAuthors) && childTexts.some((text) => text === normalizedAuthors)
  return hasTitleChild && hasAuthorChild
}

/** 论文元数据（用于去重匹配） */
export interface PaperReaderMetadata {
  title?: string | null
  authors?: unknown[]
}

/**
 * 去除 HTML 中前导的重复论文头部元素（标题、作者信息）
 * 通过解析 HTML，匹配并移除包含论文标题和作者的重复开头节点
 *
 * @param rawHtml - 原始 HTML 字符串
 * @param paper - 论文元数据（标题、作者）
 * @returns 去除重复头部后的 HTML 字符串
 */
export function stripLeadingDuplicatePaperHeaderHtml(
  rawHtml: string | null | undefined,
  paper: PaperReaderMetadata | null | undefined,
) {
  if (!rawHtml || typeof DOMParser === "undefined") {
    return rawHtml ?? null
  }

  const parser = new DOMParser()
  const document = parser.parseFromString(rawHtml, "text/html")
  const root = document.body.querySelector("article") ?? document.body
  const normalizedTitle = normalizeComparableText(paper?.title)
  const normalizedAuthors = normalizeComparableText(extractAuthorNames(paper?.authors ?? []))

  let current = root.firstElementChild
  while (current) {
    const normalizedText = normalizeComparableText(current.textContent)
    const isDuplicateTitle = Boolean(normalizedTitle) && normalizedText === normalizedTitle
    const isDuplicateAuthors = Boolean(normalizedAuthors) && normalizedText === normalizedAuthors
    const isDuplicateHeader = isDuplicatePaperHeaderElement(current, normalizedTitle, normalizedAuthors)
    if (!isDuplicateTitle && !isDuplicateAuthors && !isDuplicateHeader) {
      break
    }
    const next = current.nextElementSibling
    current.remove()
    current = next
  }

  return root === document.body ? document.body.innerHTML : root.outerHTML
}
