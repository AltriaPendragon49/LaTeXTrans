import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { Label } from "@/ui/primitives/label"
import { Input } from "@/ui/input/Input"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SelectGroup,
  SelectLabel,
} from "@/ui/primitives/select"

import type { DomainInfo } from "@/features/rag-terminology/types"

export interface TermFormData {
  source_term: string
  target_term: string
  source_lang: string
  target_lang: string
  domain?: string
}

export interface TermFormModalProps {
  open: boolean
  onClose: () => void
  onSave: (data: TermFormData) => Promise<void>
  /** Pre-fill for editing */
  initial?: Partial<TermFormData>
  title: string
  /** Whether to show language fields (default true) */
  showLanguageFields?: boolean
  /** Domain options (from API) */
  domainOptions: DomainInfo[]
  /** Domain groups for grouped dropdown */
  domainGroups: Record<string, { label_zh: string; members: string[] }>
}

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
  { value: "ru", label: "Русский" },
  { value: "es", label: "Español" },
]

export function TermFormModal({
  open,
  onClose,
  onSave,
  initial,
  title,
  showLanguageFields = true,
  domainOptions,
  domainGroups,
}: TermFormModalProps) {
  const { t } = useTranslation()
  const [sourceTerm, setSourceTerm] = useState(initial?.source_term ?? "")
  const [targetTerm, setTargetTerm] = useState(initial?.target_term ?? "")
  const [sourceLang, setSourceLang] = useState(initial?.source_lang ?? "en")
  const [targetLang, setTargetLang] = useState(initial?.target_lang ?? "zh")
  const [domain, setDomain] = useState(initial?.domain ?? "")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setSourceTerm(initial?.source_term ?? "")
      setTargetTerm(initial?.target_term ?? "")
      setSourceLang(initial?.source_lang ?? "en")
      setTargetLang(initial?.target_lang ?? "zh")
      setDomain(initial?.domain ?? "")
    }
  }, [open, initial])

  async function handleSave() {
    if (!sourceTerm.trim() || !targetTerm.trim()) return
    setSaving(true)
    try {
      await onSave({
        source_term: sourceTerm.trim(),
        target_term: targetTerm.trim(),
        source_lang: sourceLang,
        target_lang: targetLang,
        domain: domain || undefined,
      })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  // Sort domain options: ungrouped first, then grouped
  const sortedOptions = [...domainOptions].sort((a, b) => {
    const aHasGroup = a.group != null
    const bHasGroup = b.group != null
    if (aHasGroup !== bHasGroup) return aHasGroup ? 1 : -1
    return a.value.localeCompare(b.value)
  })

  // Render grouped or flat domain options
  function renderDomainOptions() {
    if (Object.keys(domainGroups).length === 0) {
      // Flat list
      return sortedOptions.map((d) => (
        <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
      ))
    }

    // Grouped list
    const ungrouped = sortedOptions.filter((d) => d.group == null)
    const groupedByGroup: Record<string, DomainInfo[]> = {}
    for (const d of sortedOptions) {
      if (d.group) {
        if (!groupedByGroup[d.group]) groupedByGroup[d.group] = []
        groupedByGroup[d.group].push(d)
      }
    }

    return (
      <>
        {ungrouped.map((d) => (
          <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
        ))}
        {Object.entries(groupedByGroup).map(([groupKey, items]) => (
          <SelectGroup key={groupKey}>
            <SelectLabel>{groupKey}</SelectLabel>
            {items.map((d) => (
              <SelectItem key={d.value} value={d.value}>{d.label_zh || d.value}</SelectItem>
            ))}
          </SelectGroup>
        ))}
      </>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-[color:var(--px-shell-surface)] p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-[color:var(--px-shell-ink)]">{title}</h2>
        <p className="mt-1 text-sm text-[color:var(--px-shell-muted)]">{t("ragTerminology.dialog.description")}</p>
        <div className="mt-5 space-y-4">
          <div className="space-y-2">
            <Label>{t("ragTerminology.dialog.sourceTerm")}</Label>
            <Input value={sourceTerm} onChange={(e) => setSourceTerm(e.target.value)} placeholder="e.g. attention mechanism" />
          </div>
          <div className="space-y-2">
            <Label>{t("ragTerminology.dialog.targetTerm")}</Label>
            <Input value={targetTerm} onChange={(e) => setTargetTerm(e.target.value)} placeholder="e.g. 注意力机制" />
          </div>
          {showLanguageFields && (
            <>
              <div className="space-y-2">
                <Label>{t("ragTerminology.dialog.sourceLang")}</Label>
                <Select value={sourceLang} onValueChange={setSourceLang}>
                  <SelectTrigger>
                    <SelectValue placeholder="en" />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGE_OPTIONS.map((l) => (
                      <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{t("ragTerminology.dialog.targetLang")}</Label>
                <Select value={targetLang} onValueChange={setTargetLang}>
                  <SelectTrigger>
                    <SelectValue placeholder="zh" />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGE_OPTIONS.map((l) => (
                      <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
          <div className="space-y-2">
            <Label>{t("ragTerminology.dialog.domain")}</Label>
            <Select value={domain} onValueChange={setDomain}>
              <SelectTrigger>
                <SelectValue placeholder={t("ragTerminology.dialog.selectDomain")} />
              </SelectTrigger>
              <SelectContent>
                {renderDomainOptions()}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>{t("common.actions.cancel")}</Button>
          <Button onClick={handleSave} disabled={!sourceTerm.trim() || !targetTerm.trim() || saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {t("common.actions.save")}
          </Button>
        </div>
      </div>
    </div>
  )
}
