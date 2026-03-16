import { describe, expect, it } from "vitest"

import deJson from "@/locales/de/common.json"
import enJson from "@/locales/en/common.json"
import esJson from "@/locales/es/common.json"
import frJson from "@/locales/fr/common.json"
import jaJson from "@/locales/ja/common.json"
import koJson from "@/locales/ko/common.json"
import ruJson from "@/locales/ru/common.json"
import zhJson from "@/locales/zh/common.json"

type LocaleMessages = Record<string, string>

const de = deJson as LocaleMessages
const en = enJson as LocaleMessages
const es = esJson as LocaleMessages
const fr = frJson as LocaleMessages
const ja = jaJson as LocaleMessages
const ko = koJson as LocaleMessages
const ru = ruJson as LocaleMessages
const zh = zhJson as LocaleMessages

const locales: Record<string, LocaleMessages> = { de, en, es, fr, ja, ko, ru, zh }

const expectedLanguageNames: LocaleMessages = {
  "language.name.en": "English",
  "language.name.zh": "中文",
  "language.name.ja": "日本語",
  "language.name.ko": "한국어",
  "language.name.de": "Deutsch",
  "language.name.fr": "Français",
  "language.name.es": "Español",
  "language.name.ru": "Русский",
}

describe("locale sanity", () => {
  it("keeps language self-names free from mojibake", () => {
    for (const [locale, messages] of Object.entries(locales)) {
      if (locale === "zh") {
        continue
      }

      for (const [key, value] of Object.entries(expectedLanguageNames)) {
        expect(messages[key]).toBe(value)
      }
    }

    expect(zh["language.name.en"]).toBe("英语")
    expect(zh["language.name.fr"]).toBe("法语")
  })

  it("keeps caption-localization copy free from broken question-mark arrows", () => {
    for (const [locale, messages] of Object.entries(locales)) {
      expect(messages["formatting.localizeCaptionsDescription"]).toContain("→")
      expect(
        messages["formatting.localizeCaptionsDescription"],
        `${locale} locale contains broken arrow punctuation`,
      ).not.toContain(" ? ")
    }
  })
})
