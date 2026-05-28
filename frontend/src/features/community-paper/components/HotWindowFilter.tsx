import { Check, Filter } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { useIsMobile } from "@/hooks/use-mobile"
import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"
import { Pill } from "@/ui/pill/Pill"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/ui/primitives/sheet"

/** 热榜时间窗口可选值 */
const WINDOW_VALUES = ["3d", "7d", "30d", "90d", "all"] as const

/** 默认时间窗口 */
const DEFAULT_WINDOW = "30d"

/** 热榜窗口筛选组件 Props */
interface HotWindowFilterProps {
  /** 当前选中的时间窗口 */
  selectedWindow: string
  /** 窗口变更回调 */
  onWindowChange: (window: string) => void
  className?: string
}

/**
 * 热榜窗口筛选组件
 * 在桌面端使用 Popover、移动端使用 Sheet 展示热榜时间窗口选项（3天/7天/30天/90天/全部）
 */
export function HotWindowFilter({
  selectedWindow,
  onWindowChange,
  className,
}: HotWindowFilterProps) {
  const { t } = useTranslation()
  const isMobile = useIsMobile()
  const [open, setOpen] = useState(false)

  const isDefault = selectedWindow === DEFAULT_WINDOW
  const selectedLabel = t(`community.feed.window.${selectedWindow}`)

  function handleSelect(value: string) {
    onWindowChange(value)
    setOpen(false)
  }

  const filterLabel = t("community.feed.window.filterLabel")

  const triggerButton = (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={filterLabel}
      title={filterLabel}
      className={cn(
        "h-10 w-10 rounded-full",
        !isDefault && "text-[color:var(--px-shell-accent)]",
        className,
      )}
    >
      <Filter className="h-4 w-4" />
    </Button>
  )

  const optionList = (
    <div className="space-y-1">
      {WINDOW_VALUES.map((value) => {
        const active = value === selectedWindow
        return (
          <button
            key={value}
            type="button"
            onClick={() => handleSelect(value)}
            className={cn(
              "flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm transition-colors",
              active
                ? "bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]"
                : "text-[color:var(--px-shell-ink)] hover:bg-[color:var(--px-shell-panel-strong)]",
            )}
          >
            <span className="font-medium">
              {t(`community.feed.window.${value}`)}
            </span>
            {active ? (
              <Check className="h-4 w-4 shrink-0 text-[color:var(--px-shell-accent)]" />
            ) : null}
          </button>
        )
      })}
    </div>
  )

  if (isMobile) {
    return (
      <div className={cn("inline-flex items-center gap-1.5", className)}>
        <Sheet open={open} onOpenChange={setOpen}>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={filterLabel}
            title={filterLabel}
            onClick={() => setOpen(true)}
            className={cn(
              "h-10 w-10 rounded-full",
              !isDefault && "text-[color:var(--px-shell-accent)]",
            )}
          >
            <Filter className="h-4 w-4" />
          </Button>

          {!isDefault ? (
            <Pill
              tone="accent"
              className="px-2 py-0.5 text-[10px] font-semibold normal-case tracking-normal"
            >
              {selectedLabel}
            </Pill>
          ) : null}

          <SheetContent
            side="bottom"
            className="rounded-t-[28px] px-4 pb-8 pt-6"
          >
            <SheetHeader className="mb-4 text-left">
              <SheetTitle>{t("community.feed.window.title")}</SheetTitle>
            </SheetHeader>
            {optionList}
          </SheetContent>
        </Sheet>
      </div>
    )
  }

  return (
    <div className={cn("inline-flex items-center gap-1.5", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          {triggerButton}
        </PopoverTrigger>

        <PopoverContent
          align="end"
          sideOffset={10}
          className="w-48 rounded-[20px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_28px_60px_-38px_rgba(15,23,42,0.4)]"
        >
          {optionList}
        </PopoverContent>
      </Popover>

      {!isDefault ? (
        <Pill
          tone="accent"
          className="px-2 py-0.5 text-[10px] font-semibold normal-case tracking-normal"
        >
          {selectedLabel}
        </Pill>
      ) : null}
    </div>
  )
}

export default HotWindowFilter
