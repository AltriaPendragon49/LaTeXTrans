import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { submitCommunityPaperFromArxiv, submitCommunityPaperFromUpload } from "@/lib/community-api"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"
import { Input } from "@/ui/input/Input"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import { UploadCard } from "@/ui/upload-card/UploadCard"
import { TabsContent } from "@/ui/primitives/tabs"

/** 提交模式 */
type SubmitMode = "arxiv" | "upload"

/**
 * 社区论文提交面板组件
 * 支持两种提交方式：
 * 1. arXiv ID 提交：调用 submitCommunityPaperFromArxiv API
 * 2. 本地上传：调用 submitCommunityPaperFromUpload API
 * 未登录用户显示登录提示
 */
export function CommunitySubmitPanel() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { config, loadUserSettings } = useTranslationConfig()
  const [mode, setMode] = useState<SubmitMode>("arxiv")
  const [arxivId, setArxivId] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!user) {
    return (
      <LoginPrompt
        messageKey="community.submit.loginRequiredTitle"
        descriptionKey="community.submit.loginRequiredDescription"
      />
    )
  }

  const isArxivMode = mode === "arxiv"
  const isArxivDisabled = isSubmitting || !arxivId.trim()
  const isUploadDisabled = isSubmitting || !selectedFile

  /** 提交 arXiv ID */
  async function handleArxivSubmit() {
    if (isArxivDisabled) {
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      await loadUserSettings()
      const result = await submitCommunityPaperFromArxiv({
        arxiv_id: arxivId.trim(),
        source_language: config.source_language,
        target_language: config.target_language,
      })
      navigate(`/paper/${result.paper.id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmitting(false)
    }
  }

  /** 提交本地文件 */
  async function handleUploadSubmit() {
    if (isUploadDisabled || !selectedFile) {
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      await loadUserSettings()
      const result = await submitCommunityPaperFromUpload(selectedFile, {
        source_language: config.source_language,
        target_language: config.target_language,
      })
      navigate(`/paper/${result.paper.id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm">
      <CardHeader className="space-y-3">
        <div className="space-y-1">
          <CardTitle>{t("community.submit.title")}</CardTitle>
          <CardDescription>{t("community.submit.description")}</CardDescription>
        </div>
        <div className="rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-3 text-sm text-[color:var(--px-shell-muted)]">
          <p className="font-medium text-[color:var(--px-shell-ink)]">{t("community.submit.emptyTitle")}</p>
          <p className="mt-1">{t("community.submit.emptyDescription")}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <EditorialTabs value={mode} onValueChange={(value: string) => setMode(value as SubmitMode)} className="space-y-4">
          <EditorialTabsList className="grid w-full grid-cols-2">
            <EditorialTabsTrigger value="arxiv">{t("community.submit.arxivTab")}</EditorialTabsTrigger>
            <EditorialTabsTrigger value="upload">{t("community.submit.uploadTab")}</EditorialTabsTrigger>
          </EditorialTabsList>

          <TabsContent value="arxiv" className="mt-0 space-y-4">
            <div className="space-y-2">
              <label htmlFor="community-submit-arxiv" className="text-sm font-medium">
                {t("community.submit.arxivLabel")}
              </label>
              <Input
                id="community-submit-arxiv"
                aria-label={t("community.submit.arxivLabel")}
                placeholder={t("community.submit.arxivPlaceholder")}
                value={arxivId}
                onChange={(event) => setArxivId(event.target.value)}
                disabled={isSubmitting}
                className="font-mono"
              />
            </div>
            <Button type="button" onClick={handleArxivSubmit} disabled={isArxivDisabled} className="w-full sm:w-auto">
              {isArxivMode && isSubmitting ? t("community.submit.submitting") : t("community.submit.submitArxiv")}
            </Button>
          </TabsContent>

          <TabsContent value="upload" className="mt-0 space-y-4">
            <label htmlFor="community-submit-upload" className="block">
              <span className="sr-only">{t("community.submit.uploadLabel")}</span>
              <UploadCard
                isDragActive={false}
                fileName={selectedFile?.name ?? ""}
                progress={selectedFile ? 100 : 0}
                status={selectedFile ? "success" : "idle"}
                idleTitle={t("community.submit.uploadLabel")}
                idleDescription={t("community.submit.uploadHint")}
                uploadingLabel={t("community.submit.submitting")}
                successActionLabel={t("upload.replace_file")}
                errorLabel={t("community.submit.errorFallback")}
                retryLabel={t("common.actions.retry")}
                onReset={(event) => {
                  event.preventDefault()
                  setSelectedFile(null)
                }}
              />
              <Input
                id="community-submit-upload"
                aria-label={t("community.submit.uploadLabel")}
                type="file"
                accept=".zip,.rar,.tar,.gz,.tgz,.tex"
                disabled={isSubmitting}
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                className="sr-only"
              />
            </label>
            <Button type="button" onClick={handleUploadSubmit} disabled={isUploadDisabled} className="w-full sm:w-auto">
              {!isArxivMode && isSubmitting ? t("community.submit.submitting") : t("community.submit.submitUpload")}
            </Button>
          </TabsContent>
        </EditorialTabs>

        {error ? (
          <div className="rounded-xl border border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] px-4 py-3 text-sm text-[color:var(--px-shell-danger)]">
            {error}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
