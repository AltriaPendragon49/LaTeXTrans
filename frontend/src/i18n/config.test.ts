import { beforeEach, describe, expect, it } from "vitest"

import {
  UI_LANGUAGE_STORAGE_KEY,
  getInitialLanguage,
  normalizeLanguageCode,
} from "@/i18n/config"

describe("ui language config", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it("normalizes supported codes and falls back to zh", () => {
    expect(normalizeLanguageCode("en-US")).toBe("en")
    expect(normalizeLanguageCode("ja_JP")).toBe("ja")
    expect(normalizeLanguageCode("pt-BR")).toBe("zh")
    expect(normalizeLanguageCode(undefined)).toBe("zh")
  })

  it("prefers stored language over browser language", () => {
    localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, "fr")

    expect(getInitialLanguage("en-US")).toBe("fr")
  })

  it("uses browser language when storage is empty", () => {
    expect(getInitialLanguage("de-DE")).toBe("de")
  })
})
