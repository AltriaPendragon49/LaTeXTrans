import i18n from "i18next"
import { initReactI18next } from "react-i18next"

import de from "@/locales/de/common.json"
import en from "@/locales/en/common.json"
import es from "@/locales/es/common.json"
import fr from "@/locales/fr/common.json"
import ja from "@/locales/ja/common.json"
import ko from "@/locales/ko/common.json"
import ru from "@/locales/ru/common.json"
import zh from "@/locales/zh/common.json"
import { getInitialLanguage } from "@/i18n/config"

const resources = {
  en: { translation: en },
  zh: { translation: zh },
  ja: { translation: ja },
  ko: { translation: ko },
  de: { translation: de },
  fr: { translation: fr },
  es: { translation: es },
  ru: { translation: ru },
} as const

if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: ["en", "zh"],
    interpolation: {
      escapeValue: false,
    },
    returnNull: false,
    keySeparator: false,
    react: {
      useSuspense: false,
    },
  })
}

export default i18n
