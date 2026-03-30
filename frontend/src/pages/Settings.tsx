import { useTranslation } from 'react-i18next'
import { LanguageSelector } from "@/components/LanguageSelector"
import { ThemeToggle } from "@/components/ThemeToggle"
import { Globe, Moon } from "lucide-react"

export default function SettingsPage() {
    const { t } = useTranslation()

    return (
        <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto py-8 px-4">
            <header className="mb-8 lg:mb-10">
                <h1 className="mb-2 text-3xl font-bold tracking-tighter text-on-surface lg:text-4xl">
                    {t("settings.title", "Settings")}
                </h1>
                <p className="max-w-xl text-sm text-tertiary lg:text-base">
                    System preferences including language and appearance.
                </p>
            </header>

            <div className="bg-surface-container-lowest border border-outline-variant/10 rounded-2xl shadow-sm overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-outline-variant/5 flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg text-primary">
                        <Globe className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="text-base font-bold text-on-surface">Language</h3>
                        <p className="text-xs text-tertiary">Select your preferred interface language</p>
                    </div>
                </div>
                <div className="p-6">
                    <LanguageSelector />
                </div>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant/10 rounded-2xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-outline-variant/5 flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg text-primary">
                        <Moon className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="text-base font-bold text-on-surface">Appearance</h3>
                        <p className="text-xs text-tertiary">Customize the theme of your application</p>
                    </div>
                </div>
                <div className="p-6 flex items-center">
                    <ThemeToggle />
                </div>
            </div>
        </div>
    )
}
