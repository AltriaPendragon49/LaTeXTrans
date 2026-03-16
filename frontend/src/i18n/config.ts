export const UI_LANGUAGE_STORAGE_KEY = "latextrans.ui-language"

export const UI_LANGUAGES = [
  { code: "en", nativeLabel: "English", translationKey: "language.name.en" },
  { code: "zh", nativeLabel: "中文", translationKey: "language.name.zh" },
  { code: "ja", nativeLabel: "日本語", translationKey: "language.name.ja" },
  { code: "ko", nativeLabel: "한국어", translationKey: "language.name.ko" },
  { code: "de", nativeLabel: "Deutsch", translationKey: "language.name.de" },
  { code: "fr", nativeLabel: "Français", translationKey: "language.name.fr" },
  { code: "es", nativeLabel: "Español", translationKey: "language.name.es" },
  { code: "ru", nativeLabel: "Русский", translationKey: "language.name.ru" },
] as const

export type UILanguage = (typeof UI_LANGUAGES)[number]["code"]

const supportedLanguageCodes = new Set<UILanguage>(UI_LANGUAGES.map(({ code }) => code))

export function normalizeLanguageCode(language?: string | null): UILanguage {
  if (!language) {
    return "zh"
  }

  const normalizedLanguage = language.replace("_", "-").split("-")[0].toLowerCase() as UILanguage
  return supportedLanguageCodes.has(normalizedLanguage) ? normalizedLanguage : "zh"
}

export function getInitialLanguage(browserLanguage?: string): UILanguage {
  if (typeof window !== "undefined") {
    const storedLanguage = window.localStorage.getItem(UI_LANGUAGE_STORAGE_KEY)
    if (storedLanguage) {
      return normalizeLanguageCode(storedLanguage)
    }
  }

  if (browserLanguage) {
    return normalizeLanguageCode(browserLanguage)
  }

  if (typeof navigator !== "undefined") {
    return normalizeLanguageCode(navigator.language)
  }

  return "zh"
}

export function persistLanguage(language: UILanguage) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, language)
  }
}

export function getLocalizedLanguageOptions(
  translate: (key: string) => string,
) {
  return UI_LANGUAGES.map((language) => ({
    code: language.code,
    label: translate(language.translationKey),
    nativeLabel: language.nativeLabel,
  }))
}
