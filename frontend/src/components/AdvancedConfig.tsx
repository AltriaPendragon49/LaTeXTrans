import { Settings2, Info, Languages, BookText, CheckCircle2, Palette, Mail } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useStore } from '@/store/useStore'
import { useAuth } from '@/contexts/AuthContext'
import type { TranslationMode, CompileStrategy, FormattingConfig } from '@/types/config'
import { FormattingPanel } from '@/components/FormattingPanel'

interface SimpleSwitchProps {
    checked: boolean
    onCheckedChange: (checked: boolean) => void
    id?: string
}

const SimpleSwitch = ({ checked, onCheckedChange, id }: SimpleSwitchProps) => (
    <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
            "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            checked ? "bg-primary" : "bg-input"
        )}
    >
        <span
            className={cn(
                "pointer-events-none block h-5 w-5 rounded-full bg-background ring-0 shadow-lg transition-transform",
                checked ? "translate-x-5" : "translate-x-0"
            )}
        />
    </button>
)

const LANGUAGES = [
    { code: 'en', label: '英语' },
    { code: 'zh', label: '中文' },
    { code: 'ja', label: '日语' },
    { code: 'ko', label: '韩语' },
    { code: 'de', label: '德语' },
    { code: 'fr', label: '法语' },
    { code: 'es', label: '西班牙语' },
    { code: 'ru', label: '俄语' },
]

export const AdvancedConfig = () => {
    const { config, setConfig, setAdvancedConfig, hasSystemApiKey } = useStore()
    const { user } = useAuth()
    const { advanced_config, source_language, target_language } = config

    const updateConfig = (key: keyof typeof advanced_config, value: unknown) => {
        setAdvancedConfig({ [key]: value })
    }

    const updateFormatting = (patch: Partial<FormattingConfig>) => {
        setAdvancedConfig({
            formatting: { ...(advanced_config.formatting ?? {}), ...patch }
        })
    }

    return (
        <div className="space-y-6 p-4 border rounded-xl bg-card/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 pb-2 border-b border-border/50">
                <Settings2 className="w-5 h-5 text-primary" />
                <h3 className="font-medium text-lg">高级配置</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2 space-y-4">
                    <div className="flex items-center gap-2">
                        <Languages className="w-4 h-4 text-muted-foreground" />
                        <h4 className="font-medium text-sm text-muted-foreground">语言设置</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>源语言</Label>
                            <Select
                                value={source_language}
                                onValueChange={(value) => setConfig({ source_language: value })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="选择源语言" />
                                </SelectTrigger>
                                <SelectContent>
                                    {LANGUAGES.map(lang => (
                                        <SelectItem key={lang.code} value={lang.code}>
                                            {lang.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>目标语言</Label>
                            <Select
                                value={target_language}
                                onValueChange={(value) => setConfig({ target_language: value })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="选择目标语言" />
                                </SelectTrigger>
                                <SelectContent>
                                    {LANGUAGES.map(lang => (
                                        <SelectItem key={lang.code} value={lang.code}>
                                            {lang.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <Label>翻译模式</Label>
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger>
                                    <Info className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
                                </TooltipTrigger>
                                <TooltipContent>
                                    <p>选择文档翻译方式</p>
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    </div>
                    <Select
                        value={advanced_config.translation_mode}
                        onValueChange={(value: TranslationMode) => updateConfig('translation_mode', value)}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder="选择翻译模式" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="full">全文翻译</SelectItem>
                            <SelectItem value="quick_scan">快速筛查（摘要+结论）</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label>编译策略</Label>
                    <Select
                        value={advanced_config.compile_strategy}
                        onValueChange={(value: CompileStrategy) => updateConfig('compile_strategy', value)}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder="选择编译策略" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="auto">自动检测</SelectItem>
                            <SelectItem value="pdflatex">PDFLaTeX</SelectItem>
                            <SelectItem value="xelatex">XeLaTeX</SelectItem>
                            <SelectItem value="lualatex">LuaLaTeX</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="translation-model">翻译模型</Label>
                    <Input
                        id="translation-model"
                        placeholder="例如：deepseek-chat、gpt-4o、claude-3-sonnet"
                        value={advanced_config.translation_model}
                        onChange={(e) => updateConfig('translation_model', e.target.value)}
                        className="font-mono"
                        disabled={advanced_config.use_author_api}
                    />
                    {advanced_config.use_author_api ? (
                        <p className="text-xs text-amber-600 dark:text-amber-400">
                            使用默认 API 时，模型由系统控制。
                        </p>
                    ) : (
                        <p className="text-xs text-muted-foreground">
                            不同 API 服务的模型名可能不同，请按服务商文档填写。
                        </p>
                    )}
                </div>

                <div className="space-y-4 md:col-span-2">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30 flex-1">
                            <div className="space-y-0.5">
                                <Label className="text-base">使用默认 API</Label>
                                <p className="text-xs text-muted-foreground">关闭后可填写自定义 API 端点与密钥</p>
                            </div>
                            <SimpleSwitch
                                checked={advanced_config.use_author_api}
                                onCheckedChange={(v) => updateConfig('use_author_api', v)}
                            />
                        </div>

                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30 flex-1">
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <BookText className="w-4 h-4 text-muted-foreground" />
                                    <Label className="text-base">生成术语表</Label>
                                </div>
                                <p className="text-xs text-muted-foreground">输出原文/译文术语对照表</p>
                            </div>
                            <SimpleSwitch
                                checked={advanced_config.generate_terminology_table}
                                onCheckedChange={(v) => updateConfig('generate_terminology_table', v)}
                            />
                        </div>
                    </div>

                    {user && (
                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30">
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <Mail className="w-4 h-4 text-muted-foreground" />
                                    <Label className="text-base">邮件通知</Label>
                                </div>
                                <p className="text-xs text-muted-foreground">任务完成或失败时发送通知邮件</p>
                            </div>
                            <SimpleSwitch
                                id="email-notification"
                                checked={advanced_config.email_notification ?? false}
                                onCheckedChange={(v) => updateConfig('email_notification', v)}
                            />
                        </div>
                    )}

                    {!advanced_config.use_author_api && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                            <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2 rounded-md">
                                若您已在“系统设置”保存 API 配置，这里可以留空，系统会自动复用。
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="base-url">自定义基础地址（可选）</Label>
                                    <Input
                                        id="base-url"
                                        placeholder="https://api.example.com/v1"
                                        value={advanced_config.custom_base_url || ''}
                                        onChange={(e) => updateConfig('custom_base_url', e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Label htmlFor="api-key">自定义密钥（可选）</Label>
                                        {hasSystemApiKey && (
                                            <div className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
                                                <CheckCircle2 className="w-3.5 h-3.5" />
                                                <span>系统设置中已保存</span>
                                            </div>
                                        )}
                                    </div>
                                    <Input
                                        id="api-key"
                                        type="password"
                                        placeholder={hasSystemApiKey ? "留空则使用系统已保存密钥" : "请输入 API 密钥（sk-...）"}
                                        value={advanced_config.custom_api_key || ''}
                                        onChange={(e) => updateConfig('custom_api_key', e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="space-y-3 md:col-span-2 pt-2 border-t border-border/50">
                <div className="flex items-center gap-2">
                    <Palette className="w-4 h-4 text-primary" />
                    <h4 className="text-sm font-medium">排版配置</h4>
                    <span className="text-xs text-muted-foreground ml-1">（可选，注入 LaTeX 导言区）</span>
                </div>
                <FormattingPanel
                    value={advanced_config.formatting ?? {}}
                    onChange={updateFormatting}
                    targetLanguage={target_language}
                />
            </div>
        </div>
    )
}
