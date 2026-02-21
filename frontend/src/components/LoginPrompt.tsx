/**
 * LoginPrompt Component
 *
 * Displays a styled prompt encouraging guest users to log in
 * to access restricted features (batch translation, history, etc.)
 * Uses theme CSS variables — works in both light and dark modes.
 */

import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LogIn, Lock } from 'lucide-react'

interface LoginPromptProps {
    message?: string
    description?: string
    className?: string
}

export function LoginPrompt({
    message = '请登录以使用此功能',
    description,
    className = '',
}: LoginPromptProps) {
    const navigate = useNavigate()

    return (
        <div
            className={`flex flex-col items-center justify-center gap-5 rounded-2xl border border-border bg-muted/30 px-8 py-12 text-center ${className}`}
        >
            {/* Icon */}
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 ring-1 ring-border">
                <Lock className="h-7 w-7 text-primary" />
            </div>

            {/* Text */}
            <div className="space-y-1.5">
                <p className="text-base font-semibold text-foreground">{message}</p>
                {description && (
                    <p className="max-w-xs text-sm text-muted-foreground">{description}</p>
                )}
            </div>

            {/* CTA */}
            <Button
                onClick={() => navigate('/login')}
                className="gap-2"
            >
                <LogIn className="h-4 w-4" />
                登录账户
            </Button>
        </div>
    )
}
