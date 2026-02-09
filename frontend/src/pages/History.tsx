/**
 * History Page
 * 
 * Displays user's translation history with pagination.
 * Requires authentication - shows prompt for guests.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, History, Clock, FileText, ArrowRight, LogIn, RefreshCw } from 'lucide-react'

interface TaskHistoryItem {
    task_id: string
    source_type: string
    arxiv_id?: string
    translation_mode: string
    status: string
    progress: number
    created_at: string
    completed_at?: string
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

    const [tasks, setTasks] = useState<TaskHistoryItem[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [total, setTotal] = useState(0)

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
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchHistory(1)}
                    disabled={loading}
                >
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    刷新
                </Button>
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
                        <Card
                            key={task.task_id}
                            className="border-border/50 bg-card/80 hover:bg-card/90 transition-colors cursor-pointer group"
                            onClick={() => navigate(`/processing?task=${task.task_id}`)}
                        >
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="p-2 rounded-lg bg-muted">
                                            <FileText className="h-5 w-5 text-muted-foreground" />
                                        </div>
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

                                    <div className="flex items-center gap-3">
                                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${statusStyles[task.status] || statusStyles.pending}`}>
                                            {task.status === 'completed' ? '已完成' :
                                                task.status === 'processing' ? '处理中' :
                                                    task.status === 'failed' ? '失败' : '等待中'}
                                        </span>
                                        <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
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
        </div>
    )
}
