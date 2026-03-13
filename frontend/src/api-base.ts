const REQUIRED_ENV_NAME = "VITE_API_BASE_URL";

export function getApiBaseUrl(): string {
    const value = import.meta.env.VITE_API_BASE_URL;
    if (!value || !String(value).trim()) {
        throw new Error(
            `Missing required env ${REQUIRED_ENV_NAME}. ` +
            `Set it in frontend/.env, .env.development, or .env.production before starting/building frontend.`
        );
    }
    return String(value).trim().replace(/\/+$/, "");
}

export const API_BASE_URL = getApiBaseUrl();
