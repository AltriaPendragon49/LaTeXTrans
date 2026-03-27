import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useStore } from '@/store/useStore'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Loader2, History, Clock, FileText, ArrowRight, LogIn, RefreshCw, ChevronDown, Settings2, Languages, Wrench, Sparkles, CheckCircle2, XCircle, Trash2, Download, Eye } from 'lucide-react'
import { toast } from 'sonner'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { deleteTask, deleteTasksBatch } from '@/lib/api'
import { API_BASE_URL } from '@/api-base'
import { useTranslation } from 'react-i18next'
import { getCompileStrategyLabel, getFormattingValueLabel, getTaskStatusLabel, getTranslationModeLabel } from '@/i18n/ui-text'
import { getAccessToken } from '@/lib/supabase'

interface TaskHistoryItem {
    task_id: string
    source_type: string
    arxiv_id?: string
    translation_mode: string
    status: string
    progress: number
    created_at: string
    completed_at?: string
    source_language: string
    target_language: string
    compile_strategy: string
    translation_model?: string
    generate_glossary: boolean
    use_author_api: boolean
    formatting?: Record<string, unknown> | null
}

interface HistoryResponse {
    tasks: TaskHistoryItem[]
    total: number
    page: number
    page_size: number
    has_more: boolean
}

const statusStyles: Record<string, string> = {
    pending: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
    processing: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    completed: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    completed_with_warnings: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    failed: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
    failed_compilation: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
    structure_invalid: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
}

const TERMINAL_FAIL_STATUSES = new Set(['failed', 'failed_compilation', 'structure_invalid'])

export default function HistoryPage() {
    const navigate = useNavigate()
    const { isAuthenticated, loading: authLoading, session } = useAuth()
    const { setTaskId, setArxivId } = useStore()
    const { t, i18n } = useTranslation()

    const [tasks, setTasks] = useState<TaskHistoryItem[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [total, setTotal] = useState(0)
    const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
    const [taskToDelete, setTaskToDelete] = useState<string | null>(null)

    const [selectionMode, setSelectionMode] = useState(false)
    const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())
    const retryTimeoutRef = useRef<number | null>(null)

    const HISTORY_RETRY_DELAY_MS = 1000
    const MAX_HISTORY_RETRIES = 2

    const clearScheduledRetry = useCallback(() => {
        if (retryTimeoutRef.current !== null) {
            window.clearTimeout(retryTimeoutRef.current)
            retryTimeoutRef.current = null
        }
    }, [])

    const toggleExpand = (taskId: string, e: React.MouseEvent) => {
        e.stopPropagation()
        setExpandedTasks(prev => {
            const newSet = new Set(prev)
            if (newSet.has(taskId)) {
                newSet.delete(taskId)
            } else {
                newSet.add(taskId)
            }
            return newSet
        })
    }

    const fetchHistory = useCallback(async (pageNum: number, append: boolean = false, attempt: number = 0) => {
        clearScheduledRetry()
        setLoading(true)
        if (attempt === 0) {
            setError(null)
        }

        try {
            const token = session?.access_token ?? await getAccessToken()
            if (!token) {
                if (attempt < MAX_HISTORY_RETRIES) {
                    retryTimeoutRef.current = window.setTimeout(() => {
                        void fetchHistory(pageNum, append, attempt + 1)
                    }, HISTORY_RETRY_DELAY_MS)
                    return
                }
                throw new Error(t('history.failed_to_load_history'))
            }

            const response = await fetch(
                `${API_BASE_URL}/api/history?page=${pageNum}&page_size=10`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                }
            )

            if (!response.ok) {
                if ((response.status >= 500 || response.status === 401) && attempt < MAX_HISTORY_RETRIES) {
                    retryTimeoutRef.current = window.setTimeout(() => {
                        void fetchHistory(pageNum, append, attempt + 1)
                    }, HISTORY_RETRY_DELAY_MS)
                    return
                }
                throw new Error(t('history.failed_to_load_history'))
            }

            const data: HistoryResponse = await response.json()

            if (append) {
                setTasks(prev => [...prev, ...data.tasks])
            } else {
                setTasks(data.tasks)
            }
            setHasMore(data.has_more)
            setTotal(data.total)
            setPage(pageNum)
        } catch (err) {
            if (attempt < MAX_HISTORY_RETRIES) {
                retryTimeoutRef.current = window.setTimeout(() => {
                    void fetchHistory(pageNum, append, attempt + 1)
                }, HISTORY_RETRY_DELAY_MS)
                return
            }
            setError(err instanceof Error ? err.message : t('history.failed_to_load_history'))
        } finally {
            if (retryTimeoutRef.current === null) {
                setLoading(false)
            }
        }
    }, [clearScheduledRetry, session?.access_token, t])

    const loadMore = () => {
        if (!loading && hasMore) {
            fetchHistory(page + 1, true)
        }
    }

    useEffect(() => {
        if (isAuthenticated) {
            fetchHistory(1)
        }
        return clearScheduledRetry
    }, [clearScheduledRetry, fetchHistory, isAuthenticated])

    const handleDeleteClick = (taskId: string, e: React.MouseEvent) => {
        e.stopPropagation()
        setTaskToDelete(taskId)
        setDeleteDialogOpen(true)
    }

    const confirmDelete = async () => {
        if (!taskToDelete) return

        const deletingId = taskToDelete
        setDeleteDialogOpen(false)
        setTaskToDelete(null)

        const toastId = toast.loading(t('history.deleting_task'))

        try {
            await deleteTask(deletingId)
            setTasks(prev => prev.filter(t => t.task_id !== deletingId))
            setTotal(prev => prev - 1)
            setSelectedTasks(prev => {
                const newSet = new Set(prev)
                newSet.delete(deletingId)
                return newSet
            })
            toast.success(t('history.task_deleted'), { id: toastId })
        } catch (error) {
            toast.error(t('history.delete_failed_please_try_again'), { id: toastId })
        }
    }

    const handleBatchDelete = async () => {
        if (selectedTasks.size === 0) return

        const deletingIds = Array.from(selectedTasks)
        const count = deletingIds.length

        setSelectedTasks(new Set())
        setSelectionMode(false)

        const toastId = toast.loading(t('history.deleting_tasks', { count }))

        try {
            const result = await deleteTasksBatch(deletingIds)
            const successCount = result.results.filter(r => r.success).length
            const successIds = new Set(
                result.results.filter(r => r.success).map(r => r.task_id)
            )

            if (successCount > 0) {
                setTasks(prev => prev.filter(t => !successIds.has(t.task_id)))
                setTotal(prev => prev - successCount)
            }

            if (successCount === count) {
                toast.success(t('history.successfully_deleted_tasks', { count: successCount }), { id: toastId })
            } else if (successCount > 0) {
                toast.warning(t('history.deleted_tasks_some_failed_please_try_again', { successCount, count }), { id: toastId })
            } else {
                toast.error(t('history.delete_failed_0_please_try_again', { count }), { id: toastId })
            }
        } catch (error) {
            toast.error(t('history.batch_delete_failed_please_try_again'), { id: toastId })
        }
    }

    const toggleSelection = (taskId: string) => {
        setSelectedTasks(prev => {
            const newSet = new Set(prev)
            if (newSet.has(taskId)) {
                newSet.delete(taskId)
            } else {
                newSet.add(taskId)
            }
            return newSet
        })
    }

    const selectAll = () => {
        if (selectedTasks.size === tasks.length) {
            setSelectedTasks(new Set())
        } else {
            setSelectedTasks(new Set(tasks.map(t => t.task_id)))
        }
    }

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        const locale = i18n.resolvedLanguage === 'zh' ? 'zh-CN' : i18n.resolvedLanguage
        return date.toLocaleString(locale, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    const handleTaskClick = (task: TaskHistoryItem) => {
        setTaskId(task.task_id)
        if (task.arxiv_id) {
            setArxivId(task.arxiv_id)
        }

        if (task.status === 'completed' || task.status === 'completed_with_warnings') {
            navigate('/preview')
        } else if (TERMINAL_FAIL_STATUSES.has(task.status)) {
            navigate(`/processing?taskId=${task.task_id}`)
        } else {
            navigate(`/processing?taskId=${task.task_id}`)
        }
    }

    if (authLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[40vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    if (!isAuthenticated) {
        return (
            <div className="space-y-6 animate-in fade-in duration-500 max-w-2xl mx-auto py-12">
                <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/10 shadow-sm p-10 text-center space-y-4">
                    <div className="mx-auto p-4 rounded-full bg-surface-container-low w-fit mb-6">
                        <LogIn className="h-8 w-8 text-tertiary" />
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-xl font-bold text-on-surface">{t('history.sign_in_to_view_translation_history')}</h2>
                        <p className="text-sm text-tertiary max-w-md mx-auto">
                            {t('history.sign_in_to_view_and_manage_all_translation_task_records')}
                        </p>
                    </div>
                    <Button onClick={() => navigate('/login')} className="mt-8 rounded-full px-8 py-2.5">
                        <LogIn className="mr-2 h-4 w-4" />
                        {t('common.go_to_sign_in')}
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <p className="text-sm font-bold text-tertiary">
                    {t('history.total_translation_tasks', { count: total })}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                    {selectionMode ? (
                        <>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={selectAll}
                                className="rounded-full shadow-sm"
                            >
                                {selectedTasks.size === tasks.length ? t('history.clear_selection') : t('history.select_all')}
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={handleBatchDelete}
                                disabled={selectedTasks.size === 0}
                                className="min-w-[90px] rounded-full shadow-sm"
                            >
                                <Trash2 className="h-4 w-4 mr-2" />
                                {t('history.delete_selected', { count: selectedTasks.size })}
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setSelectionMode(false)
                                    setSelectedTasks(new Set())
                                }}
                                className="rounded-full"
                            >
                                {t('common.actions.cancel')}
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectionMode(true)}
                                disabled={tasks.length === 0}
                                className="rounded-full shadow-sm"
                            >
                                {t('history.select')}
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchHistory(1)}
                                disabled={loading}
                                className="rounded-full shadow-sm"
                            >
                                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                                {t('history.refresh')}
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {error && (
                <Alert variant="destructive" className="rounded-xl">
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant/10 overflow-hidden shadow-sm">
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-4 bg-surface-container-low border-b border-outline-variant/10 text-[10px] font-bold uppercase tracking-widest text-tertiary">
                    <div className="col-span-1" />
                    <div className="col-span-4">Document</div>
                    <div className="col-span-3">Timestamp & Mode</div>
                    <div className="col-span-2">Status</div>
                    <div className="col-span-2 text-right">Actions</div>
                </div>

                <div className="divide-y divide-outline-variant/5">
                    {tasks.length === 0 && !loading ? (
                        <div className="text-center py-12 text-tertiary">
                            <FileText className="h-10 w-10 mx-auto mb-4 opacity-50 text-outline" />
                            <p className="text-sm font-medium">{t('history.no_translation_history_yet')}</p>
                        </div>
                    ) : (
                        tasks.map((task) => (
                            <Collapsible
                                key={task.task_id}
                                open={expandedTasks.has(task.task_id)}
                                onOpenChange={() => { }}
                                className="group hover:bg-surface-container-low/50 transition-colors"
                            >
                                <div className="p-4 sm:px-6 sm:py-5">
                                    <div className="flex flex-col md:grid md:grid-cols-12 gap-4 items-start md:items-center">
                                        <div className="md:col-span-1 pt-1 md:pt-0">
                                            {selectionMode ? (
                                                <Checkbox
                                                    checked={selectedTasks.has(task.task_id)}
                                                    onCheckedChange={() => toggleSelection(task.task_id)}
                                                    aria-label={t('history.select_task', { task: task.arxiv_id || task.task_id.slice(0, 8) })}
                                                />
                                            ) : (
                                                <FileText className="h-5 w-5 text-primary opacity-80" />
                                            )}
                                        </div>

                                        <div 
                                            className="md:col-span-4 self-stretch flex items-center cursor-pointer min-w-0" 
                                            onClick={() => !selectionMode && handleTaskClick(task)}
                                        >
                                            <div className="min-w-0">
                                                <div className="font-bold text-on-surface text-sm truncate">
                                                    {task.arxiv_id || task.task_id.slice(0, 8)}
                                                </div>
                                                <div className="text-[10px] text-tertiary truncate">
                                                    {task.source_type === 'upload' ? 'Local Project' : `ArXiv`}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="md:col-span-3 text-sm text-on-surface-variant flex flex-col md:block">
                                            <span className="md:block">{formatDate(task.created_at)}</span>
                                            <span className="text-[11px] text-tertiary md:mt-0.5">
                                                {getTranslationModeLabel(t, task.translation_mode)}
                                            </span>
                                        </div>

                                        <div className="md:col-span-2">
                                            <div className={`inline-flex px-2.5 py-1 rounded text-[10px] font-bold border ${statusStyles[task.status] || statusStyles.failed}`}>
                                                {getTaskStatusLabel(t, task.status)}
                                            </div>
                                        </div>

                                        <div className="md:col-span-2 flex items-center justify-end gap-1 w-full md:w-auto">
                                            {!selectionMode && (
                                                <>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-8 w-8 p-0 text-tertiary hover:bg-primary/10 hover:text-primary transition-all rounded-lg"
                                                        onClick={(e) => { e.stopPropagation(); handleTaskClick(task); }}
                                                        title="View"
                                                    >
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-8 w-8 p-0 text-tertiary hover:bg-error/10 hover:text-error transition-all rounded-lg"
                                                        onClick={(e) => handleDeleteClick(task.task_id, e)}
                                                        title={t('history.delete_task')}
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                    <CollapsibleTrigger asChild>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-8 w-8 p-0 text-tertiary hover:bg-surface-container-high transition-all rounded-lg"
                                                            onClick={(e) => toggleExpand(task.task_id, e)}
                                                            title={t('history.expand_configuration_details')}
                                                        >
                                                            <Settings2 className="h-4 w-4" />
                                                        </Button>
                                                    </CollapsibleTrigger>
                                                </>
                                            )}
                                        </div>
                                    </div>

                                    <CollapsibleContent className="animate-in slide-in-from-top-2 fade-in duration-200 mt-4 md:mt-2">
                                        <div className="pt-4 border-t border-outline-variant/10 md:ml-12 lg:ml-[11.1%] space-y-3">
                                            <div className="flex items-center gap-2 text-xs font-bold text-tertiary mb-3 uppercase tracking-widest">
                                                <Settings2 className="h-3 w-3" />
                                                {t('history.translation_configuration')}
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm pb-2">
                                                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-container-low border border-outline-variant/5">
                                                    <Languages className="h-4 w-4 text-primary" />
                                                    <span className="text-tertiary text-xs font-bold">{t('history.language')}</span>
                                                    <span className="font-medium text-on-surface-variant ml-auto">{task.source_language} → {task.target_language}</span>
                                                </div>

                                                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-container-low border border-outline-variant/5">
                                                    <Wrench className="h-4 w-4 text-primary" />
                                                    <span className="text-tertiary text-xs font-bold">{t('history.compile_strategy')}</span>
                                                    <span className="font-medium capitalize text-on-surface-variant ml-auto">{getCompileStrategyLabel(t, task.compile_strategy)}</span>
                                                </div>

                                                {task.translation_model && (
                                                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-container-low border border-outline-variant/5 md:col-span-2">
                                                        <Sparkles className="h-4 w-4 text-primary" />
                                                        <span className="text-tertiary text-xs font-bold">{t('history.translation_model')}</span>
                                                        <span className="font-mono text-xs text-on-surface-variant ml-auto">{task.translation_model}</span>
                                                    </div>
                                                )}

                                                <div className="md:col-span-2 flex flex-wrap gap-2 mt-1">
                                                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container border border-outline-variant/10">
                                                        {task.generate_glossary ? (
                                                            <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                                                        ) : (
                                                            <XCircle className="h-3.5 w-3.5 text-tertiary" />
                                                        )}
                                                        <span className="text-[11px] font-bold text-on-surface-variant">{t('common.generate_glossary')}</span>
                                                    </div>

                                                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container border border-outline-variant/10">
                                                        {task.use_author_api ? (
                                                            <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                                                        ) : (
                                                            <XCircle className="h-3.5 w-3.5 text-tertiary" />
                                                        )}
                                                        <span className="text-[11px] font-bold text-on-surface-variant">{t('history.use_author_api')}</span>
                                                    </div>
                                                </div>

                                                {task.formatting && Object.keys(task.formatting).length > 0 && (
                                                    <div className="md:col-span-2 mt-3 p-4 bg-surface-container-lowest border border-outline-variant/10 rounded-xl">
                                                        <div className="text-[10px] font-bold uppercase tracking-widest text-tertiary mb-3">
                                                            {t('history.formatting_settings')}
                                                        </div>
                                                        <div className="flex flex-wrap gap-2">
                                                            {task.formatting.line_spacing != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.line_spacing', { value: String(task.formatting.line_spacing) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.font_size != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.font_size_pt', { value: String(task.formatting.font_size) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.column_mode != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {getFormattingValueLabel(t, 'column_mode', String(task.formatting.column_mode))}
                                                                </span>
                                                            )}
                                                            {task.formatting.margin != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.margins', { value: getFormattingValueLabel(t, 'margin', String(task.formatting.margin)) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.cjk_font != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.font', { value: getFormattingValueLabel(t, 'cjk_font', String(task.formatting.cjk_font)) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.paragraph_indent === true && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('formatting.firstLineIndent')}
                                                                </span>
                                                            )}
                                                            {task.formatting.localize_captions === true && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.localize_figures_tables')}
                                                                </span>
                                                            )}
                                                            {task.formatting.bib_style != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.bibliography', { value: String(task.formatting.bib_style) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.cite_style != null && (
                                                                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-primary/10 text-primary border border-primary/20">
                                                                    {t('history.citation', { value: getFormattingValueLabel(t, 'cite_style', String(task.formatting.cite_style)) })}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </CollapsibleContent>
                                </div>
                            </Collapsible>
                        ))
                    )}
                </div>
            </div>

            {hasMore && (
                <div className="flex justify-center pt-2">
                    <Button
                        variant="outline"
                        onClick={loadMore}
                        disabled={loading}
                        className="rounded-full shadow-sm"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                {t('common.status.loading')}
                            </>
                        ) : (
                            t('common.actions.loadMore')
                        )}
                    </Button>
                </div>
            )}

            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent className="rounded-2xl">
                    <AlertDialogHeader>
                        <AlertDialogTitle>{t('history.dialog.confirmDeleteTitle')}</AlertDialogTitle>
                        <AlertDialogDescription className="text-sm">
                            {t('history.this_action_deletes_all_data_for_this_task_source_files_translated_results_glossary_and_cannot_be_undone_continue')}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter className="gap-2 sm:gap-0 mt-4">
                        <AlertDialogCancel className="rounded-full">{t('common.actions.cancel')}</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={confirmDelete}
                            className="bg-error text-on-error hover:bg-error/90 rounded-full"
                        >
                            {t('common.actions.confirmDelete')}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
