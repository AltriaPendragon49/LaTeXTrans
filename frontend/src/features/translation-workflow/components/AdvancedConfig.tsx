import { BookText, CheckCircle2, Info, Languages, Mail, Palette, Settings2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Input } from "@/ui/input/Input"
import { InfoTile } from "@/ui/info-tile/InfoTile"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import { Label } from "@/ui/primitives/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/primitives/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/ui/primitives/tooltip"
import { useAuth } from "@/contexts/AuthContext"
import { getLocalizedLanguageOptions } from "@/i18n/config"
import { FormattingPanel } from "@/features/translation-workflow/components/FormattingPanel"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import type { CompileStrategy, FormattingConfig, TranslationMode } from "@/types/config"

export function AdvancedConfig() {
  const { config, setConfig, setAdvancedConfig, hasSystemApiKey } = useTranslationConfig()
  const { user } = useAuth()
  const { advanced_config, source_language, target_language } = config
  const { t } = useTranslation()
  const languages = getLocalizedLanguageOptions(t)

  function updateConfig(key: keyof typeof advanced_config, value: unknown) {
    setAdvancedConfig({ [key]: value })
  }

  function updateFormatting(patch: Partial<FormattingConfig>) {
    setAdvancedConfig({
      formatting: { ...(advanced_config.formatting ?? {}), ...patch },
    })
  }

  return (
    <PanelShell className="space-y-6 p-4">
      <div className="flex items-center gap-2 border-b border-[color:var(--px-shell-line)] pb-2">
        <Settings2 className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
        <h3 className="text-lg font-medium text-[color:var(--px-shell-ink)]">{t("dashboard.advancedConfig")}</h3>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="space-y-4 md:col-span-2">
          <div className="flex items-center gap-2">
            <Languages className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
            <h4 className="text-sm font-medium text-[color:var(--px-shell-muted)]">{t("common.sections.languageSettings")}</h4>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>{t("common.labels.sourceLanguage")}</Label>
              <Select value={source_language} onValueChange={(value) => setConfig({ source_language: value })}>
                <SelectTrigger>
                  <SelectValue placeholder={t("dashboard.config.choose_source_language")} />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((language) => (
                    <SelectItem key={language.code} value={language.code}>
                      {language.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t("common.labels.targetLanguage")}</Label>
              <Select value={target_language} onValueChange={(value) => setConfig({ target_language: value })}>
                <SelectTrigger>
                  <SelectValue placeholder={t("dashboard.config.choose_target_language")} />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((language) => (
                    <SelectItem key={language.code} value={language.code}>
                      {language.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>{t("common.labels.translationMode")}</Label>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-4 w-4 text-[color:var(--px-shell-muted)] transition-colors hover:text-[color:var(--px-shell-ink)]" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t("dashboard.config.choose_how_to_translate_the_document")}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <Select
            value={advanced_config.translation_mode}
            onValueChange={(value: TranslationMode) => updateConfig("translation_mode", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("dashboard.config.choose_translation_mode")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="full">{t("task.translationMode.full")}</SelectItem>
              <SelectItem value="quick_scan">{t("dashboard.config.quick_scan_abstract_conclusion")}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>{t("common.labels.compileStrategy")}</Label>
          <Select
            value={advanced_config.compile_strategy}
            onValueChange={(value: CompileStrategy) => updateConfig("compile_strategy", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("dashboard.config.choose_compile_strategy")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">{t("task.compileStrategy.auto")}</SelectItem>
              <SelectItem value="pdflatex">PDFLaTeX</SelectItem>
              <SelectItem value="xelatex">XeLaTeX</SelectItem>
              <SelectItem value="lualatex">LuaLaTeX</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="translation-model">{t("common.labels.translationModel")}</Label>
          <Input
            id="translation-model"
            placeholder={t("dashboard.config.for_example_deepseek_chat_gpt_4o_claude_3_sonnet")}
            value={advanced_config.translation_model}
            onChange={(event) => updateConfig("translation_model", event.target.value)}
            className="font-mono"
            disabled={advanced_config.use_author_api}
          />
          {advanced_config.use_author_api ? (
            <NoticeBanner
              tone="warning"
              icon={<Info className="h-4 w-4" />}
              description={t("dashboard.config.when_the_default_api_is_enabled_the_system_controls_the_model")}
              className="rounded-lg px-3 py-2 text-xs"
            />
          ) : (
            <p className="text-xs text-[color:var(--px-shell-muted)]">
              {t("dashboard.config.model_names_vary_by_api_provider_use_the_provider_s_documented_name")}
            </p>
          )}
        </div>

        <div className="space-y-4 md:col-span-2">
          <div className="flex flex-col gap-4 md:flex-row">
            <InfoTile
              className="flex-1"
              title={t("dashboard.config.use_default_api")}
              description={t("dashboard.config.turn_off_to_enter_a_custom_api_endpoint_and_key")}
              trailing={(
                <ToggleSwitch
                  checked={advanced_config.use_author_api}
                  onCheckedChange={(checked) => updateConfig("use_author_api", checked)}
                />
              )}
            />

            <InfoTile
              className="flex-1"
              icon={<BookText className="h-4 w-4" />}
              title={t("ragTerminology.enableRagTerminology")}
              description={t("ragTerminology.mergedDescription")}
              trailing={(
                <ToggleSwitch
                  id="enable-rag-terminology"
                  checked={advanced_config.enable_rag_terminology ?? false}
                  onCheckedChange={(checked) => {
                    updateConfig("enable_rag_terminology", checked)
                    updateConfig("generate_terminology_table", checked)
                  }}
                />
              )}
            />
          </div>

          {user ? (
            <InfoTile
              icon={<Mail className="h-4 w-4" />}
              title={t("dashboard.config.email_notifications")}
              description={t("dashboard.config.send_an_email_when_a_task_completes_or_fails")}
              trailing={(
                <ToggleSwitch
                  id="email-notification"
                  checked={advanced_config.email_notification ?? false}
                  onCheckedChange={(checked) => updateConfig("email_notification", checked)}
                />
              )}
            />
          ) : null}

          {advanced_config.enable_rag_terminology ? (
            <div className="animate-in slide-in-from-top-2 space-y-2 duration-200">
              <Label className="text-sm">{t("ragTerminology.domainFilter")}</Label>
              <Select
                value={advanced_config.rag_terminology_domain || "__all__"}
                onValueChange={(v) => updateConfig("rag_terminology_domain", v === "__all__" ? undefined : v)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={t("ragTerminology.allDomains")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">{t("ragTerminology.allDomains")}</SelectItem>
                  <SelectItem value="machine_learning">Machine Learning</SelectItem>
                  <SelectItem value="natural_language_processing">NLP</SelectItem>
                  <SelectItem value="computer_vision">Computer Vision</SelectItem>
                  <SelectItem value="systems">Systems</SelectItem>
                  <SelectItem value="security">Security</SelectItem>
                  <SelectItem value="mathematics">Mathematics</SelectItem>
                  <SelectItem value="physics">Physics</SelectItem>
                  <SelectItem value="biology">Biology</SelectItem>
                  <SelectItem value="medicine">Medicine</SelectItem>
                  <SelectItem value="engineering">Engineering</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ) : null}

          {!advanced_config.use_author_api ? (
            <div className="animate-in slide-in-from-top-2 space-y-4 duration-200">
              <NoticeBanner
                tone="warning"
                icon={<Info className="h-4 w-4" />}
                description={t("dashboard.config.if_you_already_saved_api_settings_in_settings_you_can_leave_these_blank_and_reuse_them_automatically")}
                className="rounded-lg px-3 py-2 text-xs"
              />
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="base-url">{t("dashboard.config.custom_base_url_optional")}</Label>
                  <Input
                    id="base-url"
                    placeholder="https://api.example.com/v1"
                    value={advanced_config.custom_base_url || ""}
                    onChange={(event) => updateConfig("custom_base_url", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="api-key">{t("dashboard.config.custom_api_key_optional")}</Label>
                    {hasSystemApiKey ? (
                      <StatusBadge
                        tone="success"
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                        className="gap-1 px-2 py-1 text-[9px]"
                      >
                        {t("dashboard.config.saved_in_settings")}
                      </StatusBadge>
                    ) : null}
                  </div>
                  <Input
                    id="api-key"
                    type="password"
                    placeholder={hasSystemApiKey ? t("dashboard.config.leave_blank_to_reuse_the_saved_key") : t("dashboard.config.enter_api_key_sk")}
                    value={advanced_config.custom_api_key || ""}
                    onChange={(event) => updateConfig("custom_api_key", event.target.value)}
                  />
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="space-y-3 border-t border-[color:var(--px-shell-line)] pt-2 md:col-span-2">
        <div className="flex items-center gap-2">
          <Palette className="h-4 w-4 text-[color:var(--px-shell-accent)]" />
          <h4 className="text-sm font-medium text-[color:var(--px-shell-ink)]">{t("dashboard.config.formatting_settings")}</h4>
          <span className="ml-1 text-xs text-[color:var(--px-shell-muted)]">
            {t("dashboard.config.optional_injected_into_the_latex_preamble")}
          </span>
        </div>
        <FormattingPanel
          value={advanced_config.formatting ?? {}}
          onChange={updateFormatting}
          targetLanguage={target_language}
        />
      </div>
    </PanelShell>
  )
}
