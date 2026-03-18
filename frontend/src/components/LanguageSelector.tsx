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
        className="h-11 w-[176px] rounded-2xl border border-white/10 bg-white/[0.04] pr-2 text-sm text-slate-100 shadow-[0_12px_32px_-20px_rgba(0,0,0,0.85)] transition-colors hover:bg-white/[0.06] focus:ring-2 focus:ring-slate-400"
      >
        <div className="flex items-center gap-2">
          <Languages className="h-4 w-4 text-slate-400" />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="min-w-[176px] border-white/10 bg-slate-950 text-slate-100">
        {UI_LANGUAGES.map((language) => (
          <SelectItem key={language.code} value={language.code} className="cursor-pointer focus:bg-white/[0.08] focus:text-white">
            <div className="flex items-center gap-2">
              <span className="font-medium">{language.nativeLabel}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
