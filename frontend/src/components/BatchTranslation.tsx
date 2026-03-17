/**
 * BatchTranslation Component
 *
 * Two-mode batch panel for authenticated users:
 *   1. arXiv IDs  — paste multiple IDs (one per line, max 9)
 *   2. File Upload — drag-and-drop or click to select multiple archives
 *
 * Uses theme CSS variables so it works in both light and dark modes.
 */

import { useState, useCallback, useRef, useEffect, forwardRef, useImperativeHandle, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'
import {
    Layers,
    CheckCircle2,
    XCircle,
    Clock,
    Loader2,
    ExternalLink,
    AlertCircle,
    Upload,
    FileArchive,
    X,
    Info,
} from 'lucide-react'
import { startBatchTranslation, getTaskStatus, uploadFile, startTranslation } from '@/lib/api'
import type { AdvancedConfig } from '@/types/config'
import { DEFAULT_CONFIG } from '@/types/config'
import { cn } from '@/lib/utils'
import { getTaskCopy } from '@/i18n/task-copy'

const MAX_BATCH = 9
const VALID_EXTS = ['.zip', '.rar', '.tar', '.gz', '.tgz', '.tex']
const BATCH_POLL_INTERVAL_MS = 3000
const TERMINAL_BATCH_STATUSES = new Set([
    'completed',
    'completed_with_warnings',
    'failed',
    'failed_compilation',
    'structure_invalid',
])
type Translate = (key: string, options?: Record<string, unknown>) => string

// ─── Types ────────────────────────────────────────────────────────────────────

interface BatchTask {
    task_id: string
    label: string       // arxiv_id or filename
    status: string
    progress: number
    stage?: string | null
    message: string
    detail_code?: string | null
    detail_params?: Record<string, string | number | boolean | null> | null
    warnings?: string | null  // Formatting auto-downgrade notices from backend
    failure_reason_code?: string | null
}

interface QueuedFile {
    file: File
    id: string          // local uuid for list key
}

interface BatchTranslationProps {
    advancedConfig?: AdvancedConfig
    targetLanguage?: string
    sourceLanguage?: string
}

export interface BatchTranslationHandle {
    /** 触发当前激活内部 Tab 的提交 */
    submitCurrent: () => void
}

export interface BatchTranslationState {
    isSubmitting: boolean
    activeTab: 'arxiv' | 'upload'
    canSubmit: boolean
}

interface BatchTranslationProps {
    advancedConfig?: AdvancedConfig
    targetLanguage?: string
    sourceLanguage?: string
    /** 状态变化时通知父组件，解决 ref.current 不触发重渲染的问题 */
    onStateChange?: (state: BatchTranslationState) => void
}

const uid = () => Math.random().toString(36).slice(2, 9)

const statusIcon = (status: string) => {
    switch (status) {
        case 'completed':
        case 'completed_with_warnings':
            return <CheckCircle2 className="h-4 w-4 text-green-500" />
        case 'failed':
        case 'failed_compilation':
            return <XCircle className="h-4 w-4 text-destructive" />
        case 'processing':
            return <Loader2 className="h-4 w-4 animate-spin text-primary" />
        case 'queued':
            return <Clock className="h-4 w-4 text-yellow-500" />
        default:
            return <Clock className="h-4 w-4 text-muted-foreground" />
    }
}

const statusBadgeClass = (status: string) => {
    if (status === 'completed' || status === 'completed_with_warnings')
        return 'border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400'
    if (status === 'failed' || status === 'failed_compilation')
        return 'border-destructive/30 bg-destructive/10 text-destructive'
    if (status === 'processing')
        return 'border-primary/30 bg-primary/10 text-primary'
    if (status === 'queued')
        return 'border-yellow-500/30 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
    return 'border-border bg-muted text-muted-foreground'
}

// ─── Task list panel (shared) ─────────────────────────────────────────────────

function TaskList({ tasks, translate }: { tasks: BatchTask[]; translate: Translate }) {
    const navigate = useNavigate()
    if (tasks.length === 0) return null
    return (
        <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{translate('batch.taskList')}</p>
            {tasks.map(task => (
                <div
                    key={task.task_id}
                    className="rounded-lg border border-border bg-card p-3 space-y-2 shadow-sm"
                >
                    {(() => {
                        const copy = getTaskCopy(translate, {
                            status: task.status,
                            stage: task.stage,
                            detailCode: task.detail_code,
                            detailParams: task.detail_params,
                            failureReasonCode: task.failure_reason_code,
                            warnings: task.warnings,
                        })

                        return (
                            <>
                    <div className="flex items-center gap-2">
                        {statusIcon(task.status)}
                        <span className="flex-1 font-mono text-sm text-foreground truncate">
                            {task.label}
                        </span>
                        <Badge variant="outline" className={cn('text-xs', statusBadgeClass(task.status))}>
                            {copy.statusLabel}
                        </Badge>
                        {(task.status === 'completed' || task.status === 'completed_with_warnings') && (
                            <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 gap-1 px-2 text-xs"
                                onClick={() => navigate(`/processing?taskId=${task.task_id}`)}
                            >
                                <ExternalLink className="h-3 w-3" />
                                {translate('common.actions.view')}
                            </Button>
                        )}
                    </div>

                    {(task.status === 'processing' || task.status === 'queued') && (
                        <div className="space-y-1">
                            <Progress
                                value={task.progress}
                                className={cn(
                                    "h-1.5",
                                    copy.isRateLimited && "animate-pulse [&>div]:bg-amber-500!"
                                )}
                            />
                            <p className={cn(
                                "text-xs",
                                copy.isRateLimited
                                    ? "text-amber-500 dark:text-amber-400 font-medium"
                                    : "text-muted-foreground"
                            )}>
                                {copy.detailLabel || copy.stageLabel || copy.statusLabel}
                            </p>
                        </div>
                    )}

                    {(task.status === 'failed' || task.status === 'failed_compilation') && (
                        <p className="text-xs text-destructive">{copy.failureLabel || copy.statusLabel}</p>
                    )}

                    {/* Formatting warnings (e.g. auto-downgraded font size) */}
                    {task.warnings && (
                        <p className="text-xs text-amber-500 flex items-center gap-1 mt-1">
                            <AlertCircle className="h-3 w-3 shrink-0" />
                            {translate('task.detail.formattingWarning', { warningText: task.warnings })}
                        </p>
                    )}
                            </>
                        )
                    })()}
                </div>
            ))}
        </div>
    )
}

// ─── Main component ───────────────────────────────────────────────────────────

export const BatchTranslation = forwardRef<BatchTranslationHandle, BatchTranslationProps>(function BatchTranslation({
    advancedConfig = DEFAULT_CONFIG.advanced_config,
    targetLanguage = 'ch',
    sourceLanguage = 'en',
    onStateChange,
}, ref) {
    const { t } = useTranslation()
    // ── 内部 Tab 状态
    const [activeTab, setActiveTab] = useState<'arxiv' | 'upload'>('arxiv')

    // ── arXiv tab state
    const [arxivText, setArxivText] = useState('')
    const [isArxivSubmitting, setIsArxivSubmitting] = useState(false)
    const [arxivTasks, setArxivTasks] = useState<BatchTask[]>([])

    // ── Upload tab state
    const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([])
    const [isDragActive, setIsDragActive] = useState(false)
    const [isUploadSubmitting, setIsUploadSubmitting] = useState(false)
    const [uploadTasks, setUploadTasks] = useState<BatchTask[]>([])
    const fileInputRef = useRef<HTMLInputElement>(null)

    // ── Parsed IDs
    const parsedIds = arxivText
        .split('\n')
        .map(l => l.trim())
        .filter(Boolean)
        .slice(0, MAX_BATCH)
    const isOverLimit = arxivText.split('\n').map(l => l.trim()).filter(Boolean).length > MAX_BATCH

    // ── 用 ref 持有最新的 submit 函数，避免 useImperativeHandle 闭包陈旧问题
    const submitRef = useRef<() => void>(() => { })
    submitRef.current = () => {
        if (activeTab === 'arxiv') handleArxivSubmit()
        else handleUploadSubmit()
    }

    // ── 暴露给父组件的接口
    useImperativeHandle(ref, () => ({
        submitCurrent: () => submitRef.current(),
    }), [])

    // 状态变化时通知父组件（解决 ref.current 不触发重渲染的问题）
    useEffect(() => {
        onStateChange?.({
            isSubmitting: activeTab === 'arxiv' ? isArxivSubmitting : isUploadSubmitting,
            activeTab,
            canSubmit: activeTab === 'arxiv'
                ? parsedIds.length > 0 && !isArxivSubmitting
                : queuedFiles.length > 0 && !isUploadSubmitting,
        })
    }, [activeTab, isArxivSubmitting, isUploadSubmitting, onStateChange, parsedIds.length, queuedFiles.length])

    // Track task IDs for which persist_failed warning has already been shown
    const warnedPersistFailed = useRef<Set<string>>(new Set())
    const activePollsRef = useRef<Set<string>>(new Set())
    const isMountedRef = useRef(true)

    useEffect(() => {
        isMountedRef.current = true

        return () => {
            isMountedRef.current = false
            activePollsRef.current.clear()
        }
    }, [])

    // ── Poll helper
    const pollTask = useCallback(
        async (task_id: string, setter: React.Dispatch<React.SetStateAction<BatchTask[]>>) => {
            if (activePollsRef.current.has(task_id)) {
                return
            }

            activePollsRef.current.add(task_id)

            try {
                while (isMountedRef.current) {
                    await new Promise(r => setTimeout(r, BATCH_POLL_INTERVAL_MS))
                    if (!isMountedRef.current) {
                        break
                    }

                    let s
                    try {
                        s = await getTaskStatus(task_id)
                    } catch {
                        continue
                    }

                    if (!isMountedRef.current) {
                        break
                    }

                    if (s.persist_failed && !warnedPersistFailed.current.has(task_id)) {
                        warnedPersistFailed.current.add(task_id)
                        toast.warning(
                            t('batch.due_to_a_backend_network_issue_the_result_could_not_be_saved_to_the_database_please_make_sure_to_save_your_translation_results'),
                            { duration: 8000 }
                        )
                    }

                    setter(prev =>
                        prev.map(t =>
                            t.task_id === task_id
                                ? {
                                    ...t,
                                    status: s.status,
                                    progress: s.progress,
                                    stage: s.stage ?? t.stage,
                                    message: s.message,
                                    detail_code: s.detail_code ?? t.detail_code,
                                    detail_params: s.detail_params ?? t.detail_params,
                                    warnings: s.warnings ?? t.warnings,
                                    failure_reason_code: s.failure_reason_code ?? t.failure_reason_code,
                                }
                                : t
                        )
                    )

                    if (TERMINAL_BATCH_STATUSES.has(String(s.status || '').toLowerCase())) {
                        break
                    }
                }
            } finally {
                activePollsRef.current.delete(task_id)
            }
        },
        [t]
    )

    // ── arXiv submit
    const handleArxivSubmit = async () => {
        if (parsedIds.length === 0) { toast.error(t('batch.enter_at_least_one_arxiv_id')); return }
        setIsArxivSubmitting(true)
        try {
            const resp = await startBatchTranslation({
                arxiv_ids: parsedIds,
                target_language: targetLanguage,
                source_language: sourceLanguage,
                advanced_config: advancedConfig,
            })
            const initial: BatchTask[] = resp.task_ids.map((tid, i) => ({
                task_id: tid,
                label: parsedIds[i] ?? tid,
                status: 'processing',
                stage: 'downloading',
                progress: 0,
                message: t('task.detail.taskWaiting'),
                detail_code: 'task_waiting',
                detail_params: null,
            }))
            setArxivTasks(initial)
            setArxivText('')
            toast.success(t('batch.batch_translation_submitted_tasks_created_successfully', { count: resp.queued_count }))
            for (const t of initial) pollTask(t.task_id, setArxivTasks)
        } catch (err: unknown) {
            console.error('[BatchTranslation] Failed to submit arXiv batch', err)
            toast.error(t('batch.submission_failed'))
        } finally {
            setIsArxivSubmitting(false)
        }
    }

    // ── File helpers
    const addFiles = useCallback((files: FileList | File[]) => {
        const arr = Array.from(files)
        const valid = arr.filter(f => {
            const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase()
            if (!VALID_EXTS.includes(ext)) { toast.error(t('batch.unsupported_file_type', { name: f.name })); return false }
            if (f.size > 50 * 1024 * 1024) { toast.error(t('batch.file_exceeds_50_mb', { name: f.name })); return false }
            return true
        })
        setQueuedFiles(prev => {
            const combined = [...prev, ...valid.map(file => ({ file, id: uid() }))]
            if (combined.length > MAX_BATCH) {
                toast.warning(t('batch.maximum_files_extra_files_were_removed', { count: MAX_BATCH }))
                return combined.slice(0, MAX_BATCH)
            }
            return combined
        })
    }, [t])

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault(); e.stopPropagation()
        setIsDragActive(e.type === 'dragenter' || e.type === 'dragover')
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault(); e.stopPropagation()
        setIsDragActive(false)
        if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
    }, [addFiles])

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) addFiles(e.target.files)
        e.target.value = ''
    }

    const removeFile = (id: string) => setQueuedFiles(prev => prev.filter(f => f.id !== id))

    // ── Upload submit: parallel upload → translate for each file
    // No intermediate "上传中" state — tasks appear in the list only
    // after upload + translation start succeed (with a real task_id).
    const handleUploadSubmit = async () => {
        if (queuedFiles.length === 0) { toast.error(t('batch.add_files_first')); return }
        setIsUploadSubmitting(true)

        const snapshot = [...queuedFiles]
        setQueuedFiles([])

        // Helper: append a single task to the list (called after upload succeeds)
        const appendTask = (task: BatchTask) =>
            setUploadTasks(prev => [...prev, task])

        // Process all files in parallel
        await Promise.all(snapshot.map(async (qf) => {
            try {
                // 1. Upload file (no UI entry yet)
                const uploadResp = await uploadFile(qf.file)
                const task_id = uploadResp.task_id

                // 2. Add task to list with real task_id immediately
                const newTask: BatchTask = {
                    task_id,
                    label: qf.file.name,
                    status: 'processing',
                    stage: 'parsing',
                    progress: 0,
                    message: t('task.detail.translationStarting'),
                    detail_code: 'translation_starting',
                    detail_params: null,
                }
                appendTask(newTask)

                // 3. Start polling to track translation progress
                pollTask(task_id, setUploadTasks)

                // 4. Kick off actual translation
                await startTranslation(task_id, {
                    target_language: targetLanguage,
                    source_language: sourceLanguage,
                    advanced_config: advancedConfig,
                })
            } catch (err: unknown) {
                console.error('[BatchTranslation] Failed to process uploaded file', err)
                // Show failed task so user knows which file had issues
                appendTask({
                    task_id: `failed-${qf.id}`,
                    label: qf.file.name,
                    status: 'failed',
                    progress: 0,
                    message: t('batch.submission_failed'),
                    failure_reason_code: null,
                })
            }
        }))

        setIsUploadSubmitting(false)
        toast.success(t('batch.all_files_have_been_submitted_for_translation'))
    }

    return (
        <div className="space-y-5">
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'arxiv' | 'upload')}>
                <TabsList className="w-full grid grid-cols-2">
                    <TabsTrigger value="arxiv" className="gap-1.5">
                        <Layers className="h-3.5 w-3.5" />
                        {t('batch.batch_arxiv_ids')}
                    </TabsTrigger>
                    <TabsTrigger value="upload" className="gap-1.5">
                        <Upload className="h-3.5 w-3.5" />
                        {t('batch.batch_file_upload')}
                    </TabsTrigger>
                </TabsList>

                {/* ── arXiv tab ── */}
                <TabsContent value="arxiv" className="mt-4 space-y-4">
                    {/* Hint */}
                    <div className="flex items-start gap-2 rounded-md border border-border bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                        <span>
                            {t('batch.enter_one_arxiv_id_per_line_for_example_up_to_total', { example: '2401.00001', count: MAX_BATCH })}{' '}
                            {t('batch.full_urls_or_plain_ids_are_supported')}
                        </span>
                    </div>

                    {/* Textarea */}
                    <div className="space-y-1.5">
                        <label htmlFor="batch-arxiv-input" className="text-sm font-medium text-foreground">
                            {t('batch.arxiv_id_list')}
                        </label>
                        <textarea
                            id="batch-arxiv-input"
                            value={arxivText}
                            onChange={e => setArxivText(e.target.value)}
                            placeholder={'2401.00001\n2401.00002\n2401.00003'}
                            rows={7}
                            spellCheck={false}
                            className={cn(
                                'w-full resize-none rounded-md border border-input bg-background',
                                'px-3 py-2 font-mono text-sm text-foreground',
                                'placeholder:text-muted-foreground',
                                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                                'transition-colors'
                            )}
                        />
                    </div>

                    {/* Footer row - 仅显示 ID 计数和超限警告，提交按鈕已移至 Dashboard 底部 */}
                    <div className="flex items-center gap-2">
                        {parsedIds.length > 0 && (
                            <Badge variant="secondary">
                                {t('batch.ids', { current: parsedIds.length, total: MAX_BATCH })}
                            </Badge>
                        )}
                        {isOverLimit && (
                            <span className="flex items-center gap-1 text-xs text-destructive">
                                <AlertCircle className="h-3 w-3" />
                                {t('batch.limit_exceeded_only_the_first_will_be_submitted', { count: MAX_BATCH })}
                            </span>
                        )}
                    </div>

                    <TaskList tasks={arxivTasks} translate={t} />
                </TabsContent>

                {/* ── Upload tab ── */}
                <TabsContent value="upload" className="mt-4 space-y-4">
                    {/* Hint */}
                    <div className="flex items-start gap-2 rounded-md border border-border bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                        <span>
                            {t('batch.supports_zip_rar_tar_gz_and_tex_files_up_to_50_mb_each_and_files_total', { count: MAX_BATCH })}
                        </span>
                    </div>

                    {/* Drop zone */}
                    <motion.div
                        className={cn(
                            'relative cursor-pointer rounded-xl border-2 border-dashed transition-colors duration-200',
                            isDragActive
                                ? 'border-primary bg-primary/5'
                                : 'border-border hover:border-primary/50 hover:bg-muted/40'
                        )}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
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
                        <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
                            <div className="rounded-full border bg-background p-4 shadow-sm">
                                <Upload className="h-7 w-7 text-primary/80" />
                            </div>
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-foreground">
                                    {t('batch.click_to_choose_files_or_drag_them_here')}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    {t('batch.zip_rar_tar_gz_tex_up_to', { count: MAX_BATCH })}
                                </p>
                            </div>
                        </div>
                    </motion.div>

                    {/* File queue */}
                    <AnimatePresence>
                        {queuedFiles.length > 0 && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="space-y-2"
                            >
                                <p className="text-sm font-medium text-muted-foreground">
                                    {t('batch.files_queued_for_upload', { selected: queuedFiles.length, total: MAX_BATCH })}
                                </p>
                                {queuedFiles.map(qf => (
                                    <div
                                        key={qf.id}
                                        className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2"
                                    >
                                        <FileArchive className="h-4 w-4 shrink-0 text-primary" />
                                        <span className="flex-1 truncate font-mono text-sm text-foreground">
                                            {qf.file.name}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            {(qf.file.size / 1024 / 1024).toFixed(1)} MB
                                        </span>
                                        <button
                                            onClick={e => { e.stopPropagation(); removeFile(qf.id) }}
                                            className="rounded p-0.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                                            aria-label={t('batch.remove_file')}
                                        >
                                            <X className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Submit row - 提交按鈕已移至 Dashboard 底部 */}
                    <div className="flex items-center gap-2">
                        {queuedFiles.length > 0 && (
                            <span className="text-sm text-muted-foreground">
                                {t('batch.selected_files', { selected: queuedFiles.length, total: MAX_BATCH })}
                            </span>
                        )}
                    </div>

                    <TaskList tasks={uploadTasks} translate={t} />
                </TabsContent>
            </Tabs>
        </div>
    )
})
