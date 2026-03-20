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
        className="h-11 w-[176px] rounded-2xl border border-[color:var(--shell-border)] bg-[var(--shell-pill)] pr-2 text-sm text-[var(--shell-heading)] shadow-sm transition-colors hover:bg-[var(--shell-pill-hover)] focus:ring-2 focus:ring-slate-400"
      >
        <div className="flex items-center gap-2">
          <Languages className="h-4 w-4 text-[var(--shell-icon)]" />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="min-w-[176px] border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] text-[var(--shell-heading)]">
        {UI_LANGUAGES.map((language) => (
          <SelectItem key={language.code} value={language.code} className="cursor-pointer focus:bg-[var(--shell-pill-hover)] focus:text-[var(--shell-heading)]">
            <div className="flex items-center gap-2">
              <span className="font-medium">{language.nativeLabel}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
