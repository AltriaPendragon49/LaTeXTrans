import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import i18n from '@/i18n'
import {
    bootstrapLocalSession,
    fetchQuotaSnapshot,
    isLocalAuthConfigured,
    signInWithPassword,
    signOutCurrentSession,
} from '@/lib/local-auth'
import type { LocalAuthError, LocalAuthSession, LocalAuthUser, QuotaSnapshot } from '@/lib/local-auth'
import { toast } from 'sonner'
import { useTranslationStore } from '@/features/translation-workflow/store/useTranslationStore'

interface AuthState {
    user: LocalAuthUser | null
    session: LocalAuthSession | null
    quotaSnapshot: QuotaSnapshot | null
    loading: boolean
    error: string | null
    isAuthenticated: boolean
    isAuthAvailable: boolean
}

interface AuthMethods {
    signIn: (identifier: string, password: string) => Promise<{ error: LocalAuthError | null }>
    signUp: (email: string, password: string) => Promise<{ error: LocalAuthError | null, needsEmailConfirmation?: boolean }>
    verifyOtp: (email: string, token: string) => Promise<{ error: LocalAuthError | null }>
    signOut: () => Promise<void>
    refreshQuotaSnapshot: () => Promise<QuotaSnapshot | null>
    clearError: () => void
}

type AuthContextType = AuthState & AuthMethods

const defaultContext: AuthContextType = {
    user: null,
    session: null,
    quotaSnapshot: null,
    loading: true,
    error: null,
    isAuthenticated: false,
    isAuthAvailable: false,
    signIn: async () => ({ error: null }),
    signUp: async () => ({ error: null }),
    verifyOtp: async () => ({ error: null }),
    signOut: async () => { },
    refreshQuotaSnapshot: async () => null,
    clearError: () => { },
}

const AuthContext = createContext<AuthContextType>(defaultContext)

interface AuthProviderProps {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<LocalAuthUser | null>(null)
    const [session, setSession] = useState<LocalAuthSession | null>(null)
    const [quotaSnapshot, setQuotaSnapshot] = useState<QuotaSnapshot | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const isAuthAvailable = isLocalAuthConfigured()
    const isAuthenticated = !!user

    useEffect(() => {
        let cancelled = false

        void bootstrapLocalSession().then(({ session: restoredSession, user: restoredUser }) => {
            if (cancelled) {
                return
            }

            setSession(restoredSession)
            setUser(restoredUser)
            setQuotaSnapshot(restoredSession?.quota_snapshot ?? null)
            setLoading(false)
        })

        return () => {
            cancelled = true
        }
    }, [])

    const signIn = async (identifier: string, password: string) => {
        setError(null)
        const { session: nextSession, error: signInError } = await signInWithPassword(identifier, password)

        if (signInError) {
            setError(signInError.message)
            return { error: signInError }
        }

        if (nextSession) {
            setSession(nextSession)
            setUser(nextSession.user)
            setQuotaSnapshot(nextSession.quota_snapshot ?? null)

            try {
                useTranslationStore.getState().invalidateUserSettings()
                await useTranslationStore.getState().loadUserSettings(true)
                toast.success(i18n.t('auth.toast.settingsLoaded.title'), {
                    description: i18n.t('auth.toast.settingsLoaded.description'),
                    duration: 4000,
                })
            } catch (loadError) {
                console.warn('[Auth] Failed to load user settings after login:', loadError)
            }
        }

        return { error: null }
    }

    const signUp = async (email: string, password: string) => {
        void email
        void password
        return {
            error: { message: i18n.t('auth.errors.requestFailed') },
            needsEmailConfirmation: false,
        }
    }

    const verifyOtp = async (email: string, token: string) => {
        void email
        void token
        return { error: { message: i18n.t('auth.errors.requestFailed') } }
    }

    const signOut = async () => {
        setError(null)
        await signOutCurrentSession(session?.access_token)
        setSession(null)
        setUser(null)
        setQuotaSnapshot(null)
        useTranslationStore.getState().invalidateUserSettings()
    }

    const refreshQuotaSnapshot = async () => {
        const token = session?.access_token
        if (!token) {
            setQuotaSnapshot(null)
            return null
        }

        const { quotaSnapshot: nextQuotaSnapshot, error: quotaError } = await fetchQuotaSnapshot(token)
        if (quotaError || !nextQuotaSnapshot) {
            return null
        }

        setQuotaSnapshot(nextQuotaSnapshot)
        setSession((currentSession) => (
            currentSession
                ? {
                    ...currentSession,
                    quota_snapshot: nextQuotaSnapshot,
                }
                : currentSession
        ))
        return nextQuotaSnapshot
    }

    const clearError = () => {
        setError(null)
    }

    const value: AuthContextType = {
        user,
        session,
        quotaSnapshot,
        loading,
        error,
        isAuthenticated,
        isAuthAvailable,
        signIn,
        signUp,
        verifyOtp,
        signOut,
        refreshQuotaSnapshot,
        clearError,
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
