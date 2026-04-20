import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef, type ChangeEvent, type Dispatch, type SetStateAction } from "react"
import { useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "framer-motion"
import { useTranslation } from "react-i18next"
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileArchive,
  Info,
  Layers,
  Loader2,
  Upload,
  X,
  XCircle,
} from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/ui/button/Button"
import { cn } from "@/lib/utils"
import { Badge } from "@/ui/primitives/badge"
import { Progress } from "@/ui/primitives/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/primitives/tabs"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { RecordRow } from "@/ui/record-row/RecordRow"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { Textarea } from "@/ui/input/Textarea"
import { UploadDropSurface } from "@/ui/upload-card/UploadDropSurface"
import { getTaskCopy } from "@/i18n/task-copy"
import { getTaskStatus, startBatchTranslation, startTranslation, uploadFile } from "@/lib/api"
import { DEFAULT_CONFIG } from "@/types/config"
import type { AdvancedConfig } from "@/types/config"

const MAX_BATCH = 9
const VALID_EXTS = [".zip", ".rar", ".tar", ".gz", ".tgz", ".tex"]
const BATCH_POLL_INTERVAL_MS = 3000
const TERMINAL_BATCH_STATUSES = new Set([
  "completed",
  "completed_with_warnings",
  "failed",
  "failed_compilation",
  "structure_invalid",
])

type Translate = (key: string, options?: Record<string, unknown>) => string

interface BatchTask {
  task_id: string
  label: string
  status: string
  progress: number
  stage?: string | null
  message: string
  detail_code?: string | null
  detail_params?: Record<string, string | number | boolean | null> | null
  warnings?: string | null
  failure_reason_code?: string | null
}

interface QueuedFile {
  file: File
  id: string
}

export interface BatchTranslationHandle {
  submitCurrent: () => void
}

export interface BatchTranslationState {
  isSubmitting: boolean
  activeTab: "arxiv" | "upload"
  canSubmit: boolean
}

interface BatchTranslationProps {
  advancedConfig?: AdvancedConfig
  targetLanguage?: string
  sourceLanguage?: string
  onStateChange?: (state: BatchTranslationState) => void
}

const uid = () => Math.random().toString(36).slice(2, 9)

function statusIcon(status: string) {
  switch (status) {
    case "completed":
    case "completed_with_warnings":
      return <CheckCircle2 className="h-4 w-4 text-[color:var(--px-shell-success)]" />
    case "failed":
    case "failed_compilation":
      return <XCircle className="h-4 w-4 text-[color:var(--px-shell-danger)]" />
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin text-[color:var(--px-shell-accent)]" />
    case "queued":
      return <Clock className="h-4 w-4 text-[color:var(--px-shell-warning)]" />
    default:
      return <Clock className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
  }
}

function statusBadgeTone(status: string): "success" | "danger" | "accent" | "warning" | "muted" {
  if (status === "completed" || status === "completed_with_warnings") {
    return "success"
  }
  if (status === "failed" || status === "failed_compilation") {
    return "danger"
  }
  if (status === "processing") {
    return "accent"
  }
  if (status === "queued") {
    return "warning"
  }
  return "muted"
}

function TaskList({ tasks, translate }: { tasks: BatchTask[]; translate: Translate }) {
  const navigate = useNavigate()

  if (tasks.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-[color:var(--px-shell-muted)]">{translate("batch.taskList")}</p>
      {tasks.map((task) => {
        const copy = getTaskCopy(translate, {
          status: task.status,
          stage: task.stage,
          detailCode: task.detail_code,
          detailParams: task.detail_params,
          failureReasonCode: task.failure_reason_code,
          warnings: task.warnings,
        })

        return (
          <RecordRow
            key={task.task_id}
            icon={statusIcon(task.status)}
            title={<span className="font-mono">{task.label}</span>}
            badge={<StatusBadge tone={statusBadgeTone(task.status)}>{copy.statusLabel}</StatusBadge>}
            action={task.status === "completed" || task.status === "completed_with_warnings" ? (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 gap-1 px-2 text-xs"
                onClick={() => navigate(`/processing?taskId=${task.task_id}`)}
              >
                <ExternalLink className="h-3 w-3" />
                {translate("common.actions.view")}
              </Button>
            ) : null}
            detail={task.status === "processing" || task.status === "queued" ? (
              <div className="space-y-1">
                <Progress
                  value={task.progress}
                  className={cn("h-1.5", copy.isRateLimited && "animate-pulse [&>div]:bg-[color:var(--px-shell-warning)]!")}
                />
                <p className={cn(
                  "text-xs",
                  copy.isRateLimited ? "font-medium text-[color:var(--px-shell-warning)]" : "text-[color:var(--px-shell-muted)]",
                )}>
                  {copy.detailLabel || copy.stageLabel || copy.statusLabel}
                </p>
              </div>
            ) : task.status === "failed" || task.status === "failed_compilation" ? (
              <p className="text-xs text-[color:var(--px-shell-danger)]">{copy.failureLabel || copy.statusLabel}</p>
            ) : null}
            alert={task.warnings ? (
              <p className="mt-1 flex items-center gap-1 text-xs text-[color:var(--px-shell-warning)]">
                <AlertCircle className="h-3 w-3 shrink-0" />
                {translate("task.detail.formattingWarning", { warningText: task.warnings })}
              </p>
            ) : null}
          />
        )
      })}
    </div>
  )
}

export const BatchTranslation = forwardRef<BatchTranslationHandle, BatchTranslationProps>(function BatchTranslation({
  advancedConfig = DEFAULT_CONFIG.advanced_config,
  targetLanguage = "ch",
  sourceLanguage = "en",
  onStateChange,
}, ref) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<"arxiv" | "upload">("arxiv")
  const [arxivText, setArxivText] = useState("")
  const [isArxivSubmitting, setIsArxivSubmitting] = useState(false)
  const [arxivTasks, setArxivTasks] = useState<BatchTask[]>([])
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([])
  const [isDragActive, setIsDragActive] = useState(false)
  const [isUploadSubmitting, setIsUploadSubmitting] = useState(false)
  const [uploadTasks, setUploadTasks] = useState<BatchTask[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const parsedIds = arxivText.split("\n").map((line) => line.trim()).filter(Boolean).slice(0, MAX_BATCH)
  const isOverLimit = arxivText.split("\n").map((line) => line.trim()).filter(Boolean).length > MAX_BATCH
  const submitRef = useRef<() => void>(() => {})
  submitRef.current = () => {
    if (activeTab === "arxiv") {
      void handleArxivSubmit()
    } else {
      void handleUploadSubmit()
    }
  }

  useImperativeHandle(ref, () => ({
    submitCurrent: () => submitRef.current(),
  }), [])

  useEffect(() => {
    onStateChange?.({
      isSubmitting: activeTab === "arxiv" ? isArxivSubmitting : isUploadSubmitting,
      activeTab,
      canSubmit: activeTab === "arxiv"
        ? parsedIds.length > 0 && !isArxivSubmitting
        : queuedFiles.length > 0 && !isUploadSubmitting,
    })
  }, [activeTab, isArxivSubmitting, isUploadSubmitting, onStateChange, parsedIds.length, queuedFiles.length])

  const warnedPersistFailed = useRef<Set<string>>(new Set())
  const activePollsRef = useRef<Set<string>>(new Set())
  const isMountedRef = useRef(true)

  useEffect(() => {
    const activePolls = activePollsRef.current
    isMountedRef.current = true

    return () => {
      isMountedRef.current = false
      activePolls.clear()
    }
  }, [])

  const pollTask = useCallback(async (task_id: string, setter: Dispatch<SetStateAction<BatchTask[]>>) => {
    if (activePollsRef.current.has(task_id)) {
      return
    }

    activePollsRef.current.add(task_id)

    try {
      while (isMountedRef.current) {
        await new Promise((resolve) => setTimeout(resolve, BATCH_POLL_INTERVAL_MS))
        if (!isMountedRef.current) {
          break
        }

        let status
        try {
          status = await getTaskStatus(task_id)
        } catch {
          continue
        }

        if (!isMountedRef.current) {
          break
        }

        if (status.persist_failed && !warnedPersistFailed.current.has(task_id)) {
          warnedPersistFailed.current.add(task_id)
          toast.warning(
            t("batch.due_to_a_backend_network_issue_the_result_could_not_be_saved_to_the_database_please_make_sure_to_save_your_translation_results"),
            { duration: 8000 },
          )
        }

        setter((prev) => prev.map((task) => (
          task.task_id === task_id
            ? {
                ...task,
                status: status.status,
                progress: status.progress,
                stage: status.stage ?? task.stage,
                message: status.message,
                detail_code: status.detail_code ?? task.detail_code,
                detail_params: status.detail_params ?? task.detail_params,
                warnings: status.warnings ?? task.warnings,
                failure_reason_code: status.failure_reason_code ?? task.failure_reason_code,
              }
            : task
        )))

        if (TERMINAL_BATCH_STATUSES.has(String(status.status || "").toLowerCase())) {
          break
        }
      }
    } finally {
      activePollsRef.current.delete(task_id)
    }
  }, [t])

  async function handleArxivSubmit() {
    if (parsedIds.length === 0) {
      toast.error(t("batch.enter_at_least_one_arxiv_id"))
      return
    }

    setIsArxivSubmitting(true)
    try {
      const response = await startBatchTranslation({
        arxiv_ids: parsedIds,
        target_language: targetLanguage,
        source_language: sourceLanguage,
        advanced_config: advancedConfig,
      })
      const initial: BatchTask[] = response.task_ids.map((taskId, index) => ({
        task_id: taskId,
        label: parsedIds[index] ?? taskId,
        status: "processing",
        stage: "downloading",
        progress: 0,
        message: t("task.detail.taskWaiting"),
        detail_code: "task_waiting",
        detail_params: null,
      }))
      setArxivTasks(initial)
      setArxivText("")
      toast.success(t("batch.batch_translation_submitted_tasks_created_successfully", { count: response.queued_count }))
      for (const task of initial) {
        void pollTask(task.task_id, setArxivTasks)
      }
    } catch (error: unknown) {
      console.error("[BatchTranslation] Failed to submit arXiv batch", error)
      toast.error(t("batch.submission_failed"))
    } finally {
      setIsArxivSubmitting(false)
    }
  }

  const addFiles = useCallback((files: FileList | File[]) => {
    const arr = Array.from(files)
    const valid = arr.filter((file) => {
      const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()
      if (!VALID_EXTS.includes(ext)) {
        toast.error(t("batch.unsupported_file_type", { name: file.name }))
        return false
      }
      if (file.size > 50 * 1024 * 1024) {
        toast.error(t("batch.file_exceeds_50_mb", { name: file.name }))
        return false
      }
      return true
    })
    setQueuedFiles((prev) => {
      const combined = [...prev, ...valid.map((file) => ({ file, id: uid() }))]
      if (combined.length > MAX_BATCH) {
        toast.warning(t("batch.maximum_files_extra_files_were_removed", { count: MAX_BATCH }))
        return combined.slice(0, MAX_BATCH)
      }
      return combined
    })
  }, [t])

  const handleDrag = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(event.type === "dragenter" || event.type === "dragover")
  }, [])

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(false)
    if (event.dataTransfer.files.length) {
      addFiles(event.dataTransfer.files)
    }
  }, [addFiles])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files?.length) {
      addFiles(event.target.files)
    }
    event.target.value = ""
  }

  function removeFile(id: string) {
    setQueuedFiles((prev) => prev.filter((file) => file.id !== id))
  }

  async function handleUploadSubmit() {
    if (queuedFiles.length === 0) {
      toast.error(t("batch.add_files_first"))
      return
    }

    setIsUploadSubmitting(true)
    const snapshot = [...queuedFiles]
    setQueuedFiles([])

    function appendTask(task: BatchTask) {
      setUploadTasks((prev) => [...prev, task])
    }

    await Promise.all(snapshot.map(async (queuedFile) => {
      try {
        const uploadResponse = await uploadFile(queuedFile.file)
        const taskId = uploadResponse.task_id

        appendTask({
          task_id: taskId,
          label: queuedFile.file.name,
          status: "processing",
          stage: "parsing",
          progress: 0,
          message: t("task.detail.translationStarting"),
          detail_code: "translation_starting",
          detail_params: null,
        })

        void pollTask(taskId, setUploadTasks)

        await startTranslation(taskId, {
          target_language: targetLanguage,
          source_language: sourceLanguage,
          advanced_config: advancedConfig,
        })
      } catch (error: unknown) {
        console.error("[BatchTranslation] Failed to process uploaded file", error)
        appendTask({
          task_id: `failed-${queuedFile.id}`,
          label: queuedFile.file.name,
          status: "failed",
          progress: 0,
          message: t("batch.submission_failed"),
          failure_reason_code: null,
        })
      }
    }))

    setIsUploadSubmitting(false)
    toast.success(t("batch.all_files_have_been_submitted_for_translation"))
  }

  return (
    <div className="space-y-5">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "arxiv" | "upload")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="arxiv" className="gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            {t("batch.batch_arxiv_ids")}
          </TabsTrigger>
          <TabsTrigger value="upload" className="gap-1.5">
            <Upload className="h-3.5 w-3.5" />
            {t("batch.batch_file_upload")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="arxiv" className="mt-4 space-y-4">
          <NoticeBanner
            tone="info"
            icon={<Info className="h-4 w-4" />}
            description={(
              <span>
              {t("batch.enter_one_arxiv_id_per_line_for_example_up_to_total", { example: "2401.00001", count: MAX_BATCH })}{" "}
              {t("batch.full_urls_or_plain_ids_are_supported")}
              </span>
            )}
          />

          <div className="space-y-1.5">
            <label htmlFor="batch-arxiv-input" className="text-sm font-medium text-[color:var(--px-shell-ink)]">
              {t("batch.arxiv_id_list")}
            </label>
            <Textarea
              id="batch-arxiv-input"
              value={arxivText}
              onChange={(event) => setArxivText(event.target.value)}
              placeholder={"2401.00001\n2401.00002\n2401.00003"}
              rows={7}
              spellCheck={false}
              className="min-h-[188px] font-mono text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            {parsedIds.length > 0 ? (
              <Badge variant="secondary">{t("batch.ids", { current: parsedIds.length, total: MAX_BATCH })}</Badge>
            ) : null}
            {isOverLimit ? (
                <span className="flex items-center gap-1 text-xs text-[color:var(--px-shell-danger)]">
                <AlertCircle className="h-3 w-3" />
                {t("batch.limit_exceeded_only_the_first_will_be_submitted", { count: MAX_BATCH })}
              </span>
            ) : null}
          </div>

          <TaskList tasks={arxivTasks} translate={t} />
        </TabsContent>

        <TabsContent value="upload" className="mt-4 space-y-4">
          <NoticeBanner
            tone="info"
            icon={<Info className="h-4 w-4" />}
            description={(
              <span>
              {t("batch.supports_zip_rar_tar_gz_and_tex_files_up_to_50_mb_each_and_files_total", { count: MAX_BATCH })}
              </span>
            )}
          />

          <motion.div
            className="cursor-pointer"
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault()
                fileInputRef.current?.click()
              }
            }}
            role="button"
            tabIndex={0}
            whileHover={{ scale: 1.005 }}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".zip,.rar,.tar,.tar.gz,.tgz,.tex"
              className="hidden"
              onChange={handleFileChange}
            />
            <UploadDropSurface
              isDragActive={isDragActive}
              heading={t("batch.click_to_choose_files_or_drag_them_here")}
              body={t("batch.zip_rar_tar_gz_tex_up_to", { count: MAX_BATCH })}
              icon={<Upload className="h-8 w-8 text-[color:var(--px-shell-accent)]" />}
            />
          </motion.div>

          <AnimatePresence>
            {queuedFiles.length > 0 ? (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-2"
              >
                <p className="text-sm font-medium text-[color:var(--px-shell-muted)]">
                  {t("batch.files_queued_for_upload", { selected: queuedFiles.length, total: MAX_BATCH })}
                </p>
                {queuedFiles.map((queuedFile) => (
                  <RecordRow
                    key={queuedFile.id}
                    className="py-2.5"
                    icon={<FileArchive className="h-4 w-4 shrink-0 text-[color:var(--px-shell-accent)]" />}
                    title={<span className="font-mono">{queuedFile.file.name}</span>}
                    meta={`${(queuedFile.file.size / 1024 / 1024).toFixed(1)} MB`}
                    action={(
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={(event) => {
                          event.stopPropagation()
                          removeFile(queuedFile.id)
                        }}
                        className="h-7 w-7 rounded-full text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-danger-soft)] hover:text-[color:var(--px-shell-danger)]"
                        aria-label={t("batch.remove_file")}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  />
                ))}
              </motion.div>
            ) : null}
          </AnimatePresence>

          <div className="flex items-center gap-2">
            {queuedFiles.length > 0 ? (
              <span className="text-sm text-[color:var(--px-shell-muted)]">
                {t("batch.selected_files", { selected: queuedFiles.length, total: MAX_BATCH })}
              </span>
            ) : null}
          </div>

          <TaskList tasks={uploadTasks} translate={t} />
        </TabsContent>
      </Tabs>
    </div>
  )
})
