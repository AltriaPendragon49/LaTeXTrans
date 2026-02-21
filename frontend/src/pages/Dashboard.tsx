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
import { Progress } from '@/components/ui/progress'
import { ChevronDown, ChevronRight, Play, FileText, Download, RefreshCw, Info, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

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
    // const [isDownloading, setIsDownloading] = useState(false) // Removed local state in favor of store state

    // Load user settings on mount (if authenticated)
    useEffect(() => {
        loadUserSettings()
    }, [loadUserSettings])

    // Handle ArXiv Load
    const handleLoadArxiv = async () => {
        if (!localArxivId.trim()) return
        setIsLoadingSource(true)
        toast.info('正在加载源文件，请稍候...')
        try {
            await startArxivDownload(localArxivId)
            // Success handled in store
        } catch (e) {
            // Error handled in store
        } finally {
            setIsLoadingSource(false)
        }
    }

    // Handle Start Translation
    const handleStart = async () => {
        if (!taskId) return
        try {
            // Build config request
            const request = {
                source_language: config.source_language,
                target_language: config.target_language,
                advanced_config: config.advanced_config
            }
            await startTranslation(request)
            navigate('/processing')
        } catch (e) {
            // Error
        }
    }

    return (
        <div className="container mx-auto max-w-4xl p-6 space-y-8 animate-in fade-in duration-500">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">New Translation</h1>
                <p className="text-muted-foreground">
                    Start a new translation task by entering an ArXiv ID or uploading a LaTeX project.
                </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="grid w-full grid-cols-3 lg:w-[520px]">
                    <TabsTrigger value="arxiv">ArXiv ID</TabsTrigger>
                    <TabsTrigger value="upload">Local Upload</TabsTrigger>
                    <TabsTrigger value="batch">Batch</TabsTrigger>
                </TabsList>

                <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-sm">
                    {activeTab !== 'batch' && (
                        <CardHeader>
                            <CardTitle>{activeTab === 'arxiv' ? 'ArXiv Paper' : 'File Upload'}</CardTitle>
                            <CardDescription>
                                {activeTab === 'arxiv'
                                    ? 'Enter the ArXiv ID (e.g., 2310.xxxxx) to download source.'
                                    : 'Upload your LaTeX project as a ZIP/RAR archive.'}
                            </CardDescription>
                        </CardHeader>
                    )}
                    <CardContent className="space-y-6">
                        <TabsContent value="arxiv" className="mt-0 space-y-4">
                            <div className="flex gap-4">
                                <Input
                                    placeholder="Enter ArXiv ID (e.g., 2301.12345)"
                                    value={localArxivId}
                                    onChange={(e) => setLocalArxivId(e.target.value)}
                                    className="font-mono bg-background"
                                />
                                <Button
                                    onClick={handleLoadArxiv}
                                    disabled={!localArxivId || isLoadingSource || isDownloading || (status === 'processing')}
                                    className="transition-all duration-150 active:scale-95"
                                >
                                    {(isLoadingSource || isDownloading) ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                                    Load Source
                                </Button>
                            </div>

                            {/* Info tip about load time */}
                            <div className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md p-3 border border-border/50">
                                <Info className="h-4 w-4 mt-0.5 text-blue-500 flex-shrink-0" />
                                <p>
                                    <span className="font-medium text-foreground/80">Tip:</span> Loading typically takes over 70% of total task time. Please wait patiently, then configure your translation settings below.
                                </p>
                            </div>

                            {/* Download Progress Bar */}
                            {isDownloading && (
                                <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                                    <div className="flex justify-between text-sm text-muted-foreground">
                                        <span className="capitalize">{downloadStage?.replace(/_/g, ' ') || 'Process Started...'}</span>
                                        <span className="font-mono">{Math.round(downloadProgress)}%</span>
                                    </div>
                                    <Progress value={downloadProgress} className="h-2" />
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
                                    message="请登录以使用批量翻译"
                                    description="批量翻译功能仅对登录用户开放，支持一次提交最多 9 篇 arXiv 论文。"
                                />
                            )}
                        </TabsContent>

                        {/* Task Ready Indicator - 只在下载完成后显示 */}
                        {taskId && status === 'ready' && (
                            <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4 flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                                <div className="p-2 rounded-full bg-green-500/20 text-green-600 dark:text-green-400">
                                    <FileText className="w-5 h-5" />
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-green-700 dark:text-green-300">Source Ready</p>
                                    <p className="text-xs text-green-600/80 dark:text-green-400/80 font-mono">Task ID: {taskId}</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </Tabs>

            {/* Advanced Configuration - 对所有 Tab 均可用，配置共享给单论文和批量翻译 */}
            <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen} className="space-y-2">
                <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="flex items-center gap-2 w-full justify-start p-0 hover:bg-transparent hover:text-primary group">
                        {isConfigOpen ? <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-primary" /> : <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary" />}
                        <span className="font-medium text-lg">Advanced Configuration</span>
                        <span className="text-sm text-muted-foreground ml-2 font-normal">(Optional)</span>
                    </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-4 pt-2 animate-in slide-in-from-top-2 fade-in duration-200">
                    <AdvancedConfig />
                </CollapsibleContent>
            </Collapsible>

            {/* 底部按鈕：根据 Tab 动态切换 */}
            <div className="flex justify-end pt-4 pb-12">
                {activeTab === 'batch' ? (
                    // Batch Tab: 显示批量提交按鈕
                    <Button
                        size="lg"
                        onClick={() => batchRef.current?.submitCurrent()}
                        disabled={!batchState.canSubmit}
                        className="w-full md:w-auto min-w-[200px] shadow-lg shadow-primary/20 text-lg py-6"
                    >
                        {batchState.isSubmitting ? (
                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        ) : (
                            <Play className="mr-2 h-5 w-5 fill-current" />
                        )}
                        {batchState.isSubmitting
                            ? '提交中…'
                            : batchState.activeTab === 'upload'
                                ? '开始批量上传翻译'
                                : '开始批量翻译'}
                    </Button>
                ) : (
                    // ArXiv / Upload Tab: 单论文翻译按鈕
                    <Button
                        size="lg"
                        onClick={handleStart}
                        disabled={!taskId || status === 'downloading' || status === 'starting_translation'}
                        className="w-full md:w-auto min-w-[200px] shadow-lg shadow-primary/20 text-lg py-6"
                    >
                        <Play className="mr-2 h-5 w-5 fill-current" />
                        Start Translation
                    </Button>
                )}
            </div>
        </div>
    )
}
