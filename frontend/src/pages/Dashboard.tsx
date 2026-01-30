import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Search, ChevronRight, Upload } from "lucide-react"
import { useStore } from "@/store/useStore"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Label } from "@/components/ui/label"

export default function Dashboard() {
    const [arxivId, setArxivId] = useState("")
    const [isOpen, setIsOpen] = useState(false)
    const navigate = useNavigate()
    const { startArxivDownload, startTranslation } = useStore()

    const [sourceLang, setSourceLang] = useState("en")
    const [targetLang, setTargetLang] = useState("zh")
    const [isSubmitting, setIsSubmitting] = useState(false)

    const handleTranslate = async () => {
        if (!arxivId) return
        setIsSubmitting(true)

        // 立即跳转到处理页面，不等待API响应
        navigate("/processing")

        // 在后台执行下载和翻译
        try {
            await startArxivDownload(arxivId)
            await startTranslation({ source_language: sourceLang, target_language: targetLang })
        } catch (error) {
            console.error("Workflow failed", error)
            // 错误会通过 store 的状态和 toast 显示
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Hero Section */}
            <div className="text-center space-y-4 py-8">
                <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                    Translate ArXiv Papers Instantly
                </h1>
                <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                    Academic-grade translation with dual-model verification and LaTeX source preservation.
                </p>
            </div>

            <Card className="border-2 border-indigo-50 dark:border-indigo-900/20 shadow-lg">
                <CardHeader>
                    <CardTitle>New Translation Task</CardTitle>
                    <CardDescription>Enter an ArXiv ID to start.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* ArXiv ID Input */}
                    <div className="flex gap-4">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Enter ArXiv ID (e.g. 2401.12345)"
                                className="pl-9 h-12 text-lg"
                                value={arxivId}
                                onChange={(e) => setArxivId(e.target.value)}
                            />
                        </div>
                        <Button size="lg" className="h-12 px-8 bg-indigo-600 hover:bg-indigo-700 text-white" onClick={handleTranslate} disabled={isSubmitting}>
                            {isSubmitting ? "Initializing..." : "Translate Now"}
                        </Button>
                    </div>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-background px-2 text-muted-foreground">
                                Configuration
                            </span>
                        </div>
                    </div>

                    {/* Quick Config */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label>Source Language</Label>
                            <Select defaultValue="en" onValueChange={setSourceLang}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select Language" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="en">English (English)</SelectItem>
                                    <SelectItem value="zh">Chinese (简体中文)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Target Language</Label>
                            <Select defaultValue="zh" onValueChange={setTargetLang}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select Language" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="zh">Chinese (简体中文)</SelectItem>
                                    <SelectItem value="en">English (English)</SelectItem>
                                    <SelectItem value="jp">Japanese (日本語)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="space-y-2 border rounded-md p-4 bg-slate-50 dark:bg-slate-900">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold text-foreground">
                                Advanced Settings
                            </h4>
                            <CollapsibleTrigger asChild>
                                <Button variant="ghost" size="sm" className="w-9 p-0">
                                    <ChevronRight className={`h-4 w-4 transition-transform ${isOpen ? "rotate-90" : ""}`} />
                                    <span className="sr-only">Toggle</span>
                                </Button>
                            </CollapsibleTrigger>
                        </div>
                        <CollapsibleContent className="space-y-4 pt-4">
                            <div className="grid gap-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Translation Model</Label>
                                        <Select defaultValue="deepseek">
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="deepseek">DeepSeek-V3</SelectItem>
                                                <SelectItem value="gpt4">GPT-4o</SelectItem>
                                                <SelectItem value="claude">Claude 3.5 Sonnet</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>API Key (Optional)</Label>
                                        <Input type="password" placeholder="Use system default" />
                                    </div>
                                </div>

                                <Separator className="my-2" />

                                <div className="space-y-2">
                                    <Label>Glossary (Optional)</Label>
                                    <div className="flex gap-2">
                                        <Button variant="outline" className="w-full border-dashed">
                                            <Upload className="mr-2 h-4 w-4" /> Upload Terminology (.csv)
                                        </Button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>TeX Sources Directory (Optional)</Label>
                                        <Input placeholder="Auto-detected from ArXiv or Upload" disabled />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Output Directory (Optional)</Label>
                                        <Input placeholder="./outputs" />
                                    </div>
                                </div>
                            </div>
                        </CollapsibleContent>
                    </Collapsible>

                </CardContent>
            </Card>
        </div>
    )
}
