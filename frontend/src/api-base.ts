const REQUIRED_ENV_NAME = "VITE_API_BASE_URL"
const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>
const LOCAL_DEV_API_BASE_URL = "http://127.0.0.1:9001"
const HOSTED_API_BASE_URL = "https://api.latextrans.online"
const PAPER_PREVIEW_ENV_NAME = "VITE_PAPER_PREVIEW_API_BASE_URL"
const TRANSLATED_HTML_READER_ENV_NAME = "VITE_ENABLE_TRANSLATED_HTML_READER"
const PRODUCTION_FRONTEND_HOSTNAME = "latextrans.niutrans.com"
const PRODUCTION_PAPER_PREVIEW_API_BASE_URL = HOSTED_API_BASE_URL

function normalizeBaseUrl(value: string | undefined): string | null {
  if (!value || !String(value).trim()) {
    return null
  }
  const normalized = String(value).trim().replace(/\/+$/, "")
  return normalized === "/" ? "" : normalized
}

function isLocalBrowserHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost"
}

function isBrowserEnvironment(): boolean {
  return typeof window !== "undefined"
}

function isPrimaryProductionFrontend(): boolean {
  return isBrowserEnvironment() && window.location.hostname === PRODUCTION_FRONTEND_HOSTNAME
}

export function getApiBaseUrl(): string {
  const normalized = normalizeBaseUrl(viteEnv.VITE_API_BASE_URL)
  if (normalized === null) {
    if (isBrowserEnvironment() && isLocalBrowserHost(window.location.hostname)) {
      return HOSTED_API_BASE_URL
    }
    if (typeof process !== "undefined") {
      return LOCAL_DEV_API_BASE_URL
    }
    if (isBrowserEnvironment()) {
      return ""
    }
    throw new Error(
      `Missing required env ${REQUIRED_ENV_NAME}. ` +
        `Set it in frontend/.env, .env.development, or .env.production before starting/building frontend.`,
    )
  }
  return normalized
}

export const API_BASE_URL = getApiBaseUrl()

export function getPaperPreviewApiBaseUrl(): string {
  const configured = normalizeBaseUrl(viteEnv[PAPER_PREVIEW_ENV_NAME])
  if (configured !== null) {
    return configured
  }
  if (isPrimaryProductionFrontend()) {
    return PRODUCTION_PAPER_PREVIEW_API_BASE_URL
  }
  return getApiBaseUrl()
}

export const PAPER_PREVIEW_API_BASE_URL = getPaperPreviewApiBaseUrl()

export function isTranslatedHtmlReaderEnabled(): boolean {
  const rawValue = normalizeBaseUrl(viteEnv[TRANSLATED_HTML_READER_ENV_NAME])
  if (rawValue === null) {
    return !isPrimaryProductionFrontend()
  }
  return !["0", "false", "no", "off"].includes(rawValue.toLowerCase())
}

export const ENABLE_TRANSLATED_HTML_READER = isTranslatedHtmlReaderEnabled()
