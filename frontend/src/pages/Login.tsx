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

type AuthMode = 'login' | 'register'

export default function Login() {
    const navigate = useNavigate()
    const location = useLocation()
    const { signIn, signUp, verifyOtp, error, clearError, isSupabaseAvailable, loading: authLoading } = useAuth()

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
            setOtpError('请输入完整的 8 位验证码')
            return
        }
        setOtpError(null)
        setOtpLoading(true)
        try {
            const { error: verifyError } = await verifyOtp(email, otpValue)
            if (!verifyError) {
                navigate(from, { replace: true })
            } else {
                setOtpError('验证码错误或已过期，请重新尝试')
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
            setLocalError('请输入邮箱地址')
            return false
        }

        if (!email.includes('@')) {
            setLocalError('请输入有效的邮箱地址')
            return false
        }

        if (!password) {
            setLocalError('请输入密码')
            return false
        }

        if (password.length < 6) {
            setLocalError('密码至少需要 6 个字符')
            return false
        }

        if (mode === 'register' && password !== confirmPassword) {
            setLocalError('两次输入的密码不一致')
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
                        <CardTitle className="text-2xl">认证服务未配置</CardTitle>
                        <CardDescription>
                            当前系统未配置 Supabase 认证服务，无法使用登录功能。
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Alert variant="default" className="border-amber-500/30 bg-amber-500/10">
                            <AlertCircle className="h-4 w-4 text-amber-500" />
                            <AlertDescription className="text-amber-700 dark:text-amber-300">
                                请在 .env 文件中设置 VITE_SUPABASE_URL 和 VITE_SUPABASE_ANON_KEY
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                    <CardFooter>
                        <Button
                            className="w-full"
                            variant="outline"
                            onClick={() => navigate('/')}
                        >
                            返回首页（访客模式）
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
                        <CardTitle className="text-2xl">输入验证码</CardTitle>
                        <CardDescription>
                            已向 <span className="font-medium text-foreground">{email}</span> 发送了 8 位验证码，请查收邮件并输入。
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
                                aria-label="输入8位验证码"
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
                                    验证中...
                                </>
                            ) : '确认验证码'}
                        </Button>

                        {/* Resend */}
                        <div className="text-center text-sm text-muted-foreground">
                            没有收到验证码？{' '}
                            <button
                                type="button"
                                onClick={handleResend}
                                disabled={resendCountdown > 0 || loading}
                                className="text-primary hover:underline font-medium disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed cursor-pointer transition-colors duration-150"
                            >
                                {resendCountdown > 0
                                    ? `重新发送 (${resendCountdown}s)`
                                    : loading ? '发送中...' : '重新发送'}
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
                            返回登录
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        )
    }

    {/* OTP error */ }
    {
        otpError && (
            <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{otpError}</AlertDescription>
            </Alert>
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

    return (
        <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh] animate-in fade-in duration-500">
            <Card className="w-full border-border/50 bg-card/80 backdrop-blur-sm shadow-xl">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl">
                        {mode === 'login' ? '欢迎回来' : '创建账户'}
                    </CardTitle>
                    <CardDescription>
                        {mode === 'login'
                            ? '登录以保存您的翻译历史和设置'
                            : '注册账户以使用完整功能'
                        }
                    </CardDescription>
                </CardHeader>

                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4">
                        {/* Error display */}
                        {(error || localError) && (
                            <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error || localError}</AlertDescription>
                            </Alert>
                        )}

                        {/* Email field */}
                        <div className="space-y-2">
                            <Label htmlFor="email">邮箱地址</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="请输入邮箱地址"
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
                            <Label htmlFor="password">密码</Label>
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
                                <Label htmlFor="confirmPassword">确认密码</Label>
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
                                    {mode === 'login' ? '登录中...' : '注册中...'}
                                </>
                            ) : (
                                mode === 'login' ? '登录' : '注册'
                            )}
                        </Button>

                        <div className="text-center text-sm text-muted-foreground">
                            {mode === 'login' ? (
                                <>
                                    还没有账户？{' '}
                                    <button
                                        type="button"
                                        onClick={toggleMode}
                                        className="text-primary hover:underline font-medium cursor-pointer"
                                    >
                                        立即注册
                                    </button>
                                </>
                            ) : (
                                <>
                                    已有账户？{' '}
                                    <button
                                        type="button"
                                        onClick={toggleMode}
                                        className="text-primary hover:underline font-medium cursor-pointer"
                                    >
                                        返回登录
                                    </button>
                                </>
                            )}
                        </div>

                        <div className="relative w-full">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-border/50" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-card px-2 text-muted-foreground">或</span>
                            </div>
                        </div>

                        <Button
                            type="button"
                            variant="outline"
                            className="w-full"
                            onClick={() => navigate('/')}
                        >
                            继续使用访客模式
                        </Button>
                    </CardFooter>
                </form>
            </Card>
        </div>
    )
}
