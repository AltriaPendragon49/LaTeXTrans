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

const MAX_BATCH = 9
const VALID_EXTS = ['.zip', '.rar', '.tar', '.gz', '.tgz', '.tex']

// ─── Types ────────────────────────────────────────────────────────────────────

interface BatchTask {
    task_id: string
    label: string       // arxiv_id or filename
    status: string
    progress: number
    message: string
    warnings?: string | null  // Formatting auto-downgrade notices from backend
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

const statusLabel = (status: string, message?: string) => {
    const map: Record<string, string> = {
        queued: '排队中',
        processing: message?.includes('下载') ? '下载中' : '翻译中',
        completed: '已完成',
        completed_with_warnings: '完成（有警告）',
        failed: '失败',
        failed_compilation: '编译失败',
        pending: '等待中',
    }
    return map[status] ?? status
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

function TaskList({ tasks }: { tasks: BatchTask[] }) {
    const navigate = useNavigate()
    if (tasks.length === 0) return null
    return (
        <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">任务列表</p>
            {tasks.map(task => (
                <div
                    key={task.task_id}
                    className="rounded-lg border border-border bg-card p-3 space-y-2 shadow-sm"
                >
                    <div className="flex items-center gap-2">
                        {statusIcon(task.status)}
                        <span className="flex-1 font-mono text-sm text-foreground truncate">
                            {task.label}
                        </span>
                        <Badge variant="outline" className={cn('text-xs', statusBadgeClass(task.status))}>
                            {statusLabel(task.status, task.message)}
                        </Badge>
                        {(task.status === 'completed' || task.status === 'completed_with_warnings') && (
                            <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 gap-1 px-2 text-xs"
                                onClick={() => navigate(`/processing?taskId=${task.task_id}`)}
                            >
                                <ExternalLink className="h-3 w-3" />
                                查看
                            </Button>
                        )}
                    </div>

                    {(task.status === 'processing' || task.status === 'queued') && (
                        <div className="space-y-1">
                            <Progress
                                value={task.progress}
                                className={cn(
                                    "h-1.5",
                                    task.message?.includes("rate limited") && "animate-pulse [&>div]:bg-amber-500!"
                                )}
                            />
                            <p className={cn(
                                "text-xs",
                                task.message?.includes("rate limited")
                                    ? "text-amber-500 dark:text-amber-400 font-medium"
                                    : "text-muted-foreground"
                            )}>
                                {task.message}
                            </p>
                        </div>
                    )}

                    {(task.status === 'failed' || task.status === 'failed_compilation') && (
                        <p className="text-xs text-destructive">{task.message}</p>
                    )}

                    {/* Formatting warnings (e.g. auto-downgraded font size) */}
                    {task.warnings && (
                        <p className="text-xs text-amber-500 flex items-center gap-1 mt-1">
                            <AlertCircle className="h-3 w-3 shrink-0" />
                            {task.warnings}
                        </p>
                    )}
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
    }, [activeTab, isArxivSubmitting, isUploadSubmitting, parsedIds.length, queuedFiles.length])

    // Track task IDs for which persist_failed warning has already been shown
    const warnedPersistFailed = useRef<Set<string>>(new Set())

    // ── Poll helper
    const pollTask = useCallback(
        async (task_id: string, setter: React.Dispatch<React.SetStateAction<BatchTask[]>>) => {
            const INTERVAL = 3000
            const MAX = 200
            for (let i = 0; i < MAX; i++) {
                await new Promise(r => setTimeout(r, INTERVAL))
                try {
                    const s = await getTaskStatus(task_id)
                    // Detect persist_failed flag and show one-time warning toast
                    if (s.persist_failed && !warnedPersistFailed.current.has(task_id)) {
                        warnedPersistFailed.current.add(task_id)
                        toast.warning(
                            '由于后端服务器网络问题，未能存入数据库，请注意保存翻译结果！',
                            { duration: 8000 }
                        )
                    }
                    setter(prev =>
                        prev.map(t =>
                            t.task_id === task_id
                                ? { ...t, status: s.status, progress: s.progress, message: s.message, warnings: (s as any).warnings ?? t.warnings }
                                : t
                        )
                    )
                    if (['completed', 'completed_with_warnings', 'failed', 'failed_compilation'].includes(s.status))
                        break
                } catch {
                    // ignore transient
                }
            }
        },
        []
    )

    // ── arXiv submit
    const handleArxivSubmit = async () => {
        if (parsedIds.length === 0) { toast.error('请输入至少一个 arXiv ID'); return }
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
                progress: 0,
                message: '等待下载...',
            }))
            setArxivTasks(initial)
            setArxivText('')
            toast.success(`批量翻译已提交：${resp.queued_count} 个任务创建成功`)
            for (const t of initial) pollTask(t.task_id, setArxivTasks)
        } catch (err: unknown) {
            toast.error((err as any)?.response?.data?.detail ?? (err as Error)?.message ?? '提交失败')
        } finally {
            setIsArxivSubmitting(false)
        }
    }

    // ── File helpers
    const addFiles = (files: FileList | File[]) => {
        const arr = Array.from(files)
        const valid = arr.filter(f => {
            const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase()
            if (!VALID_EXTS.includes(ext)) { toast.error(`不支持的文件类型：${f.name}`); return false }
            if (f.size > 50 * 1024 * 1024) { toast.error(`文件超过 50MB：${f.name}`); return false }
            return true
        })
        setQueuedFiles(prev => {
            const combined = [...prev, ...valid.map(file => ({ file, id: uid() }))]
            if (combined.length > MAX_BATCH) {
                toast.warning(`最多 ${MAX_BATCH} 个文件，已截断`)
                return combined.slice(0, MAX_BATCH)
            }
            return combined
        })
    }

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault(); e.stopPropagation()
        setIsDragActive(e.type === 'dragenter' || e.type === 'dragover')
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault(); e.stopPropagation()
        setIsDragActive(false)
        if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
    }, [])

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) addFiles(e.target.files)
        e.target.value = ''
    }

    const removeFile = (id: string) => setQueuedFiles(prev => prev.filter(f => f.id !== id))

    // ── Upload submit: parallel upload → translate for each file
    // No intermediate "上传中" state — tasks appear in the list only
    // after upload + translation start succeed (with a real task_id).
    const handleUploadSubmit = async () => {
        if (queuedFiles.length === 0) { toast.error('请先添加文件'); return }
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
                    progress: 0,
                    message: '启动翻译…',
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
                const msg = (err as any)?.response?.data?.detail ?? (err as Error)?.message ?? '失败'
                // Show failed task so user knows which file had issues
                appendTask({
                    task_id: `failed-${qf.id}`,
                    label: qf.file.name,
                    status: 'failed',
                    progress: 0,
                    message: msg,
                })
            }
        }))

        setIsUploadSubmitting(false)
        toast.success('所有文件已提交翻译')
    }

    return (
        <div className="space-y-5">
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'arxiv' | 'upload')}>
                <TabsList className="w-full grid grid-cols-2">
                    <TabsTrigger value="arxiv" className="gap-1.5">
                        <Layers className="h-3.5 w-3.5" />
                        arXiv ID 批量
                    </TabsTrigger>
                    <TabsTrigger value="upload" className="gap-1.5">
                        <Upload className="h-3.5 w-3.5" />
                        文件批量上传
                    </TabsTrigger>
                </TabsList>

                {/* ── arXiv tab ── */}
                <TabsContent value="arxiv" className="mt-4 space-y-4">
                    {/* Hint */}
                    <div className="flex items-start gap-2 rounded-md border border-border bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                        <span>
                            每行输入一个 arXiv ID（如 <code className="font-mono text-foreground">2401.00001</code>），最多 {MAX_BATCH} 个。
                            支持完整 URL 或纯 ID 格式。
                        </span>
                    </div>

                    {/* Textarea */}
                    <div className="space-y-1.5">
                        <label htmlFor="batch-arxiv-input" className="text-sm font-medium text-foreground">
                            arXiv ID 列表
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
                                {parsedIds.length}/{MAX_BATCH} 个 ID
                            </Badge>
                        )}
                        {isOverLimit && (
                            <span className="flex items-center gap-1 text-xs text-destructive">
                                <AlertCircle className="h-3 w-3" />
                                超出限制，仅前 {MAX_BATCH} 个将被提交
                            </span>
                        )}
                    </div>

                    <TaskList tasks={arxivTasks} />
                </TabsContent>

                {/* ── Upload tab ── */}
                <TabsContent value="upload" className="mt-4 space-y-4">
                    {/* Hint */}
                    <div className="flex items-start gap-2 rounded-md border border-border bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                        <span>
                            支持 <code className="font-mono text-foreground">.zip .rar .tar.gz .tex</code> 格式，
                            单文件最大 50 MB，最多 {MAX_BATCH} 个文件。
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
                                    点击选择文件，或拖拽到此处
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    ZIP / RAR / TAR.GZ / TEX，最多 {MAX_BATCH} 个
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
                                    待上传文件（{queuedFiles.length}/{MAX_BATCH}）
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
                                            aria-label="移除文件"
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
                                已选 {queuedFiles.length}/{MAX_BATCH} 个文件
                            </span>
                        )}
                    </div>

                    <TaskList tasks={uploadTasks} />
                </TabsContent>
            </Tabs>
        </div>
    )
})
