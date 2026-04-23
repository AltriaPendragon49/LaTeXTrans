import { API_BASE_URL } from "@/api-base"
import { retryOnTransientNetworkError } from "@/lib/network-retry"

export interface LocalAuthUser {
    id: string
    external_provider: string
    external_user_id: string
    roles: string[]
    login_identifier?: string | null
    display_name?: string | null
    email?: string | null
    phone?: string | null
}

export interface LocalAuthSession {
    access_token: string
    token_type: string
    expires_in: number
    user: LocalAuthUser
}

export interface LocalAuthError {
    message: string
    code?: string
    status?: number
}

const SESSION_STORAGE_KEY = "latextrans.localAuth.session"
const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>

const DEFAULT_NIUTRANS_LOGIN_URL = "https://niutrans.com/login?active=0"
const DEFAULT_NIUTRANS_REGISTER_URL = "https://niutrans.com/login?active=3"
const DEFAULT_NIUTRANS_ACCOUNT_URL = "https://niutrans.com/login?active=0"

function isBrowser(): boolean {
    return typeof window !== "undefined"
}

function normalizeUser(input: Partial<LocalAuthUser>): LocalAuthUser | null {
    if (typeof input.id !== "string" || !input.id.trim()) {
        return null
    }

    return {
        id: input.id,
        external_provider: String(input.external_provider ?? "niutrans"),
        external_user_id: String(input.external_user_id ?? ""),
        roles: Array.isArray(input.roles) ? input.roles.map((role) => String(role)) : ["user"],
        login_identifier: typeof input.login_identifier === "string" ? input.login_identifier : null,
        display_name: typeof input.display_name === "string" ? input.display_name : null,
        email: typeof input.email === "string" ? input.email : null,
        phone:
            typeof input.phone === "string"
                ? input.phone
                : typeof (input as { phone_number?: unknown }).phone_number === "string"
                  ? (input as { phone_number: string }).phone_number
                  : null,
    }
}

function parseErrorPayload(payload: unknown, fallbackMessage: string): LocalAuthError {
    if (!payload || typeof payload !== "object") {
        return { message: fallbackMessage }
    }

    const record = payload as Record<string, unknown>
    return {
        message: typeof record.message === "string" ? record.message : fallbackMessage,
        code: typeof record.code === "string" ? record.code : undefined,
    }
}

export function isLocalAuthConfigured(): boolean {
    return true
}

export function getStoredSession(): LocalAuthSession | null {
    if (!isBrowser()) {
        return null
    }

    const rawValue = window.localStorage.getItem(SESSION_STORAGE_KEY)
    if (!rawValue) {
        return null
    }

    try {
        const parsed = JSON.parse(rawValue) as Partial<LocalAuthSession>
        if (
            typeof parsed.access_token !== "string" ||
            typeof parsed.token_type !== "string" ||
            typeof parsed.expires_in !== "number"
        ) {
            return null
        }

        const user = normalizeUser((parsed.user as Partial<LocalAuthUser>) ?? {})
        if (!user) {
            return null
        }

        return {
            access_token: parsed.access_token,
            token_type: parsed.token_type,
            expires_in: parsed.expires_in,
            user,
        }
    } catch {
        return null
    }
}

export function persistSession(session: LocalAuthSession): void {
    if (!isBrowser()) {
        return
    }
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

export function clearStoredSession(): void {
    if (!isBrowser()) {
        return
    }
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
}

export async function getAccessToken(): Promise<string | null> {
    return getStoredSession()?.access_token ?? null
}

export async function signInWithPassword(
    identifier: string,
    password: string,
): Promise<{ session: LocalAuthSession | null; error: LocalAuthError | null }> {
    try {
        const response = await retryOnTransientNetworkError(
            () =>
                fetch(`${API_BASE_URL}/api/auth/login`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        identifier,
                        password,
                    }),
                }),
            { attempts: 3, baseDelayMs: 150 },
        )

        const payload = await response.json().catch(() => null)
        if (!response.ok) {
            return {
                session: null,
                error: {
                    ...parseErrorPayload(payload, "Unable to sign in."),
                    status: response.status,
                },
            }
        }

        const session = payload as Partial<LocalAuthSession>
        const user = normalizeUser((session.user as Partial<LocalAuthUser>) ?? {})
        if (
            typeof session.access_token !== "string" ||
            typeof session.token_type !== "string" ||
            typeof session.expires_in !== "number" ||
            !user
        ) {
            return {
                session: null,
                error: { message: "Unable to sign in." },
            }
        }

        const nextSession: LocalAuthSession = {
            access_token: session.access_token,
            token_type: session.token_type,
            expires_in: session.expires_in,
            user,
        }
        persistSession(nextSession)
        return { session: nextSession, error: null }
    } catch {
        return {
            session: null,
            error: { message: "Unable to sign in." },
        }
    }
}

export async function bootstrapLocalSession(): Promise<{
    session: LocalAuthSession | null
    user: LocalAuthUser | null
}> {
    const session = getStoredSession()
    if (!session) {
        return { session: null, user: null }
    }

    try {
        const response = await retryOnTransientNetworkError(
            () =>
                fetch(`${API_BASE_URL}/api/auth/me`, {
                    headers: {
                        Authorization: `Bearer ${session.access_token}`,
                        "Content-Type": "application/json",
                    },
                }),
            { attempts: 3, baseDelayMs: 150 },
        )

        const payload = await response.json().catch(() => null)
        const restoredUser = normalizeUser(
            payload && typeof payload === "object" ? ((payload as { user?: Partial<LocalAuthUser> }).user ?? {}) : {},
        )
        if (!response.ok || !restoredUser) {
            clearStoredSession()
            return { session: null, user: null }
        }

        const nextSession: LocalAuthSession = {
            ...session,
            user: restoredUser,
        }
        persistSession(nextSession)
        return { session: nextSession, user: restoredUser }
    } catch {
        clearStoredSession()
        return { session: null, user: null }
    }
}

export async function signOutCurrentSession(accessToken?: string | null): Promise<void> {
    const token = accessToken ?? (await getAccessToken())

    try {
        if (token) {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
            })
        }
    } finally {
        clearStoredSession()
    }
}

export function getNiuTransLoginUrl(): string {
    return viteEnv.VITE_NIUTRANS_LOGIN_URL || DEFAULT_NIUTRANS_LOGIN_URL
}

export function getNiuTransRegisterUrl(): string {
    return viteEnv.VITE_NIUTRANS_REGISTER_URL || DEFAULT_NIUTRANS_REGISTER_URL
}

export function getNiuTransAccountUrl(): string {
    return viteEnv.VITE_NIUTRANS_ACCOUNT_URL || DEFAULT_NIUTRANS_ACCOUNT_URL
}
