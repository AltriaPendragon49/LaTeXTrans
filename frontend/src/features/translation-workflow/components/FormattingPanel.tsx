import type { ReactNode } from "react"
import { AlignJustify, BookOpen, Columns2, FileText, Indent, Maximize2, Quote, Type } from "lucide-react"
import { useTranslation } from "react-i18next"

import { FormFieldShell } from "@/ui/form-field-shell/FormFieldShell"
import { Input } from "@/ui/input/Input"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import { cn } from "@/lib/utils"
import { Label } from "@/ui/primitives/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/primitives/select"
import type { FormattingConfig } from "@/types/config"

/** 数值字段 Props */
interface NumericFieldProps {
  id: string
  label: string
  icon: ReactNode
  value: number | undefined | null
  onChange: (value: number | null) => void
  min?: number
  max?: number
  step?: number
  placeholder?: string
  tooltip?: string
}

/**
 * 数值输入字段组件
 * 带开关控制的数字输入，关闭时显示占位符"保持原文"，适用于行间距、字号等格式设置
 */
function NumericField({
  id,
  label,
  icon,
  value,
  onChange,
  min,
  max,
  step,
  placeholder,
  tooltip,
}: NumericFieldProps) {
  const { t } = useTranslation()
  const enabled = value !== undefined && value !== null

  return (
    <FormFieldShell
      label={(
        <Label htmlFor={id} className="flex cursor-pointer select-none items-center gap-2 text-sm">
          {label}
        </Label>
      )}
      icon={icon}
      headerAside={(
        <ToggleSwitch
          id={`${id}-switch`}
          checked={enabled}
          onCheckedChange={(on) => onChange(on ? (value ?? (min ?? 1)) : null)}
        />
      )}
    >
      <Input
        id={id}
        type="number"
        min={min}
        max={max}
        step={step ?? 0.1}
        placeholder={enabled ? "" : (placeholder ?? t("formatting.keepOriginal"))}
        value={enabled ? (value ?? "") : ""}
        disabled={!enabled}
        onChange={(event) => {
          const nextValue = parseFloat(event.target.value)
          onChange(Number.isNaN(nextValue) ? null : nextValue)
        }}
        className={cn("h-8 text-sm transition-opacity duration-200", !enabled && "cursor-not-allowed opacity-40")}
        title={tooltip}
      />
    </FormFieldShell>
  )
}

/** 下拉选择字段 Props */
interface SelectFieldProps {
  id: string
  label: string
  icon: ReactNode
  value: string | undefined | null
  onChange: (value: string | null) => void
  options: { value: string; label: string }[]
}

/**
 * 下拉选择字段组件
 * 用于列模式、边距、参考文献样式等格式项的下拉选择，默认选项为"保持原文"
 */
function SelectField({ id, label, icon, value, onChange, options }: SelectFieldProps) {
  const { t } = useTranslation()

  return (
    <FormFieldShell
      label={<Label htmlFor={id} className="flex items-center gap-2 text-sm">{label}</Label>}
      icon={icon}
    >
      <Select value={value ?? "__keep__"} onValueChange={(nextValue) => onChange(nextValue === "__keep__" ? null : nextValue)}>
        <SelectTrigger id={id} className="h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__keep__">{t("formatting.keepOriginal")}</SelectItem>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FormFieldShell>
  )
}

/** 开关行字段 Props */
interface ToggleRowProps {
  id: string
  label: string
  description: string
  icon: ReactNode
  value: boolean | undefined | null
  onChange: (value: boolean | null) => void
}

/**
 * 开关行字段组件
 * 用于首行缩进、本地化图表标题等布尔类型格式开关
 */
function ToggleRow({ id, label, description, icon, value, onChange }: ToggleRowProps) {
  return (
    <FormFieldShell
      label={<Label htmlFor={id} className="cursor-pointer text-sm">{label}</Label>}
      icon={icon}
      description={description}
      headerAside={<ToggleSwitch id={id} checked={value === true} onCheckedChange={(on) => onChange(on ? true : null)} />}
      bodyClassName="mt-0"
    />
  )
}

/** 格式化面板 Props */
export interface FormattingPanelProps {
  /** 当前格式化配置值 */
  value: FormattingConfig
  /** 配置变更回调，接收部分更新 */
  onChange: (patch: Partial<FormattingConfig>) => void
  /** 目标语言代码，用于判断是否显示中文字体选项 */
  targetLanguage?: string
  className?: string
}

/** 中日韩语言集合，用于判断是否需要显示中文字体选项 */
const CJK_LANGS = new Set(["zh", "ja", "ko"])

/**
 * 格式化面板组件
 * 提供行间距、字号、分栏、页边距、参考文献格式、引文格式、中文字体、
 * 首行缩进和图表标题本地化等排版格式的配置界面
 */
export function FormattingPanel({ value, onChange, targetLanguage, className }: FormattingPanelProps) {
  const isCjk = targetLanguage ? CJK_LANGS.has(targetLanguage) : false
  const { t } = useTranslation()

  return (
    <div className={cn("space-y-3", className)}>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <NumericField
          id="fmt-line-spacing"
          label={t("formatting.lineSpacing")}
          icon={<AlignJustify className="h-4 w-4" />}
          value={value.line_spacing}
          onChange={(nextValue) => onChange({ line_spacing: nextValue ?? undefined })}
          min={1.0}
          max={2.5}
          step={0.1}
          placeholder={t("formatting.keepOriginalLineSpacing")}
          tooltip={t("formatting.line_spacing_multiplier_recommended_range_1_0_2_5")}
        />
        <NumericField
          id="fmt-font-size"
          label={t("formatting.fontSize")}
          icon={<Type className="h-4 w-4" />}
          value={value.font_size}
          onChange={(nextValue) => onChange({ font_size: nextValue ?? undefined })}
          min={8}
          max={14}
          step={0.5}
          placeholder={t("formatting.keepOriginalFontSize")}
          tooltip={t("formatting.global_font_size_recommended_range_8_14_pt")}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectField
          id="fmt-column-mode"
          label={t("formatting.columnMode")}
          icon={<Columns2 className="h-4 w-4" />}
          value={value.column_mode}
          onChange={(nextValue) => onChange({ column_mode: nextValue ?? undefined })}
          options={[
            { value: "single", label: t("formatting.column.single") },
            { value: "double", label: t("formatting.column.double") },
          ]}
        />
        <SelectField
          id="fmt-margin"
          label={t("formatting.pageMargin")}
          icon={<Maximize2 className="h-4 w-4" />}
          value={value.margin}
          onChange={(nextValue) => onChange({ margin: nextValue ?? undefined })}
          options={[
            { value: "narrow", label: t("formatting.margin.narrow") },
            { value: "normal", label: t("formatting.margin.standard") },
            { value: "wide", label: t("formatting.margin.wide") },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectField
          id="fmt-bib-style"
          label={t("formatting.bibliographyStyle")}
          icon={<BookOpen className="h-4 w-4" />}
          value={value.bib_style}
          onChange={(nextValue) => onChange({ bib_style: nextValue ?? undefined })}
          options={[
            { value: "gbt7714-numerical", label: t("formatting.bibliography.gbtNumerical") },
            { value: "gbt7714-author-year", label: t("formatting.bibliography.gbtAuthorYear") },
            { value: "ieeetr", label: "IEEE" },
            { value: "apalike", label: "APA" },
          ]}
        />
        <SelectField
          id="fmt-cite-style"
          label={t("formatting.citationStyle")}
          icon={<Quote className="h-4 w-4" />}
          value={value.cite_style}
          onChange={(nextValue) => onChange({ cite_style: nextValue ?? undefined })}
          options={[
            { value: "numbers", label: t("formatting.citationStyle.numeric") },
            { value: "super", label: t("formatting.citationStyle.superscript") },
            { value: "authoryear", label: t("formatting.citationStyle.authorYear") },
          ]}
        />
      </div>

      {isCjk ? (
        <SelectField
          id="fmt-cjk-font"
          label={t("formatting.chineseFont")}
          icon={<FileText className="h-4 w-4" />}
          value={value.cjk_font}
          onChange={(nextValue) => onChange({ cjk_font: nextValue ?? undefined })}
          options={[
            { value: "songti", label: t("formatting.font.songti") },
            { value: "heiti", label: t("formatting.font.heiti") },
          ]}
        />
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ToggleRow
          id="fmt-paragraph-indent"
          label={t("formatting.firstLineIndent")}
          description={t("formatting.use_a_2em_first_line_indent_when_enabled")}
          icon={<Indent className="h-4 w-4" />}
          value={value.paragraph_indent}
          onChange={(nextValue) => onChange({ paragraph_indent: nextValue ?? undefined })}
        />
        <ToggleRow
          id="fmt-localize-captions"
          label={t("formatting.localizeCaptions")}
          description={t("formatting.localizeCaptionsDescription")}
          icon={<FileText className="h-4 w-4" />}
          value={value.localize_captions}
          onChange={(nextValue) => onChange({ localize_captions: nextValue ?? undefined })}
        />
      </div>
    </div>
  )
}
