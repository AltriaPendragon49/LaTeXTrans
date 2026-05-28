/**
 * 本地认证模块
 * 管理用户登录、会话持久化、配额快照和登出等功能
 */
import { API_BASE_URL } from "@/api-base"
import { retryOnTransientNetworkError } from "@/lib/network-retry"

/** 本地认证用户信息 */
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

/** LaTeX 翻译配额快照 */
export interface LatexTranslationQuotaSnapshot {
    limit: number
    used: number
    remaining: number
    quota_date: string
    reset_timezone: string
}

/** PDF 直译配额快照 */
export interface PdfDirectQuotaSnapshot {
    unused_integral: number | null
    unused_pages: number | null
    source: string
    status: string
    fetched_at: string | null
}

/** 完整配额快照（含 LaTeX 翻译和 PDF 直译） */
export interface QuotaSnapshot {
    latex_translation: LatexTranslationQuotaSnapshot
    pdf_direct: PdfDirectQuotaSnapshot
}

/** 本地认证会话 */
export interface LocalAuthSession {
    access_token: string
    token_type: string
    expires_in: number
    user: LocalAuthUser
    quota_snapshot?: QuotaSnapshot | null
}

/** 本地认证错误 */
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

/** 判断当前是否在浏览器环境 */
function isBrowser(): boolean {
    return typeof window !== "undefined"
}

/** 标准化用户对象，返回 null 表示数据不合法 */
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

/** 判断输入是否为 Record 类型 */
function isRecord(input: unknown): input is Record<string, unknown> {
    return Boolean(input && typeof input === "object")
}

/** 标准化数值：非有限数值返回 null */
function normalizeNumber(input: unknown): number | null {
    if (typeof input !== "number" || !Number.isFinite(input)) {
        return null
    }
    return input
}

/** 标准化字符串：非字符串或空串返回 fallback */
function normalizeString(input: unknown, fallback: string): string {
    return typeof input === "string" && input.trim() ? input : fallback
}

/**
 * 标准化配额快照数据结构
 * @param input - 原始数据
 * @returns 标准化后的 QuotaSnapshot，数据不合法则返回 null
 */
export function normalizeQuotaSnapshot(input: unknown): QuotaSnapshot | null {
    if (!isRecord(input) || !isRecord(input.latex_translation)) {
        return null
    }

    const latex = input.latex_translation
    const limit = normalizeNumber(latex.limit)
    const used = normalizeNumber(latex.used)
    const remaining = normalizeNumber(latex.remaining)

    if (limit === null || used === null || remaining === null) {
        return null
    }

    const pdf = isRecord(input.pdf_direct) ? input.pdf_direct : {}
    const unusedIntegral = normalizeNumber(pdf.unused_integral)
    const unusedPages = normalizeNumber(pdf.unused_pages)

    return {
        latex_translation: {
            limit,
            used,
            remaining,
            quota_date: normalizeString(latex.quota_date, ""),
            reset_timezone: normalizeString(latex.reset_timezone, "Asia/Shanghai"),
        },
        pdf_direct: {
            unused_integral: unusedIntegral,
            unused_pages: unusedPages,
            source: normalizeString(pdf.source, "niutrans"),
            status: normalizeString(pdf.status, unusedIntegral === null ? "unavailable" : "available"),
            fetched_at: typeof pdf.fetched_at === "string" && pdf.fetched_at.trim() ? pdf.fetched_at : null,
        },
    }
}

/** 解析错误 payload 为 LocalAuthError */
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

/**
 * 检查本地认证是否已配置
 * @returns 始终返回 true（认证模块已集成）
 */
export function isLocalAuthConfigured(): boolean {
    return true
}

/**
 * 从 localStorage 读取已存储的会话
 * @returns 会话对象，不存在或无效时返回 null
 */
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
        const quotaSnapshot = normalizeQuotaSnapshot((parsed as { quota_snapshot?: unknown }).quota_snapshot)

        return {
            access_token: parsed.access_token,
            token_type: parsed.token_type,
            expires_in: parsed.expires_in,
            user,
            quota_snapshot: quotaSnapshot,
        }
    } catch {
        return null
    }
}

/**
 * 持久化会话到 localStorage
 * @param session - 会话对象
 */
export function persistSession(session: LocalAuthSession): void {
    if (!isBrowser()) {
        return
    }
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

/** 清除 localStorage 中存储的会话 */
export function clearStoredSession(): void {
    if (!isBrowser()) {
        return
    }
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
}

/**
 * 获取当前有效的 access token
 * @returns token 字符串，未登录返回 null
 */
export async function getAccessToken(): Promise<string | null> {
    return getStoredSession()?.access_token ?? null
}

/**
 * 使用密码方式登录
 * @param identifier - 登录标识（用户名/邮箱）
 * @param password - 密码
 * @returns 包含会话或错误的对象
 */
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
        const quotaSnapshot = normalizeQuotaSnapshot(
            payload && typeof payload === "object" ? (payload as { quota_snapshot?: unknown }).quota_snapshot : null,
        )
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
            quota_snapshot: quotaSnapshot,
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

/**
 * 启动时从服务端恢复并验证本地会话
 * @returns 包含会话和用户的对象，token 过期或无效时自动清除
 */
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
        const payloadRecord = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {}
        const restoredUser = normalizeUser(
            ((payloadRecord as { user?: Partial<LocalAuthUser> }).user ?? {}),
        )
        if (!response.ok || !restoredUser) {
            clearStoredSession()
            return { session: null, user: null }
        }
        const quotaSnapshot = normalizeQuotaSnapshot(payloadRecord.quota_snapshot) ?? session.quota_snapshot ?? null

        const nextSession: LocalAuthSession = {
            ...session,
            user: restoredUser,
            quota_snapshot: quotaSnapshot,
        }
        persistSession(nextSession)
        return { session: nextSession, user: restoredUser }
    } catch {
        clearStoredSession()
        return { session: null, user: null }
    }
}

/**
 * 从服务端获取当前配额快照
 * @param accessToken - 可选的 access token，不传则自动获取
 * @returns 包含配额快照或错误的对象
 */
export async function fetchQuotaSnapshot(accessToken?: string | null): Promise<{
    quotaSnapshot: QuotaSnapshot | null
    error: LocalAuthError | null
}> {
    const token = accessToken ?? (await getAccessToken())
    if (!token) {
        return {
            quotaSnapshot: null,
            error: { message: "Unable to load quota snapshot.", code: "AUTH_SESSION_MISSING" },
        }
    }

    try {
        const response = await retryOnTransientNetworkError(
            () =>
                fetch(`${API_BASE_URL}/api/auth/quota`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                        "Content-Type": "application/json",
                    },
                }),
            { attempts: 3, baseDelayMs: 150 },
        )
        const payload = await response.json().catch(() => null)

        if (!response.ok) {
            return {
                quotaSnapshot: null,
                error: {
                    ...parseErrorPayload(payload, "Unable to load quota snapshot."),
                    status: response.status,
                },
            }
        }

        const quotaSnapshot = normalizeQuotaSnapshot(
            payload && typeof payload === "object" ? (payload as { quota_snapshot?: unknown }).quota_snapshot : null,
        )
        if (!quotaSnapshot) {
            return {
                quotaSnapshot: null,
                error: { message: "Unable to load quota snapshot." },
            }
        }

        // 同步更新 localStorage 中的会话
        const session = getStoredSession()
        if (session?.access_token === token) {
            persistSession({
                ...session,
                quota_snapshot: quotaSnapshot,
            })
        }

        return { quotaSnapshot, error: null }
    } catch {
        return {
            quotaSnapshot: null,
            error: { message: "Unable to load quota snapshot." },
        }
    }
}

/**
 * 登出当前会话
 * @param accessToken - 可选的 access token
 */
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

/** 获取小牛翻译登录页 URL */
export function getNiuTransLoginUrl(): string {
    return viteEnv.VITE_NIUTRANS_LOGIN_URL || DEFAULT_NIUTRANS_LOGIN_URL
}

/** 获取小牛翻译注册页 URL */
export function getNiuTransRegisterUrl(): string {
    return viteEnv.VITE_NIUTRANS_REGISTER_URL || DEFAULT_NIUTRANS_REGISTER_URL
}

/** 获取小牛翻译账户管理页 URL */
export function getNiuTransAccountUrl(): string {
    return viteEnv.VITE_NIUTRANS_ACCOUNT_URL || DEFAULT_NIUTRANS_ACCOUNT_URL
}
