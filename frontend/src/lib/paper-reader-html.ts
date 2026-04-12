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

function normalizeComparableText(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, " ").trim().toLowerCase()
}

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

  const childTexts = Array.from(element.children).map((child) => normalizeComparableText(child.textContent))
  const hasTitleChild = Boolean(normalizedTitle) && childTexts.some((text) => text === normalizedTitle)
  const hasAuthorChild = Boolean(normalizedAuthors) && childTexts.some((text) => text === normalizedAuthors)
  return hasTitleChild && hasAuthorChild
}

export interface PaperReaderMetadata {
  title?: string | null
  authors?: unknown[]
}

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
