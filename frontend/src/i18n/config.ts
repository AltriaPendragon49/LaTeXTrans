/**
 * 国际化（i18n）配置
 * 管理 UI 语言列表、语言检测、存储和切换逻辑
 */

/** localStorage 中存储界面语言的键名 */
export const UI_LANGUAGE_STORAGE_KEY = "latextrans.ui-language"

/** 支持的界面语言列表 */
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

/** 界面语言代码类型 */
export type UILanguage = (typeof UI_LANGUAGES)[number]["code"]

const supportedLanguageCodes = new Set<UILanguage>(UI_LANGUAGES.map(({ code }) => code))

/**
 * 标准化语言代码为支持的 UILanguage 类型
 * @param language - 原始语言代码（如 "en-US"、"zh-CN"）
 * @returns 匹配到的 UILanguage 代码，不匹配时默认返回 "zh"
 */
export function normalizeLanguageCode(language?: string | null): UILanguage {
  if (!language) {
    return "zh"
  }

  const normalizedLanguage = language.replace("_", "-").split("-")[0].toLowerCase() as UILanguage
  return supportedLanguageCodes.has(normalizedLanguage) ? normalizedLanguage : "zh"
}

/**
 * 获取初始界面语言
 * 优先级：localStorage > 传入的浏览器语言 > navigator.language > 默认 "zh"
 * @param browserLanguage - 浏览器语言代码
 */
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

/**
 * 持久化界面语言到 localStorage
 * @param language - 要持久化的语言代码
 */
export function persistLanguage(language: UILanguage) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, language)
  }
}

/**
 * 获取带翻译标签的语言选项列表（用于 UI 展示）
 * @param translate - i18n 翻译函数
 */
export function getLocalizedLanguageOptions(
  translate: (key: string) => string,
) {
  return UI_LANGUAGES.map((language) => ({
    code: language.code,
    label: translate(language.translationKey),
    nativeLabel: language.nativeLabel,
  }))
}
