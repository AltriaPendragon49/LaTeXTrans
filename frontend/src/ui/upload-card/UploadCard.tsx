import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, CheckCircle2, FileArchive, Loader2, Upload, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"

interface UploadCardProps {
  isDragActive: boolean
  fileName: string
  progress: number
  status: "idle" | "uploading" | "success" | "error"
  idleTitle: string
  idleDescription: string
  uploadingLabel: string
  successActionLabel: string
  errorLabel: string
  retryLabel: string
  onReset: (event: React.MouseEvent) => void
}

export function UploadCard({
  isDragActive,
  fileName,
  progress,
  status,
  idleTitle,
  idleDescription,
  uploadingLabel,
  successActionLabel,
  errorLabel,
  retryLabel,
  onReset,
}: UploadCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border-2 border-dashed transition-all duration-300 ease-in-out",
        isDragActive
          ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] shadow-[var(--px-shell-shadow)] scale-[1.01]"
          : "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] hover:border-[color:var(--px-shell-accent)]/45 hover:bg-[color:var(--px-shell-panel-strong)]",
        status === "error" && "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)]",
        status === "success" && "border-[color:var(--px-shell-accent)]/30 bg-[color:var(--px-shell-panel-strong)]",
      )}
    >
      <div className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
        <AnimatePresence mode="wait">
          {status === "idle" ? (
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              className="space-y-4"
            >
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-sm">
                <Upload className="h-8 w-8 text-[color:var(--px-shell-accent)]" />
              </div>
              <div className="space-y-1.5">
                <p className="text-lg font-black text-[color:var(--px-shell-ink)]">{idleTitle}</p>
                <p className="max-w-sm text-sm leading-6 text-[color:var(--px-shell-muted)]">{idleDescription}</p>
              </div>
            </motion.div>
          ) : null}

          {status === "uploading" ? (
            <motion.div
              key="uploading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-sm space-y-4"
            >
              <div className="relative mx-auto h-12 w-12">
                <Loader2 className="h-12 w-12 animate-spin text-[color:var(--px-shell-accent)]" />
                <div className="absolute inset-0 flex items-center justify-center text-[10px] font-black">
                  {progress}%
                </div>
              </div>
              <div className="space-y-1">
                <div className="truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">{fileName}</div>
                <div className="h-1.5 overflow-hidden rounded-full bg-black/8">
                  <motion.div
                    className="h-full rounded-full bg-[color:var(--px-shell-accent)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-[color:var(--px-shell-muted)]">{uploadingLabel}</p>
              </div>
            </motion.div>
          ) : null}

          {status === "success" ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="space-y-3"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]">
                <FileArchive className="h-7 w-7" />
              </div>
              <div className="flex items-center justify-center gap-2">
                <span className="max-w-xs truncate text-lg font-semibold text-[color:var(--px-shell-ink)]">{fileName}</span>
                <CheckCircle2 className="h-5 w-5 text-[color:var(--px-shell-success)]" />
              </div>
              <Button variant="ghost" size="sm" onClick={onReset}>
                <X className="h-4 w-4" />
                {successActionLabel}
              </Button>
            </motion.div>
          ) : null}

          {status === "error" ? (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger-strong)]">
                <AlertTriangle className="h-7 w-7" />
              </div>
              <p className="font-semibold text-[color:var(--px-shell-danger)]">{errorLabel}</p>
              <Button variant="outline" size="sm" onClick={onReset}>
                {retryLabel}
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}
