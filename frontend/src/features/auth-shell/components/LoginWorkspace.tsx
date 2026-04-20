import { useState } from "react"
import type { FormEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { AlertCircle, ArrowUpRight, Loader2, Lock, Mail } from "lucide-react"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { getNiuTransAccountUrl, getNiuTransRegisterUrl } from "@/lib/local-auth"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/ui/card/Card"
import { Input } from "@/ui/input/Input"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { Label } from "@/ui/primitives/label"

function openExternalUrl(url: string) {
  if (typeof window === "undefined") {
    return
  }
  window.location.assign(url)
}

export function LoginWorkspace() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signIn, error, clearError, loading: authLoading } = useAuth()
  const { t } = useTranslation()

  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const from = (location.state as { from?: string })?.from || "/"
  const registerUrl = getNiuTransRegisterUrl()
  const accountUrl = getNiuTransAccountUrl()

  const validateForm = (): boolean => {
    setLocalError(null)

    if (!identifier.trim()) {
      setLocalError(t("auth.enter_your_email_or_phone_number"))
      return false
    }

    if (!password) {
      setLocalError(t("auth.enter_your_password"))
      return false
    }

    return true
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    clearError()

    if (!validateForm()) {
      return
    }

    setLoading(true)
    try {
      const { error: authError } = await signIn(identifier, password)
      if (!authError) {
        navigate(from, { replace: true })
      }
    } finally {
      setLoading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="container mx-auto flex min-h-[60vh] max-w-md items-center justify-center p-6">
        <LoadingState label={t("common.status.loading")} />
      </div>
    )
  }

  const authErrorMessage = error || null

  return (
    <div className="container mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center p-6 animate-in fade-in duration-500">
      <PanelShell tone="glass" padding="none" className="w-full">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">{t("auth.welcome_back")}</CardTitle>
          <CardDescription>{t("auth.sign_in_to_save_your_translation_history_and_settings")}</CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {(error || localError) ? (
              <NoticeBanner
                tone="danger"
                icon={<AlertCircle className="h-4 w-4" />}
                description={authErrorMessage || localError}
                className="animate-in fade-in slide-in-from-top-2"
              />
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="identifier">{t("auth.labels.emailOrPhoneNumber")}</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--px-shell-muted)]" />
                <Input
                  id="identifier"
                  type="text"
                  placeholder={t("auth.enter_your_email_or_phone_number")}
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  className="pl-10"
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t("auth.labels.password")}</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--px-shell-muted)]" />
                <Input
                  id="password"
                  type="password"
                  placeholder="********"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
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
              className="h-11 w-full text-base"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("auth.signing_in")}
                </>
              ) : (
                t("common.actions.signIn")
              )}
            </Button>

            <Card variant="strong" className="w-full rounded-[24px] shadow-none">
              <CardContent className="px-4 py-4 text-left">
                <p className="text-sm font-medium text-[color:var(--px-shell-ink)]">
                  {t("auth.create_an_account_to_use_all_features")}
                </p>
                <p className="mt-1 text-xs text-[color:var(--px-shell-muted)]">
                  {t("profile.manage_your_account_information")}
                </p>
                <div className="mt-4 flex flex-col gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full justify-between"
                    onClick={() => openExternalUrl(registerUrl)}
                  >
                    <span>{t("auth.actions.createAccount")}</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full justify-between"
                    onClick={() => openExternalUrl(accountUrl)}
                  >
                    <span>{t("profile.manage_your_account_information")}</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="relative w-full">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-[color:var(--px-shell-line)]" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-[color:var(--px-shell-panel)] px-2 text-[color:var(--px-shell-muted)]">{t("auth.or")}</span>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => navigate("/")}
            >
              {t("auth.actions.continueInGuestMode")}
            </Button>
          </CardFooter>
        </form>
      </PanelShell>
    </div>
  )
}
