const REQUIRED_ENV_NAME = "VITE_API_BASE_URL";
const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>
const TEST_FALLBACK_API_BASE_URL = "http://127.0.0.1:9001"

export function getApiBaseUrl(): string {
    const value = viteEnv.VITE_API_BASE_URL;
    if (!value || !String(value).trim()) {
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
    if (!value || !String(value).trim()) {
        throw new Error(
            `Missing required env ${REQUIRED_ENV_NAME}. ` +
            `Set it in frontend/.env, .env.development, or .env.production before starting/building frontend.`
        );
    }
    return String(value).trim().replace(/\/+$/, "");
}

export const API_BASE_URL = getApiBaseUrl();
