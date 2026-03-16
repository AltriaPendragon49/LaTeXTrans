/**
 * Settings Page
 * 
 * User settings management for translation preferences.
 * Requires authentication - shows prompt for guests.
 */

import { useState, useEffect, useCallback } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Settings, LogIn, Save, CheckCircle2 } from 'lucide-react'
import { toast } from 'sonner'
import { FormattingPanel } from '@/components/FormattingPanel'
import type { FormattingConfig } from '@/types/config'
import { API_BASE_URL } from '@/api-base'
import { useTranslation } from 'react-i18next'
import { getLocalizedLanguageOptions } from '@/i18n/config'
import { getAccessToken } from '@/lib/supabase'
import { useStore } from '@/store/useStore'

interface UserSettings {
    default_source_language: string
    default_target_language: string
    translation_mode: string
    compile_strategy: string
    translation_model: string | null
    generate_glossary: boolean
    use_author_api: boolean
    custom_base_url: string | null
    has_custom_api_key: boolean
    default_formatting: FormattingConfig | null
}

const defaultSettings: UserSettings = {
    default_source_language: 'en',
    default_target_language: 'zh',
    translation_mode: 'full',
    compile_strategy: 'auto',
    translation_model: null,
    generate_glossary: true,
    use_author_api: true,
    custom_base_url: null,
    has_custom_api_key: false,
    default_formatting: null,
}

export default function SettingsPage() {
    const navigate = useNavigate()
    const { isAuthenticated, loading: authLoading } = useAuth()
    const { t } = useTranslation()
    const languages = getLocalizedLanguageOptions(t)

    const [settings, setSettings] = useState<UserSettings>(defaultSettings)
    const [customApiKey, setCustomApiKey] = useState('')
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Fetch settings
    const fetchSettings = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
            const token = await getAccessToken()

            const response = await fetch(
                `${API_BASE_URL}/api/settings`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                }
            )

            if (!response.ok) {
                throw new Error(t('settings.failed_to_load_settings'))
            }

            const data: UserSettings = await response.json()
            setSettings(data)
        } catch (err) {
            setError(err instanceof Error ? err.message : t('settings.failed_to_load_settings'))
        } finally {
            setLoading(false)
        }
    }, [t])

    // Save settings
    const handleSave = async (e: FormEvent) => {
        e.preventDefault()
        setSaving(true)
        setError(null)

        // Validation: if not using author API, require base url and api key
        if (!settings.use_author_api) {
            if (!settings.custom_base_url || settings.custom_base_url.trim() === '') {
                setError(t('settings.a_custom_api_endpoint_is_required_when_the_default_author_api_is_disabled'))
                setSaving(false)
                return
            }
            if (!settings.has_custom_api_key && !customApiKey) {
                setError(t('settings.an_api_key_is_required_when_the_default_author_api_is_disabled'))
                setSaving(false)
                return
            }
        }

        try {
            const token = await getAccessToken()

            const updateData: Record<string, unknown> = {
                default_source_language: settings.default_source_language,
                default_target_language: settings.default_target_language,
                translation_mode: settings.translation_mode,
                compile_strategy: settings.compile_strategy,
                translation_model: settings.translation_model,
                generate_glossary: settings.generate_glossary,
                use_author_api: settings.use_author_api,
                custom_base_url: settings.custom_base_url,
            }

            // Only include API key if user entered a new one
            if (customApiKey) {
                updateData.custom_api_key = customApiKey
            }

            // Include formatting if user has configured it (null clears it)
            if (settings.default_formatting !== undefined) {
                updateData.default_formatting = settings.default_formatting
            }

            const response = await fetch(
                `${API_BASE_URL}/api/settings`,
                {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                }
            )

            if (!response.ok) {
                throw new Error(t('settings.failed_to_save_settings'))
            }

            const data: UserSettings = await response.json()
            setSettings(data)
            setCustomApiKey('') // Clear the input after save

            // Invalidate cached settings in store so Dashboard will reload
            useStore.getState().invalidateUserSettings()

            toast.success(t('settings.settings_saved'))
        } catch (err) {
            setError(err instanceof Error ? err.message : t('settings.failed_to_save_settings'))
            toast.error(t('settings.save_failed'))
        } finally {
            setSaving(false)
        }
    }

    // Initial load
    useEffect(() => {
        if (isAuthenticated) {
            fetchSettings()
        }
    }, [fetchSettings, isAuthenticated])

    // Loading state
    if (authLoading) {
        return (
            <div className="container mx-auto max-w-2xl p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    // Not authenticated
    if (!isAuthenticated) {
        return (
            <div className="container mx-auto max-w-2xl p-6 space-y-6 animate-in fade-in duration-500">
                <div className="space-y-2">
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Settings className="h-8 w-8" />
                        {t('settings.title')}
                    </h1>
                </div>

                <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="pt-6 space-y-4">
                        <div className="text-center py-8 space-y-4">
                            <div className="mx-auto p-4 rounded-full bg-muted/50 w-fit">
                                <LogIn className="h-8 w-8 text-muted-foreground" />
                            </div>
                            <div className="space-y-2">
                                <p className="text-lg font-medium">{t('settings.sign_in_to_save_settings')}</p>
                                <p className="text-muted-foreground">
                                    {t('settings.after_signing_in_you_can_save_default_translation_settings_and_reuse_them_next_time')}
                                </p>
                            </div>
                            <Button onClick={() => navigate('/login')} className="mt-4">
                                <LogIn className="mr-2 h-4 w-4" />
                                {t('common.go_to_sign_in')}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="container mx-auto max-w-2xl p-6 space-y-6 animate-in fade-in duration-500">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    <Settings className="h-8 w-8" />
                    {t('settings.title')}
                </h1>
                <p className="text-muted-foreground">
                    {t('settings.configure_default_translation_options_that_apply_when_you_create_a_new_translation')}
                </p>
                <p className="text-xs text-amber-600 dark:text-amber-400">
                    {t('settings.tip_after_saving_return_to_the_home_page_or_refresh_to_apply_changes')}
                </p>
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {loading ? (
                <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <form onSubmit={handleSave} className="space-y-6">
                    {/* Language Settings */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">{t('common.sections.languageSettings')}</CardTitle>
                            <CardDescription>{t('settings.set_the_default_source_and_target_languages')}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="source_language">{t('common.labels.sourceLanguage')}</Label>
                                    <Select
                                        value={settings.default_source_language}
                                        onValueChange={(v) => setSettings(s => ({ ...s, default_source_language: v }))}
                                    >
                                        <SelectTrigger id="source_language">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {languages.map((language) => (
                                                <SelectItem key={`source-${language.code}`} value={language.code}>
                                                    {language.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="target_language">{t('common.labels.targetLanguage')}</Label>
                                    <Select
                                        value={settings.default_target_language}
                                        onValueChange={(v) => setSettings(s => ({ ...s, default_target_language: v }))}
                                    >
                                        <SelectTrigger id="target_language">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {languages.map((language) => (
                                                <SelectItem key={`target-${language.code}`} value={language.code}>
                                                    {language.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Translation Settings */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">{t('settings.translation_settings')}</CardTitle>
                            <CardDescription>{t('settings.configure_translation_mode_and_compile_options')}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="translation_mode">{t('common.labels.translationMode')}</Label>
                                <Select
                                    value={settings.translation_mode}
                                    onValueChange={(v) => setSettings(s => ({ ...s, translation_mode: v }))}
                                >
                                    <SelectTrigger id="translation_mode">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="full">{t('task.translationMode.full')}</SelectItem>
                                        <SelectItem value="quick_scan">{t('task.translationMode.quickScan')}</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="compile_strategy">{t('common.labels.compileStrategy')}</Label>
                                <Select
                                    value={settings.compile_strategy}
                                    onValueChange={(v) => setSettings(s => ({ ...s, compile_strategy: v }))}
                                >
                                    <SelectTrigger id="compile_strategy">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="auto">{t('task.compileStrategy.auto')}</SelectItem>
                                        <SelectItem value="pdflatex">PDFLaTeX</SelectItem>
                                        <SelectItem value="xelatex">XeLaTeX</SelectItem>
                                        <SelectItem value="lualatex">LuaLaTeX</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="translation_model">{t('common.labels.translationModel')}</Label>
                                <Input
                                    id="translation_model"
                                    placeholder={t('settings.leave_blank_to_use_the_system_default')}
                                    value={settings.translation_model || ''}
                                    onChange={(e) => setSettings(s => ({ ...s, translation_model: e.target.value || null }))}
                                    disabled={settings.use_author_api}
                                />
                                {settings.use_author_api && (
                                    <p className="text-xs text-amber-600 dark:text-amber-400">
                                        {t('settings.when_the_author_api_is_enabled_the_model_is_locked_and_does_not_need_configuration')}
                                    </p>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Advanced Settings */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">{t('settings.advancedSettings')}</CardTitle>
                            <CardDescription>{t('settings.configure_glossary_and_api_options')}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Generate Glossary */}
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label htmlFor="generate_glossary">{t('common.generate_glossary')}</Label>
                                    <p className="text-xs text-muted-foreground">
                                        {t('settings.generate_a_terminology_table_csv_during_translation')}
                                    </p>
                                </div>
                                <Switch
                                    id="generate_glossary"
                                    checked={settings.generate_glossary}
                                    onCheckedChange={(checked) => setSettings(s => ({ ...s, generate_glossary: checked }))}
                                />
                            </div>

                            {/* Use Author API */}
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label htmlFor="use_author_api">{t('settings.use_default_author_api')}</Label>
                                    <p className="text-xs text-muted-foreground">
                                        {t('settings.turning_this_off_requires_a_custom_api_endpoint_and_key')}
                                    </p>
                                </div>
                                <Switch
                                    id="use_author_api"
                                    checked={settings.use_author_api}
                                    onCheckedChange={(checked) => setSettings(s => ({ ...s, use_author_api: checked }))}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Formatting Defaults */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">{t('settings.formatting_defaults')}</CardTitle>
                            <CardDescription>{t('settings.set_the_default_output_formatting_for_translated_documents_manual_translation_time_settings_override_these_values')}</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <FormattingPanel
                                value={settings.default_formatting ?? {}}
                                onChange={(patch) =>
                                    setSettings(s => ({
                                        ...s,
                                        default_formatting: { ...(s.default_formatting ?? {}), ...patch }
                                    }))
                                }
                                targetLanguage={settings.default_target_language}
                            />
                        </CardContent>
                    </Card>

                    {/* API Settings */}
                    {!settings.use_author_api && (
                        <Card className="border-border/50 bg-card/80 animate-in fade-in">
                            <CardHeader>
                                <CardTitle className="text-lg">{t('settings.custom_api')}</CardTitle>
                                <CardDescription>{t('settings.use_your_own_api_endpoint_and_key')}</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="custom_base_url">{t('settings.api_endpoint')}</Label>
                                    <Input
                                        id="custom_base_url"
                                        placeholder="https://api.openai.com/v1"
                                        value={settings.custom_base_url || ''}
                                        onChange={(e) => setSettings(s => ({ ...s, custom_base_url: e.target.value || null }))}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="custom_api_key">
                                        API Key
                                        {settings.has_custom_api_key && (
                                            <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                                                <CheckCircle2 className="inline h-3 w-3 mr-1" />
                                                {t('settings.set')}
                                            </span>
                                        )}
                                    </Label>
                                    <Input
                                        id="custom_api_key"
                                        type="password"
                                        placeholder={settings.has_custom_api_key ? t('settings.enter_a_new_key_to_update') : 'sk-...'}
                                        value={customApiKey}
                                        onChange={(e) => setCustomApiKey(e.target.value)}
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        {t('settings.the_api_key_is_stored_encrypted_and_is_never_returned_to_the_client')}
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Save Button */}
                    <div className="flex justify-end pt-4">
                        <Button type="submit" disabled={saving} className="min-w-[120px]">
                            {saving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {t('settings.actions.saving')}
                                </>
                            ) : (
                                <>
                                    <Save className="mr-2 h-4 w-4" />
                                    {t('settings.actions.save')}
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            )}
        </div>
    )
}
