import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '@/store/useStore'
import { AdvancedConfig } from '@/components/AdvancedConfig'
import { DropZone } from '@/components/DropZone'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { ChevronDown, ChevronRight, Play, FileText, Download, RefreshCw } from 'lucide-react'

export default function Dashboard() {
    const navigate = useNavigate()
    const {
        taskId, status, config,
        downloadProgress, downloadStage, isDownloading,
        startArxivDownload, startTranslation
    } = useStore()

    const [activeTab, setActiveTab] = useState('arxiv')
    const [isConfigOpen, setIsConfigOpen] = useState(false)
    const [localArxivId, setLocalArxivId] = useState('')
    // const [isDownloading, setIsDownloading] = useState(false) // Removed local state in favor of store state

    // Handle ArXiv Load
    const handleLoadArxiv = async () => {
        if (!localArxivId.trim()) return
        // setIsDownloading(true) // Handled by store
        try {
            await startArxivDownload(localArxivId)
            // Success handled in store
        } catch (e) {
            // Error handled in store
        } finally {
            // setIsDownloading(false) // Handled by store
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
                <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
                    <TabsTrigger value="arxiv">ArXiv ID</TabsTrigger>
                    <TabsTrigger value="upload">Local Upload</TabsTrigger>
                </TabsList>

                <Card className="border-border/50 bg-card/50 backdrop-blur-sm shadow-sm">
                    <CardHeader>
                        <CardTitle>{activeTab === 'arxiv' ? 'ArXiv Paper' : 'File Upload'}</CardTitle>
                        <CardDescription>
                            {activeTab === 'arxiv'
                                ? 'Enter the ArXiv ID (e.g., 2310.xxxxx) to download source.'
                                : 'Upload your LaTeX project as a ZIP/RAR archive.'}
                        </CardDescription>
                    </CardHeader>
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
                                    disabled={!localArxivId || isDownloading || (status === 'processing')}
                                >
                                    {isDownloading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                                    Load Source
                                </Button>
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

            <div className="flex justify-end pt-4 pb-12">
                <Button
                    size="lg"
                    onClick={handleStart}
                    disabled={!taskId || status === 'downloading' || status === 'starting_translation'}
                    className="w-full md:w-auto min-w-[200px] shadow-lg shadow-primary/20 text-lg py-6"
                >
                    <Play className="mr-2 h-5 w-5 fill-current" />
                    Start Translation
                </Button>
            </div>
        </div>
    )
}
