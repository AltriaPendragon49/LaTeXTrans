import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { Lock, LogIn } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

/** 登录提示组件 Props */
interface LoginPromptProps {
  /** 提示消息的 i18n key */
  messageKey?: string
  /** 提示描述的 i18n key */
  descriptionKey?: string
  /** 操作按钮文案的 i18n key */
  actionLabelKey?: string
  /** 消息插值参数 */
  messageValues?: Record<string, unknown>
  /** 描述插值参数 */
  descriptionValues?: Record<string, unknown>
  className?: string
}

/**
 * 登录提示组件
 * 当用户未登录时，展示锁图标、提示文案和"前往登录"按钮。
 * 可在各功能模块中复用作为未登录状态的标准 UI
 */
export function LoginPrompt({
  messageKey = "auth.loginRequiredForThisFeature",
  descriptionKey,
  actionLabelKey = "auth.actions.signInAccount",
  messageValues,
  descriptionValues,
  className = "",
}: LoginPromptProps) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  return (
    <StatePanel
      className={className}
      icon={<Lock className="h-7 w-7" />}
      title={t(messageKey, messageValues)}
      description={descriptionKey ? t(descriptionKey, descriptionValues) : undefined}
      actions={(
        <Button onClick={() => navigate("/login")} className="gap-2">
          <LogIn className="h-4 w-4" />
          {t(actionLabelKey)}
        </Button>
      )}
    />
  )
}
