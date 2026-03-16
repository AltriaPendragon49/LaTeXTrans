/**
 * Login Page
 * 
 * Provides user authentication with email/password.
 * Supports login and registration modes with email verification.
 * 
 * UI Design: Following ui-ux-pro-max skill guidelines
 * - Minimalism style with glassmorphism card
 * - 44px minimum touch targets
 * - Visible focus states
 * - Clear error feedback
 * - Loading states for async operations
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock, AlertCircle, KeySquare } from 'lucide-react'
import { useTranslation } from 'react-i18next'

type AuthMode = 'login' | 'register'

export default function Login() {
    const navigate = useNavigate()
    const location = useLocation()
    const { signIn, signUp, verifyOtp, error, clearError, isSupabaseAvailable, loading: authLoading } = useAuth()
    const { t } = useTranslation()

    const [mode, setMode] = useState<AuthMode>('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [emailSent, setEmailSent] = useState(false)
    const [localError, setLocalError] = useState<string | null>(null)

    // OTP state
    const [otpValue, setOtpValue] = useState('')
    const [otpLoading, setOtpLoading] = useState(false)
    const [otpError, setOtpError] = useState<string | null>(null)
    const [resendCountdown, setResendCountdown] = useState(0)
    const otpInputRef = useRef<HTMLInputElement | null>(null)

    // Get redirect path from location state or default to home
    const from = (location.state as { from?: string })?.from || '/'

    // Start countdown timer when emailSent becomes true
    useEffect(() => {
        if (!emailSent) return
        setResendCountdown(60)
        const timer = setInterval(() => {
            setResendCountdown(prev => {
                if (prev <= 1) {
                    clearInterval(timer)
                    return 0
                }
                return prev - 1
            })
        }, 1000)
        return () => clearInterval(timer)
    }, [emailSent])

    // OTP: handle input change
    const handleOtpChange = useCallback((value: string) => {
        const digits = value.replace(/\D/g, '').slice(0, 8)
        setOtpValue(digits)
    }, [])

    // OTP: verify token
    const handleOtpVerify = async () => {
        if (otpValue.length !== 8) {
            setOtpError(t('auth.enter_the_full_8_digit_verification_code'))
            return
        }
        setOtpError(null)
        setOtpLoading(true)
        try {
            const { error: verifyError } = await verifyOtp(email, otpValue)
            if (!verifyError) {
                navigate(from, { replace: true })
            } else {
                setOtpError(t('auth.the_verification_code_is_incorrect_or_expired_please_try_again'))
                setOtpValue('')
                otpInputRef.current?.focus()
            }
        } finally {
            setOtpLoading(false)
        }
    }

    // OTP: resend verification code
    const handleResend = async () => {
        if (resendCountdown > 0) return
        setOtpError(null)
        setOtpValue('')
        setLoading(true)
        try {
            await signUp(email, password)
        } finally {
            setLoading(false)
        }
    }

    // Form validation
    const validateForm = (): boolean => {
        setLocalError(null)

        if (!email.trim()) {
            setLocalError(t('auth.enter_your_email_address'))
            return false
        }

        if (!email.includes('@')) {
            setLocalError(t('auth.enter_a_valid_email_address'))
            return false
        }

        if (!password) {
            setLocalError(t('auth.enter_your_password'))
            return false
        }

        if (password.length < 6) {
            setLocalError(t('auth.password_must_be_at_least_6_characters'))
            return false
        }

        if (mode === 'register' && password !== confirmPassword) {
            setLocalError(t('auth.the_passwords_do_not_match'))
            return false
        }

        return true
    }

    // Handle form submission
    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        clearError()

        if (!validateForm()) return

        setLoading(true)

        try {
            if (mode === 'login') {
                const { error: authError } = await signIn(email, password)
                if (!authError) {
                    navigate(from, { replace: true })
                }
            } else {
                const { error: authError, needsEmailConfirmation } = await signUp(email, password)
                if (!authError) {
                    if (needsEmailConfirmation) {
                        setEmailSent(true)
                    } else {
                        navigate(from, { replace: true })
                    }
                }
            }
        } finally {
            setLoading(false)
        }
    }

    // Toggle between login and register modes
    const toggleMode = () => {
        setMode(mode === 'login' ? 'register' : 'login')
        setLocalError(null)
        clearError()
        setEmailSent(false)
    }

    // Show warning if Supabase is not configured
    if (!isSupabaseAvailable) {
        return (
            <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Card className="w-full border-border/50 bg-card/80 backdrop-blur-sm shadow-xl">
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl">{t('auth.authentication_service_unavailable')}</CardTitle>
                        <CardDescription>
                            {t('auth.supabase_authentication_is_not_configured_for_this_system_so_sign_in_is_unavailable')}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Alert variant="default" className="border-amber-500/30 bg-amber-500/10">
                            <AlertCircle className="h-4 w-4 text-amber-500" />
                            <AlertDescription className="text-amber-700 dark:text-amber-300">
                                {t('auth.set_vite_supabase_url_and_vite_supabase_anon_key_in_your_env_file')}
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                    <CardFooter>
                        <Button
                            className="w-full"
                            variant="outline"
                            onClick={() => navigate('/')}
                        >
                            {t('auth.actions.backToGuestHome')}
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        )
    }

    // Show OTP verification screen
    if (emailSent) {
        return (
            <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Card className="w-full border-border/50 bg-card/80 backdrop-blur-sm shadow-xl">
                    <CardHeader className="text-center space-y-2">
                        <div className="mx-auto p-3 rounded-full bg-primary/10 text-primary w-fit">
                            <KeySquare className="h-8 w-8" />
                        </div>
                        <CardTitle className="text-2xl">{t('auth.enter_verification_code')}</CardTitle>
                        <CardDescription>
                            {t('auth.we_sent_an_8_digit_verification_code_to_check_your_email_and_enter_it', { email })}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-5">
                        {/* OTP error */}
                        {otpError && (
                            <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{otpError}</AlertDescription>
                            </Alert>
                        )}

                        {/* OTP input grid - single input overlaid on visual cells */}
                        <div
                            className="relative h-14 flex gap-1.5 cursor-text"
                            onClick={() => otpInputRef.current?.focus()}
                        >
                            {/* Visual cells (pointer-events-none) */}
                            {Array.from({ length: 8 }).map((_, i) => {
                                const char = otpValue[i] ?? ''
                                const isFocused = otpValue.length === i
                                const isFilled = !!char
                                return (
                                    <div
                                        key={i}
                                        className={[
                                            'flex-1 flex items-center justify-center',
                                            'rounded-lg border-2 text-xl font-bold font-mono',
                                            'transition-all duration-150 select-none',
                                            isFilled
                                                ? 'border-primary bg-primary/5 text-foreground'
                                                : isFocused
                                                    ? 'border-primary bg-background shadow-[0_0_0_3px_hsl(var(--primary)/0.15)]'
                                                    : 'border-border bg-background text-muted-foreground',
                                            otpLoading ? 'opacity-50' : '',
                                        ].join(' ')}
                                    >
                                        {char || (isFocused ? <span className="w-0.5 h-5 bg-primary animate-pulse rounded" /> : '')}
                                    </div>
                                )
                            })}

                            {/* Invisible real input stretched over cells */}
                            <input
                                ref={otpInputRef}
                                type="text"
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                autoFocus
                                value={otpValue}
                                maxLength={8}
                                disabled={otpLoading}
                                onChange={e => handleOtpChange(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter' && otpValue.length === 8) handleOtpVerify()
                                }}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-text"
                                aria-label={t('auth.enter_8_digit_verification_code')}
                            />
                        </div>

                        {/* Verify button */}
                        <Button
                            className="w-full h-11 text-base shadow-lg shadow-primary/20"
                            onClick={handleOtpVerify}
                            disabled={otpLoading || otpValue.length !== 8}
                        >
                            {otpLoading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {t('auth.verifying')}
                                </>
                            ) : t('auth.verify_code')}
                        </Button>

                        {/* Resend */}
                        <div className="text-center text-sm text-muted-foreground">
                            {t('auth.didn_t_receive_the_code')}{' '}
                            <button
                                type="button"
                                onClick={handleResend}
                                disabled={resendCountdown > 0 || loading}
                                className="text-primary hover:underline font-medium disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed cursor-pointer transition-colors duration-150"
                            >
                                {resendCountdown > 0
                                    ? t('auth.resend_s', { seconds: resendCountdown })
                                    : loading ? t('auth.sending') : t('auth.actions.resendCode')}
                            </button>
                        </div>
                    </CardContent>
                    <CardFooter>
                        <Button
                            variant="ghost"
                            className="w-full cursor-pointer"
                            onClick={() => {
                                setEmailSent(false)
                                setMode('login')
                                setOtpValue('')
                                setOtpError(null)
                            }}
                        >
                            {t('auth.actions.backToSignIn')}
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        )
    }

    // Loading state
    if (authLoading) {
        return (
            <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    const authErrorMessage = error ? t('auth.errors.requestFailed') : null

    return (
        <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh] animate-in fade-in duration-500">
            <Card className="w-full border-border/50 bg-card/80 backdrop-blur-sm shadow-xl">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl">
                        {mode === 'login' ? t('auth.welcome_back') : t('auth.actions.createAccount')}
                    </CardTitle>
                    <CardDescription>
                        {mode === 'login'
                            ? t('auth.sign_in_to_save_your_translation_history_and_settings')
                            : t('auth.create_an_account_to_use_all_features')
                        }
                    </CardDescription>
                </CardHeader>

                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4">
                        {/* Error display */}
                        {(error || localError) && (
                            <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{authErrorMessage || localError}</AlertDescription>
                            </Alert>
                        )}

                        {/* Email field */}
                        <div className="space-y-2">
                            <Label htmlFor="email">{t('auth.labels.emailAddress')}</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder={t('auth.enter_your_email_address')}
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="pl-10"
                                    autoComplete="email"
                                    disabled={loading}
                                />
                            </div>
                        </div>

                        {/* Password field */}
                        <div className="space-y-2">
                            <Label htmlFor="password">{t('auth.labels.password')}</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pl-10"
                                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                                    disabled={loading}
                                />
                            </div>
                        </div>

                        {/* Confirm password field (register only) */}
                        {mode === 'register' && (
                            <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                                <Label htmlFor="confirmPassword">{t('auth.confirm_password')}</Label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="confirmPassword"
                                        type="password"
                                        placeholder="••••••••"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="pl-10"
                                        autoComplete="new-password"
                                        disabled={loading}
                                    />
                                </div>
                            </div>
                        )}
                    </CardContent>

                    <CardFooter className="flex flex-col gap-4">
                        <Button
                            type="submit"
                            className="w-full h-11 text-base shadow-lg shadow-primary/20"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {mode === 'login' ? t('auth.signing_in') : t('auth.creating_account')}
                                </>
                            ) : (
                                mode === 'login' ? t('common.actions.signIn') : t('auth.actions.signUp')
                            )}
                        </Button>

                        <div className="text-center text-sm text-muted-foreground">
                            {mode === 'login' ? (
                                <>
                                    {t('auth.don_t_have_an_account')}{' '}
                                    <button
                                        type="button"
                                        onClick={toggleMode}
                                        className="text-primary hover:underline font-medium cursor-pointer"
                                    >
                                        {t('auth.actions.signUpNow')}
                                    </button>
                                </>
                            ) : (
                                <>
                                    {t('auth.already_have_an_account')}{' '}
                                    <button
                                        type="button"
                                        onClick={toggleMode}
                                        className="text-primary hover:underline font-medium cursor-pointer"
                                    >
                                        {t('auth.actions.backToSignIn')}
                                    </button>
                                </>
                            )}
                        </div>

                        <div className="relative w-full">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-border/50" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-card px-2 text-muted-foreground">{t('auth.or')}</span>
                            </div>
                        </div>

                        <Button
                            type="button"
                            variant="outline"
                            className="w-full"
                            onClick={() => navigate('/')}
                        >
                            {t('auth.actions.continueInGuestMode')}
                        </Button>
                    </CardFooter>
                </form>
            </Card>
        </div>
    )
}
