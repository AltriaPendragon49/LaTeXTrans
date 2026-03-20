import {
  Download,
  Eye,
  Languages,
  Timer,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

interface ActionConfig {
  key: string
  icon: typeof Languages
  labelKey: string
  enabled: boolean
  onClick?: () => void
}

interface PaperActionShellProps {
  onTranslate: () => void
  onPreview: () => void
  onDownload: () => void
  onViewProgress: () => void
  canTranslate: boolean
  canViewProgress: boolean
  canDownload: boolean
}

export function PaperActionShell({
  onTranslate,
  onPreview,
  onDownload,
  onViewProgress,
  canTranslate,
  canViewProgress,
  canDownload,
}: PaperActionShellProps) {
  const { t } = useTranslation()
  const actions: ActionConfig[] = [
    { key: "translate", icon: Languages, labelKey: "community.actions.translate", enabled: canTranslate, onClick: onTranslate },
    { key: "progress", icon: Timer, labelKey: "community.actions.viewProgress", enabled: canViewProgress, onClick: onViewProgress },
    { key: "preview", icon: Eye, labelKey: "community.actions.preview", enabled: true, onClick: onPreview },
    { key: "download", icon: Download, labelKey: "community.actions.download", enabled: canDownload, onClick: onDownload },
  ]

  return (
    <div className="rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-5 shadow-[var(--shell-panel-shadow)]">
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[var(--shell-text)]">
          {t("community.actions.sectionTitle")}
        </p>
        <p className="max-w-2xl text-sm text-[var(--shell-text-muted)]">
          {t("community.actions.sectionDescription")}
        </p>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {actions.map(({ key, icon: Icon, labelKey, enabled, onClick }) => (
          <Button
            key={key}
            type="button"
            disabled={!enabled}
            aria-label={t(labelKey)}
            onClick={onClick}
            variant="outline"
            className="h-11 w-full justify-start rounded-[18px] border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)]"
          >
            <Icon className="h-4 w-4" />
            <span>{t(labelKey)}</span>
          </Button>
        ))}
      </div>
    </div>
  )
}
