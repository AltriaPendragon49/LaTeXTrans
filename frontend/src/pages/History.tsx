/**
 * History Page
 * 
 * Displays user's translation history with pagination.
 * Requires authentication - shows prompt for guests.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useStore } from '@/store/useStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Loader2, History, Clock, FileText, ArrowRight, LogIn, RefreshCw, ChevronDown, Settings2, Languages, Wrench, Sparkles, CheckCircle2, XCircle, Trash2 } from 'lucide-react'
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
    // Config snapshot
    source_language: string
    target_language: string
    compile_strategy: string
    translation_model?: string
    generate_glossary: boolean
    use_author_api: boolean
    // Typography formatting snapshot
    formatting?: Record<string, unknown> | null
}

interface HistoryResponse {
    tasks: TaskHistoryItem[]
    total: number
    page: number
    page_size: number
    has_more: boolean
}

// Status badge styling
// fix-task-status-sync Task 3: Map all terminal failure states to the red "Failed" badge.
// structure_invalid and failed_compilation must NOT fall through to the yellow "pending" default.
const statusStyles: Record<string, string> = {
    pending: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
    processing: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    completed: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
    completed_with_warnings: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
    failed: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
    failed_compilation: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
    structure_invalid: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
}

// Terminal failure statuses — clicking these should navigate to preview/details, not processing.
const TERMINAL_FAIL_STATUSES = new Set(['failed', 'failed_compilation', 'structure_invalid'])

export default function HistoryPage() {
    const navigate = useNavigate()
    const { isAuthenticated, loading: authLoading } = useAuth()
    const { setTaskId, setArxivId } = useStore()
    const { t, i18n } = useTranslation()

    const [tasks, setTasks] = useState<TaskHistoryItem[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [total, setTotal] = useState(0)
    const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

    // Delete states
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
    const [taskToDelete, setTaskToDelete] = useState<string | null>(null)

    // Batch selection state
    const [selectionMode, setSelectionMode] = useState(false)
    const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())

    const toggleExpand = (taskId: string, e: React.MouseEvent) => {
        e.stopPropagation() // 防止触发卡片点击
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

    // Fetch history
    const fetchHistory = useCallback(async (pageNum: number, append: boolean = false) => {
        setLoading(true)
        setError(null)

        try {
            const token = await getAccessToken()

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
            setError(err instanceof Error ? err.message : t('history.failed_to_load_history'))
        } finally {
            setLoading(false)
        }
    }, [t])

    // Load more handler
    const loadMore = () => {
        if (!loading && hasMore) {
            fetchHistory(page + 1, true)
        }
    }

    // Initial load when authenticated
    useEffect(() => {
        if (isAuthenticated) {
            fetchHistory(1)
        }
    }, [fetchHistory, isAuthenticated])

    // Delete handlers
    const handleDeleteClick = (taskId: string, e: React.MouseEvent) => {
        e.stopPropagation()
        setTaskToDelete(taskId)
        setDeleteDialogOpen(true)
    }

    const confirmDelete = async () => {
        if (!taskToDelete) return

        const deletingId = taskToDelete

        // Close dialog immediately, show loading toast
        setDeleteDialogOpen(false)
        setTaskToDelete(null)

        const toastId = toast.loading(t('history.deleting_task'))

        try {
            await deleteTask(deletingId)

            // Only remove from list after API success
            setTasks(prev => prev.filter(t => t.task_id !== deletingId))
            setTotal(prev => prev - 1)
            setSelectedTasks(prev => {
                const newSet = new Set(prev)
                newSet.delete(deletingId)
                return newSet
            })

            toast.success(t('history.task_deleted'), { id: toastId })
        } catch (error) {
            console.error('[History] Failed to delete task', error)
            toast.error(t('history.delete_failed_please_try_again'), { id: toastId })
        }
    }

    // Batch delete handler
    const handleBatchDelete = async () => {
        if (selectedTasks.size === 0) return

        const deletingIds = Array.from(selectedTasks)
        const count = deletingIds.length

        // Exit selection mode, show loading toast
        setSelectedTasks(new Set())
        setSelectionMode(false)

        const toastId = toast.loading(t('history.deleting_tasks', { count }))

        try {
            const result = await deleteTasksBatch(deletingIds)
            const successCount = result.results.filter(r => r.success).length
            const successIds = new Set(
                result.results.filter(r => r.success).map(r => r.task_id)
            )

            // Only remove successfully deleted tasks
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
            console.error('[History] Failed to delete tasks', error)
            toast.error(t('history.batch_delete_failed_please_try_again'), { id: toastId })
        }
    }

    // Selection handlers
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

    // Loading state
    if (authLoading) {
        return (
            <div className="container mx-auto max-w-4xl p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    // Not authenticated
    if (!isAuthenticated) {
        return (
            <div className="container mx-auto max-w-4xl p-6 space-y-6 animate-in fade-in duration-500">
                <div className="space-y-2">
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <History className="h-8 w-8" />
                        {t('history.history')}
                    </h1>
                </div>

                <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="pt-6 space-y-4">
                        <div className="text-center py-8 space-y-4">
                            <div className="mx-auto p-4 rounded-full bg-muted/50 w-fit">
                                <LogIn className="h-8 w-8 text-muted-foreground" />
                            </div>
                            <div className="space-y-2">
                                <p className="text-lg font-medium">{t('history.sign_in_to_view_translation_history')}</p>
                                <p className="text-muted-foreground">
                                    {t('history.sign_in_to_view_and_manage_all_translation_task_records')}
                                </p>
                            </div>
                            <Button onClick={() => navigate('/login')} className="mt-4">
                                <LogIn className="mr-2 h-4 w-4" />
                                {t('common.go_to_sign_in')}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )
    }

    // Format date
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        const locale = i18n.resolvedLanguage === 'zh' ? 'zh-CN' : i18n.resolvedLanguage
        return date.toLocaleString(locale, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    // Handle task click - navigate based on status
    const handleTaskClick = (task: TaskHistoryItem) => {
        // Set taskId in store so preview/processing pages can access it
        setTaskId(task.task_id)
        if (task.arxiv_id) {
            setArxivId(task.arxiv_id)
        }

        // Navigate based on task status
        if (task.status === 'completed' || task.status === 'completed_with_warnings') {
            navigate('/preview')
        } else if (TERMINAL_FAIL_STATUSES.has(task.status)) {
            // fix-task-status-sync Task 3: Terminal failures stay in history; navigate to
            // processing page so user can see the failure details/reason.
            navigate(`/processing?taskId=${task.task_id}`)
        } else {
            // 直接将 taskId 放入 URL 参数，避免依赖 store 异步更新
            navigate(`/processing?taskId=${task.task_id}`)
        }
    }

    return (
        <div className="container mx-auto max-w-4xl p-6 space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div className="space-y-2">
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <History className="h-8 w-8" />
                        {t('history.history')}
                    </h1>
                    <p className="text-muted-foreground">
                        {t('history.total_translation_tasks', { count: total })}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {selectionMode ? (
                        <>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={selectAll}
                            >
                                {selectedTasks.size === tasks.length ? t('history.clear_selection') : t('history.select_all')}
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={handleBatchDelete}
                                disabled={selectedTasks.size === 0}
                                className="min-w-[90px]"
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
                            >
                                {t('history.select')}
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchHistory(1)}
                                disabled={loading}
                            >
                                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                                {t('history.refresh')}
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Task list */}
            <div className="space-y-3">
                {tasks.length === 0 && !loading ? (
                    <Card className="border-border/50 bg-card/80">
                        <CardContent className="pt-6">
                            <div className="text-center py-8 text-muted-foreground">
                                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                <p>{t('history.no_translation_history_yet')}</p>
                            </div>
                        </CardContent>
                    </Card>
                ) : (
                    tasks.map((task) => (
                        <Collapsible
                            key={task.task_id}
                            open={expandedTasks.has(task.task_id)}
                            onOpenChange={() => { }}
                        >
                            <Card className="border-border/50 bg-card/80 hover:bg-card/90 transition-colors group">
                                <CardContent className="p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div
                                            className="flex items-center gap-4 flex-1 cursor-pointer"
                                            onClick={() => !selectionMode && handleTaskClick(task)}
                                        >
                                            {selectionMode ? (
                                                <Checkbox
                                                    checked={selectedTasks.has(task.task_id)}
                                                    onCheckedChange={() => toggleSelection(task.task_id)}
                                                    className="ml-2"
                                                    aria-label={t('history.select_task', { task: task.arxiv_id || task.task_id.slice(0, 8) })}
                                                />
                                            ) : (
                                                <div className="p-2 rounded-lg bg-muted">
                                                    <FileText className="h-5 w-5 text-muted-foreground" />
                                                </div>
                                            )}
                                            <div className="space-y-1">
                                                <p className="font-medium font-mono">
                                                    {task.arxiv_id || task.task_id.slice(0, 8)}
                                                </p>
                                                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                                    <span className="flex items-center gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {formatDate(task.created_at)}
                                                    </span>
                                                    <span className="capitalize">
                                                        {getTranslationModeLabel(t, task.translation_mode)}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${statusStyles[task.status] || statusStyles.failed}`}>
                                                {getTaskStatusLabel(t, task.status)}
                                            </span>

                                            {!selectionMode && (
                                                <>
                                                    {/* Delete button */}
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-11 w-11 p-0 hover:bg-destructive/10 hover:text-destructive transition-colors"
                                                        onClick={(e) => handleDeleteClick(task.task_id, e)}
                                                        aria-label={t('history.delete_task')}
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>

                                                    {/* 展开配置详情按钮 */}
                                                    <CollapsibleTrigger asChild>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-11 w-11 p-0 hover:bg-muted"
                                                            onClick={(e) => toggleExpand(task.task_id, e)}
                                                            aria-label={t('history.expand_configuration_details')}
                                                        >
                                                            <Settings2 className="h-4 w-4" />
                                                            <ChevronDown
                                                                className={`h-4 w-4 ml-0.5 transition-transform duration-200 ${expandedTasks.has(task.task_id) ? 'rotate-180' : ''
                                                                    }`}
                                                            />
                                                        </Button>
                                                    </CollapsibleTrigger>

                                                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                                </>
                                            )}
                                        </div>
                                    </div>

                                    {/* 可折叠的配置详情区域 */}
                                    <CollapsibleContent className="animate-in slide-in-from-top-2 fade-in duration-200">
                                            <div className="pt-3 border-t border-border/50 space-y-3">
                                                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                                    <Settings2 className="h-4 w-4" />
                                                    <span className="font-medium">{t('history.translation_configuration')}</span>
                                                </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                                {/* 语言设置 */}
                                                <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
                                                    <Languages className="h-4 w-4 text-blue-500" />
                                                    <span className="text-muted-foreground">{t('history.language')}</span>
                                                    <span className="font-medium">{task.source_language} → {task.target_language}</span>
                                                </div>

                                                {/* 编译策略 */}
                                                <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
                                                    <Wrench className="h-4 w-4 text-orange-500" />
                                                    <span className="text-muted-foreground">{t('history.compile_strategy')}</span>
                                                    <span className="font-medium capitalize">{getCompileStrategyLabel(t, task.compile_strategy)}</span>
                                                </div>

                                                {/* 翻译模型 */}
                                                {task.translation_model && (
                                                    <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30 md:col-span-2">
                                                        <Sparkles className="h-4 w-4 text-purple-500" />
                                                        <span className="text-muted-foreground">{t('history.translation_model')}</span>
                                                        <span className="font-mono text-xs">{task.translation_model}</span>
                                                    </div>
                                                )}

                                                {/* 高级选项 */}
                                                <div className="md:col-span-2 flex flex-wrap gap-2">
                                                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/30">
                                                        {task.generate_glossary ? (
                                                            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                                                        ) : (
                                                            <XCircle className="h-3.5 w-3.5 text-gray-400" />
                                                        )}
                                                        <span className="text-xs">{t('common.generate_glossary')}</span>
                                                    </div>

                                                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/30">
                                                        {task.use_author_api ? (
                                                            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                                                        ) : (
                                                            <XCircle className="h-3.5 w-3.5 text-gray-400" />
                                                        )}
                                                        <span className="text-xs">{t('history.use_author_api')}</span>
                                                    </div>
                                                </div>

                                                {/* 排版配置快照 */}
                                                {task.formatting && Object.keys(task.formatting).length > 0 && (
                                                    <div className="md:col-span-2 space-y-2">
                                                        <div className="text-xs text-muted-foreground font-medium">{t('history.formatting_settings')}</div>
                                                        <div className="flex flex-wrap gap-1.5">
                                                            {task.formatting.line_spacing != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.line_spacing', { value: String(task.formatting.line_spacing) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.font_size != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.font_size_pt', { value: String(task.formatting.font_size) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.column_mode != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {getFormattingValueLabel(t, 'column_mode', String(task.formatting.column_mode))}
                                                                </span>
                                                            )}
                                                            {task.formatting.margin != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.margins', { value: getFormattingValueLabel(t, 'margin', String(task.formatting.margin)) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.cjk_font != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.font', { value: getFormattingValueLabel(t, 'cjk_font', String(task.formatting.cjk_font)) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.paragraph_indent === true && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('formatting.firstLineIndent')}
                                                                </span>
                                                            )}
                                                            {task.formatting.localize_captions === true && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.localize_figures_tables')}
                                                                </span>
                                                            )}
                                                            {task.formatting.bib_style != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.bibliography', { value: String(task.formatting.bib_style) })}
                                                                </span>
                                                            )}
                                                            {task.formatting.cite_style != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {t('history.citation', { value: getFormattingValueLabel(t, 'cite_style', String(task.formatting.cite_style)) })}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </CollapsibleContent>
                                </CardContent>
                            </Card>
                        </Collapsible>
                    ))
                )}
            </div>

            {/* Load more button */}
            {hasMore && (
                <div className="flex justify-center pt-4">
                    <Button
                        variant="outline"
                        onClick={loadMore}
                        disabled={loading}
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

            {/* Delete confirmation dialog */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{t('history.dialog.confirmDeleteTitle')}</AlertDialogTitle>
                        <AlertDialogDescription>
                            {t('history.this_action_deletes_all_data_for_this_task_source_files_translated_results_glossary_and_cannot_be_undone_continue')}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>{t('common.actions.cancel')}</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={confirmDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {t('common.actions.confirmDelete')}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
