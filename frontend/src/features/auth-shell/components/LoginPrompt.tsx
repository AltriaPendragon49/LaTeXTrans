import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { Lock, LogIn } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

interface LoginPromptProps {
  messageKey?: string
  descriptionKey?: string
  actionLabelKey?: string
  messageValues?: Record<string, unknown>
  descriptionValues?: Record<string, unknown>
  className?: string
}

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
