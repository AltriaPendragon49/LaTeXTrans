import { useState, useEffect, useCallback } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/ui/button/Button'
import { Input } from '@/ui/input/Input'
import { Label } from '@/ui/primitives/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/primitives/select'
import { Switch } from '@/ui/primitives/switch'
import { Loader2, Save, CheckCircle2, Globe, Sparkles, SlidersHorizontal, Key, Wrench, AlertTriangle, Info } from 'lucide-react'
import { toast } from 'sonner'
import type { FormattingConfig } from '@/types/config'
import { API_BASE_URL } from '@/api-base'
import { useTranslation } from 'react-i18next'
import { FormattingPanel } from '@/features/translation-workflow/components/FormattingPanel'
import { LoginPrompt } from '@/features/auth-shell/components/LoginPrompt'
import { useTranslationConfig } from '@/features/translation-workflow/hooks/useTranslationConfig'
import { getLocalizedLanguageOptions } from '@/i18n/config'
import { getAccessToken } from '@/lib/local-auth'
import { PageIntro } from '@/ui/page-intro/PageIntro'
import { SectionCard } from '@/ui/section-card/SectionCard'
import { NoticeBanner } from '@/ui/notice-banner/NoticeBanner'
import { InfoTile } from '@/ui/info-tile/InfoTile'
import { FormFieldShell } from '@/ui/form-field-shell/FormFieldShell'
import { LanguageSelector } from '@/ui/language-selector/LanguageSelector'
import { LoadingState } from '@/ui/loading-state/LoadingState'
import { ThemeToggle } from '@/ui/theme-toggle/ThemeToggle'

/** 用户设置数据结构 */
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

/**
 * 翻译设置工作区组件
 * 提供用户默认翻译设置的完整管理界面，包括：
 * - 外观（语言、主题）
 * - 语言设置（默认源/目标语言）
 * - 翻译设置（模式、编译策略、模型）
 * - 高级设置（术语表、API 开关）
 * - 格式默认值和自定义 API
 *
 * 调用 GET /api/settings 加载设置，PUT /api/settings 保存设置
 */
export function TranslationSettingsWorkspace() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const { t } = useTranslation()
  const languages = getLocalizedLanguageOptions(t)
  const { invalidateUserSettings } = useTranslationConfig()

  const [settings, setSettings] = useState<UserSettings>(defaultSettings)
  const [customApiKey, setCustomApiKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const token = await getAccessToken()

      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

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

  const handleSave = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)

    // 自定义 API 时验证必填项
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

      if (customApiKey) {
        updateData.custom_api_key = customApiKey
      }

      if (settings.default_formatting !== undefined) {
        updateData.default_formatting = settings.default_formatting
      }

      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      })

      if (!response.ok) {
        throw new Error(t('settings.failed_to_save_settings'))
      }

      const data: UserSettings = await response.json()
      setSettings(data)
      setCustomApiKey('')
      invalidateUserSettings()
      toast.success(t('settings.settings_saved'))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.failed_to_save_settings'))
      toast.error(t('settings.save_failed'))
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      void fetchSettings()
    }
  }, [fetchSettings, isAuthenticated])

  if (authLoading) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center">
        <LoadingState label={t('common.status.loading')} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 py-12 animate-in fade-in duration-500">
        <LoginPrompt
          messageKey="settings.sign_in_to_save_settings"
          descriptionKey="settings.after_signing_in_you_can_save_default_translation_settings_and_reuse_them_next_time"
          actionLabelKey="common.go_to_sign_in"
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-in fade-in duration-500">
      <PageIntro
        title={t('settings.title')}
        description={t('settings.system_preferences_description')}
        actions={(
          <Button type="submit" form="settings-form" disabled={saving} className="rounded-full shadow-sm" size="sm">
            {saving ? (<><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t('settings.actions.saving')}</>) : (<><Save className="mr-2 h-4 w-4" />{t('settings.actions.save')}</>)}
          </Button>
        )}
      />

      {error ? (<NoticeBanner tone="danger" icon={<AlertTriangle className="h-4 w-4" />} description={error} />) : null}

      {loading ? (<LoadingState className="justify-center py-12" label={t('common.status.loading')} />) : (
        <form id="settings-form" onSubmit={handleSave} className="space-y-6 pb-20">
          <SectionCard icon={<Globe className="h-5 w-5" />} title={t('settings.appearance')} description={t('settings.system_preferences_description')} contentClassName="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-col gap-3">
              <Label className="text-xs font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">{t('common.choose_global_interface_language')}</Label>
              <LanguageSelector />
            </div>
            <div className="flex flex-col gap-3 md:items-end">
              <Label className="text-xs font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">{t('settings.appearance')}</Label>
              <ThemeToggle />
            </div>
          </SectionCard>

          <SectionCard icon={<Globe className="h-5 w-5" />} title={t('common.sections.languageSettings')} description={t('settings.set_the_default_source_and_target_languages')} contentClassName="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <FormFieldShell label={t('common.labels.sourceLanguage')} size="compact">
                <Select value={settings.default_source_language} onValueChange={(value) => setSettings((prev) => ({ ...prev, default_source_language: value }))}>
                  <SelectTrigger id="source_language" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-xl">{languages.map((language) => (<SelectItem key={`source-${language.code}`} value={language.code} className="rounded-lg">{language.label}</SelectItem>))}</SelectContent>
                </Select>
              </FormFieldShell>
            </div>
            <div className="space-y-3">
              <FormFieldShell label={t('common.labels.targetLanguage')} size="compact">
                <Select value={settings.default_target_language} onValueChange={(value) => setSettings((prev) => ({ ...prev, default_target_language: value }))}>
                  <SelectTrigger id="target_language" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-xl">{languages.map((language) => (<SelectItem key={`target-${language.code}`} value={language.code} className="rounded-lg">{language.label}</SelectItem>))}</SelectContent>
                </Select>
              </FormFieldShell>
            </div>
          </SectionCard>

          <SectionCard icon={<Sparkles className="h-5 w-5" />} title={t('settings.translation_settings')} description={t('settings.configure_translation_mode_and_compile_options')} iconClassName="bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]" contentClassName="space-y-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <FormFieldShell label={t('common.labels.translationMode')} size="compact">
                  <Select value={settings.translation_mode} onValueChange={(value) => setSettings((prev) => ({ ...prev, translation_mode: value }))}>
                    <SelectTrigger id="translation_mode" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]"><SelectValue /></SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="full" className="rounded-lg">{t('task.translationMode.full')}</SelectItem>
                      <SelectItem value="quick_scan" className="rounded-lg">{t('task.translationMode.quickScan')}</SelectItem>
                    </SelectContent>
                  </Select>
                </FormFieldShell>
              </div>
              <div className="space-y-3">
                <FormFieldShell label={t('common.labels.compileStrategy')} size="compact">
                  <Select value={settings.compile_strategy} onValueChange={(value) => setSettings((prev) => ({ ...prev, compile_strategy: value }))}>
                    <SelectTrigger id="compile_strategy" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]"><SelectValue /></SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="auto" className="rounded-lg">{t('task.compileStrategy.auto')}</SelectItem>
                      <SelectItem value="pdflatex" className="rounded-lg">PDFLaTeX</SelectItem>
                      <SelectItem value="xelatex" className="rounded-lg">XeLaTeX</SelectItem>
                      <SelectItem value="lualatex" className="rounded-lg">LuaLaTeX</SelectItem>
                    </SelectContent>
                  </Select>
                </FormFieldShell>
              </div>
            </div>
            <div className="border-t border-[color:var(--px-shell-line)] pt-2">
              <FormFieldShell label={t('common.labels.translationModel')} size="compact">
                <Input id="translation_model" placeholder={t('settings.leave_blank_to_use_the_system_default')} value={settings.translation_model || ''} onChange={(event) => setSettings((prev) => ({ ...prev, translation_model: event.target.value || null }))} disabled={settings.use_author_api} className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)]" />
              </FormFieldShell>
              {settings.use_author_api ? (<NoticeBanner tone="info" icon={<Info className="h-4 w-4" />} description={t('settings.when_the_author_api_is_enabled_the_model_is_locked_and_does_not_need_configuration')} />) : null}
            </div>
          </SectionCard>

          <SectionCard icon={<SlidersHorizontal className="h-5 w-5" />} title={t('settings.advancedSettings')} description={t('settings.configure_glossary_and_api_options')} iconClassName="bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_82%,var(--px-shell-surface))] text-[color:var(--px-shell-ink)]" contentClassName="space-y-6">
            <InfoTile title={t('common.generate_glossary')} description={t('settings.generate_a_terminology_table_csv_during_translation')} trailing={<Switch id="generate_glossary" checked={settings.generate_glossary} onCheckedChange={(checked) => setSettings((prev) => ({ ...prev, generate_glossary: checked }))} />} />
            <div className="h-px w-full bg-outline-variant/10" />
            <InfoTile title={t('settings.use_default_author_api')} description={t('settings.turning_this_off_requires_a_custom_api_endpoint_and_key')} trailing={<Switch id="use_author_api" checked={settings.use_author_api} onCheckedChange={(checked) => setSettings((prev) => ({ ...prev, use_author_api: checked }))} />} />
          </SectionCard>

          <SectionCard icon={<Wrench className="h-5 w-5" />} title={t('settings.formatting_defaults')} description={t('settings.set_the_default_output_formatting_for_translated_documents_manual_translation_time_settings_override_these_values')} iconClassName="bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-success)]" contentClassName="p-0">
            <div className="bg-[color:var(--px-shell-panel-strong)]/60 px-0 py-0">
              <FormattingPanel value={settings.default_formatting ?? {}} onChange={(patch) => setSettings((prev) => ({ ...prev, default_formatting: { ...(prev.default_formatting ?? {}), ...patch } }))} targetLanguage={settings.default_target_language} />
            </div>
          </SectionCard>

          {!settings.use_author_api ? (
            <SectionCard icon={<Key className="h-5 w-5" />} title={t('settings.custom_api')} description={t('settings.use_your_own_api_endpoint_and_key')} className="animate-in zoom-in-95 duration-200" headerClassName="bg-[color:var(--px-shell-danger-soft)]" iconClassName="border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]" contentClassName="space-y-4">
              <FormFieldShell label={t('settings.api_endpoint')} size="compact">
                <Input id="custom_base_url" placeholder="https://api.openai.com/v1" value={settings.custom_base_url || ''} onChange={(event) => setSettings((prev) => ({ ...prev, custom_base_url: event.target.value || null }))} className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)]" />
              </FormFieldShell>
              <FormFieldShell label={t('settings.api_key')} size="compact" headerAside={settings.has_custom_api_key ? (<span className="ml-2 flex items-center rounded bg-[color:var(--px-shell-success-soft)] px-2 py-0.5 text-[10px] font-bold text-[color:var(--px-shell-success)]"><CheckCircle2 className="mr-1 h-3 w-3" />{t('settings.set')}</span>) : null}>
                <Input id="custom_api_key" type="password" placeholder={settings.has_custom_api_key ? t('settings.enter_a_new_key_to_update') : 'sk-...'} value={customApiKey} onChange={(event) => setCustomApiKey(event.target.value)} className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)]" />
                <p className="text-[11px] font-medium text-[color:var(--px-shell-muted)]">{t('settings.the_api_key_is_stored_encrypted_and_is_never_returned_to_the_client')}</p>
              </FormFieldShell>
            </SectionCard>
          ) : null}
        </form>
      )}
    </div>
  )
}
