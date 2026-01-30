import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { CheckCircle2, RotateCw, Download, Code } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { LogViewer } from "@/components/log-viewer"
import { useStore } from "@/store/useStore"

const steps = [
    { id: "download", label: "Downloading Source" },
    { id: "extract", label: "Extracting Files" },
    { id: "translate", label: "Translating Content" },
    { id: "compile", label: "Compiling PDF" }
]

export default function ProcessingPage() {
    const { taskId, status, logs, pollStatus, stopPolling } = useStore()
    const navigate = useNavigate()

    useEffect(() => {
        // 只有在有 taskId 时才开始轮询，没有时保持等待状态
        if (taskId) {
            pollStatus()
        }
        return () => stopPolling()
    }, [taskId])

    // Derive current step from status message or status enum
    // For MVP, simplistic mapping:
    let currentStepIndex = 0
    if (status === 'downloading') currentStepIndex = 0
    else if (status === 'processing' || status === 'started') currentStepIndex = 2 // Translating involves extracting
    else if (status === 'completed' || status === 'completed_with_warnings') currentStepIndex = 4

    const isComplete = currentStepIndex >= 4

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Translation in Progress</h1>
                    <p className="text-muted-foreground">Monitor the realtime status of your translation task.</p>
                </div>
                {isComplete ? (
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => window.open(`http://localhost:8000/api/download/${taskId}/source`, '_blank')}>
                            <Download className="mr-2 h-4 w-4" /> Download Source
                        </Button>
                        <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => navigate("/preview")}>View Result</Button>
                    </div>
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
                                    // Use simple logic: if complete, all done. If processing, step 2 is active.
                                    const isActive = !isComplete && index === currentStepIndex;
                                    const isCompleted = index < currentStepIndex || isComplete;

                                    return (
                                        <div key={step.id} className="relative">
                                            <span className={`absolute -left-[31px] flex h-6 w-6 items-center justify-center rounded-full border-2 bg-background ${isCompleted ? "border-emerald-500 bg-emerald-500 text-white" :
                                                isActive ? "border-indigo-500 border-2 animate-pulse" : "border-slate-300"
                                                }`}>
                                                {isCompleted && <CheckCircle2 className="h-3 w-3" />}
                                                {isActive && <RotateCw className="h-3 w-3 animate-spin text-indigo-500" />}
                                            </span>
                                            <div className="flex flex-col">
                                                <span className={`text-sm font-medium ${isActive ? "text-indigo-600" : isCompleted ? "text-emerald-600" : "text-slate-500"}`}>
                                                    {step.label}
                                                </span>
                                                {isActive && <span className="text-xs text-muted-foreground animate-pulse">Running...</span>}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent className="pt-6 flex justify-center items-center min-h-[200px]">
                            {isComplete ? (
                                <div className="text-center space-y-2">
                                    <CheckCircle2 className="h-16 w-16 text-emerald-500 mx-auto" />
                                    <p className="font-medium text-emerald-600">Translation Completed!</p>
                                </div>
                            ) : (
                                <div className="text-center space-y-2">
                                    <RotateCw className="h-16 w-16 text-indigo-500 animate-spin mx-auto" />
                                    <p className="text-sm text-muted-foreground">Processing...</p>
                                    <p className="text-xs text-slate-400">{status}</p>
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
