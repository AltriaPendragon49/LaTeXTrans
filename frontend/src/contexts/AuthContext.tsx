/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the application.
 * Supports guest mode when Supabase is not configured.
 */

import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { User, AuthError, Session } from '@supabase/supabase-js'
import { supabase, isSupabaseConfigured } from '@/lib/supabase'
import { toast } from 'sonner'

// Auth state interface
interface AuthState {
    user: User | null
    session: Session | null
    loading: boolean
    error: string | null
    isAuthenticated: boolean
    isSupabaseAvailable: boolean
}

// Auth methods interface  
interface AuthMethods {
    signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>
    signUp: (email: string, password: string) => Promise<{ error: AuthError | null, needsEmailConfirmation?: boolean }>
    signOut: () => Promise<void>
    clearError: () => void
}

// Combined context type
type AuthContextType = AuthState & AuthMethods

// Default context value
const defaultContext: AuthContextType = {
    user: null,
    session: null,
    loading: true,
    error: null,
    isAuthenticated: false,
    isSupabaseAvailable: false,
    signIn: async () => ({ error: null }),
    signUp: async () => ({ error: null }),
    signOut: async () => { },
    clearError: () => { },
}

// Create context
const AuthContext = createContext<AuthContextType>(defaultContext)

// Provider component
interface AuthProviderProps {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<User | null>(null)
    const [session, setSession] = useState<Session | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const isSupabaseAvailable = isSupabaseConfigured()
    const isAuthenticated = !!user

    // Initialize auth state
    useEffect(() => {
        if (!supabase) {
            setLoading(false)
            return
        }

        // Get initial session
        supabase.auth.getSession().then(({ data: { session: initialSession } }) => {
            setSession(initialSession)
            setUser(initialSession?.user ?? null)
            setLoading(false)
        })

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            (_event: string, newSession: Session | null) => {
                setSession(newSession)
                setUser(newSession?.user ?? null)
            }
        )

        return () => {
            subscription.unsubscribe()
        }
    }, [])

    // Sign in with email/password
    const signIn = async (email: string, password: string) => {
        if (!supabase) {
            return { error: { message: 'Authentication not available' } as AuthError }
        }

        setError(null)
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        })

        if (error) {
            setError(error.message)
        } else {
            // Login successful - trigger settings reload
            try {
                const { useStore } = await import('@/store/useStore')
                useStore.getState().invalidateUserSettings()
                await useStore.getState().loadUserSettings(true)
                toast.success('系统设置已加载', {
                    description: '您保存的默认配置已自动应用',
                    duration: 4000,
                })
            } catch (e) {
                console.warn('[Auth] Failed to load user settings after login:', e)
            }
        }

        return { error }
    }

    // Sign up with email/password
    const signUp = async (email: string, password: string) => {
        if (!supabase) {
            return { error: { message: 'Authentication not available' } as AuthError }
        }

        setError(null)
        const { error, data } = await supabase.auth.signUp({
            email,
            password,
        })

        if (error) {
            setError(error.message)
            return { error }
        }

        // Check if email confirmation is needed
        const needsEmailConfirmation = !data.session && !!data.user

        return { error: null, needsEmailConfirmation }
    }

    // Sign out
    const signOut = async () => {
        if (!supabase) return

        setError(null)
        await supabase.auth.signOut()
    }

    // Clear error
    const clearError = () => {
        setError(null)
    }

    const value: AuthContextType = {
        user,
        session,
        loading,
        error,
        isAuthenticated,
        isSupabaseAvailable,
        signIn,
        signUp,
        signOut,
        clearError,
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

// Hook for using auth context
export function useAuth(): AuthContextType {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
