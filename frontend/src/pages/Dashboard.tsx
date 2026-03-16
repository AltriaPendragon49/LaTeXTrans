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
import { useTranslation } from 'react-i18next'

export default function Dashboard() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const { t } = useTranslation()
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

    const stageMap: Record<string, string> = {
        downloading: t('dashboard.downloading_source_files_from_arxiv'),
        extracting: t('dashboard.extracting_source_files_2'),
        downloading_pdf: t('dashboard.downloading_the_original_pdf'),
        validating: t('dashboard.validating_latex_structure_2'),
    }

    const stageTitleMap: Record<string, string> = {
        downloading: t('task.steps.downloadSource'),
        extracting: t('dashboard.extracting_source_files'),
        downloading_pdf: t('dashboard.downloading_original_pdf'),
        validating: t('dashboard.validating_latex_structure'),
    }

    useEffect(() => {
        loadUserSettings()
    }, [loadUserSettings])

    const handleLoadArxiv = async () => {
        if (!localArxivId.trim()) return
        setIsLoadingSource(true)
        toast.info(t('dashboard.loading_source_document_please_wait'))
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
                <h1 className="text-3xl font-bold tracking-tight">{t('common.new_translation')}</h1>
                <p className="text-muted-foreground">
                    {t('dashboard.enter_an_arxiv_id_or_upload_a_latex_project_to_start_a_new_translation_task')}
                </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="grid w-full grid-cols-3 lg:w-[520px]">
                    <TabsTrigger value="arxiv">{t('dashboard.arxiv_id')}</TabsTrigger>
                    <TabsTrigger value="upload">{t('dashboard.local_upload')}</TabsTrigger>
                    <TabsTrigger value="batch">{t('dashboard.batch_translation')}</TabsTrigger>
                </TabsList>

                <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-sm">
                    {activeTab !== 'batch' && (
                        <CardHeader>
                            <CardTitle>{activeTab === 'arxiv' ? t('dashboard.arxiv_paper') : t('dashboard.file_upload')}</CardTitle>
                            <CardDescription>
                                {activeTab === 'arxiv'
                                    ? t('dashboard.enter_an_arxiv_id_for_example_2310_xxxxx_to_download_source_files')
                                    : t('dashboard.upload_a_latex_project_archive_zip_rar_tar_gz')}
                            </CardDescription>
                        </CardHeader>
                    )}
                    <CardContent className="space-y-6">
                        <TabsContent value="arxiv" className="mt-0 space-y-4">
                            <div className="flex gap-4">
                                <Input
                                    placeholder={t('dashboard.enter_an_arxiv_id_for_example_2301_12345')}
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
                                    {t('dashboard.load_source')}
                                </Button>
                            </div>

                            {showArxivTip && (
                                <div
                                    className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md p-3 border border-border/50 relative group cursor-pointer hover:bg-muted/80 transition-colors animate-in fade-in zoom-in-95 duration-200"
                                    onClick={() => setShowArxivTip(false)}
                                >
                                    <Info className="h-4 w-4 mt-0.5 text-blue-500 shrink-0" />
                                    <p className="pr-6">
                                        <span className="font-medium text-foreground/80">{t('dashboard.tip')}</span>
                                        {t('dashboard.large_papers_can_take_longer_to_download_through_the_official_arxiv_channel_please_be_patient')}
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
                                                {downloadStage ? (stageTitleMap[downloadStage] ?? downloadStage.replace(/_/g, ' ')) : t('dashboard.preparing')}
                                            </span>
                                        </div>
                                        <span className="text-sm font-mono font-semibold text-primary tabular-nums">
                                            {Math.round(downloadProgress)}%
                                        </span>
                                    </div>
                                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
                                        <div
                                            className="h-full rounded-full bg-linear-to-r from-primary/80 to-primary transition-all duration-300 ease-out"
                                            style={{ width: `${Math.round(downloadProgress)}%` }}
                                        />
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {stageMap[downloadStage] ?? t('dashboard.preparing_download')}
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
                                    messageKey="dashboard.batch.loginRequired"
                                    descriptionKey="dashboard.batch.loginRequiredDescription"
                                />
                            )}
                        </TabsContent>

                        {taskId && status === 'ready' && (
                            <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4 flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                                <div className="p-2 rounded-full bg-green-500/20 text-green-600 dark:text-green-400">
                                    <FileText className="w-5 h-5" />
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-green-700 dark:text-green-300">{t('dashboard.source_document_ready')}</p>
                                    <p className="text-xs text-green-600/80 dark:text-green-400/80 font-mono">{t('dashboard.task_id', { taskId })}</p>
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
                            <span className="font-medium text-lg whitespace-nowrap">{t('dashboard.advancedConfig')}</span>
                            <span className="text-sm text-muted-foreground ml-1 font-normal whitespace-nowrap">{t('dashboard.optional')}</span>
                        </Button>
                    </CollapsibleTrigger>

                    {showApiWarning && (
                        <div
                            className="flex items-center gap-1.5 text-[11px] sm:text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2.5 py-1.5 rounded-md border border-amber-500/20 sm:w-fit cursor-pointer hover:bg-amber-500/20 transition-colors group animate-in fade-in zoom-in-95 duration-200"
                            onClick={() => setShowApiWarning(false)}
                        >
                            <Info className="w-3.5 h-3.5 shrink-0" />
                            <span className="leading-tight mr-1">
                                {t('dashboard.the_default_api_uses_a_free_tier_and_may_affect_quality_and_speed_a_custom_api_is_recommended')}
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
                        {batchState.isSubmitting ? t('dashboard.submitting') : t('dashboard.start_batch_translation')}
                    </Button>
                ) : (
                    <Button
                        size="lg"
                        onClick={handleStart}
                        disabled={!taskId || status === 'downloading' || status === 'starting_translation'}
                        className="w-full md:w-auto min-w-[200px] shadow-lg shadow-primary/20 text-lg py-6"
                    >
                        <Play className="mr-2 h-5 w-5 fill-current" />
                        {t('dashboard.start_translation')}
                    </Button>
                )}
            </div>
        </div>
    )
}
