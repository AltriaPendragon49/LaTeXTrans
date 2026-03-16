import { Settings2, Info, Languages, BookText, CheckCircle2, Palette, Mail } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useStore } from '@/store/useStore'
import { useAuth } from '@/contexts/AuthContext'
import type { TranslationMode, CompileStrategy, FormattingConfig } from '@/types/config'
import { FormattingPanel } from '@/components/FormattingPanel'
import { useTranslation } from 'react-i18next'
import { getLocalizedLanguageOptions } from '@/i18n/config'

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
            "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            checked ? "bg-primary" : "bg-input"
        )}
    >
        <span
            className={cn(
                "pointer-events-none block h-5 w-5 rounded-full bg-background ring-0 shadow-lg transition-transform",
                checked ? "translate-x-5" : "translate-x-0"
            )}
        />
    </button>
)

export const AdvancedConfig = () => {
    const { config, setConfig, setAdvancedConfig, hasSystemApiKey } = useStore()
    const { user } = useAuth()
    const { advanced_config, source_language, target_language } = config
    const { t } = useTranslation()
    const languages = getLocalizedLanguageOptions(t)

    const updateConfig = (key: keyof typeof advanced_config, value: unknown) => {
        setAdvancedConfig({ [key]: value })
    }

    const updateFormatting = (patch: Partial<FormattingConfig>) => {
        setAdvancedConfig({
            formatting: { ...(advanced_config.formatting ?? {}), ...patch }
        })
    }

    return (
        <div className="space-y-6 p-4 border rounded-xl bg-card/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 pb-2 border-b border-border/50">
                <Settings2 className="w-5 h-5 text-primary" />
                <h3 className="font-medium text-lg">{t('dashboard.advancedConfig')}</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2 space-y-4">
                    <div className="flex items-center gap-2">
                        <Languages className="w-4 h-4 text-muted-foreground" />
                        <h4 className="font-medium text-sm text-muted-foreground">{t('common.sections.languageSettings')}</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>{t('common.labels.sourceLanguage')}</Label>
                            <Select
                                value={source_language}
                                onValueChange={(value) => setConfig({ source_language: value })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={t('dashboard.config.choose_source_language')} />
                                </SelectTrigger>
                                <SelectContent>
                                    {languages.map(lang => (
                                        <SelectItem key={lang.code} value={lang.code}>
                                            {lang.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>{t('common.labels.targetLanguage')}</Label>
                            <Select
                                value={target_language}
                                onValueChange={(value) => setConfig({ target_language: value })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={t('dashboard.config.choose_target_language')} />
                                </SelectTrigger>
                                <SelectContent>
                                    {languages.map(lang => (
                                        <SelectItem key={lang.code} value={lang.code}>
                                            {lang.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <Label>{t('common.labels.translationMode')}</Label>
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger>
                                    <Info className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
                                </TooltipTrigger>
                                <TooltipContent>
                                    <p>{t('dashboard.config.choose_how_to_translate_the_document')}</p>
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    </div>
                    <Select
                        value={advanced_config.translation_mode}
                        onValueChange={(value: TranslationMode) => updateConfig('translation_mode', value)}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder={t('dashboard.config.choose_translation_mode')} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="full">{t('task.translationMode.full')}</SelectItem>
                            <SelectItem value="quick_scan">{t('dashboard.config.quick_scan_abstract_conclusion')}</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label>{t('common.labels.compileStrategy')}</Label>
                    <Select
                        value={advanced_config.compile_strategy}
                        onValueChange={(value: CompileStrategy) => updateConfig('compile_strategy', value)}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder={t('dashboard.config.choose_compile_strategy')} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="auto">{t('task.compileStrategy.auto')}</SelectItem>
                            <SelectItem value="pdflatex">PDFLaTeX</SelectItem>
                            <SelectItem value="xelatex">XeLaTeX</SelectItem>
                            <SelectItem value="lualatex">LuaLaTeX</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="translation-model">{t('common.labels.translationModel')}</Label>
                    <Input
                        id="translation-model"
                        placeholder={t('dashboard.config.for_example_deepseek_chat_gpt_4o_claude_3_sonnet')}
                        value={advanced_config.translation_model}
                        onChange={(e) => updateConfig('translation_model', e.target.value)}
                        className="font-mono"
                        disabled={advanced_config.use_author_api}
                    />
                    {advanced_config.use_author_api ? (
                        <p className="text-xs text-amber-600 dark:text-amber-400">
                            {t('dashboard.config.when_the_default_api_is_enabled_the_system_controls_the_model')}
                        </p>
                    ) : (
                        <p className="text-xs text-muted-foreground">
                            {t('dashboard.config.model_names_vary_by_api_provider_use_the_provider_s_documented_name')}
                        </p>
                    )}
                </div>

                <div className="space-y-4 md:col-span-2">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30 flex-1">
                            <div className="space-y-0.5">
                                <Label className="text-base">{t('dashboard.config.use_default_api')}</Label>
                                <p className="text-xs text-muted-foreground">{t('dashboard.config.turn_off_to_enter_a_custom_api_endpoint_and_key')}</p>
                            </div>
                            <SimpleSwitch
                                checked={advanced_config.use_author_api}
                                onCheckedChange={(v) => updateConfig('use_author_api', v)}
                            />
                        </div>

                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30 flex-1">
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <BookText className="w-4 h-4 text-muted-foreground" />
                                    <Label className="text-base">{t('common.generate_glossary')}</Label>
                                </div>
                                <p className="text-xs text-muted-foreground">{t('dashboard.config.output_a_source_translation_terminology_table')}</p>
                            </div>
                            <SimpleSwitch
                                checked={advanced_config.generate_terminology_table}
                                onCheckedChange={(v) => updateConfig('generate_terminology_table', v)}
                            />
                        </div>
                    </div>

                    {user && (
                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30">
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <Mail className="w-4 h-4 text-muted-foreground" />
                                    <Label className="text-base">{t('dashboard.config.email_notifications')}</Label>
                                </div>
                                <p className="text-xs text-muted-foreground">{t('dashboard.config.send_an_email_when_a_task_completes_or_fails')}</p>
                            </div>
                            <SimpleSwitch
                                id="email-notification"
                                checked={advanced_config.email_notification ?? false}
                                onCheckedChange={(v) => updateConfig('email_notification', v)}
                            />
                        </div>
                    )}

                    {!advanced_config.use_author_api && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                            <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2 rounded-md">
                                {t('dashboard.config.if_you_already_saved_api_settings_in_settings_you_can_leave_these_blank_and_reuse_them_automatically')}
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="base-url">{t('dashboard.config.custom_base_url_optional')}</Label>
                                    <Input
                                        id="base-url"
                                        placeholder="https://api.example.com/v1"
                                        value={advanced_config.custom_base_url || ''}
                                        onChange={(e) => updateConfig('custom_base_url', e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Label htmlFor="api-key">{t('dashboard.config.custom_api_key_optional')}</Label>
                                        {hasSystemApiKey && (
                                            <div className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
                                                <CheckCircle2 className="w-3.5 h-3.5" />
                                                <span>{t('dashboard.config.saved_in_settings')}</span>
                                            </div>
                                        )}
                                    </div>
                                    <Input
                                        id="api-key"
                                        type="password"
                                        placeholder={hasSystemApiKey ? t('dashboard.config.leave_blank_to_reuse_the_saved_key') : t('dashboard.config.enter_api_key_sk')}
                                        value={advanced_config.custom_api_key || ''}
                                        onChange={(e) => updateConfig('custom_api_key', e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="space-y-3 md:col-span-2 pt-2 border-t border-border/50">
                <div className="flex items-center gap-2">
                    <Palette className="w-4 h-4 text-primary" />
                    <h4 className="text-sm font-medium">{t('dashboard.config.formatting_settings')}</h4>
                    <span className="text-xs text-muted-foreground ml-1">{t('dashboard.config.optional_injected_into_the_latex_preamble')}</span>
                </div>
                <FormattingPanel
                    value={advanced_config.formatting ?? {}}
                    onChange={updateFormatting}
                    targetLanguage={target_language}
                />
            </div>
        </div>
    )
}
