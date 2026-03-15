import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '@/store/useStore'
import { AdvancedConfig } from '@/components/AdvancedConfig'
import { DropZone } from '@/components/DropZone'
import { BatchTranslation, type BatchTranslationHandle, type BatchTranslationState } from '@/components/BatchTranslation'
import { LoginPrompt } from '@/components/LoginPrompt'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { ChevronDown, ChevronRight, Play, FileText, Download, RefreshCw, Info, Loader2, X } from 'lucide-react'
import { toast } from 'sonner'

const stageMap: Record<string, string> = {
    downloading: '正在从 arXiv 下载源文件...',
    extracting: '正在解压源文件...',
    downloading_pdf: '正在下载原文 PDF...',
    validating: '正在校验 LaTeX 结构...',
}

export default function Dashboard() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const isAuthenticated = !!user
    const {
        taskId, status, config,
        downloadProgress, downloadStage, isDownloading,
        startArxivDownload, startTranslation, loadUserSettings
    } = useStore()

    const [activeTab, setActiveTab] = useState('arxiv')
    const [isConfigOpen, setIsConfigOpen] = useState(false)
    const [localArxivId, setLocalArxivId] = useState('')
    const [isLoadingSource, setIsLoadingSource] = useState(false)
    const batchRef = useRef<BatchTranslationHandle>(null)
    const [batchState, setBatchState] = useState<BatchTranslationState>({
        isSubmitting: false,
        activeTab: 'arxiv',
        canSubmit: false,
    })
    const [showArxivTip, setShowArxivTip] = useState(true)
    const [showApiWarning, setShowApiWarning] = useState(true)

    useEffect(() => {
        loadUserSettings()
    }, [loadUserSettings])

    const handleLoadArxiv = async () => {
        if (!localArxivId.trim()) return
        setIsLoadingSource(true)
        toast.info('正在加载源文档，请稍候...')
        try {
            await startArxivDownload(localArxivId)
        } finally {
            setIsLoadingSource(false)
        }
    }

    const handleStart = async () => {
        if (!taskId) return
        const request = {
            source_language: config.source_language,
            target_language: config.target_language,
            advanced_config: config.advanced_config
        }
        await startTranslation(request)
        navigate('/processing')
    }

    return (
        <div className="container mx-auto max-w-4xl p-6 space-y-8 animate-in fade-in duration-500">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">新建翻译</h1>
                <p className="text-muted-foreground">
                    输入 arXiv ID 或上传 LaTeX 项目，开始新的翻译任务。
                </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="grid w-full grid-cols-3 lg:w-[520px]">
                    <TabsTrigger value="arxiv">arXiv 编号</TabsTrigger>
                    <TabsTrigger value="upload">本地上传</TabsTrigger>
                    <TabsTrigger value="batch">批量翻译</TabsTrigger>
                </TabsList>

                <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-sm">
                    {activeTab !== 'batch' && (
                        <CardHeader>
                            <CardTitle>{activeTab === 'arxiv' ? 'arXiv 论文' : '文件上传'}</CardTitle>
                            <CardDescription>
                                {activeTab === 'arxiv'
                                    ? '输入 arXiv ID（例如 2310.xxxxx）下载源文档。'
                                    : '上传 LaTeX 项目压缩包（ZIP / RAR / TAR.GZ）。'}
                            </CardDescription>
                        </CardHeader>
                    )}
                    <CardContent className="space-y-6">
                        <TabsContent value="arxiv" className="mt-0 space-y-4">
                            <div className="flex gap-4">
                                <Input
                                    placeholder="请输入 arXiv ID（例如 2301.12345）"
                                    value={localArxivId}
                                    onChange={(e) => setLocalArxivId(e.target.value)}
                                    className="font-mono bg-background"
                                />
                                <Button
                                    onClick={handleLoadArxiv}
                                    disabled={!localArxivId || isLoadingSource || isDownloading || (status === 'processing')}
                                    className="transition-all duration-150 active:scale-95"
                                >
                                    {(isLoadingSource || isDownloading)
                                        ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                        : <Download className="mr-2 h-4 w-4" />}
                                    加载源文档
                                </Button>
                            </div>

                            {showArxivTip && (
                                <div
                                    className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md p-3 border border-border/50 relative group cursor-pointer hover:bg-muted/80 transition-colors animate-in fade-in zoom-in-95 duration-200"
                                    onClick={() => setShowArxivTip(false)}
                                >
                                    <Info className="h-4 w-4 mt-0.5 text-blue-500 flex-shrink-0" />
                                    <p className="pr-6">
                                        <span className="font-medium text-foreground/80">提示：</span>
                                        通过官方 arXiv 通道下载时，大论文会耗时较久，请耐心等待。
                                    </p>
                                    <X className="h-4 w-4 absolute right-2 top-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                            )}

                            {isDownloading && (
                                <div className="space-y-3 animate-in fade-in slide-in-from-top-2 rounded-xl border border-border/60 bg-muted/30 p-4 backdrop-blur-sm">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="relative flex h-2.5 w-2.5">
                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
                                            </span>
                                            <span className="text-sm font-medium text-foreground">
                                                {downloadStage ? downloadStage.replace(/_/g, ' ') : '准备中...'}
                                            </span>
                                        </div>
                                        <span className="text-sm font-mono font-semibold text-primary tabular-nums">
                                            {Math.round(downloadProgress)}%
                                        </span>
                                    </div>
                                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
                                        <div
                                            className="h-full rounded-full bg-gradient-to-r from-primary/80 to-primary transition-all duration-300 ease-out"
                                            style={{ width: `${Math.round(downloadProgress)}%` }}
                                        />
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {stageMap[downloadStage] ?? '正在准备下载...'}
                                    </p>
                                </div>
                            )}
                        </TabsContent>

                        <TabsContent value="upload" className="mt-0">
                            <DropZone />
                        </TabsContent>

                        <TabsContent value="batch" className="mt-0">
                            {isAuthenticated ? (
                                <BatchTranslation
                                    ref={batchRef}
                                    advancedConfig={config.advanced_config}
                                    targetLanguage={config.target_language}
                                    sourceLanguage={config.source_language}
                                    onStateChange={setBatchState}
                                />
                            ) : (
                                <LoginPrompt
                                    message="请登录后使用批量翻译"
                                    description="批量翻译仅对登录用户开放，支持一次提交最多 9 篇 arXiv 论文或多个本地文件。"
                                />
                            )}
                        </TabsContent>

                        {taskId && status === 'ready' && (
                            <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4 flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                                <div className="p-2 rounded-full bg-green-500/20 text-green-600 dark:text-green-400">
                                    <FileText className="w-5 h-5" />
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-green-700 dark:text-green-300">源文档已就绪</p>
                                    <p className="text-xs text-green-600/80 dark:text-green-400/80 font-mono">任务编号: {taskId}</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </Tabs>

            <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen} className="space-y-2">
                <div className="flex flex-col md:flex-row md:items-center justify-between w-full gap-3">
                    <CollapsibleTrigger asChild>
                        <Button variant="ghost" className="flex items-center gap-2 w-fit justify-start p-0 hover:bg-transparent hover:text-primary group">
                            {isConfigOpen
                                ? <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0" />
                                : <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0" />}
                            <span className="font-medium text-lg whitespace-nowrap">高级配置</span>
                            <span className="text-sm text-muted-foreground ml-1 font-normal whitespace-nowrap">（可选）</span>
                        </Button>
                    </CollapsibleTrigger>

                    {showApiWarning && (
                        <div
                            className="flex items-center gap-1.5 text-[11px] sm:text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2.5 py-1.5 rounded-md border border-amber-500/20 sm:w-fit cursor-pointer hover:bg-amber-500/20 transition-colors group animate-in fade-in zoom-in-95 duration-200"
                            onClick={() => setShowApiWarning(false)}
                        >
                            <Info className="w-3.5 h-3.5 shrink-0" />
                            <span className="leading-tight mr-1">
                                默认 API 使用免费额度，质量与速度可能受影响，建议配置自定义 API。
                            </span>
                            <X className="w-3.5 h-3.5 shrink-0 opacity-50 group-hover:opacity-100 transition-opacity" />
                        </div>
                    )}
                </div>
                <CollapsibleContent className="space-y-4 pt-2 animate-in slide-in-from-top-2 fade-in duration-200">
                    <AdvancedConfig />
                </CollapsibleContent>
            </Collapsible>

            <div className="flex justify-end pt-4 pb-12">
                {activeTab === 'batch' ? (
                    <Button
                        size="lg"
                        onClick={() => batchRef.current?.submitCurrent()}
                        disabled={!batchState.canSubmit}
                        className="w-full md:w-auto min-w-[200px] shadow-lg shadow-primary/20 text-lg py-6"
                    >
                        {batchState.isSubmitting
                            ? <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                            : <Play className="mr-2 h-5 w-5 fill-current" />}
                        {batchState.isSubmitting ? '提交中...' : '开始批量翻译'}
                    </Button>
                ) : (
                    <Button
                        size="lg"
                        onClick={handleStart}
                        disabled={!taskId || status === 'downloading' || status === 'starting_translation'}
                        className="w-full md:w-auto min-w-[200px] shadow-lg shadow-primary/20 text-lg py-6"
                    >
                        <Play className="mr-2 h-5 w-5 fill-current" />
                        开始翻译
                    </Button>
                )}
            </div>
        </div>
    )
}
