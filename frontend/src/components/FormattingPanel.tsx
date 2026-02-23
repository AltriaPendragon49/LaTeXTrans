/**
 * FormattingPanel — Typography Configuration UI
 *
 * Provides user controls for advanced LaTeX typography settings:
 * line spacing, font size, CJK font, column mode, margins,
 * paragraph indent, bibliography style, citation style, and caption localization.
 *
 * Design: shadcn/ui components, 2-column grid, Lucide icons, dark/light dual mode.
 * Line spacing & font size use enable-switch + number-input pattern.
 * Other options use Select dropdowns with "保持原样" as first item.
 */

import { Type, AlignJustify, Columns2, Indent, BookOpen, Quote, FileText, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import type { FormattingConfig } from '@/types/config'

// ── Simple Switch (same as used in AdvancedConfig) ─────────────────────────
interface SimpleSwitchProps {
    checked: boolean
    onCheckedChange: (checked: boolean) => void
    id?: string
}

const SimpleSwitch = ({ checked, onCheckedChange, id }: SimpleSwitchProps) => (
    <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
            'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'focus-visible:ring-offset-2 focus-visible:ring-offset-background',
            checked ? 'bg-primary' : 'bg-input'
        )}
    >
        <span
            className={cn(
                'pointer-events-none block h-5 w-5 rounded-full bg-background ring-0 shadow-lg transition-transform',
                checked ? 'translate-x-5' : 'translate-x-0'
            )}
        />
    </button>
)

// ── Numeric Field with Enable Switch ───────────────────────────────────────
interface NumericFieldProps {
    id: string
    label: string
    icon: React.ReactNode
    value: number | undefined | null
    onChange: (v: number | null) => void
    min?: number
    max?: number
    step?: number
    placeholder?: string
    tooltip?: string
}

const NumericField = ({
    id, label, icon, value, onChange, min, max, step, placeholder, tooltip
}: NumericFieldProps) => {
    const enabled = value !== undefined && value !== null
    return (
        <div className="flex flex-col gap-2 p-3 rounded-lg border border-border/50 bg-card/30 hover:bg-muted/30 transition-colors duration-200">
            <div className="flex items-center justify-between">
                <Label htmlFor={id} className="flex items-center gap-2 text-sm cursor-pointer select-none">
                    <span className="text-muted-foreground">{icon}</span>
                    {label}
                </Label>
                <SimpleSwitch
                    id={`${id}-switch`}
                    checked={enabled}
                    onCheckedChange={(on) => onChange(on ? (value ?? (min ?? 1)) : null)}
                />
            </div>
            <Input
                id={id}
                type="number"
                min={min}
                max={max}
                step={step ?? 0.1}
                placeholder={enabled ? '' : (placeholder ?? '保持原样')}
                value={enabled ? (value ?? '') : ''}
                disabled={!enabled}
                onChange={(e) => {
                    const v = parseFloat(e.target.value)
                    onChange(isNaN(v) ? null : v)
                }}
                className={cn(
                    'h-8 text-sm transition-opacity duration-200',
                    !enabled && 'opacity-40 cursor-not-allowed'
                )}
                title={tooltip}
            />
        </div>
    )
}

// ── Select Field Row ────────────────────────────────────────────────────────
interface SelectFieldProps {
    id: string
    label: string
    icon: React.ReactNode
    value: string | undefined | null
    onChange: (v: string | null) => void
    options: { value: string; label: string }[]
}

const SelectField = ({ id, label, icon, value, onChange, options }: SelectFieldProps) => (
    <div className="flex flex-col gap-2 p-3 rounded-lg border border-border/50 bg-card/30 hover:bg-muted/30 transition-colors duration-200">
        <Label htmlFor={id} className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">{icon}</span>
            {label}
        </Label>
        <Select
            value={value ?? '__keep__'}
            onValueChange={(v) => onChange(v === '__keep__' ? null : v)}
        >
            <SelectTrigger id={id} className="h-8 text-sm">
                <SelectValue />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value="__keep__">保持原样</SelectItem>
                {options.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    </div>
)

// ── Toggle Row ──────────────────────────────────────────────────────────────
interface ToggleRowProps {
    id: string
    label: string
    description: string
    icon: React.ReactNode
    value: boolean | undefined | null
    onChange: (v: boolean | null) => void
}

const ToggleRow = ({ id, label, description, icon, value, onChange }: ToggleRowProps) => (
    <div className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-card/30 hover:bg-muted/30 transition-colors duration-200">
        <div className="flex items-start gap-2">
            <span className="text-muted-foreground mt-0.5">{icon}</span>
            <div>
                <Label htmlFor={id} className="text-sm cursor-pointer">{label}</Label>
                <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
            </div>
        </div>
        <SimpleSwitch
            id={id}
            checked={value === true}
            onCheckedChange={(on) => onChange(on ? true : null)}
        />
    </div>
)

// ── FormattingPanel Props ───────────────────────────────────────────────────
export interface FormattingPanelProps {
    value: FormattingConfig
    onChange: (patch: Partial<FormattingConfig>) => void
    targetLanguage?: string
    className?: string
}

// CJK languages where font selection is relevant
const CJK_LANGS = new Set(['zh', 'ja', 'ko'])

// ── Main Component ──────────────────────────────────────────────────────────
export const FormattingPanel = ({
    value,
    onChange,
    targetLanguage,
    className,
}: FormattingPanelProps) => {
    const isCjk = targetLanguage ? CJK_LANGS.has(targetLanguage) : false

    return (
        <div className={cn('space-y-3', className)}>
            {/* Row 1: Line spacing + Font size */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <NumericField
                    id="fmt-line-spacing"
                    label="行距"
                    icon={<AlignJustify className="w-4 h-4" />}
                    value={value.line_spacing}
                    onChange={(v) => onChange({ line_spacing: v ?? undefined })}
                    min={1.0}
                    max={2.5}
                    step={0.1}
                    placeholder="保持原样（例：1.5）"
                    tooltip="行距倍数 (1.0-2.5)。小于 1.0 会导致排版混乱，后端会自动跳过"
                />
                <NumericField
                    id="fmt-font-size"
                    label="字号 (pt)"
                    icon={<Type className="w-4 h-4" />}
                    value={value.font_size}
                    onChange={(v) => onChange({ font_size: v ?? undefined })}
                    min={8}
                    max={14}
                    step={0.5}
                    placeholder="保持原样（例：12）"
                    tooltip="全局字号 (8-14pt)。revtex4-2、IEEEtran 等文档类仅支持特定字号，后端会自动选择最近的安全值"
                />
            </div>

            {/* Row 2: Column mode + Margin */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <SelectField
                    id="fmt-column-mode"
                    label="栏模式"
                    icon={<Columns2 className="w-4 h-4" />}
                    value={value.column_mode}
                    onChange={(v) => onChange({ column_mode: v ?? undefined })}
                    options={[
                        { value: 'single', label: '单栏' },
                        { value: 'double', label: '双栏' },
                    ]}
                />
                <SelectField
                    id="fmt-margin"
                    label="页边距"
                    icon={<Maximize2 className="w-4 h-4" />}
                    value={value.margin}
                    onChange={(v) => onChange({ margin: v ?? undefined })}
                    options={[
                        { value: 'narrow', label: '窄边距' },
                        { value: 'normal', label: '标准边距' },
                        { value: 'wide', label: '宽边距' },
                    ]}
                />
            </div>

            {/* Row 3: Bib style + Cite style */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <SelectField
                    id="fmt-bib-style"
                    label="参考文献格式"
                    icon={<BookOpen className="w-4 h-4" />}
                    value={value.bib_style}
                    onChange={(v) => onChange({ bib_style: v ?? undefined })}
                    options={[
                        { value: 'gbt7714-numerical', label: 'GB/T 7714 数字式' },
                        { value: 'gbt7714-author-year', label: 'GB/T 7714 著者-年' },
                        { value: 'ieeetr', label: 'IEEE' },
                        { value: 'apalike', label: 'APA' },
                    ]}
                />
                <SelectField
                    id="fmt-cite-style"
                    label="引文标记风格"
                    icon={<Quote className="w-4 h-4" />}
                    value={value.cite_style}
                    onChange={(v) => onChange({ cite_style: v ?? undefined })}
                    options={[
                        { value: 'numbers', label: '数字 [1]' },
                        { value: 'super', label: '上标 ¹' },
                        { value: 'authoryear', label: '著者-年' },
                    ]}
                />
            </div>

            {/* Row 4: CJK font (only for CJK target languages) */}
            {isCjk && (
                <SelectField
                    id="fmt-cjk-font"
                    label="中文字体"
                    icon={<FileText className="w-4 h-4" />}
                    value={value.cjk_font}
                    onChange={(v) => onChange({ cjk_font: v ?? undefined })}
                    options={[
                        { value: 'songti', label: '宋体（正文推荐）' },
                        { value: 'heiti', label: '黑体（标题推荐）' },
                    ]}
                />
            )}

            {/* Row 5: Toggles — paragraph indent + localize captions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ToggleRow
                    id="fmt-paragraph-indent"
                    label="首行缩进"
                    description="启用 2em 首行缩进（中文惯例）"
                    icon={<Indent className="w-4 h-4" />}
                    value={value.paragraph_indent}
                    onChange={(v) => onChange({ paragraph_indent: v ?? undefined })}
                />
                <ToggleRow
                    id="fmt-localize-captions"
                    label="图表标题本地化"
                    description="图→图，Table→表，etc."
                    icon={<FileText className="w-4 h-4" />}
                    value={value.localize_captions}
                    onChange={(v) => onChange({ localize_captions: v ?? undefined })}
                />
            </div>
        </div>
    )
}
