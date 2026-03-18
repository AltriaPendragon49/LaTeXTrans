import {
  Download,
  Eye,
  Heart,
  Languages,
  MessageSquare,
  ShieldAlert,
  Star,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const ACTIONS = [
  { key: "translate", icon: Languages, labelKey: "community.actions.translate" },
  { key: "preview", icon: Eye, labelKey: "community.actions.preview" },
  { key: "download", icon: Download, labelKey: "community.actions.download" },
  { key: "like", icon: Heart, labelKey: "community.actions.like" },
  { key: "favorite", icon: Star, labelKey: "community.actions.favorite" },
  { key: "comment", icon: MessageSquare, labelKey: "community.actions.comment" },
  { key: "report", icon: ShieldAlert, labelKey: "community.actions.report" },
] as const

export function PaperActionShell() {
  const { t } = useTranslation()

  return (
    <TooltipProvider>
      <div className="rounded-[24px] border border-white/10 bg-[#1b1b1b] p-5 shadow-[0_22px_48px_-40px_rgba(0,0,0,0.84)]">
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-300">
            {t("community.actions.sectionTitle")}
          </p>
          <p className="max-w-2xl text-sm text-slate-400">
            {t("community.actions.sectionDescription")}
          </p>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {ACTIONS.map(({ key, icon: Icon, labelKey }) => (
            <Tooltip key={key}>
              <TooltipTrigger asChild>
                <div>
                  <Button
                    type="button"
                    disabled
                    aria-label={t(labelKey)}
                    variant="outline"
                    className="h-11 w-full justify-start rounded-[18px] border-white/10 bg-white/[0.025] px-4 text-slate-100"
                  >
                    <Icon className="h-4 w-4" />
                    <span>{t(labelKey)}</span>
                  </Button>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs bg-slate-100 text-slate-950">
                {t("community.actions.comingSoon")}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </div>
    </TooltipProvider>
  )
}
