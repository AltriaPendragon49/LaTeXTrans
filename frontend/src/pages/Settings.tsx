/**
 * Settings Page
 * 
 * User settings management for translation preferences.
 * Requires authentication - shows prompt for guests.
 */

import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Settings, LogIn, Save, CheckCircle2 } from 'lucide-react'
import { toast } from 'sonner'
import { FormattingPanel } from '@/components/FormattingPanel'
import type { FormattingConfig } from '@/types/config'

interface UserSettings {
    default_source_language: string
    default_target_language: string
    translation_mode: string
    compile_strategy: string
    translation_model: string | null
    enable_verification: boolean
    generate_glossary: boolean
    use_author_api: boolean
    custom_base_url: string | null
    has_custom_api_key: boolean
    default_formatting: FormattingConfig | null
}

const defaultSettings: UserSettings = {
    default_source_language: 'en',
    default_target_language: 'zh',
    translation_mode: 'full',
    compile_strategy: 'auto',
    translation_model: null,
    enable_verification: true,
    generate_glossary: true,
    use_author_api: true,
    custom_base_url: null,
    has_custom_api_key: false,
    default_formatting: null,
}

export default function SettingsPage() {
    const navigate = useNavigate()
    const { isAuthenticated, loading: authLoading } = useAuth()

    const [settings, setSettings] = useState<UserSettings>(defaultSettings)
    const [customApiKey, setCustomApiKey] = useState('')
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Fetch settings
    const fetchSettings = async () => {
        setLoading(true)
        setError(null)

        try {
            const { getAccessToken } = await import('@/lib/supabase')
            const token = await getAccessToken()

            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/settings`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                }
            )

            if (!response.ok) {
                throw new Error('Failed to fetch settings')
            }

            const data: UserSettings = await response.json()
            setSettings(data)
        } catch (err) {
            setError(err instanceof Error ? err.message : '获取设置失败')
        } finally {
            setLoading(false)
        }
    }

    // Save settings
    const handleSave = async (e: FormEvent) => {
        e.preventDefault()
        setSaving(true)
        setError(null)

        // Validation: if not using author API, require base url and api key
        if (!settings.use_author_api) {
            if (!settings.custom_base_url || settings.custom_base_url.trim() === '') {
                setError('关闭作者默认 API 时，必须填写自定义 API 端点')
                setSaving(false)
                return
            }
            if (!settings.has_custom_api_key && !customApiKey) {
                setError('关闭作者默认 API 时，必须填写 API Key')
                setSaving(false)
                return
            }
        }

        try {
            const { getAccessToken } = await import('@/lib/supabase')
            const token = await getAccessToken()

            const updateData: Record<string, unknown> = {
                default_source_language: settings.default_source_language,
                default_target_language: settings.default_target_language,
                translation_mode: settings.translation_mode,
                compile_strategy: settings.compile_strategy,
                translation_model: settings.translation_model,
                enable_verification: settings.enable_verification,
                generate_glossary: settings.generate_glossary,
                use_author_api: settings.use_author_api,
                custom_base_url: settings.custom_base_url,
            }

            // Only include API key if user entered a new one
            if (customApiKey) {
                updateData.custom_api_key = customApiKey
            }

            // Include formatting if user has configured it (null clears it)
            if (settings.default_formatting !== undefined) {
                updateData.default_formatting = settings.default_formatting
            }

            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/settings`,
                {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updateData),
                }
            )

            if (!response.ok) {
                throw new Error('Failed to save settings')
            }

            const data: UserSettings = await response.json()
            setSettings(data)
            setCustomApiKey('') // Clear the input after save

            // Invalidate cached settings in store so Dashboard will reload
            const { useStore } = await import('@/store/useStore')
            useStore.getState().invalidateUserSettings()

            toast.success('设置已保存')
        } catch (err) {
            setError(err instanceof Error ? err.message : '保存设置失败')
            toast.error('保存失败')
        } finally {
            setSaving(false)
        }
    }

    // Initial load
    useEffect(() => {
        if (isAuthenticated) {
            fetchSettings()
        }
    }, [isAuthenticated])

    // Loading state
    if (authLoading) {
        return (
            <div className="container mx-auto max-w-2xl p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    // Not authenticated
    if (!isAuthenticated) {
        return (
            <div className="container mx-auto max-w-2xl p-6 space-y-6 animate-in fade-in duration-500">
                <div className="space-y-2">
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Settings className="h-8 w-8" />
                        系统设置
                    </h1>
                </div>

                <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="pt-6 space-y-4">
                        <div className="text-center py-8 space-y-4">
                            <div className="mx-auto p-4 rounded-full bg-muted/50 w-fit">
                                <LogIn className="h-8 w-8 text-muted-foreground" />
                            </div>
                            <div className="space-y-2">
                                <p className="text-lg font-medium">登录以保存设置</p>
                                <p className="text-muted-foreground">
                                    登录后您可以保存默认翻译配置，下次翻译时自动应用
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

    return (
        <div className="container mx-auto max-w-2xl p-6 space-y-6 animate-in fade-in duration-500">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    <Settings className="h-8 w-8" />
                    系统设置
                </h1>
                <p className="text-muted-foreground">
                    配置默认翻译选项，创建新翻译时自动应用
                </p>
                <p className="text-xs text-amber-600 dark:text-amber-400">
                    提示：保存后返回首页或刷新页面生效
                </p>
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {loading ? (
                <div className="flex justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <form onSubmit={handleSave} className="space-y-6">
                    {/* Language Settings */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">语言设置</CardTitle>
                            <CardDescription>设置默认的源语言和目标语言</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="source_language">源语言</Label>
                                    <Select
                                        value={settings.default_source_language}
                                        onValueChange={(v) => setSettings(s => ({ ...s, default_source_language: v }))}
                                    >
                                        <SelectTrigger id="source_language">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="en">English</SelectItem>
                                            <SelectItem value="zh">中文</SelectItem>
                                            <SelectItem value="ja">日本語</SelectItem>
                                            <SelectItem value="ko">한국어</SelectItem>
                                            <SelectItem value="de">Deutsch</SelectItem>
                                            <SelectItem value="fr">Français</SelectItem>
                                            <SelectItem value="es">Español</SelectItem>
                                            <SelectItem value="ru">Русский</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="target_language">目标语言</Label>
                                    <Select
                                        value={settings.default_target_language}
                                        onValueChange={(v) => setSettings(s => ({ ...s, default_target_language: v }))}
                                    >
                                        <SelectTrigger id="target_language">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="zh">中文</SelectItem>
                                            <SelectItem value="en">English</SelectItem>
                                            <SelectItem value="ja">日本語</SelectItem>
                                            <SelectItem value="ko">한국어</SelectItem>
                                            <SelectItem value="de">Deutsch</SelectItem>
                                            <SelectItem value="fr">Français</SelectItem>
                                            <SelectItem value="es">Español</SelectItem>
                                            <SelectItem value="ru">Русский</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Translation Settings */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">翻译设置</CardTitle>
                            <CardDescription>配置翻译模式和编译选项</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="translation_mode">翻译模式</Label>
                                <Select
                                    value={settings.translation_mode}
                                    onValueChange={(v) => setSettings(s => ({ ...s, translation_mode: v }))}
                                >
                                    <SelectTrigger id="translation_mode">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="full">全文翻译</SelectItem>
                                        <SelectItem value="quick_scan">快速筛查</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="compile_strategy">编译策略</Label>
                                <Select
                                    value={settings.compile_strategy}
                                    onValueChange={(v) => setSettings(s => ({ ...s, compile_strategy: v }))}
                                >
                                    <SelectTrigger id="compile_strategy">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="auto">自动检测</SelectItem>
                                        <SelectItem value="pdflatex">PDFLaTeX</SelectItem>
                                        <SelectItem value="xelatex">XeLaTeX</SelectItem>
                                        <SelectItem value="lualatex">LuaLaTeX</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="translation_model">翻译模型</Label>
                                <Input
                                    id="translation_model"
                                    placeholder="留空使用系统默认"
                                    value={settings.translation_model || ''}
                                    onChange={(e) => setSettings(s => ({ ...s, translation_model: e.target.value || null }))}
                                    disabled={settings.use_author_api}
                                />
                                {settings.use_author_api && (
                                    <p className="text-xs text-amber-600 dark:text-amber-400">
                                        🔒 使用作者 API 时模型已锁定,无需配置
                                    </p>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Advanced Settings */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">高级设置</CardTitle>
                            <CardDescription>配置验证、术语表和 API 选项</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Enable Verification */}
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label htmlFor="enable_verification">验证代理</Label>
                                    <p className="text-xs text-muted-foreground">
                                        使用双模型验证提高翻译质量
                                    </p>
                                </div>
                                <Switch
                                    id="enable_verification"
                                    checked={settings.enable_verification}
                                    onCheckedChange={(checked) => setSettings(s => ({ ...s, enable_verification: checked }))}
                                />
                            </div>

                            {/* Generate Glossary */}
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label htmlFor="generate_glossary">生成术语表</Label>
                                    <p className="text-xs text-muted-foreground">
                                        翻译时生成术语对照表 (CSV)
                                    </p>
                                </div>
                                <Switch
                                    id="generate_glossary"
                                    checked={settings.generate_glossary}
                                    onCheckedChange={(checked) => setSettings(s => ({ ...s, generate_glossary: checked }))}
                                />
                            </div>

                            {/* Use Author API */}
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label htmlFor="use_author_api">使用作者默认 API</Label>
                                    <p className="text-xs text-muted-foreground">
                                        关闭后需要配置自定义 API 端点和密钥
                                    </p>
                                </div>
                                <Switch
                                    id="use_author_api"
                                    checked={settings.use_author_api}
                                    onCheckedChange={(checked) => setSettings(s => ({ ...s, use_author_api: checked }))}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Formatting Defaults */}
                    <Card className="border-border/50 bg-card/80">
                        <CardHeader>
                            <CardTitle className="text-lg">排版默认值</CardTitle>
                            <CardDescription>设置翻译输出的默认排版格式，优先级低于翻译时手动设置的值</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <FormattingPanel
                                value={settings.default_formatting ?? {}}
                                onChange={(patch) =>
                                    setSettings(s => ({
                                        ...s,
                                        default_formatting: { ...(s.default_formatting ?? {}), ...patch }
                                    }))
                                }
                                targetLanguage={settings.default_target_language}
                            />
                        </CardContent>
                    </Card>

                    {/* API Settings */}
                    {!settings.use_author_api && (
                        <Card className="border-border/50 bg-card/80 animate-in fade-in">
                            <CardHeader>
                                <CardTitle className="text-lg">自定义 API</CardTitle>
                                <CardDescription>使用自己的 API 端点和密钥</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="custom_base_url">API 端点</Label>
                                    <Input
                                        id="custom_base_url"
                                        placeholder="https://api.openai.com/v1"
                                        value={settings.custom_base_url || ''}
                                        onChange={(e) => setSettings(s => ({ ...s, custom_base_url: e.target.value || null }))}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="custom_api_key">
                                        API Key
                                        {settings.has_custom_api_key && (
                                            <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                                                <CheckCircle2 className="inline h-3 w-3 mr-1" />
                                                已设置
                                            </span>
                                        )}
                                    </Label>
                                    <Input
                                        id="custom_api_key"
                                        type="password"
                                        placeholder={settings.has_custom_api_key ? '输入新密钥以更新' : 'sk-...'}
                                        value={customApiKey}
                                        onChange={(e) => setCustomApiKey(e.target.value)}
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        API Key 将加密存储，不会返回给客户端
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Save Button */}
                    <div className="flex justify-end pt-4">
                        <Button type="submit" disabled={saving} className="min-w-[120px]">
                            {saving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    保存中...
                                </>
                            ) : (
                                <>
                                    <Save className="mr-2 h-4 w-4" />
                                    保存设置
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            )}
        </div>
    )
}
