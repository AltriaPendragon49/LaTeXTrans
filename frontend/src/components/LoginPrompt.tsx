import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LogIn, Lock } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface LoginPromptProps {
    messageKey?: string
    descriptionKey?: string
    messageValues?: Record<string, unknown>
    descriptionValues?: Record<string, unknown>
    className?: string
}

export function LoginPrompt({
    messageKey = 'auth.loginRequiredForThisFeature',
    descriptionKey,
    messageValues,
    descriptionValues,
    className = '',
}: LoginPromptProps) {
    const navigate = useNavigate()
    const { t } = useTranslation()

    return (
        <div
            className={`flex flex-col items-center justify-center gap-5 rounded-2xl border border-border bg-muted/30 px-8 py-12 text-center ${className}`}
        >
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 ring-1 ring-border">
                <Lock className="h-7 w-7 text-primary" />
            </div>

            <div className="space-y-1.5">
                <p className="text-base font-semibold text-foreground">{t(messageKey, messageValues)}</p>
                {descriptionKey && (
                    <p className="max-w-xs text-sm text-muted-foreground">{t(descriptionKey, descriptionValues)}</p>
                )}
            </div>

            <Button
                onClick={() => navigate('/login')}
                className="gap-2"
            >
                <LogIn className="h-4 w-4" />
                {t('auth.actions.signInAccount')}
            </Button>
        </div>
    )
}
