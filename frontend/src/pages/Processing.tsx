import { useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { CheckCircle2, RotateCw, Download, Code, LogIn, AlertTriangle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { LogViewer } from "@/components/log-viewer"
import { useStore } from "@/store/useStore"
import { useAuth } from "@/contexts/AuthContext"

const steps = [
    { id: "download", label: "Downloading Source" },
    { id: "extract", label: "Extracting Files" },
    { id: "translate", label: "Translating Content" },
    { id: "compile", label: "Compiling PDF" }
]

export default function ProcessingPage() {
    const { taskId: storeTaskId, status, logs, pollStatus, stopPolling, setTaskId, taskWarnings, error } = useStore()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const { user } = useAuth()
    const isGuest = !user

    // URL 参数优先，兼容 store（单论文翻译流程）
    const urlTaskId = searchParams.get('taskId')
    const effectiveTaskId = urlTaskId || storeTaskId

    // 若 URL 有 taskId 但 store 没有，同步到 store（确保 pollStatus 等方法能读到）
    useEffect(() => {
        if (urlTaskId && urlTaskId !== storeTaskId) {
            setTaskId(urlTaskId)
        }
    }, [urlTaskId])

    useEffect(() => {
        // 只有在有 effectiveTaskId 时才开始轮询
        if (effectiveTaskId) {
            pollStatus()
        }
        return () => stopPolling()
    }, [effectiveTaskId])

    const normalizedStatus = (status || "").toLowerCase()
    const canPreview = normalizedStatus === 'completed' || normalizedStatus === 'completed_with_warnings'
    const isFailed = normalizedStatus === 'failed' || normalizedStatus === 'failed_compilation'

    // Derive current step from status message or status enum
    let currentStepIndex = 0
    if (normalizedStatus === 'downloading') currentStepIndex = 0
    else if (normalizedStatus === 'processing' || normalizedStatus === 'started') currentStepIndex = 2
    else if (normalizedStatus === 'failed_compilation') currentStepIndex = 3
    else if (normalizedStatus === 'failed') currentStepIndex = 2
    else if (canPreview) currentStepIndex = 4

    // 使用 effectiveTaskId 替代 taskId 用于下载链接
    const activeTaskId = effectiveTaskId

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            {/* Guest warning banner */}
            {isGuest && (
                <div className="flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                    <p className="flex-1 text-sm text-amber-300">
                        <span className="font-semibold">访客模式：</span>
                        离开此页面后将无法重新访问翻译结果。
                        <button
                            onClick={() => navigate('/login')}
                            className="ml-2 inline-flex items-center gap-1 underline underline-offset-2 hover:text-amber-200"
                        >
                            <LogIn className="h-3 w-3" />
                            登录以保存到历史记录
                        </button>
                    </p>
                </div>
            )}

            {/* Formatting warnings (e.g. auto-downgraded font size) */}
            {taskWarnings && (
                <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
                    <p className="flex-1 text-sm text-amber-300">
                        <span className="font-semibold">排版提示：</span>{taskWarnings}
                    </p>
                </div>
            )}

            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Translation in Progress</h1>
                    <p className="text-muted-foreground">Monitor the realtime status of your translation task.</p>
                </div>
                {canPreview ? (
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => window.open(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/download/${activeTaskId}/source`, '_blank')}>
                            <Download className="mr-2 h-4 w-4" /> Download Source
                        </Button>
                        <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => navigate("/preview")}>View Result</Button>
                    </div>
                ) : isFailed ? (
                    <Button variant="outline" onClick={() => navigate("/")}>Back to Home</Button>
                ) : (
                    <Button variant="destructive" onClick={() => navigate("/")}>Cancel Task</Button>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column: Status & Visualization */}
                <div className="col-span-1 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Status</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="relative border-l-2 border-slate-200 dark:border-slate-800 ml-3 space-y-8 pl-6 py-2">
                                {steps.map((step, index) => {
                                    const isActive = !canPreview && !isFailed && index === currentStepIndex
                                    const isFailedStep = isFailed && index === currentStepIndex
                                    const isCompleted = index < currentStepIndex || canPreview

                                    return (
                                        <div key={step.id} className="relative">
                                            <span className={`absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full border-2 bg-background ${isCompleted ? "border-emerald-500 bg-emerald-500 text-white" :
                                                isFailedStep ? "border-red-500 bg-red-500 text-white" :
                                                    isActive ? "border-indigo-500 border-2 animate-pulse" : "border-slate-300"
                                                }`}>
                                                {isCompleted && <CheckCircle2 className="h-3 w-3" />}
                                                {isFailedStep && <AlertTriangle className="h-3 w-3" />}
                                                {isActive && <RotateCw className="h-3 w-3 animate-spin text-indigo-500" />}
                                            </span>
                                            <div className="flex flex-col">
                                                <span className={`text-sm font-medium ${isActive ? "text-indigo-600" : isCompleted ? "text-emerald-600" : isFailedStep ? "text-red-600" : "text-slate-500"}`}>
                                                    {step.label}
                                                </span>
                                                {isActive && <span className="text-xs text-muted-foreground animate-pulse">Running...</span>}
                                                {isFailedStep && <span className="text-xs text-red-600">Failed</span>}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="pt-6 flex justify-center items-center min-h-[200px]">
                            {canPreview ? (
                                <div className="text-center space-y-2">
                                    <CheckCircle2 className="h-16 w-16 text-emerald-500 mx-auto" />
                                    <p className="font-medium text-emerald-600">Translation Completed!</p>
                                </div>
                            ) : isFailed ? (
                                <div className="text-center space-y-2">
                                    <AlertTriangle className="h-16 w-16 text-red-500 mx-auto" />
                                    <p className="font-medium text-red-600">Translation Failed</p>
                                    <p className="text-xs text-slate-500">{error || status}</p>
                                </div>
                            ) : (
                                <div className="text-center space-y-2">
                                    <RotateCw className="h-16 w-16 text-indigo-500 animate-spin mx-auto" />
                                    <p className="text-sm text-muted-foreground">Processing...</p>
                                    <p className="text-xs text-slate-400">{status}</p>
                                    {logs.length > 0 && logs[logs.length - 1]?.includes("rate limited") && (
                                        <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 animate-pulse">
                                            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                                            <p className="text-xs text-amber-500 dark:text-amber-400 text-left">
                                                API rate limited, retrying until API recovers. Consider using your own API key for better performance.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column: Logs */}
                <div className="lg:col-span-2">
                    <Card className="h-full flex flex-col">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Live Logs</CardTitle>
                            <div className="flex gap-2">
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0"><Code className="h-4 w-4" /></Button>
                            </div>
                        </CardHeader>
                        <CardContent className="flex-1">
                            <LogViewer logs={logs} />
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
