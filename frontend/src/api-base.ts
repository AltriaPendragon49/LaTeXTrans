const REQUIRED_ENV_NAME = "VITE_API_BASE_URL";
const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>
const TEST_FALLBACK_API_BASE_URL = "http://127.0.0.1:9001"
const PAPER_PREVIEW_ENV_NAME = "VITE_PAPER_PREVIEW_API_BASE_URL"
const TRANSLATED_HTML_READER_ENV_NAME = "VITE_ENABLE_TRANSLATED_HTML_READER"

function normalizeBaseUrl(value: string | undefined): string | null {
    if (!value || !String(value).trim()) {
        return null
    }
    const normalized = String(value).trim().replace(/\/+$/, "")
    return normalized === "/" ? "" : normalized
}

export function getApiBaseUrl(): string {
    const normalized = normalizeBaseUrl(viteEnv.VITE_API_BASE_URL)
    if (normalized === null) {
        if (typeof process !== "undefined") {
            return TEST_FALLBACK_API_BASE_URL
        }
        if (
            typeof window !== "undefined" &&
            (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost")
        ) {
            return `http://${window.location.hostname}:9001`
        }
    }
    if (normalized === null) {
        throw new Error(
            `Missing required env ${REQUIRED_ENV_NAME}. ` +
            `Set it in frontend/.env, .env.development, or .env.production before starting/building frontend.`
        );
    }
    return normalized;
}

export const API_BASE_URL = getApiBaseUrl();

export function getPaperPreviewApiBaseUrl(): string {
    const configured = normalizeBaseUrl(viteEnv[PAPER_PREVIEW_ENV_NAME])
    if (configured !== null) {
        return configured
    }
    return getApiBaseUrl()
}

export const PAPER_PREVIEW_API_BASE_URL = getPaperPreviewApiBaseUrl()

export function isTranslatedHtmlReaderEnabled(): boolean {
    const rawValue = normalizeBaseUrl(viteEnv[TRANSLATED_HTML_READER_ENV_NAME])
    if (rawValue === null) {
        return true
    }
    return !["0", "false", "no", "off"].includes(rawValue.toLowerCase())
}

export const ENABLE_TRANSLATED_HTML_READER = isTranslatedHtmlReaderEnabled()
