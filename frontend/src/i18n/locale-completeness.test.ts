import { describe, expect, it } from "vitest"

import de from "@/locales/de/common.json"
import en from "@/locales/en/common.json"
import es from "@/locales/es/common.json"
import fr from "@/locales/fr/common.json"
import ja from "@/locales/ja/common.json"
import ko from "@/locales/ko/common.json"
import ru from "@/locales/ru/common.json"
import zh from "@/locales/zh/common.json"

const locales = {
  de,
  en,
  es,
  fr,
  ja,
  ko,
  ru,
  zh,
} as const

describe("locale completeness", () => {
  const expectedKeys = Object.keys(en).sort()

  it("keeps every locale aligned with the English key set", () => {
    for (const [locale, messages] of Object.entries(locales)) {
      expect(
        Object.keys(messages).sort(),
        `${locale} locale is missing translation keys`,
      ).toEqual(expectedKeys)
    }
  })
})
