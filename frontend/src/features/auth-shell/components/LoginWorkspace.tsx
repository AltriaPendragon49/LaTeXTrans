import { useState } from "react"
import type { FormEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { AlertCircle, Loader2, Lock, Mail } from "lucide-react"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { getNiuTransAccountUrl, getNiuTransRegisterUrl } from "@/lib/local-auth"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { Label } from "@/ui/primitives/label"

import styles from "./LoginWorkspace.module.css"

/** 打开外部 URL（小牛翻译注册/账户管理页面） */
function openExternalUrl(url: string) {
  if (typeof window === "undefined") {
    return
  }
  window.location.assign(url)
}

/**
 * 登录工作区组件
 * 提供邮箱/手机号+密码的登录表单，支持：
 * - 表单验证
 * - 登录成功后导航回来源页面
 * - 跳转到小牛翻译注册和账户管理页面
 * - 游客模式继续浏览
 */
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

  /** 表单验证 */
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

  /** 提交登录 */
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
    <div className={`${styles.scene} animate-in fade-in duration-500`}>
      <section className={styles.shell}>
        <div className={styles.panel}>
          <form className={styles.form} onSubmit={handleSubmit}>
            <header className={styles.header}>
              <div className={styles.eyebrow}>{t("brand.name")}</div>
              <h1 className={styles.title} id="heading">
                {t("auth.welcome_back")}
              </h1>
              <p className={styles.description}>
                {t("auth.sign_in_to_save_your_translation_history_and_settings")}
              </p>
            </header>

            {(error || localError) ? (
              <NoticeBanner
                tone="danger"
                icon={<AlertCircle className="h-4 w-4" />}
                description={authErrorMessage || localError}
                className={`${styles.error} animate-in fade-in slide-in-from-top-2`}
              />
            ) : null}

            <div className={styles.fieldBlock}>
              <Label htmlFor="identifier" className={styles.label}>
                {t("auth.labels.emailOrPhoneNumber")}
              </Label>
              <div className={styles.field}>
                <Mail className={styles.icon} />
                <input
                  id="identifier"
                  type="text"
                  placeholder={t("auth.enter_your_email_or_phone_number")}
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  className={styles.input}
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
            </div>

            <div className={styles.fieldBlock}>
              <Label htmlFor="password" className={styles.label}>
                {t("auth.labels.password")}
              </Label>
              <div className={styles.field}>
                <Lock className={styles.icon} />
                <input
                  id="password"
                  type="password"
                  placeholder="********"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className={styles.input}
                  autoComplete="current-password"
                  disabled={loading}
                />
              </div>
            </div>

            <div className={styles.actions}>
              <button
                type="submit"
                className={styles.primaryButton}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("auth.signing_in")}
                  </>
                ) : (
                  t("common.actions.signIn")
                )}
              </button>

              <div className={styles.secondaryRow}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => openExternalUrl(registerUrl)}
                >
                  {t("auth.actions.createAccount")}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => openExternalUrl(accountUrl)}
                >
                  {t("profile.manage_your_account_information")}
                </button>
              </div>

              <button
                type="button"
                className={styles.ghostButton}
                onClick={() => navigate("/")}
              >
                {t("auth.actions.continueInGuestMode")}
              </button>
            </div>

            <p className={styles.footerNote}>
              {t("brand.subtitle")}
            </p>
          </form>
        </div>
      </section>
    </div>
  )
}
