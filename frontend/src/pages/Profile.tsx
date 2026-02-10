/**
 * Profile Page
 * 
 * Simple user profile page showing email and logout option.
 * Redirects to login if not authenticated.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, User, Mail, LogOut, LogIn, Settings } from 'lucide-react'
import { toast } from 'sonner'

export default function ProfilePage() {
    const navigate = useNavigate()
    const { user, isAuthenticated, loading, signOut } = useAuth()
    const [isLoggingOut, setIsLoggingOut] = useState(false)

    // Handle logout
    const handleLogout = async () => {
        setIsLoggingOut(true)
        await signOut()
        toast.success('已退出登录')
        navigate('/')
        // Note: setIsLoggingOut(false) 不需要，因为会导航离开页面
    }

    // Loading state
    if (loading) {
        return (
            <div className="container mx-auto max-w-md p-6 flex flex-col items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    // Not authenticated
    if (!isAuthenticated) {
        return (
            <div className="container mx-auto max-w-md p-6 space-y-6 animate-in fade-in duration-500">
                <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                    <CardContent className="pt-6 space-y-4">
                        <div className="text-center py-8 space-y-4">
                            <div className="mx-auto p-4 rounded-full bg-muted/50 w-fit">
                                <LogIn className="h-8 w-8 text-muted-foreground" />
                            </div>
                            <div className="space-y-2">
                                <p className="text-lg font-medium">尚未登录</p>
                                <p className="text-muted-foreground">
                                    登录以管理您的账户
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
        <div className="container mx-auto max-w-md p-6 space-y-6 animate-in fade-in duration-500">
            <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
                <CardHeader className="text-center pb-2">
                    <div className="mx-auto p-4 rounded-full bg-primary/10 text-primary w-fit mb-2">
                        <User className="h-10 w-10" />
                    </div>
                    <CardTitle className="text-2xl">个人资料</CardTitle>
                    <CardDescription>管理您的账户信息</CardDescription>
                </CardHeader>

                <CardContent className="space-y-6">
                    {/* User info */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                            <Mail className="h-5 w-5 text-muted-foreground" />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-muted-foreground">邮箱地址</p>
                                <p className="font-medium truncate">{user?.email}</p>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="space-y-2 pt-4">
                        <Button
                            variant="outline"
                            className="w-full justify-start"
                            onClick={() => navigate('/settings')}
                        >
                            <Settings className="mr-2 h-4 w-4" />
                            系统设置
                        </Button>

                        <Button
                            variant="destructive"
                            className="w-full justify-start transition-all duration-200 active:scale-[0.98]"
                            onClick={handleLogout}
                            disabled={isLoggingOut}
                        >
                            {isLoggingOut ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    正在退出...
                                </>
                            ) : (
                                <>
                                    <LogOut className="mr-2 h-4 w-4" />
                                    退出登录
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
