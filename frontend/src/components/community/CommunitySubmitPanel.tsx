import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { LoginPrompt } from "@/components/LoginPrompt"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/contexts/AuthContext"
import { submitCommunityPaperFromArxiv, submitCommunityPaperFromUpload } from "@/lib/community-api"
import { useStore } from "@/store/useStore"

type SubmitMode = "arxiv" | "upload"

export function CommunitySubmitPanel() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { config, loadUserSettings } = useStore()
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
      setError(
        submitError instanceof Error
          ? submitError.message
          : t("community.submit.errorFallback"),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

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
      setError(
        submitError instanceof Error
          ? submitError.message
          : t("community.submit.errorFallback"),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-sm">
      <CardHeader className="space-y-3">
        <div className="space-y-1">
          <CardTitle>{t("community.submit.title")}</CardTitle>
          <CardDescription>{t("community.submit.description")}</CardDescription>
        </div>
        <div className="rounded-xl border border-border/60 bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">{t("community.submit.emptyTitle")}</p>
          <p className="mt-1">{t("community.submit.emptyDescription")}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs value={mode} onValueChange={(value) => setMode(value as SubmitMode)} className="space-y-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="arxiv">{t("community.submit.arxivTab")}</TabsTrigger>
            <TabsTrigger value="upload">{t("community.submit.uploadTab")}</TabsTrigger>
          </TabsList>

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
            <Button
              type="button"
              onClick={handleArxivSubmit}
              disabled={isArxivDisabled}
              className="w-full sm:w-auto"
            >
              {isArxivMode && isSubmitting
                ? t("community.submit.submitting")
                : t("community.submit.submitArxiv")}
            </Button>
          </TabsContent>

          <TabsContent value="upload" className="mt-0 space-y-4">
            <div className="space-y-2">
              <label htmlFor="community-submit-upload" className="text-sm font-medium">
                {t("community.submit.uploadLabel")}
              </label>
              <Input
                id="community-submit-upload"
                aria-label={t("community.submit.uploadLabel")}
                type="file"
                accept=".zip,.rar,.tar,.gz,.tgz,.tex"
                disabled={isSubmitting}
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-muted-foreground">
                {selectedFile
                  ? t("community.submit.fileSelected", { name: selectedFile.name })
                  : t("community.submit.uploadHint")}
              </p>
            </div>
            <Button
              type="button"
              onClick={handleUploadSubmit}
              disabled={isUploadDisabled}
              className="w-full sm:w-auto"
            >
              {!isArxivMode && isSubmitting
                ? t("community.submit.submitting")
                : t("community.submit.submitUpload")}
            </Button>
          </TabsContent>
        </Tabs>

        {error ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
