import { Type, AlignJustify, Columns2, Indent, BookOpen, Quote, FileText, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useTranslation } from 'react-i18next'
import type { FormattingConfig } from '@/types/config'

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

const NumericField = ({ id, label, icon, value, onChange, min, max, step, placeholder, tooltip }: NumericFieldProps) => {
    const { t } = useTranslation()
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
                placeholder={enabled ? '' : (placeholder ?? t('formatting.keepOriginal'))}
                value={enabled ? (value ?? '') : ''}
                disabled={!enabled}
                onChange={(e) => {
                    const v = parseFloat(e.target.value)
                    onChange(isNaN(v) ? null : v)
                }}
                className={cn('h-8 text-sm transition-opacity duration-200', !enabled && 'opacity-40 cursor-not-allowed')}
                title={tooltip}
            />
        </div>
    )
}

interface SelectFieldProps {
    id: string
    label: string
    icon: React.ReactNode
    value: string | undefined | null
    onChange: (v: string | null) => void
    options: { value: string; label: string }[]
}

const SelectField = ({ id, label, icon, value, onChange, options }: SelectFieldProps) => {
    const { t } = useTranslation()

    return (
        <div className="flex flex-col gap-2 p-3 rounded-lg border border-border/50 bg-card/30 hover:bg-muted/30 transition-colors duration-200">
            <Label htmlFor={id} className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">{icon}</span>
                {label}
            </Label>
            <Select value={value ?? '__keep__'} onValueChange={(v) => onChange(v === '__keep__' ? null : v)}>
                <SelectTrigger id={id} className="h-8 text-sm">
                    <SelectValue />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="__keep__">{t('formatting.keepOriginal')}</SelectItem>
                    {options.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    )
}

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
        <SimpleSwitch id={id} checked={value === true} onCheckedChange={(on) => onChange(on ? true : null)} />
    </div>
)

export interface FormattingPanelProps {
    value: FormattingConfig
    onChange: (patch: Partial<FormattingConfig>) => void
    targetLanguage?: string
    className?: string
}

const CJK_LANGS = new Set(['zh', 'ja', 'ko'])

export const FormattingPanel = ({ value, onChange, targetLanguage, className }: FormattingPanelProps) => {
    const isCjk = targetLanguage ? CJK_LANGS.has(targetLanguage) : false
    const { t } = useTranslation()

    return (
        <div className={cn('space-y-3', className)}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <NumericField
                    id="fmt-line-spacing"
                    label={t('formatting.lineSpacing')}
                    icon={<AlignJustify className="w-4 h-4" />}
                    value={value.line_spacing}
                    onChange={(v) => onChange({ line_spacing: v ?? undefined })}
                    min={1.0}
                    max={2.5}
                    step={0.1}
                    placeholder={t('formatting.keepOriginalLineSpacing')}
                    tooltip={t('formatting.line_spacing_multiplier_recommended_range_1_0_2_5')}
                />
                <NumericField
                    id="fmt-font-size"
                    label={t('formatting.fontSize')}
                    icon={<Type className="w-4 h-4" />}
                    value={value.font_size}
                    onChange={(v) => onChange({ font_size: v ?? undefined })}
                    min={8}
                    max={14}
                    step={0.5}
                    placeholder={t('formatting.keepOriginalFontSize')}
                    tooltip={t('formatting.global_font_size_recommended_range_8_14_pt')}
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <SelectField
                    id="fmt-column-mode"
                    label={t('formatting.columnMode')}
                    icon={<Columns2 className="w-4 h-4" />}
                    value={value.column_mode}
                    onChange={(v) => onChange({ column_mode: v ?? undefined })}
                    options={[
                        { value: 'single', label: t('formatting.column.single') },
                        { value: 'double', label: t('formatting.column.double') },
                    ]}
                />
                <SelectField
                    id="fmt-margin"
                    label={t('formatting.pageMargin')}
                    icon={<Maximize2 className="w-4 h-4" />}
                    value={value.margin}
                    onChange={(v) => onChange({ margin: v ?? undefined })}
                    options={[
                        { value: 'narrow', label: t('formatting.margin.narrow') },
                        { value: 'normal', label: t('formatting.margin.standard') },
                        { value: 'wide', label: t('formatting.margin.wide') },
                    ]}
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <SelectField
                    id="fmt-bib-style"
                    label={t('formatting.bibliographyStyle')}
                    icon={<BookOpen className="w-4 h-4" />}
                    value={value.bib_style}
                    onChange={(v) => onChange({ bib_style: v ?? undefined })}
                    options={[
                        { value: 'gbt7714-numerical', label: t('formatting.bibliography.gbtNumerical') },
                        { value: 'gbt7714-author-year', label: t('formatting.bibliography.gbtAuthorYear') },
                        { value: 'ieeetr', label: 'IEEE' },
                        { value: 'apalike', label: 'APA' },
                    ]}
                />
                <SelectField
                    id="fmt-cite-style"
                    label={t('formatting.citationStyle')}
                    icon={<Quote className="w-4 h-4" />}
                    value={value.cite_style}
                    onChange={(v) => onChange({ cite_style: v ?? undefined })}
                    options={[
                        { value: 'numbers', label: t('formatting.citationStyle.numeric') },
                        { value: 'super', label: t('formatting.citationStyle.superscript') },
                        { value: 'authoryear', label: t('formatting.citationStyle.authorYear') },
                    ]}
                />
            </div>

            {isCjk && (
                <SelectField
                    id="fmt-cjk-font"
                    label={t('formatting.chineseFont')}
                    icon={<FileText className="w-4 h-4" />}
                    value={value.cjk_font}
                    onChange={(v) => onChange({ cjk_font: v ?? undefined })}
                    options={[
                        { value: 'songti', label: t('formatting.font.songti') },
                        { value: 'heiti', label: t('formatting.font.heiti') },
                    ]}
                />
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ToggleRow
                    id="fmt-paragraph-indent"
                    label={t('formatting.firstLineIndent')}
                    description={t('formatting.use_a_2em_first_line_indent_when_enabled')}
                    icon={<Indent className="w-4 h-4" />}
                    value={value.paragraph_indent}
                    onChange={(v) => onChange({ paragraph_indent: v ?? undefined })}
                />
                <ToggleRow
                    id="fmt-localize-captions"
                    label={t('formatting.localizeCaptions')}
                    description={t('formatting.localizeCaptionsDescription')}
                    icon={<FileText className="w-4 h-4" />}
                    value={value.localize_captions}
                    onChange={(v) => onChange({ localize_captions: v ?? undefined })}
                />
            </div>
        </div>
    )
}
