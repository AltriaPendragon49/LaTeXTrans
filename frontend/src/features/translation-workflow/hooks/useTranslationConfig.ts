import { useTranslationStore } from "@/features/translation-workflow/store/useTranslationStore"

export function useTranslationConfig() {
  const config = useTranslationStore((state) => state.config)
  const latexValidation = useTranslationStore((state) => state.latexValidation)
  const hasSystemApiKey = useTranslationStore((state) => state.hasSystemApiKey)
  const userSettingsLoaded = useTranslationStore((state) => state.userSettingsLoaded)
  const setConfig = useTranslationStore((state) => state.setConfig)
  const setAdvancedConfig = useTranslationStore((state) => state.setAdvancedConfig)
  const resetConfig = useTranslationStore((state) => state.resetConfig)
  const setLatexValidation = useTranslationStore((state) => state.setLatexValidation)
  const loadUserSettings = useTranslationStore((state) => state.loadUserSettings)
  const invalidateUserSettings = useTranslationStore((state) => state.invalidateUserSettings)

  return {
    config,
    latexValidation,
    hasSystemApiKey,
    userSettingsLoaded,
    setConfig,
    setAdvancedConfig,
    resetConfig,
    setLatexValidation,
    loadUserSettings,
    invalidateUserSettings,
  }
}
