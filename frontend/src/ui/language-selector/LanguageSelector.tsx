import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/ui/primitives/select"
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
        className="h-11 w-[176px] rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] pr-2 text-sm text-[color:var(--px-shell-ink)] shadow-sm transition-colors hover:bg-[color:var(--px-shell-panel)] focus:ring-2 focus:ring-[color:var(--px-shell-accent)]/20"
      >
        <div className="flex items-center gap-2">
          <Languages className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="min-w-[176px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]">
        {UI_LANGUAGES.map((language) => (
          <SelectItem
            key={language.code}
            value={language.code}
            className="cursor-pointer focus:bg-[color:var(--px-shell-accent-soft)] focus:text-[color:var(--px-shell-ink)]"
          >
            <div className="flex items-center gap-2">
              <span className="font-medium">{language.nativeLabel}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
