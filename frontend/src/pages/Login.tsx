import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowUpRight, Loader2, Lock, Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/contexts/AuthContext'
import { getNiuTransAccountUrl, getNiuTransRegisterUrl } from '@/lib/local-auth'

export default function Login() {
    const navigate = useNavigate()
    const location = useLocation()
    const { signIn, error, clearError, loading: authLoading } = useAuth()
    const { t } = useTranslation()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [localError, setLocalError] = useState<string | null>(null)

    const from = (location.state as { from?: string })?.from || '/'
    const registerUrl = getNiuTransRegisterUrl()
    const accountUrl = getNiuTransAccountUrl()

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

        return true
    }

    const openExternalUrl = (url: string) => {
        if (typeof window === 'undefined') {
            return
        }
        window.location.assign(url)
    }

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault()
        clearError()

        if (!validateForm()) {
            return
        }

        setLoading(true)
        try {
            const { error: authError } = await signIn(email, password)
            if (!authError) {
                navigate(from, { replace: true })
            }
        } finally {
            setLoading(false)
        }
    }

    if (authLoading) {
        return (
            <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    const authErrorMessage = error || null

    return (
        <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh] animate-in fade-in duration-500">
            <Card className="w-full border-border/50 bg-card/80 backdrop-blur-sm shadow-xl">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl">{t('auth.welcome_back')}</CardTitle>
                    <CardDescription>{t('auth.sign_in_to_save_your_translation_history_and_settings')}</CardDescription>
                </CardHeader>

                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4">
                        {(error || localError) && (
                            <Alert variant="destructive" className="animate-in fade-in slide-in-from-top-2">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{authErrorMessage || localError}</AlertDescription>
                            </Alert>
                        )}

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

                        <div className="space-y-2">
                            <Label htmlFor="password">{t('auth.labels.password')}</Label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="********"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pl-10"
                                    autoComplete="current-password"
                                    disabled={loading}
                                />
                            </div>
                        </div>
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
                                    {t('auth.signing_in')}
                                </>
                            ) : (
                                t('common.actions.signIn')
                            )}
                        </Button>

                        <div className="w-full rounded-xl border border-border/50 bg-muted/20 p-4 text-left">
                            <p className="text-sm font-medium text-foreground">
                                {t('auth.create_an_account_to_use_all_features')}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                                {t('profile.manage_your_account_information')}
                            </p>
                            <div className="mt-4 flex flex-col gap-2">
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="w-full justify-between"
                                    onClick={() => openExternalUrl(registerUrl)}
                                >
                                    <span>{t('auth.actions.createAccount')}</span>
                                    <ArrowUpRight className="h-4 w-4" />
                                </Button>
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="w-full justify-between"
                                    onClick={() => openExternalUrl(accountUrl)}
                                >
                                    <span>{t('profile.manage_your_account_information')}</span>
                                    <ArrowUpRight className="h-4 w-4" />
                                </Button>
                            </div>
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
