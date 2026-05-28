import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Loader2, LogOut, Mail, Settings, User } from "lucide-react"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { getUserLoginInfo } from "@/features/user-workspace/accountIdentity"
import { Button } from "@/ui/button/Button"
import { Card, CardContent } from "@/ui/card/Card"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { SectionCard } from "@/ui/section-card/SectionCard"

/**
 * 个人资料工作区组件
 * 展示用户的登录信息、账户操作入口（设置、登出）。
 * 未登录用户显示登录提示
 */
export function ProfileWorkspace() {
  const navigate = useNavigate()
  const { user, isAuthenticated, loading, signOut } = useAuth()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const { t } = useTranslation()
  const loginInfo = getUserLoginInfo(user)
  const profileValue = loginInfo || t("profile.no_login_information_available")

  const handleLogout = async () => {
    setIsLoggingOut(true)
    await signOut()
    toast.success(t("profile.signed_out"))
    navigate("/")
  }

  if (loading) {
    return (
      <div className="container mx-auto flex min-h-[60vh] max-w-md flex-col justify-center p-6">
        <LoadingState label={t("common.status.loading")} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto max-w-md space-y-6 p-6 animate-in fade-in duration-500">
        <LoginPrompt
          messageKey="profile.not_signed_in"
          descriptionKey="profile.sign_in_to_manage_your_account"
          actionLabelKey="common.go_to_sign_in"
        />
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-3xl space-y-6 p-6 animate-in fade-in duration-500">
      <PageIntro
        icon={<User className="h-6 w-6" />}
        title={t("profile.profile")}
        description={t("profile.manage_your_account_information")}
      />

      <SectionCard
        icon={<Mail className="h-5 w-5" />}
        title={t("profile.login_information")}
        description={t("auth.labels.emailOrPhoneNumber")}
      >
        <Card variant="strong" className="rounded-2xl shadow-none">
          <CardContent className="px-4 py-4">
            <p className="truncate text-base font-semibold text-[color:var(--px-shell-ink)]">{profileValue}</p>
          </CardContent>
        </Card>
      </SectionCard>

      <SectionCard
        icon={<Settings className="h-5 w-5" />}
        title={t("profile.account_actions")}
        description={t("profile.manage_your_account_information")}
        contentClassName="space-y-3"
      >
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => navigate("/workspace/settings")}
        >
          <Settings className="mr-2 h-4 w-4" />
          {t("settings.title")}
        </Button>

        <Button
          variant="destructive"
          className="w-full justify-start transition-all duration-200 active:scale-[0.98]"
          onClick={handleLogout}
          disabled={isLoggingOut}
        >
          {isLoggingOut ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t("profile.signing_out")}
            </>
          ) : (
            <>
              <LogOut className="mr-2 h-4 w-4" />
              {t("profile.sign_out")}
            </>
          )}
        </Button>
      </SectionCard>
    </div>
  )
}
