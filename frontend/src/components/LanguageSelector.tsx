import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { UI_LANGUAGES, persistLanguage, type UILanguage } from "@/i18n/config"

export function LanguageSelector() {
  const { i18n, t } = useTranslation()
  const currentLanguage = (i18n.resolvedLanguage ?? i18n.language) as UILanguage

  const handleValueChange = async (language: string) => {
    const nextLanguage = language as UILanguage
    persistLanguage(nextLanguage)
    await i18n.changeLanguage(nextLanguage)
  }

  return (
    <Select value={currentLanguage} onValueChange={handleValueChange}>
      <SelectTrigger
        aria-label={t("common.choose_global_interface_language")}
        className="w-[164px] border-slate-200 bg-white/90 pr-2 text-sm shadow-sm transition-colors hover:bg-accent/60 focus:ring-2 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-900/90"
      >
        <div className="flex items-center gap-2">
          <Languages className="h-4 w-4 text-slate-500 dark:text-slate-300" />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="min-w-[164px]">
        {UI_LANGUAGES.map((language) => (
          <SelectItem key={language.code} value={language.code} className="cursor-pointer">
            <div className="flex items-center gap-2">
              <span className="font-medium">{language.nativeLabel}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
