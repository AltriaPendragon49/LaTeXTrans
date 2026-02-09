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

import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock, AlertCircle, CheckCircle2 } from 'lucide-react'

type AuthMode = 'login' | 'register'

export default function Login() {
    const navigate = useNavigate()
    const location = useLocation()
    const { signIn, signUp, error, clearError, isSupabaseAvailable, loading: authLoading } = useAuth()

    const [mode, setMode] = useState<AuthMode>('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [emailSent, setEmailSent] = useState(false)
    const [localError, setLocalError] = useState<string | null>(null)

    // Get redirect path from location state or default to home
    const from = (location.state as { from?: string })?.from || '/'

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

    // Show email confirmation message
    if (emailSent) {
        return (
            <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Card className="w-full border-border/50 bg-card/80 backdrop-blur-sm shadow-xl">
                    <CardHeader className="text-center space-y-2">
                        <div className="mx-auto p-3 rounded-full bg-green-500/10 text-green-600 dark:text-green-400 w-fit">
                            <CheckCircle2 className="h-8 w-8" />
                        </div>
                        <CardTitle className="text-2xl">验证邮件已发送</CardTitle>
                        <CardDescription>
                            请检查您的邮箱 <span className="font-medium text-foreground">{email}</span> 并点击验证链接完成注册。
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Alert className="border-blue-500/30 bg-blue-500/10">
                            <Mail className="h-4 w-4 text-blue-500" />
                            <AlertDescription className="text-blue-700 dark:text-blue-300">
                                验证链接有效期为 24 小时。如未收到邮件，请检查垃圾邮件文件夹。
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                    <CardFooter className="flex flex-col gap-2">
                        <Button
                            className="w-full"
                            onClick={() => {
                                setEmailSent(false)
                                setMode('login')
                            }}
                        >
                            返回登录
                        </Button>
                        <Button
                            variant="ghost"
                            className="w-full"
                            onClick={() => navigate('/')}
                        >
                            继续使用访客模式
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
                                    placeholder="your@email.com"
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
