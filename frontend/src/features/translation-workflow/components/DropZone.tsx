import type { ChangeEvent } from "react"
import { useCallback, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, CheckCircle2, File, X } from "lucide-react"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { UploadCard } from "@/ui/upload-card/UploadCard"
import { uploadFile } from "@/lib/api"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"

type UploadErrorShape = {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

export function DropZone() {
  const { setTaskId, setArxivId, resetTranslationState } = useTranslationTask()
  const { setLatexValidation, latexValidation } = useTranslationConfig()
  const { t } = useTranslation()
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle")
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrag = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    if (event.type === "dragenter" || event.type === "dragover") {
      setIsDragActive(true)
    } else if (event.type === "dragleave") {
      setIsDragActive(false)
    }
  }, [])

  const processFile = useCallback(async (file: File) => {
    const validExtensions = [".zip", ".rar", ".tar", ".gz", ".tgz", ".tex"]
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()

    if (!validExtensions.includes(ext)) {
      toast.error(t("upload.unsupported_file_type_upload_a_zip_rar_tar_gz_or_tex_file"))
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      toast.error(t("upload.file_size_exceeds_the_50_mb_limit"))
      return
    }

    resetTranslationState()
    setFileName(file.name)
    setUploadStatus("uploading")
    setProgress(0)

    const interval = window.setInterval(() => {
      setProgress((prev) => (prev >= 90 ? prev : prev + 10))
    }, 200)

    try {
      const response = await uploadFile(file)

      window.clearInterval(interval)
      setProgress(100)
      setUploadStatus("success")
      setTaskId(response.task_id)

      if (response.latex_validation) {
        setLatexValidation(response.latex_validation)
        if (response.latex_validation.is_valid) {
          toast.success(t("upload.file_uploaded_successfully_and_passed_validation"))
        } else {
          toast.warning(t("upload.file_uploaded_successfully_but_validation_found_issues"))
        }
      } else {
        toast.success(t("upload.file_uploaded_successfully"))
      }

      setArxivId(null)
    } catch (error: unknown) {
      window.clearInterval(interval)
      setUploadStatus("error")
      const uploadError = error as UploadErrorShape
      console.error("[DropZone] Upload failed", uploadError)
      toast.error(t("upload.upload_failed"))
    }
  }, [resetTranslationState, setArxivId, setLatexValidation, setTaskId, t])

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(false)

    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      void processFile(event.dataTransfer.files[0])
    }
  }, [processFile])

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    event.preventDefault()
    if (event.target.files && event.target.files[0]) {
      void processFile(event.target.files[0])
    }
  }

  function resetUpload(event: React.MouseEvent) {
    event.stopPropagation()
    setUploadStatus("idle")
    setFileName("")
    setProgress(0)
    if (inputRef.current) {
      inputRef.current.value = ""
    }
    setLatexValidation(null)
  }

  function openFileDialog() {
    inputRef.current?.click()
  }

  return (
    <div className="w-full space-y-4">
      <motion.div
        layout
        className="cursor-pointer"
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            openFileDialog()
          }
        }}
        role="button"
        tabIndex={0}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".zip,.rar,.tar,.tar.gz,.tgz,.tex"
          onChange={handleChange}
        />

        <UploadCard
          isDragActive={isDragActive}
          fileName={fileName}
          progress={progress}
          status={uploadStatus}
          idleTitle={t("upload.click_to_upload_or_drag_a_file_here")}
          idleDescription={t("upload.supports_zip_rar_tar_gz_archives_or_a_single_tex_file_max_50_mb")}
          uploadingLabel={t("upload.uploading_and_validating")}
          successActionLabel={t("upload.replace_file")}
          errorLabel={t("upload.upload_failed")}
          retryLabel={t("common.actions.retry")}
          onReset={resetUpload}
        />
      </motion.div>

      <AnimatePresence>
        {uploadStatus === "success" && latexValidation ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <NoticeBanner
              tone={latexValidation.is_valid ? "success" : "danger"}
              icon={latexValidation.is_valid ? <CheckCircle2 className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
              title={latexValidation.is_valid ? t("upload.valid_latex_project") : t("upload.invalid_latex_project")}
              description={
                latexValidation.main_file ? (
                  <span className="flex items-center gap-2">
                    <File className="h-4 w-4 shrink-0" />
                    <span>
                      {t("upload.main_entry_file")}
                      <span className="ml-1 font-mono">{latexValidation.main_file}</span>
                    </span>
                  </span>
                ) : undefined
              }
            >
              {latexValidation.warnings.length > 0 || latexValidation.errors.length > 0 ? (
                <div className="space-y-1 border-t border-current/15 pt-2 text-sm">
                  {latexValidation.errors.map((err, index) => (
                    <div key={`err-${index}`} className="flex items-center gap-2">
                      <X className="h-3 w-3 shrink-0" />
                      <span>{err}</span>
                    </div>
                  ))}
                  {latexValidation.warnings.map((warn, index) => (
                    <div key={`warn-${index}`} className="flex items-center gap-2">
                      <AlertTriangle className="h-3 w-3 shrink-0" />
                      <span>{warn}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </NoticeBanner>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
