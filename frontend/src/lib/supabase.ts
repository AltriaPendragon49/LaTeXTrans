/**
 * Supabase Client Configuration
 * 
 * Provides a singleton Supabase client for frontend authentication.
 * Uses VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY environment variables.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'

// Environment variables
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

// Validate environment variables
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.warn(
        'Supabase configuration missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env file for authentication features.'
    )
}

// Create Supabase client (singleton)
export const supabase: SupabaseClient | null =
    SUPABASE_URL && SUPABASE_ANON_KEY
        ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
            auth: {
                autoRefreshToken: true,
                persistSession: true,
                detectSessionInUrl: true,
            }
        })
        : null

/**
 * Check if Supabase is configured
 */
export const isSupabaseConfigured = (): boolean => {
    return supabase !== null
}

/**
 * Get the current access token for API requests
 */
export const getAccessToken = async (): Promise<string | null> => {
    if (!supabase) return null

    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
}
