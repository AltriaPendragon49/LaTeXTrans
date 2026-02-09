import { Settings2, Info, Languages, BookText, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip'
import { useStore } from '@/store/useStore'
import type { TranslationMode, CompileStrategy } from '@/types/config'

// Custom Simple Switch Component since Radix Switch is not installed
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
            "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
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

// Language options
const LANGUAGES = [
    { code: 'en', label: 'English' },
    { code: 'zh', label: '中文 (Chinese)' },
    { code: 'ja', label: '日本語 (Japanese)' },
    { code: 'ko', label: '한국어 (Korean)' },
    { code: 'de', label: 'Deutsch (German)' },
    { code: 'fr', label: 'Français (French)' },
    { code: 'es', label: 'Español (Spanish)' },
    { code: 'ru', label: 'Русский (Russian)' },
]

export const AdvancedConfig = () => {
    const { config, setConfig, setAdvancedConfig, hasSystemApiKey } = useStore()
    const { advanced_config, source_language, target_language } = config

    // Local handlers
    const updateConfig = (key: keyof typeof advanced_config, value: unknown) => {
        setAdvancedConfig({ [key]: value })
    }

    return (
        <div className="space-y-6 p-4 border rounded-xl bg-card/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 pb-2 border-b border-border/50">
                <Settings2 className="w-5 h-5 text-primary" />
                <h3 className="font-medium text-lg">高级配置</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* Language Settings Section */}
                <div className="md:col-span-2 space-y-4">
                    <div className="flex items-center gap-2">
                        <Languages className="w-4 h-4 text-muted-foreground" />
                        <h4 className="font-medium text-sm text-muted-foreground">语言设置</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Source Language */}
                        <div className="space-y-2">
                            <Label>源语言 (Source)</Label>
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

                        {/* Target Language */}
                        <div className="space-y-2">
                            <Label>目标语言 (Target)</Label>
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

                {/* Translation Mode */}
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
                            <SelectItem value="quick_scan">文献快速筛查 (仅摘要+结论)</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Compilation Strategy */}
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

                {/* Translation Model Input */}
                <div className="space-y-2 md:col-span-2">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="translation-model">翻译模型</Label>
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger>
                                    <Info className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                    <p>手动输入模型名称，如 gpt-4o, deepseek-chat, claude-3-opus 等。不同 API 中转的模型名称可能不同，请参考您的 API 提供商文档。</p>
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    </div>
                    <Input
                        id="translation-model"
                        placeholder="例如: deepseek-chat, gpt-4o, claude-3-sonnet..."
                        value={advanced_config.translation_model}
                        onChange={(e) => updateConfig('translation_model', e.target.value)}
                        className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground">
                        提示：不同 API 中转服务的模型名称可能不同，如报错请检查名称是否正确
                    </p>
                </div>

                {/* Toggles */}
                <div className="space-y-4 md:col-span-2">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30 flex-1">
                            <div className="space-y-0.5">
                                <Label className="text-base">验证代理</Label>
                                <p className="text-xs text-muted-foreground">
                                    使用双模型校验提高准确性
                                </p>
                            </div>
                            <SimpleSwitch
                                checked={advanced_config.enable_verification}
                                onCheckedChange={(v) => updateConfig('enable_verification', v)}
                            />
                        </div>

                        <div className="flex items-center justify-between space-x-4 p-3 rounded-lg border bg-card/30 flex-1">
                            <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <BookText className="w-4 h-4 text-muted-foreground" />
                                    <Label className="text-base">生成术语表</Label>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    输出原文/译文术语对照表
                                </p>
                            </div>
                            <SimpleSwitch
                                checked={advanced_config.generate_terminology_table}
                                onCheckedChange={(v) => updateConfig('generate_terminology_table', v)}
                            />
                        </div>
                    </div>
                </div>

                {/* API Configuration */}
                <div className="md:col-span-2 space-y-4 pt-2 border-t border-border/50">
                    <div className="flex items-center justify-between">
                        <h4 className="font-medium text-sm text-muted-foreground">API 设置</h4>
                    </div>

                    <div className="flex items-center justify-between space-x-2">
                        <Label>使用作者默认 API</Label>
                        <SimpleSwitch
                            checked={advanced_config.use_author_api}
                            onCheckedChange={(v) => updateConfig('use_author_api', v)}
                        />
                    </div>

                    {!advanced_config.use_author_api && (
                        <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                            <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2 rounded-md">
                                ⓘ 如果您已在「系统设置」中配置了 API，此处无需重复填写，系统将自动使用保存的配置
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="base-url">自定义 Base URL（可选）</Label>
                                    <Input
                                        id="base-url"
                                        placeholder="https://api.example.com/v1"
                                        value={advanced_config.custom_base_url || ''}
                                        onChange={(e) => updateConfig('custom_base_url', e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Label htmlFor="api-key">自定义 API Key（可选）</Label>
                                        {hasSystemApiKey && (
                                            <div className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
                                                <CheckCircle2 className="w-3.5 h-3.5" />
                                                <span>已在系统设置中配置</span>
                                            </div>
                                        )}
                                    </div>
                                    <Input
                                        id="api-key"
                                        type="password"
                                        placeholder={hasSystemApiKey ? "留空将使用系统设置中的密钥" : "请输入 API Key (sk-...)"}
                                        value={advanced_config.custom_api_key || ''}
                                        onChange={(e) => updateConfig('custom_api_key', e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
