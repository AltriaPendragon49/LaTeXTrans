/**
 * History Page
 * 
 * Displays user's translation history with pagination.
 * Requires authentication - shows prompt for guests.
 */

import { useState, useEffect } from 'react'
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
const statusStyles: Record<string, string> = {
    pending: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
    processing: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    completed: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
    failed: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
}

export default function HistoryPage() {
    const navigate = useNavigate()
    const { isAuthenticated, loading: authLoading } = useAuth()
    const { setTaskId, setArxivId } = useStore()

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
    const fetchHistory = async (pageNum: number, append: boolean = false) => {
        setLoading(true)
        setError(null)

        try {
            const { getAccessToken } = await import('@/lib/supabase')
            const token = await getAccessToken()

            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/history?page=${pageNum}&page_size=10`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                }
            )

            if (!response.ok) {
                throw new Error('Failed to fetch history')
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
            setError(err instanceof Error ? err.message : '获取历史记录失败')
        } finally {
            setLoading(false)
        }
    }

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
    }, [isAuthenticated])

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

        const toastId = toast.loading('正在删除任务...')

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

            toast.success('任务已删除', { id: toastId })
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : '删除失败，请重试',
                { id: toastId }
            )
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

        const toastId = toast.loading(`正在删除 ${count} 个任务...`)

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
                toast.success(`成功删除 ${successCount} 个任务`, { id: toastId })
            } else if (successCount > 0) {
                toast.warning(`删除了 ${successCount}/${count} 个任务，部分失败请重试`, { id: toastId })
            } else {
                toast.error(`删除失败（0/${count}），请重试`, { id: toastId })
            }
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : '批量删除失败，请重试',
                { id: toastId }
            )
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
                        翻译历史
                    </h1>
                </div>

                <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="pt-6 space-y-4">
                        <div className="text-center py-8 space-y-4">
                            <div className="mx-auto p-4 rounded-full bg-muted/50 w-fit">
                                <LogIn className="h-8 w-8 text-muted-foreground" />
                            </div>
                            <div className="space-y-2">
                                <p className="text-lg font-medium">登录以查看翻译历史</p>
                                <p className="text-muted-foreground">
                                    登录后您可以查看和管理所有的翻译任务记录
                                </p>
                            </div>
                            <Button onClick={() => navigate('/login')} className="mt-4">
                                <LogIn className="mr-2 h-4 w-4" />
                                前往登录
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
        return date.toLocaleString('zh-CN', {
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
                        翻译历史
                    </h1>
                    <p className="text-muted-foreground">
                        共 {total} 个翻译任务
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
                                {selectedTasks.size === tasks.length ? '取消全选' : '全选'}
                            </Button>
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={handleBatchDelete}
                                disabled={selectedTasks.size === 0}
                                className="min-w-[90px]"
                            >
                                <Trash2 className="h-4 w-4 mr-2" />
                                删除选中 ({selectedTasks.size})
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setSelectionMode(false)
                                    setSelectedTasks(new Set())
                                }}
                            >
                                取消
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
                                选择
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchHistory(1)}
                                disabled={loading}
                            >
                                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                                刷新
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
                                <p>暂无翻译记录</p>
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
                                                    aria-label={`选择任务 ${task.arxiv_id || task.task_id.slice(0, 8)}`}
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
                                                        {task.translation_mode === 'full' ? '全文翻译' : '快速筛查'}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${statusStyles[task.status] || statusStyles.pending}`}>
                                                {task.status === 'completed' ? '已完成' :
                                                    task.status === 'processing' ? '处理中' :
                                                        task.status === 'failed' ? '失败' : '等待中'}
                                            </span>

                                            {!selectionMode && (
                                                <>
                                                    {/* Delete button */}
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-11 w-11 p-0 hover:bg-destructive/10 hover:text-destructive transition-colors"
                                                        onClick={(e) => handleDeleteClick(task.task_id, e)}
                                                        aria-label="删除任务"
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
                                                            aria-label="展开配置详情"
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
                                                <span className="font-medium">翻译配置</span>
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                                {/* 语言设置 */}
                                                <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
                                                    <Languages className="h-4 w-4 text-blue-500" />
                                                    <span className="text-muted-foreground">语言：</span>
                                                    <span className="font-medium">{task.source_language} → {task.target_language}</span>
                                                </div>

                                                {/* 编译策略 */}
                                                <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
                                                    <Wrench className="h-4 w-4 text-orange-500" />
                                                    <span className="text-muted-foreground">编译策略：</span>
                                                    <span className="font-medium capitalize">{task.compile_strategy}</span>
                                                </div>

                                                {/* 翻译模型 */}
                                                {task.translation_model && (
                                                    <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30 md:col-span-2">
                                                        <Sparkles className="h-4 w-4 text-purple-500" />
                                                        <span className="text-muted-foreground">翻译模型：</span>
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
                                                        <span className="text-xs">生成术语表</span>
                                                    </div>

                                                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/30">
                                                        {task.use_author_api ? (
                                                            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                                                        ) : (
                                                            <XCircle className="h-3.5 w-3.5 text-gray-400" />
                                                        )}
                                                        <span className="text-xs">使用作者 API</span>
                                                    </div>
                                                </div>

                                                {/* 排版配置快照 */}
                                                {task.formatting && Object.keys(task.formatting).length > 0 && (
                                                    <div className="md:col-span-2 space-y-2">
                                                        <div className="text-xs text-muted-foreground font-medium">排版设置：</div>
                                                        <div className="flex flex-wrap gap-1.5">
                                                            {task.formatting.line_spacing != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    行距: {String(task.formatting.line_spacing)}
                                                                </span>
                                                            )}
                                                            {task.formatting.font_size != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    字号: {String(task.formatting.font_size)}pt
                                                                </span>
                                                            )}
                                                            {task.formatting.column_mode != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    {task.formatting.column_mode === 'single' ? '单栏' : '双栏'}
                                                                </span>
                                                            )}
                                                            {task.formatting.margin != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    边距: {task.formatting.margin === 'narrow' ? '窄' : task.formatting.margin === 'wide' ? '宽' : '标准'}
                                                                </span>
                                                            )}
                                                            {task.formatting.cjk_font != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    字体: {task.formatting.cjk_font === 'songti' ? '宋体' : '黑体'}
                                                                </span>
                                                            )}
                                                            {task.formatting.paragraph_indent === true && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    首行缩进
                                                                </span>
                                                            )}
                                                            {task.formatting.localize_captions === true && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    图表本地化
                                                                </span>
                                                            )}
                                                            {task.formatting.bib_style != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    文献: {String(task.formatting.bib_style)}
                                                                </span>
                                                            )}
                                                            {task.formatting.cite_style != null && (
                                                                <span className="px-2 py-0.5 text-xs rounded bg-violet-500/10 text-violet-600 dark:text-violet-400">
                                                                    引文: {task.formatting.cite_style === 'numbers' ? '数字' : task.formatting.cite_style === 'super' ? '上标' : '著者-年'}
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
                                加载中...
                            </>
                        ) : (
                            '加载更多'
                        )}
                    </Button>
                </div>
            )}

            {/* Delete confirmation dialog */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>确认删除任务</AlertDialogTitle>
                        <AlertDialogDescription>
                            此操作将删除该任务的所有数据（源文件、翻译结果、术语表），且无法恢复。确定要继续吗？
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>取消</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={confirmDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            确认删除
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
