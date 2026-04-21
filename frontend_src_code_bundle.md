# Frontend Source Bundle

Source root: D:\future\antigravity\LaTexTrans\frontend\src

## File Tree

```text
D:/future/antigravity/LaTexTrans/frontend/src
|-- App.tsx
|-- api-base.ts
|-- contexts
|   `-- AuthContext.tsx
|-- features
|   |-- admin-curation
|   |   |-- components
|   |   |   |-- AdminCurationTasksWorkspace.tsx
|   |   |   `-- AdminCurationWorkspace.tsx
|   |   |-- services
|   |   |   `-- admin-curation-api.ts
|   |   `-- utils
|   |       `-- admin-access.ts
|   |-- auth-shell
|   |   `-- components
|   |       |-- LoginPrompt.tsx
|   |       |-- LoginWorkspace.module.css
|   |       `-- LoginWorkspace.tsx
|   |-- community-conversation
|   |   |-- components
|   |   |   |-- CommunityConversationWorkspace.tsx
|   |   |   |-- ConversationComposer.tsx
|   |   |   |-- ConversationRail.tsx
|   |   |   `-- ConversationThread.tsx
|   |   |-- services
|   |   |   `-- community-conversation-api.ts
|   |   `-- utils
|   |       |-- conversation-records.ts
|   |       `-- conversation-runtime.ts
|   |-- community-paper
|   |   |-- components
|   |   |   |-- CommunityFeedSurface.tsx
|   |   |   |-- CommunitySubmitPanel.tsx
|   |   |   |-- PaperCard.tsx
|   |   |   |-- PaperCardSkeleton.tsx
|   |   |   |-- PaperDetailHeader.tsx
|   |   |   |-- PaperDetailScreen.tsx
|   |   |   |-- PaperDetailSkeleton.tsx
|   |   |   |-- PaperDetailStateBoundary.tsx
|   |   |   |-- PaperDetailWorkspace.tsx
|   |   |   |-- PaperFeedEmptyState.tsx
|   |   |   |-- PaperFeedErrorState.tsx
|   |   |   |-- PaperPreviewReader.tsx
|   |   |   `-- PaperStatusBadge.tsx
|   |   |-- hooks
|   |   |   |-- use-paper-detail.ts
|   |   |   `-- useCommunityPapers.ts
|   |   |-- services
|   |   |   `-- community-paper-api.ts
|   |   `-- utils
|   |       `-- paper-detail-mode-resolution.ts
|   |-- translation-workflow
|   |   |-- components
|   |   |   |-- AdvancedConfig.tsx
|   |   |   |-- BatchTranslation.tsx
|   |   |   |-- ComparisonWorkbench.tsx
|   |   |   |-- DropZone.tsx
|   |   |   |-- FormattingPanel.tsx
|   |   |   |-- ProcessingLogViewer.tsx
|   |   |   |-- ProcessingWorkspace.tsx
|   |   |   |-- TerminologyTable.tsx
|   |   |   `-- TranslationWorkspace.tsx
|   |   |-- hooks
|   |   |   |-- useTranslationConfig.ts
|   |   |   `-- useTranslationTask.ts
|   |   `-- store
|   |       `-- useTranslationStore.ts
|   `-- user-workspace
|       `-- components
|           |-- GlossaryWorkspace.tsx
|           |-- HistoryWorkspace.tsx
|           |-- ProfileWorkspace.tsx
|           |-- TranslationSettingsWorkspace.tsx
|           `-- WorkspaceAccountMenu.tsx
|-- i18n
|   |-- config.ts
|   |-- formatting-copy.ts
|   |-- task-copy.ts
|   `-- ui-text.ts
|-- i18n.ts
|-- index.css
|-- layout
|   `-- AppSidebar.tsx
|-- layout.tsx
|-- lib
|   |-- api.ts
|   |-- community-agent-conversations.ts
|   |-- community-api.ts
|   |-- local-auth.ts
|   |-- network-retry.ts
|   |-- paper-preview-enhancer.ts
|   |-- paper-reader-html.ts
|   `-- utils.ts
|-- main.tsx
|-- pages
|   |-- community-admin-curation
|   |   `-- index.tsx
|   |-- community-admin-curation-tasks
|   |   `-- index.tsx
|   |-- community-conversation
|   |   `-- index.tsx
|   |-- home
|   |   |-- components
|   |   |   `-- HomeFeedSection.tsx
|   |   `-- index.tsx
|   |-- login
|   |   `-- index.tsx
|   |-- paper-detail
|   |   `-- index.tsx
|   |-- preview
|   |   `-- index.tsx
|   |-- processing
|   |   `-- index.tsx
|   |-- profile
|   |   `-- index.tsx
|   |-- tools-hub
|   |   `-- index.tsx
|   |-- translate
|   |   `-- index.tsx
|   |-- workspace-glossary
|   |   `-- index.tsx
|   |-- workspace-history
|   |   `-- index.tsx
|   `-- workspace-settings
|       `-- index.tsx
|-- styles
|   `-- tokens.css
|-- theme
|   `-- theme-provider.tsx
|-- types
|   |-- community.ts
|   |-- config.ts
|   `-- katex-auto-render.d.ts
`-- ui
    |-- button
    |   `-- Button.tsx
    |-- card
    |   `-- Card.tsx
    |-- chat-bubble
    |   `-- ChatBubble.tsx
    |-- composer-shell
    |   `-- ComposerShell.tsx
    |-- data-table
    |   `-- DataTable.tsx
    |-- disclosure-card
    |   `-- DisclosureCard.tsx
    |-- filter-toolbar
    |   `-- FilterToolbar.tsx
    |-- form-field-shell
    |   `-- FormFieldShell.tsx
    |-- info-tile
    |   `-- InfoTile.tsx
    |-- input
    |   |-- Input.tsx
    |   `-- Textarea.tsx
    |-- interactive-card
    |   `-- InteractiveCard.tsx
    |-- language-selector
    |   `-- LanguageSelector.tsx
    |-- loading-state
    |   `-- LoadingState.tsx
    |-- notice-banner
    |   `-- NoticeBanner.tsx
    |-- page-intro
    |   `-- PageIntro.tsx
    |-- panel-shell
    |   `-- PanelShell.tsx
    |-- pill
    |   `-- Pill.tsx
    |-- primitives
    |   |-- alert-dialog.tsx
    |   |-- badge.tsx
    |   |-- checkbox.tsx
    |   |-- collapsible.tsx
    |   |-- label.tsx
    |   |-- popover.tsx
    |   |-- progress.tsx
    |   |-- resizable.tsx
    |   |-- scroll-area.tsx
    |   |-- select.tsx
    |   |-- separator.tsx
    |   |-- sheet.tsx
    |   |-- skeleton.tsx
    |   |-- sonner.tsx
    |   |-- switch.tsx
    |   |-- tabs.tsx
    |   |-- toggle-group.tsx
    |   |-- toggle.tsx
    |   `-- tooltip.tsx
    |-- record-row
    |   `-- RecordRow.tsx
    |-- search-bar
    |   `-- SearchBar.tsx
    |-- section-card
    |   `-- SectionCard.tsx
    |-- section-heading
    |   `-- SectionHeading.tsx
    |-- segmented-control
    |   `-- SegmentedControl.tsx
    |-- sidebar-shell
    |   |-- SidebarBrandButton.tsx
    |   |-- SidebarNavItem.tsx
    |   |-- SidebarProfileButton.tsx
    |   |-- SidebarShell.tsx
    |   `-- SidebarUtilityPanel.tsx
    |-- state-panel
    |   `-- StatePanel.tsx
    |-- status-badge
    |   `-- StatusBadge.tsx
    |-- tabs
    |   `-- EditorialTabs.tsx
    |-- theme-toggle
    |   `-- ThemeToggle.tsx
    |-- toggle-switch
    |   `-- ToggleSwitch.tsx
    |-- upload-card
    |   |-- UploadCard.tsx
    |   `-- UploadDropSurface.tsx
    `-- workflow-stepper
        `-- WorkflowStepper.tsx
```

## File: D:\future\antigravity\LaTexTrans\frontend\src\api-base.ts
Relative path: api-base.ts

```ts
const REQUIRED_ENV_NAME = "VITE_API_BASE_URL"
const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>
const LOCAL_DEV_API_BASE_URL = "http://127.0.0.1:9001"
const HOSTED_API_BASE_URL = "https://api.latextrans.online"
const PAPER_PREVIEW_ENV_NAME = "VITE_PAPER_PREVIEW_API_BASE_URL"
const TRANSLATED_HTML_READER_ENV_NAME = "VITE_ENABLE_TRANSLATED_HTML_READER"
const PRODUCTION_FRONTEND_HOSTNAME = "latextrans.niutrans.com"
const PRODUCTION_PAPER_PREVIEW_API_BASE_URL = HOSTED_API_BASE_URL

function normalizeBaseUrl(value: string | undefined): string | null {
  if (!value || !String(value).trim()) {
    return null
  }
  const normalized = String(value).trim().replace(/\/+$/, "")
  return normalized === "/" ? "" : normalized
}

function isLocalBrowserHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost"
}

function isBrowserEnvironment(): boolean {
  return typeof window !== "undefined"
}

function isPrimaryProductionFrontend(): boolean {
  return isBrowserEnvironment() && window.location.hostname === PRODUCTION_FRONTEND_HOSTNAME
}

export function getApiBaseUrl(): string {
  const normalized = normalizeBaseUrl(viteEnv.VITE_API_BASE_URL)
  if (normalized === null) {
    if (isBrowserEnvironment() && isLocalBrowserHost(window.location.hostname)) {
      return HOSTED_API_BASE_URL
    }
    if (typeof process !== "undefined") {
      return LOCAL_DEV_API_BASE_URL
    }
    if (isBrowserEnvironment()) {
      return ""
    }
    throw new Error(
      `Missing required env ${REQUIRED_ENV_NAME}. ` +
        `Set it in frontend/.env, .env.development, or .env.production before starting/building frontend.`,
    )
  }
  return normalized
}

export const API_BASE_URL = getApiBaseUrl()

export function getPaperPreviewApiBaseUrl(): string {
  const configured = normalizeBaseUrl(viteEnv[PAPER_PREVIEW_ENV_NAME])
  if (configured !== null) {
    return configured
  }
  if (isPrimaryProductionFrontend()) {
    return PRODUCTION_PAPER_PREVIEW_API_BASE_URL
  }
  return getApiBaseUrl()
}

export const PAPER_PREVIEW_API_BASE_URL = getPaperPreviewApiBaseUrl()

export function isTranslatedHtmlReaderEnabled(): boolean {
  const rawValue = normalizeBaseUrl(viteEnv[TRANSLATED_HTML_READER_ENV_NAME])
  if (rawValue === null) {
    return !isPrimaryProductionFrontend()
  }
  return !["0", "false", "no", "off"].includes(rawValue.toLowerCase())
}

export const ENABLE_TRANSLATED_HTML_READER = isTranslatedHtmlReaderEnabled()

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\App.tsx
Relative path: App.tsx

```tsx
import { lazy, Suspense, type ReactNode } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ThemeProvider } from "@/theme/theme-provider"
import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { LoadingState } from "@/ui/loading-state/LoadingState"

import { AuthProvider } from "./contexts/AuthContext"

const Layout = lazy(() => import("./layout"))
const HomePage = lazy(() => import("./pages/home"))
const CommunityAdminCurationPage = lazy(() => import("./pages/community-admin-curation"))
const CommunityAdminCurationTasksPage = lazy(() => import("./pages/community-admin-curation-tasks"))
const CommunityConversationPage = lazy(() => import("./pages/community-conversation"))
const ProcessingPage = lazy(() => import("./pages/processing"))
const Login = lazy(() => import("./pages/login"))
const ProfilePage = lazy(() => import("./pages/profile"))
const PaperDetailPage = lazy(() => import("@/pages/paper-detail"))
const PreviewPage = lazy(() => import("@/pages/preview"))
const TranslatePage = lazy(() => import("./pages/translate"))
const WorkspaceHistoryPage = lazy(() => import("./pages/workspace-history"))
const WorkspaceSettingsPage = lazy(() => import("./pages/workspace-settings"))
const WorkspaceGlossaryPage = lazy(() => import("./pages/workspace-glossary"))
const ToolsHubPage = lazy(() => import("./pages/tools-hub"))

function RouteLoading() {
  const { t } = useTranslation()

  return (
    <LoadingState className="min-h-[50vh]" label={t("common.status.loading")} />
  )
}

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<RouteLoading />}>{element}</Suspense>
}

function AdminRoute({ children }: { children: ReactNode }) {
  const { user, loading, isAuthenticated } = useAuth()

  if (loading) {
    return <RouteLoading />
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  if (!hasAdminRole(user?.roles)) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function AuthenticatedWorkspaceRoute({ children }: { children: ReactNode }) {
  const { user, loading, isAuthenticated } = useAuth()

  if (loading) {
    return <RouteLoading />
  }
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={withSuspense(<Login />)} />
            <Route path="/" element={withSuspense(<Layout />)}>
              <Route index element={withSuspense(<HomePage />)} />
              <Route path="agent" element={withSuspense(<CommunityConversationPage />)} />
              <Route path="agent/:conversationId" element={withSuspense(<CommunityConversationPage />)} />
              <Route
                path="admin/curation"
                element={
                  <AdminRoute>
                    {withSuspense(<CommunityAdminCurationPage />)}
                  </AdminRoute>
                }
              />
              <Route
                path="admin/curation/tasks"
                element={
                  <AdminRoute>
                    {withSuspense(<CommunityAdminCurationTasksPage />)}
                  </AdminRoute>
                }
              />
              <Route path="tools" element={withSuspense(<ToolsHubPage />)} />
              <Route
                path="translate"
                element={
                  <AuthenticatedWorkspaceRoute>
                    {withSuspense(<TranslatePage />)}
                  </AuthenticatedWorkspaceRoute>
                }
              />
              <Route path="paper/:paperId" element={withSuspense(<PaperDetailPage />)} />
              <Route path="processing" element={withSuspense(<ProcessingPage />)} />
              <Route path="preview" element={withSuspense(<PreviewPage />)} />
              <Route
                path="workspace/history"
                element={
                  <AuthenticatedWorkspaceRoute>
                    {withSuspense(<WorkspaceHistoryPage />)}
                  </AuthenticatedWorkspaceRoute>
                }
              />
              <Route
                path="workspace/settings"
                element={
                  <AuthenticatedWorkspaceRoute>
                    {withSuspense(<WorkspaceSettingsPage />)}
                  </AuthenticatedWorkspaceRoute>
                }
              />
              <Route
                path="workspace/glossary"
                element={
                  <AuthenticatedWorkspaceRoute>
                    {withSuspense(<WorkspaceGlossaryPage />)}
                  </AuthenticatedWorkspaceRoute>
                }
              />
              <Route path="history" element={<Navigate to="/workspace/history" replace />} />
              <Route path="glossary" element={<Navigate to="/workspace/glossary" replace />} />
              <Route path="settings" element={<Navigate to="/workspace/settings" replace />} />
              <Route path="profile" element={withSuspense(<ProfilePage />)} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\contexts\AuthContext.tsx
Relative path: contexts\AuthContext.tsx

```tsx
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import i18n from '@/i18n'
import {
    bootstrapLocalSession,
    isLocalAuthConfigured,
    signInWithPassword,
    signOutCurrentSession,
} from '@/lib/local-auth'
import type { LocalAuthError, LocalAuthSession, LocalAuthUser } from '@/lib/local-auth'
import { toast } from 'sonner'
import { useTranslationStore } from '@/features/translation-workflow/store/useTranslationStore'

interface AuthState {
    user: LocalAuthUser | null
    session: LocalAuthSession | null
    loading: boolean
    error: string | null
    isAuthenticated: boolean
    isAuthAvailable: boolean
}

interface AuthMethods {
    signIn: (identifier: string, password: string) => Promise<{ error: LocalAuthError | null }>
    signUp: (email: string, password: string) => Promise<{ error: LocalAuthError | null, needsEmailConfirmation?: boolean }>
    verifyOtp: (email: string, token: string) => Promise<{ error: LocalAuthError | null }>
    signOut: () => Promise<void>
    clearError: () => void
}

type AuthContextType = AuthState & AuthMethods

const defaultContext: AuthContextType = {
    user: null,
    session: null,
    loading: true,
    error: null,
    isAuthenticated: false,
    isAuthAvailable: false,
    signIn: async () => ({ error: null }),
    signUp: async () => ({ error: null }),
    verifyOtp: async () => ({ error: null }),
    signOut: async () => { },
    clearError: () => { },
}

const AuthContext = createContext<AuthContextType>(defaultContext)

interface AuthProviderProps {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [user, setUser] = useState<LocalAuthUser | null>(null)
    const [session, setSession] = useState<LocalAuthSession | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const isAuthAvailable = isLocalAuthConfigured()
    const isAuthenticated = !!user

    useEffect(() => {
        let cancelled = false

        void bootstrapLocalSession().then(({ session: restoredSession, user: restoredUser }) => {
            if (cancelled) {
                return
            }

            setSession(restoredSession)
            setUser(restoredUser)
            setLoading(false)
        })

        return () => {
            cancelled = true
        }
    }, [])

    const signIn = async (identifier: string, password: string) => {
        setError(null)
        const { session: nextSession, error: signInError } = await signInWithPassword(identifier, password)

        if (signInError) {
            setError(signInError.message)
            return { error: signInError }
        }

        if (nextSession) {
            setSession(nextSession)
            setUser(nextSession.user)

            try {
                useTranslationStore.getState().invalidateUserSettings()
                await useTranslationStore.getState().loadUserSettings(true)
                toast.success(i18n.t('auth.toast.settingsLoaded.title'), {
                    description: i18n.t('auth.toast.settingsLoaded.description'),
                    duration: 4000,
                })
            } catch (loadError) {
                console.warn('[Auth] Failed to load user settings after login:', loadError)
            }
        }

        return { error: null }
    }

    const signUp = async (email: string, password: string) => {
        void email
        void password
        return {
            error: { message: i18n.t('auth.errors.requestFailed') },
            needsEmailConfirmation: false,
        }
    }

    const verifyOtp = async (email: string, token: string) => {
        void email
        void token
        return { error: { message: i18n.t('auth.errors.requestFailed') } }
    }

    const signOut = async () => {
        setError(null)
        await signOutCurrentSession(session?.access_token)
        setSession(null)
        setUser(null)
        useTranslationStore.getState().invalidateUserSettings()
    }

    const clearError = () => {
        setError(null)
    }

    const value: AuthContextType = {
        user,
        session,
        loading,
        error,
        isAuthenticated,
        isAuthAvailable,
        signIn,
        signUp,
        verifyOtp,
        signOut,
        clearError,
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\admin-curation\components\AdminCurationTasksWorkspace.tsx
Relative path: features\admin-curation\components\AdminCurationTasksWorkspace.tsx

```tsx
import { History, Loader2, RefreshCw, Search, ShieldAlert, Trash2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import {
  batchDeleteAdminCurationJobs,
  deleteAdminCurationJob,
  listAdminCurationJobs,
} from "@/features/admin-curation/services/admin-curation-api"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import type { AdminCurationJobHistoryItem } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"
import { FormFieldShell } from "@/ui/form-field-shell/FormFieldShell"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { Checkbox } from "@/ui/primitives/checkbox"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/ui/primitives/alert-dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/ui/primitives/select"
import { SearchBar } from "@/ui/search-bar/SearchBar"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"

const STATUS_OPTIONS = [
  { value: "all", labelKey: "community.admin.tasks.filters.all", fallback: "All" },
  { value: "queued", labelKey: "community.admin.tasks.filters.queued", fallback: "Queued" },
  { value: "processing", labelKey: "community.admin.tasks.filters.processing", fallback: "Processing" },
  { value: "completed", labelKey: "community.admin.tasks.filters.completed", fallback: "Completed" },
  { value: "failed", labelKey: "community.admin.tasks.filters.failed", fallback: "Failed" },
]

function getJobStatusTone(status: string): "accent" | "success" | "danger" | "warning" | "muted" {
  switch (status.toLowerCase()) {
    case "completed":
      return "success"
    case "failed":
      return "danger"
    case "processing":
      return "accent"
    case "queued":
      return "warning"
    default:
      return "muted"
  }
}

export function AdminCurationTasksWorkspace() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const [statusFilter, setStatusFilter] = useState("all")
  const [searchValue, setSearchValue] = useState("")
  const [jobs, setJobs] = useState<AdminCurationJobHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [jobPendingDelete, setJobPendingDelete] = useState<AdminCurationJobHistoryItem | null>(null)
  const [isBatchDeleteDialogOpen, setIsBatchDeleteDialogOpen] = useState(false)
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([])

  const isAdmin = hasAdminRole(user?.roles)

  const loadJobs = useCallback(async (params?: { status?: string, q?: string }) => {
    const status = params?.status ?? statusFilter
    const q = params?.q ?? searchValue
    try {
      setIsLoading(true)
      const payload = await listAdminCurationJobs({ status, q })
      setJobs(payload.items)
      setTotal(payload.total)
      setSelectedJobIds((current) => current.filter((jobId) => payload.items.some((job) => job.job_id === jobId)))
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("community.submit.errorFallback"))
    } finally {
      setIsLoading(false)
    }
  }, [searchValue, statusFilter, t])

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) {
      return
    }
    void loadJobs({ status: statusFilter, q: searchValue })
  }, [isAuthenticated, isAdmin, loadJobs, searchValue, statusFilter])

  async function handleDeleteJob() {
    if (!jobPendingDelete) {
      return
    }

    try {
      setIsDeleting(true)
      await deleteAdminCurationJob(jobPendingDelete.job_id)
      toast.success(t("community.admin.tasks.deleteSuccess", "Task deleted permanently."))
      setJobPendingDelete(null)
      await loadJobs({ status: statusFilter, q: searchValue })
    } catch (deleteError) {
      toast.error(deleteError instanceof Error ? deleteError.message : t("community.submit.errorFallback"))
    } finally {
      setIsDeleting(false)
    }
  }

  const visibleJobIds = jobs.map((job) => job.job_id)
  const allVisibleSelected = visibleJobIds.length > 0 && visibleJobIds.every((jobId) => selectedJobIds.includes(jobId))
  const selectedVisibleCount = selectedJobIds.filter((jobId) => visibleJobIds.includes(jobId)).length

  function toggleJobSelection(jobId: string, checked: boolean | "indeterminate") {
    const shouldSelect = checked === true
    setSelectedJobIds((current) => {
      if (shouldSelect) {
        return current.includes(jobId) ? current : [...current, jobId]
      }
      return current.filter((candidate) => candidate !== jobId)
    })
  }

  function toggleSelectAllVisible() {
    setSelectedJobIds((current) => {
      if (allVisibleSelected) {
        return current.filter((jobId) => !visibleJobIds.includes(jobId))
      }
      return Array.from(new Set([...current, ...visibleJobIds]))
    })
  }

  async function handleBatchDeleteJobs() {
    const visibleSelectedJobIds = selectedJobIds.filter((jobId) => visibleJobIds.includes(jobId))
    if (!visibleSelectedJobIds.length) {
      return
    }

    try {
      setIsDeleting(true)
      const payload = await batchDeleteAdminCurationJobs(visibleSelectedJobIds)
      const failedIds = payload.failed.map((item) => item.job_id)
      setIsBatchDeleteDialogOpen(false)
      await loadJobs({ status: statusFilter, q: searchValue })
      setSelectedJobIds(failedIds)

      if (payload.deleted_count > 0) {
        toast.success(
          t("community.admin.tasks.batchDeleteSuccess", {
            count: payload.deleted_count,
            defaultValue: "Deleted {{count}} tasks permanently.",
          }),
        )
      }

      if (payload.failed_count > 0) {
        toast.error(
          t("community.admin.tasks.batchDeletePartialFailure", {
            count: payload.failed_count,
            defaultValue: "{{count}} tasks could not be deleted. They remain selected.",
          }),
        )
      }
    } catch (deleteError) {
      toast.error(deleteError instanceof Error ? deleteError.message : t("community.submit.errorFallback"))
    } finally {
      setIsDeleting(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <LoginPrompt
        messageKey="community.submit.loginRequiredTitle"
        descriptionKey="community.submit.loginRequiredDescription"
      />
    )
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto w-full max-w-3xl px-6 py-8">
        <StatePanel
          tone="danger"
          className="py-10"
          icon={<ShieldAlert className="h-7 w-7" />}
          title={t("community.admin.accessDenied", "Admin access required")}
          description={t(
            "community.admin.accessDeniedDescription",
            "You do not have permission to access the community curation console.",
          )}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      <PageIntro
        icon={<History className="h-5 w-5" />}
        title={t("community.admin.tasks.title", "Admin curation task history")}
        description={t(
          "community.admin.tasks.description",
          "Review queued, processing, completed, and failed admin curation jobs. Deletes are permanent hard deletes.",
        )}
      />

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.tasks.filtersTitle", "Filters")}</CardTitle>
          <CardDescription>
            {t("community.admin.tasks.filtersDescription", "Search by arXiv ID or batch ID, then manage task history.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[minmax(220px,260px)_minmax(0,1fr)] md:items-start">
          <FormFieldShell
            label={t("community.admin.tasks.statusLabel", "Status")}
            description={t("community.admin.tasks.filtersTitle", "Filters")}
            size="compact"
          >
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger aria-label={t("community.admin.tasks.statusLabel", "Status")} className="bg-[color:var(--px-shell-panel-strong)]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {t(option.labelKey, option.fallback)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormFieldShell>
          <div className="min-w-0 flex-1">
            <SearchBar
              value={searchValue}
              onValueChange={setSearchValue}
              onSubmit={(nextValue) => void loadJobs({ status: statusFilter, q: nextValue })}
              ariaLabel={t("community.admin.tasks.searchLabel", "Search")}
              placeholder={t("community.admin.tasks.searchPlaceholder", "Search arXiv ID or batch ID")}
              actionLabel={t("community.admin.tasks.searchAction", "Search")}
              actionIcon={<Search className="h-4 w-4" />}
              auxiliaryAction={(
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void loadJobs({ status: statusFilter, q: searchValue })}
                >
                  <RefreshCw className="h-4 w-4" />
                  {t("common.actions.refresh", "Refresh")}
                </Button>
              )}
              inputClassName="min-h-10"
            />
          </div>
        </CardContent>
      </Card>

      {error ? (
        <NoticeBanner tone="danger" description={error} />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.tasks.resultsTitle", "Task records")}</CardTitle>
          <CardDescription>
            {t("community.admin.tasks.totalLabel", "Total tasks")}: {total}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <p className="text-sm text-[color:var(--px-shell-muted)]">
              {t("community.admin.tasks.selectedCount", {
                count: selectedVisibleCount,
                defaultValue: "{{count}} selected",
              })}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={toggleSelectAllVisible}
                disabled={jobs.length === 0}
              >
                {t("community.admin.tasks.selectAllVisible", "Select all visible")}
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => setIsBatchDeleteDialogOpen(true)}
                disabled={selectedVisibleCount === 0}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t("community.admin.tasks.batchDeleteAction", "Delete selected")}
              </Button>
            </div>
          </div>
          {isLoading ? (
            <LoadingState className="py-8" label={t("common.status.loading")} />
          ) : jobs.length === 0 ? (
            <StatePanel
              className="py-10 shadow-none"
              title={t("community.admin.tasks.empty", "No admin curation tasks match the current filters.")}
              description={t(
                "community.admin.tasks.filtersDescription",
                "Search by arXiv ID or batch ID, then manage task history.",
              )}
            />
          ) : (
            <DataTable className="shadow-none">
              <DataTableHeader className="hidden lg:block">
                <DataTableHeaderRow className="grid-cols-[40px_minmax(0,2.3fr)_minmax(180px,1fr)_minmax(180px,1fr)_auto]">
                  <DataTableHeaderCell />
                  <DataTableHeaderCell>{t("community.admin.tasks.resultsTitle", "Task records")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("community.admin.tasks.statusLabel", "Status")}</DataTableHeaderCell>
                  <DataTableHeaderCell>{t("community.admin.tasks.updatedAt", "Updated")}</DataTableHeaderCell>
                  <DataTableHeaderCell className="text-right">{t("common.actions.delete", "Delete")}</DataTableHeaderCell>
                </DataTableHeaderRow>
              </DataTableHeader>
              <DataTableBody>
                {jobs.map((job) => (
                  <DataTableRow
                    key={job.job_id}
                    className="grid-cols-1 gap-4 lg:grid-cols-[40px_minmax(0,2.3fr)_minmax(180px,1fr)_minmax(180px,1fr)_auto] lg:items-start"
                  >
                    <DataTableCell className="pt-1 lg:pt-2">
                      <Checkbox
                        checked={selectedJobIds.includes(job.job_id)}
                        onCheckedChange={(checked) => toggleJobSelection(job.job_id, checked)}
                        aria-label={t("community.admin.tasks.selectJobAriaLabel", {
                          jobId: job.job_id,
                          defaultValue: "Select {{jobId}}",
                        })}
                      />
                    </DataTableCell>

                    <DataTableCell className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge tone={getJobStatusTone(job.status)}>{job.status}</StatusBadge>
                        {job.terminal_task_status ? (
                          <StatusBadge tone="muted">{job.terminal_task_status}</StatusBadge>
                        ) : null}
                      </div>
                      <div className="space-y-2">
                        <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                          {job.arxiv_id || job.original_filename || job.job_id}
                        </p>
                        <div className="grid gap-1 text-xs text-[color:var(--px-shell-muted)]">
                          <p>job: {job.job_id}</p>
                          <p>batch: {job.batch_id}</p>
                          {job.task_id ? <p>task: {job.task_id}</p> : null}
                          {job.paper_id ? <p>paper: {job.paper_id}</p> : null}
                          {job.published_paper_id ? <p>published: {job.published_paper_id}</p> : null}
                          {job.failed_artifact_path ? <p>{job.failed_artifact_path}</p> : null}
                        </div>
                        {job.error ? (
                          <p className="text-sm text-[color:var(--px-shell-danger)]">{job.error}</p>
                        ) : null}
                      </div>
                    </DataTableCell>

                    <DataTableCell className="space-y-2 text-sm text-[color:var(--px-shell-muted)]">
                      <p className="font-medium text-[color:var(--px-shell-ink)]">{job.source_type}</p>
                      <p>{job.arxiv_id ? `arXiv:${job.arxiv_id}` : job.original_filename || t("common.labels.none", "None")}</p>
                    </DataTableCell>

                    <DataTableCell className="space-y-2 text-sm text-[color:var(--px-shell-muted)]">
                      <p>{job.updated_at ? `${t("community.admin.tasks.updatedAt", "Updated")}: ${job.updated_at}` : t("common.labels.none", "None")}</p>
                      <p>{job.created_at}</p>
                    </DataTableCell>

                    <DataTableCell className="flex items-center justify-start lg:justify-end">
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => setJobPendingDelete(job)}
                        aria-label={`Delete ${job.job_id}`}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        {t("community.admin.tasks.deleteAction", "Delete")}
                      </Button>
                    </DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={jobPendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) {
            setJobPendingDelete(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("community.admin.tasks.deleteDialogTitle", "Permanently delete this task?")}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              {jobPendingDelete
                ? t(
                    "community.admin.tasks.deleteDialogDescription",
                    "This permanently deletes the task record and all retained artifacts. This action cannot be undone.",
                  )
                : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2 sm:gap-0">
            <AlertDialogCancel>
              {t("common.actions.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={(event) => {
                event.preventDefault()
                void handleDeleteJob()
              }}
            >
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t("community.admin.tasks.deleteConfirm", "Permanently delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={isBatchDeleteDialogOpen}
        onOpenChange={(open) => {
          setIsBatchDeleteDialogOpen(open)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("community.admin.tasks.batchDeleteDialogTitle", "Permanently delete selected tasks?")}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              {t("community.admin.tasks.batchDeleteDialogDescription", {
                count: selectedVisibleCount,
                defaultValue:
                  "This permanently deletes {{count}} selected task records and their retained artifacts. This action cannot be undone.",
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2 sm:gap-0">
            <AlertDialogCancel>
              {t("common.actions.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={(event) => {
                event.preventDefault()
                void handleBatchDeleteJobs()
              }}
            >
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t("community.admin.tasks.deleteConfirm", "Permanently delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\admin-curation\components\AdminCurationWorkspace.tsx
Relative path: features\admin-curation\components\AdminCurationWorkspace.tsx

```tsx
import { Loader2, RefreshCw, ShieldAlert, Upload } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import {
  getAdminCurationBatch,
  submitAdminArxivCurationBatch,
  submitAdminUploadCurationBatch,
} from "@/features/admin-curation/services/admin-curation-api"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import type { AdminCurationBatchResponse } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"
import { FormFieldShell } from "@/ui/form-field-shell/FormFieldShell"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { Textarea } from "@/ui/input/Textarea"
import { Pill } from "@/ui/pill/Pill"
import { RecordRow } from "@/ui/record-row/RecordRow"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { UploadDropSurface } from "@/ui/upload-card/UploadDropSurface"

const ACTIVE_BATCH_STATUSES = new Set(["queued", "pending", "running"])
const ACTIVE_JOB_STATUSES = new Set(["queued", "pending", "running", "processing"])

function parseArxivIds(rawValue: string): string[] {
  return Array.from(
    new Set(
      rawValue
        .split(/\r?\n/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  )
}

function isBatchActive(batch: AdminCurationBatchResponse | null): boolean {
  if (!batch) {
    return false
  }
  if (ACTIVE_BATCH_STATUSES.has(batch.status.toLowerCase())) {
    return true
  }
  return batch.items.some((item) => ACTIVE_JOB_STATUSES.has(item.status.toLowerCase()))
}

export function AdminCurationWorkspace() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const { config, loadUserSettings } = useTranslationConfig()

  const [arxivInput, setArxivInput] = useState("")
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [batch, setBatch] = useState<AdminCurationBatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmittingArxiv, setIsSubmittingArxiv] = useState(false)
  const [isSubmittingUpload, setIsSubmittingUpload] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const uploadInputRef = useRef<HTMLInputElement>(null)

  const isAdmin = hasAdminRole(user?.roles)
  const sourceLanguage = config.source_language || "en"
  const targetLanguage = config.target_language || "zh"
  const arxivIds = useMemo(() => parseArxivIds(arxivInput), [arxivInput])
  const hasActiveBatch = isBatchActive(batch)

  useEffect(() => {
    if (isAuthenticated) {
      void loadUserSettings()
    }
  }, [isAuthenticated, loadUserSettings])

  const refreshBatch = useCallback(async (batchId: string) => {
    try {
      setIsRefreshing(true)
      const nextBatch = await getAdminCurationBatch(batchId)
      setBatch(nextBatch)
      setError(null)
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : t("community.submit.errorFallback"))
    } finally {
      setIsRefreshing(false)
    }
  }, [t])

  useEffect(() => {
    if (!batch?.batch_id || !hasActiveBatch) {
      return
    }

    const intervalId = window.setInterval(() => {
      void refreshBatch(batch.batch_id)
    }, 4000)

    return () => window.clearInterval(intervalId)
  }, [batch?.batch_id, hasActiveBatch, refreshBatch])

  async function handleSubmitArxiv(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!arxivIds.length) {
      return
    }

    try {
      setIsSubmittingArxiv(true)
      const result = await submitAdminArxivCurationBatch({
        arxiv_ids: arxivIds,
        source_language: sourceLanguage,
        target_language: targetLanguage,
      })
      setBatch(result)
      setError(null)
      setArxivInput("")
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmittingArxiv(false)
    }
  }

  async function handleSubmitUploads() {
    if (!selectedFiles.length) {
      return
    }

    try {
      setIsSubmittingUpload(true)
      const result = await submitAdminUploadCurationBatch({
        files: selectedFiles,
        source_language: sourceLanguage,
        target_language: targetLanguage,
      })
      setBatch(result)
      setError(null)
      setSelectedFiles([])
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmittingUpload(false)
    }
  }

  function handleFileSelect(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFiles(Array.from(event.target.files ?? []))
    event.target.value = ""
  }

  if (!isAuthenticated) {
    return (
      <LoginPrompt
        messageKey="community.submit.loginRequiredTitle"
        descriptionKey="community.submit.loginRequiredDescription"
      />
    )
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto w-full max-w-3xl px-6 py-8">
        <StatePanel
          tone="danger"
          className="py-10"
          icon={<ShieldAlert className="h-7 w-7" />}
          title={t("community.admin.accessDenied", "Admin access required")}
          description={t(
            "community.admin.accessDeniedDescription",
            "You do not have permission to access the community curation console.",
          )}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <PageIntro
        title={t("community.admin.curation.title", "Community admin curation")}
        description={t(
          "community.admin.curation.description",
          "Submit arXiv IDs or upload archives for official community curation.",
        )}
        meta={
          <>
            {t("community.admin.curation.languageHint", "Language pair")} {sourceLanguage} {"->"} {targetLanguage}
          </>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.curation.arxivTitle", "Batch import from arXiv")}</CardTitle>
          <CardDescription>
            {t("community.admin.curation.arxivDescription", "Enter one arXiv ID per line.")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleSubmitArxiv}>
            <FormFieldShell
              label={t("community.submit.arxivLabel")}
              description={t("community.admin.curation.arxivDescription", "Enter one arXiv ID per line.")}
              headerAside={<Pill tone="accent">{arxivIds.length}</Pill>}
            >
              <Textarea
                value={arxivInput}
                onChange={(event) => setArxivInput(event.target.value)}
                placeholder={t("community.submit.arxivPlaceholder")}
                className="min-h-24"
                aria-label={t("community.submit.arxivLabel")}
              />
            </FormFieldShell>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[color:var(--px-shell-muted)]">
                {t("community.admin.curation.pendingCount", "IDs ready")}: {arxivIds.length}
              </span>
              <Button type="submit" disabled={!arxivIds.length || isSubmittingArxiv}>
                {isSubmittingArxiv ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {t("community.submit.submitArxiv")}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("community.admin.curation.uploadTitle", "Batch import from uploads")}</CardTitle>
          <CardDescription>
            {t("community.admin.curation.uploadDescription", "Upload one or more source packages for curation.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <input
            ref={uploadInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileSelect}
            aria-label={t("community.submit.uploadLabel")}
          />
          <FormFieldShell
            label={t("community.submit.uploadLabel")}
            description={t("community.admin.curation.uploadDescription", "Upload one or more source packages for curation.")}
            headerAside={selectedFiles.length ? <Pill tone="accent">{selectedFiles.length}</Pill> : null}
          >
            <UploadDropSurface
              heading={t("community.submit.uploadLabel")}
              body={t("community.admin.curation.uploadDescription", "Upload one or more source packages for curation.")}
              onClick={() => uploadInputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault()
                  uploadInputRef.current?.click()
                }
              }}
              role="button"
              tabIndex={0}
              className="cursor-pointer"
            />
          </FormFieldShell>
          {selectedFiles.length ? (
            <div className="grid gap-2">
              {selectedFiles.map((file) => (
                <RecordRow
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  icon={<Upload className="h-4 w-4 text-[color:var(--px-shell-accent)]" />}
                  title={file.name}
                  meta={`${(file.size / 1024 / 1024).toFixed(1)} MB`}
                  className="bg-[color:var(--px-shell-panel-strong)]"
                />
              ))}
            </div>
          ) : null}
          <div className="flex items-center justify-between">
            <span className="text-xs text-[color:var(--px-shell-muted)]">
              {t("community.submit.fileSelected", { name: `${selectedFiles.length}` })}
            </span>
            <Button type="button" disabled={!selectedFiles.length || isSubmittingUpload} onClick={() => void handleSubmitUploads()}>
              {isSubmittingUpload ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              {t("community.submit.submitUpload")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error ? (
        <NoticeBanner tone="danger" description={error} />
      ) : null}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle>{t("community.admin.curation.batchStatusTitle", "Batch status")}</CardTitle>
            <CardDescription>{batch ? batch.batch_id : t("community.admin.curation.batchStatusEmpty", "No batch submitted yet.")}</CardDescription>
          </div>
          {batch ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isRefreshing}
              onClick={() => void refreshBatch(batch.batch_id)}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
              {t("common.actions.refresh", "Refresh")}
            </Button>
          ) : null}
        </CardHeader>
        <CardContent>
          {!batch ? (
            <p className="text-sm text-[color:var(--px-shell-muted)]">{t("community.submit.emptyDescription")}</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[color:var(--px-shell-muted)]">{t("task.status", "Status")}:</span>
                <Pill>{batch.status}</Pill>
              </div>
              <div className="grid gap-2">
                {batch.items.map((item) => (
                  <RecordRow
                    key={item.job_id}
                    title={item.arxiv_id ? `arXiv:${item.arxiv_id}` : item.original_filename || item.job_id}
                    badge={<Pill tone="accent">{item.status}</Pill>}
                    meta={
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        <span>{item.source_type}</span>
                        {item.paper_id ? <span>paper:{item.paper_id}</span> : null}
                        <span>job:{item.job_id}</span>
                      </div>
                    }
                    alert={item.error ? <p className="text-xs text-[color:var(--px-shell-danger)]">{item.error}</p> : null}
                    className="bg-[color:var(--px-shell-panel-strong)]"
                  />
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\admin-curation\services\admin-curation-api.ts
Relative path: features\admin-curation\services\admin-curation-api.ts

```ts
export {
  batchDeleteAdminCurationJobs,
  deleteAdminCurationJob,
  getAdminCurationBatch,
  listAdminCurationJobs,
  submitAdminArxivCurationBatch,
  submitAdminUploadCurationBatch,
} from "@/lib/community-api"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\admin-curation\utils\admin-access.ts
Relative path: features\admin-curation\utils\admin-access.ts

```ts
const ADMIN_ROLES = new Set(["admin", "super_admin", "community_admin", "curation_admin"])

export function hasAdminRole(roles: string[] | null | undefined): boolean {
  if (!roles?.length) {
    return false
  }

  return roles.some((role) => ADMIN_ROLES.has(String(role).trim().toLowerCase()))
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\auth-shell\components\LoginPrompt.tsx
Relative path: features\auth-shell\components\LoginPrompt.tsx

```tsx
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { Lock, LogIn } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

interface LoginPromptProps {
  messageKey?: string
  descriptionKey?: string
  actionLabelKey?: string
  messageValues?: Record<string, unknown>
  descriptionValues?: Record<string, unknown>
  className?: string
}

export function LoginPrompt({
  messageKey = "auth.loginRequiredForThisFeature",
  descriptionKey,
  actionLabelKey = "auth.actions.signInAccount",
  messageValues,
  descriptionValues,
  className = "",
}: LoginPromptProps) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  return (
    <StatePanel
      className={className}
      icon={<Lock className="h-7 w-7" />}
      title={t(messageKey, messageValues)}
      description={descriptionKey ? t(descriptionKey, descriptionValues) : undefined}
      actions={(
        <Button onClick={() => navigate("/login")} className="gap-2">
          <LogIn className="h-4 w-4" />
          {t(actionLabelKey)}
        </Button>
      )}
    />
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\auth-shell\components\LoginWorkspace.module.css
Relative path: features\auth-shell\components\LoginWorkspace.module.css

```css
.scene {
  position: relative;
  width: 100%;
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.5rem;
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 20%, color-mix(in srgb, var(--px-shell-accent) 14%, white 86%) 0%, transparent 26%),
    radial-gradient(circle at 85% 85%, color-mix(in srgb, var(--px-shell-info) 12%, white 88%) 0%, transparent 22%),
    linear-gradient(180deg, color-mix(in srgb, white 84%, var(--px-shell-bg) 16%) 0%, color-mix(in srgb, white 72%, var(--px-shell-bg) 28%) 100%);
}

.scene::before,
.scene::after {
  content: "";
  position: absolute;
  border-radius: 9999px;
  filter: blur(18px);
  opacity: 0.9;
  pointer-events: none;
}

.scene::before {
  top: 4%;
  left: -4rem;
  width: 16rem;
  height: 16rem;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--px-shell-accent) 18%, white 12%) 0%, transparent 68%);
}

.scene::after {
  right: -5rem;
  bottom: -1rem;
  width: 18rem;
  height: 18rem;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--px-shell-info) 16%, white 10%) 0%, transparent 70%);
}

.shell {
  position: relative;
  z-index: 1;
  width: min(100%, 30rem);
  border-radius: 1.75rem;
  padding: 1px;
  background-image: linear-gradient(
    160deg,
    color-mix(in srgb, var(--px-shell-accent) 56%, white 44%) 0%,
    color-mix(in srgb, var(--px-shell-accent) 20%, white 80%) 52%,
    color-mix(in srgb, var(--px-shell-info) 36%, white 64%) 100%
  );
  box-shadow:
    0 28px 75px -44px color-mix(in srgb, var(--px-shell-accent) 24%, transparent),
    0 24px 44px -32px rgba(31, 50, 86, 0.24);
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease;
}

.shell:hover {
  box-shadow:
    0 0 28px color-mix(in srgb, var(--px-shell-accent) 12%, transparent),
    0 28px 60px -36px rgba(31, 50, 86, 0.28);
}

.panel {
  border-radius: calc(1.75rem - 1px);
  background:
    linear-gradient(180deg, color-mix(in srgb, white 94%, var(--px-shell-panel) 6%) 0%, color-mix(in srgb, white 88%, var(--px-shell-bg) 12%) 100%);
  color: var(--px-shell-ink);
  transition:
    transform 0.25s ease,
    border-radius 0.25s ease;
}

.panel:hover {
  transform: scale(0.988);
  border-radius: 1.5rem;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.8rem;
}

.header {
  margin-bottom: 0.5rem;
  text-align: center;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.9rem;
  padding: 0.35rem 0.8rem;
  border: 1px solid color-mix(in srgb, var(--px-shell-accent) 20%, white 35%);
  border-radius: 9999px;
  background: color-mix(in srgb, var(--px-shell-accent-soft) 58%, white 42%);
  color: color-mix(in srgb, var(--px-shell-accent-strong) 82%, var(--px-shell-ink) 18%);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.title {
  margin: 0;
  color: color-mix(in srgb, var(--px-shell-ink) 92%, #0f2748 8%);
  font-size: 1.6rem;
  font-weight: 700;
}

.description {
  margin: 0.75rem 0 0;
  color: color-mix(in srgb, var(--px-shell-muted) 86%, var(--px-shell-ink) 14%);
  font-size: 0.98rem;
  line-height: 1.65;
}

.error {
  margin-bottom: 0.25rem;
  border-radius: 1rem;
  border-color: color-mix(in srgb, var(--px-shell-danger-line) 80%, transparent);
  background: color-mix(in srgb, var(--px-shell-danger-soft) 68%, white 32%);
  color: color-mix(in srgb, var(--px-shell-danger) 88%, var(--px-shell-ink) 12%);
}

.fieldBlock {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.label {
  color: color-mix(in srgb, var(--px-shell-ink) 76%, var(--px-shell-muted) 24%);
  font-size: 0.88rem;
  font-weight: 600;
}

.field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.78rem 0.95rem;
  border: 1px solid color-mix(in srgb, var(--px-shell-line) 88%, white 12%);
  border-radius: 1.4rem;
  background: color-mix(in srgb, white 94%, var(--px-shell-panel) 6%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.78),
    0 8px 18px -16px rgba(15, 23, 42, 0.25);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.field:focus-within {
  border-color: color-mix(in srgb, var(--px-shell-accent) 56%, white 18%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.86),
    0 0 0 4px color-mix(in srgb, var(--px-shell-accent) 14%, transparent),
    0 10px 24px -18px color-mix(in srgb, var(--px-shell-accent) 32%, transparent);
  transform: translateY(-1px);
}

.icon {
  width: 1.15rem;
  height: 1.15rem;
  flex-shrink: 0;
  color: color-mix(in srgb, var(--px-shell-muted) 72%, var(--px-shell-accent) 28%);
}

.input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: color-mix(in srgb, var(--px-shell-ink) 94%, black 6%);
  font-size: 0.98rem;
  line-height: 1.4;
}

.input::placeholder {
  color: color-mix(in srgb, var(--px-shell-muted) 78%, white 22%);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  margin-top: 0.85rem;
}

.primaryButton,
.secondaryButton,
.ghostButton {
  border: none;
  outline: none;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.primaryButton,
.secondaryButton {
  min-height: 2.95rem;
  border-radius: 0.75rem;
  font-size: 0.95rem;
  font-weight: 600;
}

.primaryButton:hover,
.secondaryButton:hover,
.ghostButton:hover {
  transform: translateY(-1px);
}

.primaryButton {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--px-shell-accent) 76%, white 24%) 0%, var(--px-shell-accent) 100%);
  color: white;
  box-shadow: 0 18px 28px -22px color-mix(in srgb, var(--px-shell-accent) 54%, transparent);
}

.primaryButton:hover {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--px-shell-accent-strong) 74%, white 14%) 0%, var(--px-shell-accent-strong) 100%);
}

.secondaryRow {
  display: flex;
  gap: 0.7rem;
}

.secondaryButton {
  flex: 1;
  padding: 0.72rem 0.9rem;
  background: color-mix(in srgb, white 90%, var(--px-shell-panel-strong) 10%);
  border: 1px solid color-mix(in srgb, var(--px-shell-line) 86%, white 14%);
  color: color-mix(in srgb, var(--px-shell-ink) 82%, var(--px-shell-accent-strong) 18%);
  box-shadow: 0 8px 18px -18px rgba(15, 23, 42, 0.28);
}

.secondaryButton:hover {
  background: color-mix(in srgb, var(--px-shell-accent-soft) 50%, white 50%);
  border-color: color-mix(in srgb, var(--px-shell-accent) 24%, white 20%);
}

.ghostButton {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 2.85rem;
  padding: 0.7rem 1rem;
  border-radius: 0.85rem;
  background: transparent;
  color: color-mix(in srgb, var(--px-shell-muted) 92%, var(--px-shell-ink) 8%);
}

.ghostButton:hover {
  background: color-mix(in srgb, var(--px-shell-accent-soft) 34%, white 66%);
  color: color-mix(in srgb, var(--px-shell-accent-strong) 86%, var(--px-shell-ink) 14%);
}

.footerNote {
  margin-top: 0.15rem;
  text-align: center;
  color: color-mix(in srgb, var(--px-shell-muted) 90%, white 10%);
  font-size: 0.8rem;
  line-height: 1.5;
}

@media (max-width: 640px) {
  .scene {
    padding: 1.25rem;
  }

  .form {
    padding: 1.35rem;
  }

  .secondaryRow {
    flex-direction: column;
  }
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\auth-shell\components\LoginWorkspace.tsx
Relative path: features\auth-shell\components\LoginWorkspace.tsx

```tsx
import { useState } from "react"
import type { FormEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { AlertCircle, Loader2, Lock, Mail } from "lucide-react"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { getNiuTransAccountUrl, getNiuTransRegisterUrl } from "@/lib/local-auth"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { Label } from "@/ui/primitives/label"

import styles from "./LoginWorkspace.module.css"

function openExternalUrl(url: string) {
  if (typeof window === "undefined") {
    return
  }
  window.location.assign(url)
}

export function LoginWorkspace() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signIn, error, clearError, loading: authLoading } = useAuth()
  const { t } = useTranslation()

  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const from = (location.state as { from?: string })?.from || "/"
  const registerUrl = getNiuTransRegisterUrl()
  const accountUrl = getNiuTransAccountUrl()

  const validateForm = (): boolean => {
    setLocalError(null)

    if (!identifier.trim()) {
      setLocalError(t("auth.enter_your_email_or_phone_number"))
      return false
    }

    if (!password) {
      setLocalError(t("auth.enter_your_password"))
      return false
    }

    return true
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    clearError()

    if (!validateForm()) {
      return
    }

    setLoading(true)
    try {
      const { error: authError } = await signIn(identifier, password)
      if (!authError) {
        navigate(from, { replace: true })
      }
    } finally {
      setLoading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="container mx-auto flex min-h-[60vh] max-w-md items-center justify-center p-6">
        <LoadingState label={t("common.status.loading")} />
      </div>
    )
  }

  const authErrorMessage = error || null

  return (
    <div className={`${styles.scene} animate-in fade-in duration-500`}>
      <section className={styles.shell}>
        <div className={styles.panel}>
          <form className={styles.form} onSubmit={handleSubmit}>
            <header className={styles.header}>
              <div className={styles.eyebrow}>{t("brand.name")}</div>
              <h1 className={styles.title} id="heading">
                {t("auth.welcome_back")}
              </h1>
              <p className={styles.description}>
                {t("auth.sign_in_to_save_your_translation_history_and_settings")}
              </p>
            </header>

            {(error || localError) ? (
              <NoticeBanner
                tone="danger"
                icon={<AlertCircle className="h-4 w-4" />}
                description={authErrorMessage || localError}
                className={`${styles.error} animate-in fade-in slide-in-from-top-2`}
              />
            ) : null}

            <div className={styles.fieldBlock}>
              <Label htmlFor="identifier" className={styles.label}>
                {t("auth.labels.emailOrPhoneNumber")}
              </Label>
              <div className={styles.field}>
                <Mail className={styles.icon} />
                <input
                  id="identifier"
                  type="text"
                  placeholder={t("auth.enter_your_email_or_phone_number")}
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  className={styles.input}
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
            </div>

            <div className={styles.fieldBlock}>
              <Label htmlFor="password" className={styles.label}>
                {t("auth.labels.password")}
              </Label>
              <div className={styles.field}>
                <Lock className={styles.icon} />
                <input
                  id="password"
                  type="password"
                  placeholder="********"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className={styles.input}
                  autoComplete="current-password"
                  disabled={loading}
                />
              </div>
            </div>

            <div className={styles.actions}>
              <button
                type="submit"
                className={styles.primaryButton}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("auth.signing_in")}
                  </>
                ) : (
                  t("common.actions.signIn")
                )}
              </button>

              <div className={styles.secondaryRow}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => openExternalUrl(registerUrl)}
                >
                  {t("auth.actions.createAccount")}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => openExternalUrl(accountUrl)}
                >
                  {t("profile.manage_your_account_information")}
                </button>
              </div>

              <button
                type="button"
                className={styles.ghostButton}
                onClick={() => navigate("/")}
              >
                {t("auth.actions.continueInGuestMode")}
              </button>
            </div>

            <p className={styles.footerNote}>
              {t("brand.subtitle")}
            </p>
          </form>
        </div>
      </section>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\components\CommunityConversationWorkspace.tsx
Relative path: features\community-conversation\components\CommunityConversationWorkspace.tsx

```tsx
import { Loader2 } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { useLocation, useNavigate, useParams } from "react-router-dom"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { Pill } from "@/ui/pill/Pill"
import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityAgentSkillToggles,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

import { ConversationComposer } from "./ConversationComposer"
import { ConversationRail } from "./ConversationRail"
import { ConversationThread } from "./ConversationThread"
import {
  deleteCommunityAgentConversation,
  importCommunityPaper,
  listCommunityAgentConversations,
  streamCommunityAgentRun,
  upsertCommunityAgentConversation,
} from "../services/community-conversation-api"
import {
  buildConversationHistory,
  createSeedConversationRecord,
  deriveConversationTitle,
} from "../utils/conversation-records"
import {
  applyStreamEventToRun,
  buildRunningProgressSteps,
  createAssistantTurnFromRun,
  createConversationId,
  createRunningAssistantTurn,
  createUserTurn,
  getConversationScopedPaperId,
  getIntentBadgeLabel,
  getModeBadgeLabel,
} from "../utils/conversation-runtime"

interface LocationState {
  seedInput?: string
  seedSkillToggles?: CommunityAgentSkillToggles
}

export function CommunityConversationWorkspace() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { conversationId = "" } = useParams()
  const { user, isAuthenticated, loading: authLoading } = useAuth()
  const locationState = (location.state ?? null) as LocationState | null

  const [conversations, setConversations] = useState<CommunityConversationRecord[]>([])
  const [conversationsLoading, setConversationsLoading] = useState(false)
  const [conversationsHydrated, setConversationsHydrated] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null)
  const [input, setInput] = useState("")
  const [agentMode, setAgentMode] = useState<CommunityAgentMode>("chat")
  const [externalSearchEnabled, setExternalSearchEnabled] = useState(
    Boolean(locationState?.seedSkillToggles?.external_search),
  )
  const [agentBusy, setAgentBusy] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [runningStageIndex, setRunningStageIndex] = useState(0)
  const messageListRef = useRef<HTMLDivElement | null>(null)
  const seededConversationIdRef = useRef<string | null>(null)
  const suppressedBootstrapConversationIdRef = useRef<string | null>(null)

  const runningProgressSteps = useMemo(
    () => buildRunningProgressSteps(t, externalSearchEnabled, agentMode),
    [agentMode, externalSearchEnabled, t],
  )

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      setConversations([])
      setConversationsLoading(false)
      setConversationsHydrated(false)
      return
    }

    let cancelled = false
    setConversationsLoading(true)
    setConversationsHydrated(false)
    void listCommunityAgentConversations()
      .then((records) => {
        if (!cancelled) {
          setConversations(records)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : t("community.agent.error")
          setAgentError(message)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setConversationsLoading(false)
          setConversationsHydrated(true)
        }
      })

    return () => {
      cancelled = true
    }
  }, [authLoading, isAuthenticated, t])

  useEffect(() => {
    setExternalSearchEnabled(Boolean(locationState?.seedSkillToggles?.external_search))
  }, [conversationId, locationState?.seedSkillToggles?.external_search])

  useEffect(() => {
    if (
      suppressedBootstrapConversationIdRef.current &&
      suppressedBootstrapConversationIdRef.current !== conversationId
    ) {
      suppressedBootstrapConversationIdRef.current = null
    }
  }, [conversationId])

  useEffect(() => {
    if (authLoading || !conversationsHydrated || conversationsLoading || !isAuthenticated || !conversationId) {
      return
    }

    if (suppressedBootstrapConversationIdRef.current === conversationId) {
      return
    }

    const existing = conversations.find((entry) => entry.id === conversationId)
    if (existing) {
      return
    }

    const seedInput = locationState?.seedInput?.trim()
    const nextRecord = seedInput
      ? createSeedConversationRecord(conversationId, seedInput)
      : {
          id: conversationId,
          title: t("community.agent.newChat"),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          turns: [],
        }

    seededConversationIdRef.current = seedInput ? nextRecord.id : null
    setConversations((current) =>
      [nextRecord, ...current.filter((entry) => entry.id !== nextRecord.id)].sort((left, right) =>
        right.updated_at.localeCompare(left.updated_at),
      ),
    )
    void upsertCommunityAgentConversation(nextRecord).catch(() => undefined)
  }, [
    authLoading,
    conversationId,
    conversations,
    conversationsHydrated,
    conversationsLoading,
    isAuthenticated,
    locationState?.seedInput,
    t,
  ])

  const currentConversation = useMemo(
    () => conversations.find((entry) => entry.id === conversationId) ?? null,
    [conversationId, conversations],
  )

  const mergeConversationRecord = useCallback((record: CommunityConversationRecord) => {
    setConversations((current) =>
      [record, ...current.filter((entry) => entry.id !== record.id)].sort((left, right) =>
        right.updated_at.localeCompare(left.updated_at),
      ),
    )
  }, [])

  const updateConversationTurn = useCallback((
    targetConversationId: string,
    targetTurnId: string,
    updater: (turn: CommunityConversationTurn) => CommunityConversationTurn,
  ) => {
    setConversations((current) =>
      current.map((entry) => {
        if (entry.id !== targetConversationId) {
          return entry
        }
        return {
          ...entry,
          updated_at: new Date().toISOString(),
          turns: entry.turns.map((turn) => (turn.id === targetTurnId ? updater(turn) : turn)),
        }
      }),
    )
  }, [])

  useEffect(() => {
    if (!agentBusy) {
      setRunningStageIndex(0)
      return
    }

    setRunningStageIndex(0)
    const intervalId = window.setInterval(() => {
      setRunningStageIndex((currentIndex) => Math.min(currentIndex + 1, runningProgressSteps.length - 1))
    }, 2500)

    return () => window.clearInterval(intervalId)
  }, [agentBusy, runningProgressSteps.length])

  useEffect(() => {
    const container = messageListRef.current
    if (!container) {
      return
    }

    const frameId = window.requestAnimationFrame(() => {
      if (typeof container.scrollTo === "function") {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: "smooth",
        })
        return
      }
      container.scrollTop = container.scrollHeight
    })

    return () => window.cancelAnimationFrame(frameId)
  }, [agentBusy, conversationId, currentConversation?.turns.length, runningStageIndex])

  const runConversationTurn = useCallback(async (
    record: CommunityConversationRecord,
    latestUserInput: string,
    skillTogglesOverride?: CommunityAgentSkillToggles,
    modeOverride?: CommunityAgentMode,
  ) => {
    setAgentBusy(true)
    setAgentError(null)
    const runMode = modeOverride ?? agentMode
    const scopedPaperId = getConversationScopedPaperId(record)

    const historySource =
      record.turns.at(-1)?.role === "user" ? record.turns.slice(0, -1) : record.turns

    try {
      const runningAssistantTurn = createRunningAssistantTurn(runMode)
      const runningRecord: CommunityConversationRecord = {
        ...record,
        title: record.title || deriveConversationTitle(latestUserInput),
        updated_at: new Date().toISOString(),
        turns: [...record.turns, runningAssistantTurn],
      }
      mergeConversationRecord(runningRecord)

      const run = await streamCommunityAgentRun({
        input: latestUserInput,
        ...(scopedPaperId ? { paper_id: scopedPaperId } : {}),
        skill_toggles: skillTogglesOverride ?? {
          external_search: externalSearchEnabled,
        },
        mode: runMode,
        context: {
          source: "conversation",
          history: buildConversationHistory(historySource),
          conversation_id: record.id,
        },
      }, {
        onEvent: (event) => {
          updateConversationTurn(record.id, runningAssistantTurn.id, (turn) => {
            const currentRun = turn.run ?? {
              run_id: runningAssistantTurn.run?.run_id ?? `pending-${Date.now()}`,
              status: "running",
              intent: "answer",
              mode: runMode,
              message: turn.content,
              summary: turn.content,
              citations: [],
              tool_trace: [],
              action: null,
            }
            const nextRun = applyStreamEventToRun(currentRun, event)
            const nextContent = nextRun.message ?? nextRun.summary ?? turn.content
            return {
              ...turn,
              content: nextContent ?? "",
              run: nextRun,
              status: nextRun.status === "failed" ? "failed" : nextRun.status === "completed" ? "completed" : "running",
              error: nextRun.status === "failed"
                ? (nextRun.message ?? nextRun.summary ?? t("community.agent.error"))
                : null,
            }
          })
        },
      })

      const updatedRecord: CommunityConversationRecord = {
        ...runningRecord,
        updated_at: new Date().toISOString(),
        turns: runningRecord.turns.map((turn) =>
          turn.id === runningAssistantTurn.id
            ? createAssistantTurnFromRun(run, runningAssistantTurn.id, runningAssistantTurn.created_at)
            : turn,
        ),
      }
      mergeConversationRecord(updatedRecord)
      const persisted = await upsertCommunityAgentConversation(updatedRecord)
      mergeConversationRecord(persisted)
    } catch (error) {
      const message = error instanceof Error ? error.message : t("community.agent.error")
      setAgentError(message)
    } finally {
      setAgentBusy(false)
    }
  }, [agentMode, externalSearchEnabled, mergeConversationRecord, t, updateConversationTurn])

  useEffect(() => {
    if (!isAuthenticated || !currentConversation || agentBusy) {
      return
    }

    if (seededConversationIdRef.current !== currentConversation.id) {
      return
    }

    const lastTurn = currentConversation.turns.at(-1)
    if (!lastTurn || lastTurn.role !== "user") {
      seededConversationIdRef.current = null
      return
    }

    seededConversationIdRef.current = null
    void runConversationTurn(
      currentConversation,
      lastTurn.content,
      locationState?.seedSkillToggles ?? {
        external_search: externalSearchEnabled,
      },
      agentMode,
    )
  }, [
    agentBusy,
    agentMode,
    currentConversation,
    externalSearchEnabled,
    isAuthenticated,
    locationState?.seedSkillToggles,
    runConversationTurn,
  ])

  async function handleCitationOpen(citation: CommunityAgentCitation) {
    if (citation.paper_id) {
      navigate(`/paper/${citation.paper_id}`)
      return
    }

    if (citation.arxiv_id) {
      try {
        const imported = await importCommunityPaper({
          source: "arxiv",
          arxiv_id: citation.arxiv_id,
        })
        navigate(`/paper/${imported.paper_id}`)
      } catch {
        window.open(`https://arxiv.org/abs/${citation.arxiv_id}`, "_blank", "noopener,noreferrer")
      }
      return
    }

    if (citation.url) {
      window.open(citation.url, "_blank", "noopener,noreferrer")
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!isAuthenticated || !currentConversation || agentBusy) {
      return
    }

    const normalized = input.trim()
    if (!normalized) {
      return
    }

    const updatedRecord: CommunityConversationRecord = {
      ...currentConversation,
      title: currentConversation.title || deriveConversationTitle(normalized),
      updated_at: new Date().toISOString(),
      turns: [...currentConversation.turns, createUserTurn(normalized)],
    }
    mergeConversationRecord(updatedRecord)
    await upsertCommunityAgentConversation(updatedRecord)
    setInput("")
    await runConversationTurn(updatedRecord, normalized, undefined, agentMode)
  }

  function handleNewChat() {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }
    seededConversationIdRef.current = null
    suppressedBootstrapConversationIdRef.current = null
    navigate(`/agent/${createConversationId()}`)
  }

  async function handleDeleteConversation(targetConversationId: string) {
    if (!isAuthenticated || deletingConversationId) {
      return
    }

    setDeletingConversationId(targetConversationId)
    try {
      await deleteCommunityAgentConversation(targetConversationId)
      const remaining = conversations.filter((entry) => entry.id !== targetConversationId)
      setConversations(remaining)
      if (targetConversationId === conversationId) {
        seededConversationIdRef.current = null
        suppressedBootstrapConversationIdRef.current = targetConversationId
        const nextConversationId = remaining[0]?.id ?? createConversationId()
        navigate(`/agent/${nextConversationId}`)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("community.agent.error")
      setAgentError(message)
    } finally {
      setDeletingConversationId(null)
    }
  }

  const lastAssistantTurn = [...(currentConversation?.turns ?? [])]
    .reverse()
    .find((turn) => turn.role === "assistant" && turn.run)

  if (authLoading) {
    return (
      <div className="min-h-[60vh] bg-[color:var(--px-shell-bg)] px-3 py-8 text-[color:var(--px-shell-ink)] sm:px-4 lg:px-6">
        <PanelShell className="mx-auto max-w-[960px] px-8 py-8">
          <div className="flex items-center gap-3 text-sm text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
            <Loader2 className="h-4 w-4 animate-spin text-[color:var(--px-shell-accent)]" />
            <span>{t("common.status.loading")}</span>
          </div>
        </PanelShell>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] bg-[color:var(--px-shell-bg)] px-3 py-8 text-[color:var(--px-shell-ink)] sm:px-4 lg:px-6">
        <div className="mx-auto max-w-[980px]">
          <LoginPrompt
            messageKey="auth.loginRequiredForThisFeature"
            descriptionKey="community.conversation.loginRequiredDescription"
            className="min-h-[360px] rounded-[32px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-[color:var(--px-shell-bg)] px-3 py-4 text-[color:var(--px-shell-ink)] sm:px-4 lg:px-6">
      <div className="mx-auto grid w-full max-w-[1920px] gap-4 xl:grid-cols-[248px_minmax(0,1fr)]">
        <ConversationRail
          userEmail={user?.email ?? undefined}
          conversations={conversations}
          activeConversationId={conversationId}
          conversationsLoading={conversationsLoading}
          deletingConversationId={deletingConversationId}
          onNewChat={handleNewChat}
          onOpenConversation={(targetConversationId) => navigate(`/agent/${targetConversationId}`)}
          onDeleteConversation={(targetConversationId) => {
            void handleDeleteConversation(targetConversationId)
          }}
        />

        <PanelShell
          as="section"
          tone="panel"
          padding="none"
          className="relative flex max-h-[calc(100vh-6.8rem)] flex-col overflow-hidden rounded-[32px] bg-[color:var(--px-shell-surface)]"
        >
          <header className="z-20 flex flex-none items-center justify-between border-b border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_82%,transparent)] px-6 py-4 backdrop-blur-xl">
            <div className="min-w-0 flex items-center gap-4">
              <div className="min-w-0 flex flex-col pr-4">
                <h1 className="truncate text-lg font-bold leading-tight tracking-[-0.01em] text-[color:var(--px-shell-ink)]">
                  {currentConversation?.title || t("community.agent.newChat")}
                </h1>
                <p className="truncate text-sm font-medium text-[color:var(--px-shell-muted)]">
                  {t("community.conversation.title")} <span aria-hidden="true">|</span> {t("community.conversation.historyBadge")}
                </p>
              </div>
            </div>
            <div className="hidden shrink-0 flex-wrap items-center justify-end gap-3 sm:flex">
              <Pill className="text-[11px]">
                {getIntentBadgeLabel(t, lastAssistantTurn?.run)}
              </Pill>
              <Pill tone="accent" className="text-[11px]">
                {getModeBadgeLabel(t, lastAssistantTurn?.run?.mode ?? agentMode)}
              </Pill>
            </div>
          </header>

          <ConversationThread
            messageListRef={messageListRef}
            currentConversation={currentConversation}
            agentBusy={agentBusy}
            agentError={agentError}
            runningProgressSteps={runningProgressSteps}
            runningStageIndex={runningStageIndex}
            onCitationOpen={(citation) => {
              void handleCitationOpen(citation)
            }}
            onOpenPaper={(paperId) => navigate(`/paper/${paperId}`)}
          />

          <ConversationComposer
            input={input}
            agentBusy={agentBusy}
            agentMode={agentMode}
            externalSearchEnabled={externalSearchEnabled}
            onInputChange={setInput}
            onSubmit={handleSubmit}
            onModeChange={setAgentMode}
            onExternalSearchChange={setExternalSearchEnabled}
          />
        </PanelShell>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\components\ConversationComposer.tsx
Relative path: features\community-conversation\components\ConversationComposer.tsx

```tsx
import { ArrowUpRight, Loader2, MessageSquarePlus, Sparkles } from "lucide-react"
import type { CSSProperties, FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { ComposerShell } from "@/ui/composer-shell/ComposerShell"
import { Textarea } from "@/ui/input/Textarea"
import { SegmentedControl } from "@/ui/segmented-control/SegmentedControl"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import type { CommunityAgentMode } from "@/types/community"

interface ConversationComposerProps {
  input: string
  agentBusy: boolean
  agentMode: CommunityAgentMode
  externalSearchEnabled: boolean
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onModeChange: (mode: CommunityAgentMode) => void
  onExternalSearchChange: (enabled: boolean) => void
}

export function ConversationComposer({
  input,
  agentBusy,
  agentMode,
  externalSearchEnabled,
  onInputChange,
  onSubmit,
  onModeChange,
  onExternalSearchChange,
}: ConversationComposerProps) {
  const { t } = useTranslation()

  return (
    <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-[color:var(--px-shell-surface)] via-[color:var(--px-shell-surface)] to-transparent px-4 pb-6 pt-10 md:px-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-3">
        <ComposerShell
          onSubmit={onSubmit}
          toolbar={(
            <div className="flex flex-wrap items-center gap-3">
              <SegmentedControl
                value={agentMode}
                onValueChange={onModeChange}
                className="bg-[color:var(--px-shell-panel)]"
                items={[
                  {
                    value: "chat",
                    label: t("community.agent.mode.chat"),
                    icon: <MessageSquarePlus className="h-4 w-4" />,
                  },
                  {
                    value: "deep_research",
                    label: t("community.agent.mode.deepResearch"),
                    icon: <Sparkles className="h-4 w-4" />,
                  },
                ]}
              />

              <label className="flex items-center gap-2 rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] px-4 py-2 shadow-sm">
                <ToggleSwitch
                  checked={externalSearchEnabled}
                  onCheckedChange={onExternalSearchChange}
                  aria-label={t("community.agent.externalSearch.label")}
                />
                <span className="text-xs font-bold uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
                  {t("community.agent.externalSearch.label")}
                </span>
              </label>
            </div>
          )}
          actionSlot={(
            <Button
              type="submit"
              size="icon"
              disabled={agentBusy}
              aria-label={t("community.agent.send")}
              className="h-10 w-10 bg-[color:var(--px-shell-accent)] text-white hover:bg-[color:var(--px-shell-accent-strong)]"
            >
              {agentBusy ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowUpRight className="h-5 w-5" />}
            </Button>
          )}
          footer={(
            <div className="text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[color:var(--px-shell-muted)]">
                {t("community.agent.markdownSupported", "Supports Markdown")}
              </p>
            </div>
          )}
        >
          <div className="min-h-[44px] max-h-32 overflow-y-auto">
            <Textarea
              id="conversation-agent-input"
              aria-label={t("community.agent.aria")}
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              placeholder={t("community.agent.placeholder")}
              rows={1}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  if (!agentBusy && input.trim()) {
                    onSubmit(event as unknown as FormEvent<HTMLFormElement>)
                  }
                }
              }}
              className="min-h-[44px] border-0 bg-transparent px-3 py-2.5 text-[15px] leading-relaxed shadow-none focus-visible:ring-0"
              style={{ fieldSizing: "content" } as CSSProperties}
            />
          </div>
        </ComposerShell>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\components\ConversationRail.tsx
Relative path: features\community-conversation\components\ConversationRail.tsx

```tsx
import { Bot, Loader2, MessageSquarePlus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { InteractiveCard } from "@/ui/interactive-card/InteractiveCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { cn } from "@/lib/utils"
import type { CommunityConversationRecord } from "@/types/community"

interface ConversationRailProps {
  userEmail?: string
  conversations: CommunityConversationRecord[]
  activeConversationId: string
  conversationsLoading: boolean
  deletingConversationId: string | null
  onNewChat: () => void
  onOpenConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
}

export function ConversationRail({
  userEmail,
  conversations,
  activeConversationId,
  conversationsLoading,
  deletingConversationId,
  onNewChat,
  onOpenConversation,
  onDeleteConversation,
}: ConversationRailProps) {
  const { t } = useTranslation()

  return (
    <PanelShell
      as="aside"
      tone="glass"
      padding="none"
      className="flex min-h-[calc(100vh-6.8rem)] flex-col overflow-hidden"
    >
      <div className="border-b border-[color:var(--px-shell-line)] px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[color:var(--px-shell-accent-soft)]">
            <Bot className="h-5 w-5 text-[color:var(--px-shell-muted)]" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {t("community.conversation.savedTitle")}
            </p>
            <p className="truncate text-xs text-[color:var(--px-shell-muted)]">{userEmail ?? ""}</p>
          </div>
        </div>

        <Button
          type="button"
          onClick={onNewChat}
          className="mt-4 h-11 w-full justify-start rounded-2xl bg-[color:var(--px-shell-accent)] px-4 text-white hover:bg-[color:var(--px-shell-accent-strong)]"
        >
          <MessageSquarePlus className="h-4 w-4" />
          {t("community.agent.newChat")}
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
        {conversationsLoading ? (
          <NoticeBanner
            tone="info"
            icon={<Loader2 className="h-4 w-4 animate-spin" />}
            description={t("common.status.loading")}
            className="rounded-[22px]"
          />
        ) : null}

        {!conversationsLoading && !conversations.length ? (
          <NoticeBanner
            tone="neutral"
            description={t("community.conversation.savedEmpty")}
            className="rounded-[22px] border-dashed"
          />
        ) : null}

        {conversations.map((conversation) => (
          <InteractiveCard
            key={conversation.id}
            element="div"
            tone={conversation.id === activeConversationId ? "selected" : "ghost"}
            size="sm"
            className={cn(
              "flex items-start gap-2",
              conversation.id === activeConversationId ? "" : "hover:shadow-none",
            )}
          >
            <div
              role="button"
              tabIndex={0}
              onClick={() => onOpenConversation(conversation.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault()
                  onOpenConversation(conversation.id)
                }
              }}
              className="min-w-0 flex-1 text-left"
            >
              <p className="line-clamp-2 text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {conversation.title || t("community.agent.newChat")}
              </p>
              <p className="mt-1 text-xs text-[color:var(--px-shell-muted)]">
                {new Date(conversation.updated_at).toLocaleString()}
              </p>
            </div>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={t("community.conversation.deleteConversationAria", { title: conversation.title })}
              disabled={deletingConversationId === conversation.id}
              onClick={() => onDeleteConversation(conversation.id)}
              className="h-9 w-9 text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)]"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </InteractiveCard>
        ))}
      </div>
    </PanelShell>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\components\ConversationThread.tsx
Relative path: features\community-conversation\components\ConversationThread.tsx

```tsx
import { ArrowUpRight, Bot, Loader2, User } from "lucide-react"
import type { RefObject } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { Card } from "@/ui/card/Card"
import { ChatBubble } from "@/ui/chat-bubble/ChatBubble"
import { InteractiveCard } from "@/ui/interactive-card/InteractiveCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { Pill } from "@/ui/pill/Pill"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { cn } from "@/lib/utils"
import type {
  CommunityAgentCitation,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

interface ConversationThreadProps {
  messageListRef: RefObject<HTMLDivElement | null>
  currentConversation: CommunityConversationRecord | null
  agentBusy: boolean
  agentError: string | null
  runningProgressSteps: string[]
  runningStageIndex: number
  onCitationOpen: (citation: CommunityAgentCitation) => void
  onOpenPaper: (paperId: string) => void
}

function formatConversationTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ""
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function ConversationTurnCard({
  turn,
  onCitationOpen,
  onOpenPaper,
}: {
  turn: CommunityConversationTurn
  onCitationOpen: (citation: CommunityAgentCitation) => void
  onOpenPaper: (paperId: string) => void
}) {
  const { t } = useTranslation()
  const assistantRun = turn.role === "assistant" ? turn.run : null
  const assistantAction = assistantRun?.action ?? null
  const assistantActionPaperId = assistantAction?.paper_id ?? null
  const primaryCitation = assistantRun?.citations?.[0] ?? null
  const secondaryCitations = assistantRun?.citations?.slice(1) ?? []
  const deepResearchReport = assistantRun?.mode === "deep_research" ? assistantRun.report : null
  const renderedContent = deepResearchReport?.body_markdown ?? turn.content

  return (
    <div
      className={cn(
        "flex w-full items-end gap-4",
        turn.role === "user" ? "justify-end" : "justify-start",
      )}
    >
      {turn.role === "assistant" ? (
        <div className="mt-6 hidden size-10 shrink-0 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm sm:flex">
          <Bot className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
        </div>
      ) : null}

      <div
        className={cn(
          "flex w-full flex-col gap-1.5",
          turn.role === "user" ? "max-w-[85%] items-end md:max-w-[70%]" : "max-w-[85%] md:max-w-[70%]",
        )}
      >
        <div className={cn("flex items-center gap-2", turn.role === "user" ? "pr-2" : "pl-2")}>
          {turn.role === "user" ? (
            <>
              <span className="text-xs text-[color:var(--px-shell-muted)]">
                {formatConversationTimestamp(turn.created_at)}
              </span>
              <span className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.conversation.userLabel", "You")}
              </span>
            </>
          ) : (
            <>
              <span className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.conversation.agentLabel", "Paper Agent")}
              </span>
              <span className="text-xs text-[color:var(--px-shell-muted)]">
                {formatConversationTimestamp(turn.created_at)}
              </span>
            </>
          )}
        </div>

        {turn.role === "assistant" && primaryCitation ? (
          <div className="mt-4 space-y-3" data-testid="community-conversation-primary-paper">
            <InteractiveCard
              onClick={() => onCitationOpen(primaryCitation)}
              tone="strong"
              size="lg"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-3xl space-y-3.5">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[color:var(--px-shell-muted)]">
                    <Pill>{primaryCitation.source}</Pill>
                    {primaryCitation.arxiv_id ? <span>{`arXiv:${primaryCitation.arxiv_id}`}</span> : null}
                    <span aria-hidden="true">|</span>
                    <span>{t("community.conversation.openPaperTitle")}</span>
                  </div>
                  <p className="text-[1.45rem] font-semibold tracking-[-0.035em] text-[color:var(--px-shell-ink)]">
                    {primaryCitation.title}
                  </p>
                  {primaryCitation.snippet ? (
                    <p className="line-clamp-4 max-w-3xl text-[15px] leading-7 text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
                      {primaryCitation.snippet}
                    </p>
                  ) : null}
                </div>

                <span className="inline-flex min-h-10 items-center gap-2 rounded-full border border-[color:var(--px-shell-ink)] bg-[color:var(--px-shell-ink)] px-4 py-2 text-sm font-semibold text-[color:var(--px-shell-surface)] shadow-[0_12px_30px_rgba(15,23,42,0.12)]">
                  {t("community.conversation.openPaperAction")}
                  <ArrowUpRight className="h-4 w-4" />
                </span>
              </div>
            </InteractiveCard>

            {secondaryCitations.length ? (
              <div className="grid gap-3 lg:grid-cols-2">
                {secondaryCitations.map((citation) => (
                  <InteractiveCard
                    key={citation.id}
                    onClick={() => onCitationOpen(citation)}
                    tone="panel"
                    size="md"
                  >
                    <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">{citation.title}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]">
                      {citation.source}
                      {citation.arxiv_id ? ` | arXiv:${citation.arxiv_id}` : ""}
                    </p>
                    {citation.snippet ? (
                      <p className="mt-3 line-clamp-3 text-sm leading-6 text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
                        {citation.snippet}
                      </p>
                    ) : null}
                  </InteractiveCard>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {deepResearchReport ? (
          <Card
            data-testid="community-deep-research-report"
            className="mt-4 rounded-[24px] bg-[color:var(--px-shell-surface)] px-5 py-4 shadow-none"
          >
            <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {t("community.conversation.deepResearchReportTitle")}
            </p>
            <p className="mt-1 text-sm text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
              {deepResearchReport.coverage_note}
            </p>
          </Card>
        ) : null}

        <ChatBubble speaker={turn.role === "assistant" ? "assistant" : "user"}>
          {renderedContent}
        </ChatBubble>

        {assistantAction?.type === "navigate_paper" && assistantActionPaperId ? (
          <Card className="mt-5 rounded-[24px] bg-[color:var(--px-shell-panel)] p-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                  {t("community.conversation.openPaperTitle")}
                </p>
                <p className="text-sm text-[color:color-mix(in_srgb,var(--px-shell-muted)_86%,black_14%)]">
                  {assistantAction.auto_started_translation
                    ? t("community.conversation.openPaperDescriptionTranslating")
                    : t("community.conversation.openPaperDescription")}
                </p>
              </div>

              <Button
                type="button"
                onClick={() => onOpenPaper(assistantActionPaperId)}
                className="h-11 bg-[color:var(--px-shell-accent)] px-4 text-white hover:bg-[color:var(--px-shell-accent-strong)]"
              >
                {t("community.conversation.openPaperAction")}
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        ) : null}
      </div>

      {turn.role === "user" ? (
        <div className="mt-6 hidden size-10 shrink-0 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm sm:flex">
          <User className="h-5 w-5 text-[color:var(--px-shell-muted)]" />
        </div>
      ) : null}
    </div>
  )
}

export function ConversationThread({
  messageListRef,
  currentConversation,
  agentBusy,
  agentError,
  runningProgressSteps,
  runningStageIndex,
  onCitationOpen,
  onOpenPaper,
}: ConversationThreadProps) {
  const { t } = useTranslation()

  return (
    <div ref={messageListRef} className="flex-1 overflow-y-auto px-4 py-6 pb-48 md:px-8 lg:px-24">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        {!currentConversation?.turns.length ? (
          <StatePanel
            className="rounded-[28px] border-dashed bg-[color:var(--px-shell-panel)] py-10 shadow-none"
            title={t("community.conversation.emptyState")}
          />
        ) : null}

        {currentConversation?.turns.map((turn) => (
          <ConversationTurnCard
            key={turn.id}
            turn={turn}
            onCitationOpen={onCitationOpen}
            onOpenPaper={onOpenPaper}
          />
        ))}

        {agentBusy ? (
          <NoticeBanner
            icon={<Loader2 className="h-4 w-4 animate-spin" />}
            title={t("community.conversation.running")}
            description={runningProgressSteps[runningStageIndex]}
            className="rounded-[24px]"
          />
        ) : null}

        {agentError ? (
          <NoticeBanner
            tone="danger"
            title={t("community.detail.errorTitle")}
            description={agentError}
            className="rounded-[24px]"
          />
        ) : null}
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\services\community-conversation-api.ts
Relative path: features\community-conversation\services\community-conversation-api.ts

```ts
export {
  deleteCommunityAgentConversation,
  importCommunityPaper,
  listCommunityAgentConversations,
  streamCommunityAgentRun,
  upsertCommunityAgentConversation,
} from "@/lib/community-api"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\utils\conversation-records.ts
Relative path: features\community-conversation\utils\conversation-records.ts

```ts
export {
  buildConversationHistory,
  createSeedConversationRecord,
  deriveConversationTitle,
} from "@/lib/community-agent-conversations"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-conversation\utils\conversation-runtime.ts
Relative path: features\community-conversation\utils\conversation-runtime.ts

```ts
import type { TFunction } from "i18next"

import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityAgentRun,
  CommunityAgentStreamEvent,
  CommunityAgentToolTrace,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

export function createConversationId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `conversation-${Date.now()}`
}

export function createAssistantTurnFromRun(
  run: CommunityAgentRun,
  id: string = `assistant-${Date.now()}`,
  createdAt: string = new Date().toISOString(),
): CommunityConversationTurn {
  const assistantMessage = run.message ?? run.summary ?? ""
  return {
    id,
    role: "assistant",
    content: assistantMessage,
    created_at: createdAt,
    run,
    status: run.status === "failed" ? "failed" : "completed",
    error: run.status === "failed" ? assistantMessage || null : null,
  }
}

export function createRunningAssistantTurn(mode: CommunityAgentMode): CommunityConversationTurn {
  const createdAt = new Date().toISOString()
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
    created_at: createdAt,
    run: {
      run_id: `pending-${Date.now()}`,
      status: "running",
      intent: "answer",
      mode,
      message: "",
      summary: "",
      citations: [],
      tool_trace: [],
      action: null,
    },
    status: "running",
    error: null,
  }
}

function upsertTrace(
  currentTrace: CommunityAgentToolTrace[] | undefined,
  nextTrace: CommunityAgentToolTrace,
): CommunityAgentToolTrace[] {
  const existing = currentTrace ?? []
  return [...existing.filter((trace) => trace.id !== nextTrace.id), nextTrace]
}

function upsertCitation(
  currentCitations: CommunityAgentCitation[] | undefined,
  nextCitation: CommunityAgentCitation,
): CommunityAgentCitation[] {
  const existing = currentCitations ?? []
  return [...existing.filter((citation) => citation.id !== nextCitation.id), nextCitation]
}

export function applyStreamEventToRun(
  currentRun: CommunityAgentRun,
  event: CommunityAgentStreamEvent,
): CommunityAgentRun {
  const nextRunId = event.run_id ?? currentRun.run_id
  const data = event.data ?? {}

  switch (event.type) {
    case "status": {
      const status = typeof data.status === "string" ? data.status : currentRun.status
      const intent = typeof data.intent === "string" ? data.intent : currentRun.intent
      return {
        ...currentRun,
        run_id: nextRunId,
        status: status as CommunityAgentRun["status"],
        intent: intent as CommunityAgentRun["intent"],
      }
    }
    case "assistant_delta": {
      const delta = typeof data.delta === "string" ? data.delta : ""
      const nextMessage = `${currentRun.message ?? currentRun.summary ?? ""}${delta}`
      return {
        ...currentRun,
        run_id: nextRunId,
        status: "running",
        message: nextMessage,
        summary: nextMessage,
      }
    }
    case "citation": {
      const citation = data.citation
      if (!citation || typeof citation !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        citations: upsertCitation(currentRun.citations, citation as CommunityAgentCitation),
      }
    }
    case "tool_start":
    case "tool_result": {
      const trace = data.trace
      if (!trace || typeof trace !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        tool_trace: upsertTrace(currentRun.tool_trace, trace as CommunityAgentToolTrace),
      }
    }
    case "action": {
      const action = data.action
      if (!action || typeof action !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        action: action as CommunityAgentRun["action"],
      }
    }
    case "complete": {
      const snapshot = data.snapshot
      if (!snapshot || typeof snapshot !== "object") {
        return currentRun
      }
      return snapshot as CommunityAgentRun
    }
    case "error": {
      const message =
        typeof data.message === "string"
          ? data.message
          : currentRun.message ?? currentRun.summary ?? ""
      return {
        ...currentRun,
        run_id: nextRunId,
        status: "failed",
        message,
        summary: message,
      }
    }
    default:
      return currentRun
  }
}

export function createUserTurn(content: string): CommunityConversationTurn {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    created_at: new Date().toISOString(),
    status: "completed",
  }
}

export function getConversationScopedPaperId(
  record: CommunityConversationRecord,
): string | undefined {
  for (let index = record.turns.length - 1; index >= 0; index -= 1) {
    const turn = record.turns[index]
    if (turn.role !== "assistant" || !turn.run) {
      continue
    }

    const actionPaperId = turn.run.action?.paper_id
    if (typeof actionPaperId === "string" && actionPaperId.trim()) {
      return actionPaperId.trim()
    }

    const citationPaperId = turn.run.citations?.find(
      (citation) => typeof citation.paper_id === "string" && citation.paper_id.trim(),
    )?.paper_id
    if (typeof citationPaperId === "string" && citationPaperId.trim()) {
      return citationPaperId.trim()
    }
  }

  return undefined
}

export function getIntentBadgeLabel(
  t: TFunction,
  run: CommunityAgentRun | null | undefined,
) {
  switch (run?.intent) {
    case "search":
      return t("community.agent.intent.search", "Search")
    case "translate":
      return t("community.agent.intent.translate", "Translate")
    case "answer":
    default:
      return t("community.agent.intent.answer", "Answer")
  }
}

export function getModeBadgeLabel(
  t: TFunction,
  mode: CommunityAgentMode | null | undefined,
) {
  return mode === "deep_research"
    ? t("community.agent.mode.deepResearch", "Deep research")
    : t("community.agent.mode.chat", "Chat")
}

export function buildRunningProgressSteps(
  t: (key: string) => string,
  externalSearchEnabled: boolean,
  mode: CommunityAgentMode,
) {
  if (mode === "deep_research") {
    const steps = [
      t("community.conversation.progressStepAnalyze"),
      t("community.conversation.progressStepSearchLocal"),
    ]
    if (externalSearchEnabled) {
      steps.push(t("community.conversation.progressStepSearchExternal"))
    }
    steps.push(
      t("community.conversation.progressStepSynthesizeReport"),
      t("community.conversation.progressStepFinalizeReport"),
    )
    return steps
  }

  const steps = [
    t("community.conversation.progressStepAnalyze"),
    t("community.conversation.progressStepSearchLocal"),
  ]

  if (externalSearchEnabled) {
    steps.push(t("community.conversation.progressStepSearchExternal"))
  }

  steps.push(
    t("community.conversation.progressStepCompose"),
    t("community.conversation.progressStepFinalize"),
  )

  return steps
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\CommunityFeedSurface.tsx
Relative path: features\community-paper\components\CommunityFeedSurface.tsx

```tsx
import { Clock3, Flame, Search, Trash2, X } from "lucide-react"
import { useState, useEffect, useRef, type ReactElement } from "react"
import { useTranslation } from "react-i18next"

import { PaperCard } from "@/features/community-paper/components/PaperCard"
import { PaperCardSkeleton } from "@/features/community-paper/components/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/features/community-paper/components/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/features/community-paper/components/PaperFeedErrorState"
import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { useCommunityPapers } from "@/features/community-paper/hooks/useCommunityPapers"
import { deleteCommunityPaper } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { FilterToolbar } from "@/ui/filter-toolbar/FilterToolbar"
import { Pill } from "@/ui/pill/Pill"

export default function CommunityFeedSurface() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [activeTab, setActiveTab] = useState<CommunityFeedSort>("latest")
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null)
  const isAdmin = hasAdminRole(user?.roles)

  const inputRef = useRef<HTMLInputElement>(null)

  const { items, total, hasMore, loading, loadingMore, error, loadMore, refetch } = useCommunityPapers(activeTab, query)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const feedSortOptions = [
    {
      value: "hot",
      label: t("community.feed.sort.hot"),
      icon: <Flame className="h-4 w-4" />,
    },
    {
      value: "latest",
      label: t("community.feed.sort.latest"),
      icon: <Clock3 className="h-4 w-4" />,
    },
  ] satisfies Array<{
    value: CommunityFeedSort
    label: string
    icon: ReactElement
  }>

  function handleSearchSubmit(nextValue: string) {
    if (!nextValue.trim()) {
      return
    }
    setQuery(nextValue.trim())
  }

  async function handleDelete(paper: CommunityPaper) {
    const confirmed = window.confirm(
      t("community.admin.deleteConfirm", {
        title: paper.title,
      }),
    )

    if (!confirmed) {
      return
    }

    try {
      setDeletingPaperId(paper.id)
      await deleteCommunityPaper(paper.id)
      refetch()
    } finally {
      setDeletingPaperId(null)
    }
  }

  return (
    <section
      aria-label={t("community.feed.title")}
      // 1. 容器宽度缩小为 4xl，顶部留白压缩为 pt-2
      className="mx-auto flex w-full max-w-4xl flex-col gap-3 text-[color:var(--px-shell-ink)] pt-2"
    >

      {/* 2. 上下留白大幅压缩 (mb-4 mt-2) */}
      <div className="flex flex-col items-center text-center mb-4 mt-2 px-4">
        {/* 3. 主标题字号缩小 (text-2xl sm:text-3xl)，主标题和副标题之间的间距缩小 (mb-2) */}
        <h1 className="mb-2 text-2xl font-semibold tracking-tight sm:text-3xl text-[color:var(--px-shell-ink)]">
          探索、学习与<span className="text-[color:var(--px-shell-accent)] font-medium">创新</span>
        </h1>
        {/* 4. 副标题字号缩小 (text-xs sm:text-sm) */}
        <p className="text-xs sm:text-sm text-[color:var(--px-shell-muted)]/80 max-w-lg leading-relaxed font-light">
          我们精选论文并提供译文与解析，也提供翻译工具，助力论文研究与学习。
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSearchSubmit(searchInput)
        }}
        // 5. 搜索框上下内边距压缩 (py-1.5)
        className="flex w-full items-center gap-2 rounded-full border border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel-strong)] px-4 py-1.5 shadow-[0_20px_40px_-34px_rgba(8,23,38,0.22)] focus-within:border-[color:var(--px-shell-accent)] focus-within:ring-1 focus-within:ring-[color:var(--px-shell-accent)] transition-all"
      >
        {isAdmin ? (
          <Pill className="shrink-0 px-3 py-1 text-[10px] font-semibold normal-case tracking-normal">
            <Trash2 className="h-3 w-3" />
            {t("community.feed.adminHint")}
          </Pill>
        ) : null}

        <input
          ref={inputRef}
          autoFocus
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t("community.feed.searchPlaceholder")}
          aria-label={t("community.feed.searchAriaLabel")}
          className="min-w-0 flex-1 bg-transparent text-sm text-[color:var(--px-shell-ink)] outline-none placeholder:text-[color:var(--px-shell-muted)]/50"
        />

        {searchInput.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setSearchInput("")
              setQuery("")
              inputRef.current?.focus()
            }}
            // 清除按钮略微缩小
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[color:var(--px-shell-muted)] transition-colors hover:bg-[color:var(--px-shell-line)] hover:text-[color:var(--px-shell-ink)]"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}

        <button
          type="submit"
          // 搜索按钮略微缩小
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent)] text-white transition-colors hover:bg-[color:var(--px-shell-accent-strong)]"
          aria-label={t("community.feed.searchLabel")}
        >
          <Search className="h-3.5 w-3.5" />
        </button>
      </form>

      <FilterToolbar
        options={feedSortOptions}
        value={activeTab}
        onValueChange={(nextValue) => setActiveTab(nextValue as CommunityFeedSort)}
        className="pb-2 mt-2"
        meta={query ? (
          <Pill className="px-3 py-2 text-xs font-medium normal-case tracking-normal">
            {t("community.feed.resultsFiltered", { count: total, query })}
          </Pill>
        ) : undefined}
      />

      <div className="relative">
        {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

        {!error && loading ? (
          <div className="grid gap-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-full">
                <PaperCardSkeleton />
              </div>
            ))}
            <div className="flex justify-center py-8">
              <div className="flex items-center gap-3 text-[color:var(--px-shell-muted)]">
                <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--px-shell-accent)] animate-bounce"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--px-shell-accent)] animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--px-shell-accent)] animate-bounce [animation-delay:-0.3s]"></div>
                <span className="ml-2 text-[10px] font-black uppercase tracking-[0.3em]">
                  {t("common.status.loading")}
                </span>
              </div>
            </div>
          </div>
        ) : null}

        {!error && !loading && !items.length ? <PaperFeedEmptyState /> : null}

        {!error && !loading && items.length > 0 ? (
          <>
            <div className="grid gap-3">
              {items.map((paper) => (
                <PaperCard
                  key={paper.id}
                  paper={paper}
                  onDelete={isAdmin ? handleDelete : undefined}
                  deleting={deletingPaperId === paper.id}
                />
              ))}
            </div>
            {hasMore ? (
              <div className="flex justify-center pt-4">
                <Button
                  type="button"
                  onClick={() => void loadMore()}
                  disabled={loadingMore}
                  variant="outline"
                >
                  {loadingMore ? `${t("common.actions.loadMore")}...` : t("common.actions.loadMore")}
                </Button>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  )
}
```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\CommunitySubmitPanel.tsx
Relative path: features\community-paper\components\CommunitySubmitPanel.tsx

```tsx
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"

import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { useAuth } from "@/contexts/AuthContext"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { submitCommunityPaperFromArxiv, submitCommunityPaperFromUpload } from "@/lib/community-api"
import { Button } from "@/ui/button/Button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"
import { Input } from "@/ui/input/Input"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import { UploadCard } from "@/ui/upload-card/UploadCard"
import { TabsContent } from "@/ui/primitives/tabs"

type SubmitMode = "arxiv" | "upload"

export function CommunitySubmitPanel() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { config, loadUserSettings } = useTranslationConfig()
  const [mode, setMode] = useState<SubmitMode>("arxiv")
  const [arxivId, setArxivId] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!user) {
    return (
      <LoginPrompt
        messageKey="community.submit.loginRequiredTitle"
        descriptionKey="community.submit.loginRequiredDescription"
      />
    )
  }

  const isArxivMode = mode === "arxiv"
  const isArxivDisabled = isSubmitting || !arxivId.trim()
  const isUploadDisabled = isSubmitting || !selectedFile

  async function handleArxivSubmit() {
    if (isArxivDisabled) {
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      await loadUserSettings()
      const result = await submitCommunityPaperFromArxiv({
        arxiv_id: arxivId.trim(),
        source_language: config.source_language,
        target_language: config.target_language,
      })
      navigate(`/paper/${result.paper.id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleUploadSubmit() {
    if (isUploadDisabled || !selectedFile) {
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      await loadUserSettings()
      const result = await submitCommunityPaperFromUpload(selectedFile, {
        source_language: config.source_language,
        target_language: config.target_language,
      })
      navigate(`/paper/${result.paper.id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("community.submit.errorFallback"))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm">
      <CardHeader className="space-y-3">
        <div className="space-y-1">
          <CardTitle>{t("community.submit.title")}</CardTitle>
          <CardDescription>{t("community.submit.description")}</CardDescription>
        </div>
        <div className="rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-3 text-sm text-[color:var(--px-shell-muted)]">
          <p className="font-medium text-[color:var(--px-shell-ink)]">{t("community.submit.emptyTitle")}</p>
          <p className="mt-1">{t("community.submit.emptyDescription")}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <EditorialTabs value={mode} onValueChange={(value: string) => setMode(value as SubmitMode)} className="space-y-4">
          <EditorialTabsList className="grid w-full grid-cols-2">
            <EditorialTabsTrigger value="arxiv">{t("community.submit.arxivTab")}</EditorialTabsTrigger>
            <EditorialTabsTrigger value="upload">{t("community.submit.uploadTab")}</EditorialTabsTrigger>
          </EditorialTabsList>

          <TabsContent value="arxiv" className="mt-0 space-y-4">
            <div className="space-y-2">
              <label htmlFor="community-submit-arxiv" className="text-sm font-medium">
                {t("community.submit.arxivLabel")}
              </label>
              <Input
                id="community-submit-arxiv"
                aria-label={t("community.submit.arxivLabel")}
                placeholder={t("community.submit.arxivPlaceholder")}
                value={arxivId}
                onChange={(event) => setArxivId(event.target.value)}
                disabled={isSubmitting}
                className="font-mono"
              />
            </div>
            <Button type="button" onClick={handleArxivSubmit} disabled={isArxivDisabled} className="w-full sm:w-auto">
              {isArxivMode && isSubmitting ? t("community.submit.submitting") : t("community.submit.submitArxiv")}
            </Button>
          </TabsContent>

          <TabsContent value="upload" className="mt-0 space-y-4">
            <label htmlFor="community-submit-upload" className="block">
              <span className="sr-only">{t("community.submit.uploadLabel")}</span>
              <UploadCard
                isDragActive={false}
                fileName={selectedFile?.name ?? ""}
                progress={selectedFile ? 100 : 0}
                status={selectedFile ? "success" : "idle"}
                idleTitle={t("community.submit.uploadLabel")}
                idleDescription={t("community.submit.uploadHint")}
                uploadingLabel={t("community.submit.submitting")}
                successActionLabel={t("upload.replace_file")}
                errorLabel={t("community.submit.errorFallback")}
                retryLabel={t("common.actions.retry")}
                onReset={(event) => {
                  event.preventDefault()
                  setSelectedFile(null)
                }}
              />
              <Input
                id="community-submit-upload"
                aria-label={t("community.submit.uploadLabel")}
                type="file"
                accept=".zip,.rar,.tar,.gz,.tgz,.tex"
                disabled={isSubmitting}
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                className="sr-only"
              />
            </label>
            <Button type="button" onClick={handleUploadSubmit} disabled={isUploadDisabled} className="w-full sm:w-auto">
              {!isArxivMode && isSubmitting ? t("community.submit.submitting") : t("community.submit.submitUpload")}
            </Button>
          </TabsContent>
        </EditorialTabs>

        {error ? (
          <div className="rounded-xl border border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] px-4 py-3 text-sm text-[color:var(--px-shell-danger)]">
            {error}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperCard.tsx
Relative path: features\community-paper\components\PaperCard.tsx

```tsx
import { useMemo, useState, type ReactNode } from "react"
import {
  Bookmark,
  Download,
  ExternalLink,
  Eye,
  FileText,
  Github,
  Languages,
  LoaderCircle,
  MessageSquareText,
  Trash2,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { createCommunityPaperDownloadSession } from "@/features/community-paper/services/community-paper-api"
import { prefetchCommunityPaperDetail } from "@/lib/community-api"
import { preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaper } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Pill } from "@/ui/pill/Pill"

interface PaperCardProps {
  paper: CommunityPaper
  onDelete?: (paper: CommunityPaper) => void
  deleting?: boolean
}

interface PdfPreviewFrameProps {
  imageUrl: string | null
  unavailableIcon: ReactNode
  placeholderTone: "neutral" | "accent"
  testId: string
}

function resolveDownloadFilename(
  response: Response,
  fallbackFilename: string,
) {
  const contentDisposition = response.headers.get("content-disposition") ?? ""
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }

  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  return filenameMatch?.[1] ?? fallbackFilename
}

function extractActionErrorMessage(error: unknown): string | null {
  if (typeof error === "string") {
    return error
  }
  if (error instanceof Error) {
    return error.message
  }
  if (!error || typeof error !== "object") {
    return null
  }
  if ("response" in error) {
    const response = error.response
    if (
      response &&
      typeof response === "object" &&
      "data" in response &&
      response.data &&
      typeof response.data === "object" &&
      "detail" in response.data &&
      typeof response.data.detail === "string"
    ) {
      return response.data.detail
    }
  }
  if ("message" in error && typeof error.message === "string") {
    return error.message
  }
  return null
}

function PdfPreviewFrame({
  imageUrl,
  unavailableIcon,
  placeholderTone,
  testId,
}: PdfPreviewFrameProps) {
  const [loadedImageUrl, setLoadedImageUrl] = useState<string | null>(null)
  const [isHovered, setIsHovered] = useState(false)
  const loaded = Boolean(imageUrl) && loadedImageUrl === imageUrl
  const frameTestId = testId.replace(/-image$/, "-frame")

  return (
    <div
      data-testid={frameTestId}
      /* 修改 1：移除 h-full 和 min-h，加入 w-full 和标准 A4 比例 aspect-[210/297] */
      className="relative flex w-full aspect-[210/297] overflow-visible"
      onPointerEnter={() => setIsHovered(true)}
      onPointerLeave={() => setIsHovered(false)}
      onPointerCancel={() => setIsHovered(false)}
      onFocus={() => setIsHovered(true)}
      onBlur={() => setIsHovered(false)}
    >
      <div
        data-testid={testId.replace(/-image$/, "-surface")}
        /* 修改 2：保持 h-full 让它填满上面定义的 A4 比例容器，移除 min-h */
        className={`relative z-0 flex h-full w-full origin-center overflow-hidden rounded-sm border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-[0_18px_48px_-34px_rgba(8,23,38,0.4)] transition-[transform,box-shadow] duration-200 ${isHovered ? "z-10 scale-[1.40] shadow-[0_34px_82px_-28px_rgba(8,23,38,0.62)]" : "scale-100"}
`}
      >
        {imageUrl ? (
          <img
            data-testid={testId}
            src={imageUrl}
            alt=""
            loading="lazy"
            /* 修改 3：恢复 object-contain 和 p-1，保证看到完整原汁原味的 PDF */
            className={`absolute inset-0 h-full w-full object-contain object-top p-1 transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
            onLoad={() => {
              setLoadedImageUrl(imageUrl)
            }}
            onError={() => {
              setLoadedImageUrl(null)
              setIsHovered(false)
            }}
          />
        ) : null}

        <div
          className={`pointer-events-none absolute inset-0 p-4 transition-opacity duration-300 ${loaded ? "opacity-0" : "opacity-100"}`}
        >
          <div className={`mb-3 h-2.5 w-3/4 rounded-full ${placeholderTone === "accent" ? "bg-[color:var(--px-shell-accent-soft)]" : "bg-[color:var(--px-shell-line)]"}`} />
          <div className="mb-2 h-1.5 w-full rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_70%,var(--px-shell-line))]" />
          <div className="mb-2 h-1.5 w-full rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_70%,var(--px-shell-line))]" />
          <div className="mb-6 h-1.5 w-5/6 rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_70%,var(--px-shell-line))]" />
          <div className={`mt-auto h-[58%] rounded-sm ${placeholderTone === "accent" ? "bg-[color:color-mix(in_srgb,var(--px-shell-accent-soft)_70%,white)]" : "bg-[color:var(--px-shell-panel)]"}`} />
        </div>

        {!imageUrl ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[color:var(--px-shell-panel)]/60 text-[color:var(--px-shell-accent)]">
            {unavailableIcon}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .slice(0, 3)
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

function PreviewLink({
  to,
  label,
  testId,
  children,
  onIntent,
}: {
  to: string | null
  label: string
  testId: string
  children: ReactNode
  onIntent: () => void
}) {
  if (!to) {
    return (
      /* 修改 4：移除 h-full，让它自然贴合内部的 A4 比例容器 */
      <div data-testid={testId} className="flex flex-col gap-2">
        {children}
      </div>
    )
  }

  return (
    <Link
      to={to}
      aria-label={label}
      data-testid={testId}
      onMouseEnter={onIntent}
      onFocus={onIntent}
      onPointerDown={onIntent}
      /* 修改 5：同样移除这里的 h-full */
      className="group flex flex-col gap-2 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25"
    >
      {children}
    </Link>
  )
}

export function PaperCard({ paper, onDelete, deleting = false }: PaperCardProps) {
  const { t } = useTranslation()
  const [sourceDownloadPending, setSourceDownloadPending] = useState(false)
  const [downloadPending, setDownloadPending] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  function prefetchDetailNavigation() {
    void prefetchCommunityPaperDetail(paper.id)
    void preloadPaperPreviewEnhancer()
  }

  const sourcePdfUrl =
    paper.source === "arxiv" || Boolean(paper.assets?.source_archive) || Boolean(paper.community_selected_task_id)
      ? `${API_BASE_URL}/api/papers/${paper.id}/source-thumbnail`
      : null
  const translatedPdfUrl =
    paper.trans_status === "completed" &&
      (Boolean(paper.assets?.translated_pdf) || Boolean(paper.community_selected_task_id))
      ? `${API_BASE_URL}/api/papers/${paper.id}/translated-thumbnail`
      : null
  const sourcePdfDocumentUrl =
    paper.source === "arxiv" || Boolean(paper.assets?.source_archive) || Boolean(paper.community_selected_task_id)
      ? `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`
      : null
  const translatedPdfDocumentUrl =
    paper.trans_status === "completed" &&
      (Boolean(paper.assets?.translated_pdf) || Boolean(paper.community_selected_task_id))
      ? `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf`
      : null
  const sourceDownloadUrl = sourcePdfDocumentUrl
    ? `${API_BASE_URL}/api/papers/${paper.id}/source-download`
    : null
  const arxivUrl = paper.arxiv_url ?? (paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : null)
  const githubUrl = paper.github_url ?? null

  const authorsLabel = useMemo(
    () => formatAuthors(paper.authors, t("community.card.authorsUnavailable")),
    [paper.authors, t],
  )
  const abstractText =
    paper.abstract_raw || paper.abstract_translated || t("community.card.abstractPlaceholder")
  const detailHref = `/paper/${paper.id}`

  async function handleSourceDownload() {
    if (!sourceDownloadUrl || sourceDownloadPending) {
      return
    }

    try {
      setActionError(null)
      setSourceDownloadPending(true)
      const response = await fetch(sourceDownloadUrl)
      if (!response.ok) {
        throw new Error(`Source download failed: ${response.status}`)
      }

      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = blobUrl
      link.download = resolveDownloadFilename(
        response,
        `${paper.arxiv_id ?? paper.id}-source.pdf`,
      )
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    } finally {
      setSourceDownloadPending(false)
    }
  }

  async function handleTranslatedDownload() {
    if (downloadPending || !translatedPdfDocumentUrl) {
      return
    }

    try {
      setActionError(null)
      setDownloadPending(true)
      const session = await createCommunityPaperDownloadSession(paper.id)
      const downloadUrl = session.download_url.startsWith("http")
        ? session.download_url
        : `${API_BASE_URL}${session.download_url}`
      window.open(downloadUrl, "_blank", "noopener,noreferrer")
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    } finally {
      setDownloadPending(false)
    }
  }

  return (
    <article className="grid gap-5 rounded-md border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-5 shadow-[var(--px-shell-shadow)] transition-colors duration-200 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
      <div className="flex min-w-0 flex-col justify-between">
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-wrap gap-2">
              {paper.categories.slice(0, 3).map((category) => (
                <Pill key={category} tone="accent" className="px-3 py-1 text-[10px]">
                  {category}
                </Pill>
              ))}
              {paper.categories.length === 0 ? (
                <Pill tone="accent" className="px-3 py-1 text-[10px]">
                  {t("community.card.categoriesUnavailable")}
                </Pill>
              ) : null}
            </div>

            {onDelete ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={deleting}
                onClick={() => onDelete(paper)}
                className="h-9 w-9 text-[color:var(--px-shell-danger)] hover:bg-[color:var(--px-shell-danger-soft)]"
                aria-label={t("community.admin.deleteAction")}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            ) : (
              <Bookmark className="h-5 w-5 shrink-0 text-[color:var(--px-shell-muted)]/45" />
            )}
          </div>

          <div className="space-y-3">
            <Link
              to={detailHref}
              onMouseEnter={prefetchDetailNavigation}
              onFocus={prefetchDetailNavigation}
              onPointerDown={prefetchDetailNavigation}
              className="inline-flex max-w-full rounded-sm outline-none transition-colors duration-200 hover:text-[color:var(--px-shell-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25"
            >
              <h3 className="text-lg font-bold leading-tight text-[color:var(--px-shell-ink)] md:text-[1.28rem]">
                {paper.title}
              </h3>
            </Link>

            <p className="select-text text-sm font-semibold text-[color:var(--px-shell-ink)]/88">
              {authorsLabel}
            </p>

            <p className="select-text text-sm leading-7 text-[color:var(--px-shell-muted)] line-clamp-3">
              {abstractText}
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex w-full flex-row items-center gap-2 pb-1">
              {sourceDownloadUrl ? (
                <Button
                  type="button"
                  variant="action"
                  size="chip"
                  disabled={sourceDownloadPending}
                  onClick={() => void handleSourceDownload()}
                  aria-label={t("community.card.action.downloadSourcePdf")}
                  className="flex-1 min-w-0 px-2"
                >
                  {sourceDownloadPending ? (
                    <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5 shrink-0" />
                  )}
                  <span className="truncate">
                    {sourceDownloadPending
                      ? t("community.card.action.preparingTranslatedPdf")
                      : t("community.card.action.downloadSourcePdf")}
                  </span>
                </Button>
              ) : null}

              {translatedPdfDocumentUrl ? (
                <Button
                  type="button"
                  variant="action"
                  size="chip"
                  disabled={downloadPending}
                  onClick={() => void handleTranslatedDownload()}
                  aria-label={t("community.card.action.downloadTranslatedPdf")}
                  className="flex-1 min-w-0 px-2"
                >
                  {downloadPending ? (
                    <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
                  ) : (
                    <Languages className="h-3.5 w-3.5 shrink-0" />
                  )}
                  <span className="truncate">
                    {downloadPending
                      ? t("community.card.action.preparingTranslatedPdf")
                      : t("community.card.action.downloadTranslatedPdf")}
                  </span>
                </Button>
              ) : null}

              {arxivUrl ? (
                <Button
                  asChild
                  variant="action"
                  size="chip"
                  className="flex-1 min-w-0 px-2"
                >
                  <a
                    href={arxivUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("community.card.action.openArxiv")}
                    className="flex w-full items-center justify-center gap-1.5"
                  >
                    <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{t("community.card.action.openArxiv")}</span>
                  </a>
                </Button>
              ) : null}

              {githubUrl ? (
                <Button
                  asChild
                  variant="action"
                  size="chip"
                  className="flex-1 min-w-0 px-2"
                >
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("community.card.action.openGithub")}
                    className="flex w-full items-center justify-center gap-1.5"
                  >
                    <Github className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{t("community.card.action.openGithub")}</span>
                  </a>
                </Button>
              ) : null}
            </div>

            {actionError ? (
              <p className="text-xs font-medium text-[color:var(--px-shell-danger)]">{actionError}</p>
            ) : null}
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-[color:var(--px-shell-line)] pt-4">
          <div className="flex items-center gap-4 text-xs text-[color:var(--px-shell-muted)] md:text-sm">
            <span className="flex items-center gap-1.5">
              <Eye className="h-4 w-4" />
              {paper.view_count || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <MessageSquareText className="h-4 w-4" />
              {paper.comment_count || 0}
            </span>
          </div>
        </div>
      </div>

      {/* 修改 6：加入 items-start 让右侧网格容器顶部对齐，彻底阻断向下延展 */}
      <div className="grid grid-cols-2 gap-4 items-start">
        <PreviewLink
          to={detailHref}
          label={t("community.detail.originalSource")}
          testId="paper-card-source-preview-link"
          onIntent={prefetchDetailNavigation}
        >
          <PdfPreviewFrame
            imageUrl={sourcePdfUrl}
            unavailableIcon={<FileText className="h-7 w-7" />}
            placeholderTone="neutral"
            testId="paper-card-source-preview-image"
          />
          <span className="px-1 text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {paper.source === "arxiv" ? t("community.detail.originalSource") : t("community.detail.sourceTitle")}
          </span>
        </PreviewLink>

        <PreviewLink
          to={translatedPdfUrl ? detailHref : null}
          label={t("community.detail.mode.translatedPdf")}
          testId="paper-card-translated-preview-link"
          onIntent={prefetchDetailNavigation}
        >
          <PdfPreviewFrame
            imageUrl={translatedPdfUrl}
            unavailableIcon={<Languages className="h-7 w-7" />}
            placeholderTone="accent"
            testId="paper-card-translated-preview-image"
          />
          <span className="px-1 text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {t("community.detail.mode.translatedPdf")}
          </span>
        </PreviewLink>
      </div>
    </article>
  )
}
```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperCardSkeleton.tsx
Relative path: features\community-paper\components\PaperCardSkeleton.tsx

```tsx
import { Skeleton } from "@/ui/primitives/skeleton"

export function PaperCardSkeleton() {
  return (
    <div className="rounded-[28px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6">
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-7 w-28 rounded-full bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-7 w-24 rounded-full bg-[color:var(--px-shell-line)]" />
      </div>
      <div className="mt-5 space-y-3">
        <Skeleton className="h-7 w-4/5 rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-2/3 rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-full rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-full rounded-xl bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-4 w-4/5 rounded-xl bg-[color:var(--px-shell-line)]" />
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <Skeleton className="h-11 rounded-full bg-[color:var(--px-shell-line)]" />
        <Skeleton className="h-11 rounded-full bg-[color:var(--px-shell-line)]" />
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperDetailHeader.tsx
Relative path: features\community-paper\components\PaperDetailHeader.tsx

```tsx
import { useEffect, useRef, useState } from "react"
import { ArrowLeft, Bookmark, Download, Info, Share2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link, useLocation } from "react-router-dom"

import { Button } from "@/ui/button/Button"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"
import { SegmentedControl } from "@/ui/segmented-control/SegmentedControl"
import type { CommunityPaper, CommunityPaperReaderMode } from "@/types/community"

interface PaperDetailHeaderProps {
  paper: CommunityPaper
  selectedMode: CommunityPaperReaderMode
  availableModes: CommunityPaperReaderMode[]
  authorsLabel: string
  canDownload: boolean
  onSelectMode: (mode: CommunityPaperReaderMode) => void
  onDownload: () => void
}

export function PaperDetailHeader({
  paper,
  selectedMode,
  availableModes,
  authorsLabel,
  canDownload,
  onSelectMode,
  onDownload,
}: PaperDetailHeaderProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const shareTimerRef = useRef<number | null>(null)
  const [shareStatus, setShareStatus] = useState<"idle" | "copied">("idle")

  useEffect(() => {
    return () => {
      if (shareTimerRef.current !== null) {
        window.clearTimeout(shareTimerRef.current)
      }
    }
  }, [])

  const publishedLabel = paper.official_published_at
    ? t("community.detail.officialPublishedAt", {
        value: new Date(paper.official_published_at).toLocaleDateString(),
      })
    : paper.created_at
      ? t("community.detail.createdAt", {
          value: new Date(paper.created_at).toLocaleDateString(),
        })
      : t("community.card.dateUnknown")

  const repositoryUrl = paper.github_url?.trim() || null
  const arxivUrl = paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : null
  const categoryLabel =
    paper.categories.length > 0
      ? paper.categories.join(" · ")
      : t("community.card.categoriesUnavailable")

  const modeItems = [
    {
      value: "source" as const,
      label: t("community.detail.mode.source"),
      testId: "paper-detail-mode-source",
    },
    {
      value: "translated_pdf" as const,
      label: t("community.detail.mode.translatedPdf"),
      disabled: !availableModes.includes("translated_pdf"),
      testId: "paper-detail-mode-translated-pdf",
    },
    {
      value: "bilingual_compare" as const,
      label: t("community.detail.mode.bilingualCompare"),
      disabled: !availableModes.includes("bilingual_compare"),
      testId: "paper-detail-mode-bilingual-compare",
    },
  ]

  async function handleShare() {
    const shareUrl =
      typeof window === "undefined"
        ? location.pathname
        : `${window.location.origin}${location.pathname}${location.search}${location.hash}`

    await navigator.clipboard.writeText(shareUrl)
    setShareStatus("copied")
    if (shareTimerRef.current !== null) {
      window.clearTimeout(shareTimerRef.current)
    }
    shareTimerRef.current = window.setTimeout(() => {
      setShareStatus("idle")
      shareTimerRef.current = null
    }, 1800)
  }

  return (
    <nav className="sticky top-0 z-10 shrink-0 border-b border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]/88 backdrop-blur-xl">
      <div className="grid min-h-12 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 px-2 py-1.5 md:px-3">
        <div className="flex items-center justify-start">
          <Button
            asChild
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Link to="/" aria-label={t("community.detail.backToFeed")} title={t("community.detail.backToFeed")}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
        </div>

        <div className="flex justify-center px-1 xl:justify-start xl:pl-[12%] 2xl:pl-[14%]">
          <SegmentedControl
            value={selectedMode}
            onValueChange={onSelectMode}
            items={modeItems}
            className="w-full max-w-[34rem] rounded-[12px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_78%,white)] bg-transparent p-0.5 shadow-none"
            itemClassName="min-h-8 rounded-[8px] px-3 text-[12px] font-semibold normal-case tracking-normal md:min-h-9 md:px-4"
          />
        </div>

        <div className="flex items-center justify-end gap-1">
          <span
            aria-live="polite"
            className={`mr-1 text-[11px] font-medium text-[color:var(--px-shell-accent)] transition-opacity duration-200 ${
              shareStatus === "copied" ? "opacity-100" : "opacity-0"
            }`}
          >
            {shareStatus === "copied" ? t("community.detail.shareCopied") : " "}
          </span>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={t("community.detail.favoriteAction")}
            title={t("community.detail.favoriteAction")}
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Bookmark className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            disabled={!canDownload}
            onClick={onDownload}
            aria-label={t("community.card.action.downloadTranslatedPdf")}
            title={t("community.card.action.downloadTranslatedPdf")}
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Download className="h-4 w-4" />
          </Button>

          <Popover>
            <PopoverTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t("community.detail.infoAction")}
                title={t("community.detail.infoAction")}
                className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
              >
                <Info className="h-4 w-4" />
              </Button>
            </PopoverTrigger>

            <PopoverContent
              align="end"
              side="bottom"
              sideOffset={8}
              className="w-[22rem] rounded-[20px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_28px_60px_-38px_rgba(15,23,42,0.4)]"
            >
              <div className="space-y-3">
                <div className="space-y-1 rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
                    {t("community.detail.infoTitle")}
                  </p>
                  <p className="text-sm font-semibold leading-6 text-[color:var(--px-shell-ink)]">
                    {paper.title}
                  </p>
                </div>

                <div className="space-y-2">
                  <InfoRow label={t("community.detail.infoAuthors")} value={authorsLabel} />
                  <InfoRow label={t("community.detail.infoPublished")} value={publishedLabel} />
                  <InfoRow label={t("community.detail.infoCategories")} value={categoryLabel} />
                  {paper.arxiv_id ? (
                    <InfoRow label={t("community.detail.infoArxivId")} value={paper.arxiv_id} />
                  ) : null}
                </div>

                <div className="space-y-2 rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-3">
                  {arxivUrl ? (
                    <div className="space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
                        {t("community.detail.infoArxiv")}
                      </p>
                      <a
                        href={arxivUrl}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                      >
                        {paper.arxiv_id}
                      </a>
                    </div>
                  ) : null}

                  {repositoryUrl ? (
                    <div className="space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
                        {t("community.detail.infoRepository")}
                      </p>
                      <a
                        href={repositoryUrl}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex break-all text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                      >
                        {repositoryUrl}
                      </a>
                    </div>
                  ) : null}
                </div>
              </div>
            </PopoverContent>
          </Popover>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => void handleShare()}
            aria-label={t("community.detail.shareAction")}
            title={t("community.detail.shareAction")}
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Share2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </nav>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[14px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-2.5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
        {label}
      </p>
      <p className="mt-1 text-sm leading-6 text-[color:var(--px-shell-ink)]">{value}</p>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperDetailScreen.tsx
Relative path: features\community-paper\components\PaperDetailScreen.tsx

```tsx
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"

import { API_BASE_URL } from "@/api-base"
import { usePaperDetail } from "@/features/community-paper/hooks/use-paper-detail"
import { createCommunityPaperDownloadSession } from "@/features/community-paper/services/community-paper-api"
import type { CommunityPaperReaderMode } from "@/types/community"

import { PaperDetailHeader } from "./PaperDetailHeader"
import { PaperDetailStateBoundary } from "./PaperDetailStateBoundary"
import { PaperDetailWorkspace } from "./PaperDetailWorkspace"
import { resolveAvailableModes, resolvePreferredMode } from "../utils/paper-detail-mode-resolution"

function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

function extractActionErrorMessage(error: unknown): string | null {
  if (typeof error === "string") {
    return error
  }
  if (error instanceof Error) {
    return error.message
  }
  if (!error || typeof error !== "object") {
    return null
  }
  if ("response" in error) {
    const response = error.response
    if (
      response &&
      typeof response === "object" &&
      "data" in response &&
      response.data &&
      typeof response.data === "object" &&
      "detail" in response.data &&
      typeof response.data.detail === "string"
    ) {
      return response.data.detail
    }
  }
  if ("message" in error && typeof error.message === "string") {
    return error.message
  }
  return null
}

interface PaperDetailScreenProps {
  paperId: string | null
}

export function PaperDetailScreen({ paperId }: PaperDetailScreenProps) {
  const { t } = useTranslation()
  const {
    paper,
    preview,
    readerState,
    reader,
    structuredInsights,
    loading,
    error,
    notFound,
  } = usePaperDetail(paperId ?? undefined)
  const [selectedModeState, setSelectedModeState] = useState<{
    paperId: string | null
    mode: CommunityPaperReaderMode | null
  }>({
    paperId: null,
    mode: null,
  })
  const [actionError, setActionError] = useState<string | null>(null)

  const availableModes = useMemo<CommunityPaperReaderMode[]>(
    () => resolveAvailableModes(paper, preview, reader),
    [paper, preview, reader],
  )

  const derivedPreferredMode = useMemo(
    () => resolvePreferredMode(reader?.preferred_mode, availableModes),
    [availableModes, reader?.preferred_mode],
  )
  const selectedMode =
    selectedModeState.paperId === paperId &&
    selectedModeState.mode &&
    availableModes.includes(selectedModeState.mode)
      ? selectedModeState.mode
      : derivedPreferredMode

  function handleSelectMode(nextMode: CommunityPaperReaderMode) {
    setSelectedModeState({
      paperId,
      mode: nextMode,
    })
  }

  async function handleDownload() {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      const session = await createCommunityPaperDownloadSession(paperId)
      const downloadUrl = session.download_url.startsWith("http")
        ? session.download_url
        : `${API_BASE_URL}${session.download_url}`
      window.open(downloadUrl, "_blank")
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    }
  }

  return (
    <PaperDetailStateBoundary
      loading={loading}
      error={error}
      notFound={notFound}
      paper={paper}
    >
      {(activePaper) => {
        const authorsLabel = formatAuthors(activePaper.authors, t("community.card.authorsUnavailable"))
        const canDownload = activePaper.trans_status === "completed"
        const originalSourceUrl =
          reader?.source?.url ??
          (activePaper.arxiv_id ? `https://arxiv.org/abs/${activePaper.arxiv_id}` : null)
        const abstractText =
          (selectedMode === "source" ? activePaper.abstract_raw : activePaper.abstract_translated) ||
          activePaper.abstract_raw ||
          activePaper.abstract_translated ||
          t("community.detail.abstractUnavailable")

        return (
          <div className="flex flex-col min-h-0 min-w-0 flex-1 bg-[color:var(--px-shell-bg)] px-2 py-2 md:px-3 md:py-3">
            <div
              data-testid="paper-detail-page-shell"
              className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[8px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]"
            >
              <PaperDetailHeader
                paper={activePaper}
                selectedMode={selectedMode}
                availableModes={availableModes}
                authorsLabel={authorsLabel}
                canDownload={canDownload}
                onSelectMode={handleSelectMode}
                onDownload={() => void handleDownload()}
              />

              <div className="relative flex min-h-0 min-w-0 flex-1 overflow-hidden bg-[color:var(--px-shell-panel-strong)]">
                <PaperDetailWorkspace
                  key={activePaper.id}
                  paper={activePaper}
                  preview={preview}
                  readerState={readerState}
                  reader={reader}
                  preferredMode={selectedMode}
                  structuredInsights={structuredInsights}
                  originalSourceUrl={originalSourceUrl}
                  abstractText={abstractText}
                  canDownload={canDownload}
                  actionError={actionError}
                />
              </div>
            </div>
          </div>
        )
      }}
    </PaperDetailStateBoundary>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperDetailSkeleton.tsx
Relative path: features\community-paper\components\PaperDetailSkeleton.tsx

```tsx
import { Skeleton } from "@/ui/primitives/skeleton"

export function PaperDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-6 w-28 rounded-xl bg-[color:var(--px-shell-line)]" />
      <div className="rounded-[32px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-8">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Skeleton className="h-7 w-28 rounded-full bg-[color:var(--px-shell-line)]" />
            <Skeleton className="h-7 w-24 rounded-full bg-[color:var(--px-shell-line)]" />
          </div>
          <Skeleton className="h-10 w-4/5 rounded-xl bg-[color:var(--px-shell-line)]" />
          <Skeleton className="h-5 w-2/3 rounded-xl bg-[color:var(--px-shell-line)]" />
        </div>
        <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.8fr)]">
          <div className="space-y-4">
            <Skeleton className="h-48 rounded-[28px] bg-[color:var(--px-shell-line)]" />
            <Skeleton className="h-36 rounded-[28px] bg-[color:var(--px-shell-line)]" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-36 rounded-[28px] bg-[color:var(--px-shell-line)]" />
            <Skeleton className="h-52 rounded-[28px] bg-[color:var(--px-shell-line)]" />
          </div>
        </div>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperDetailStateBoundary.tsx
Relative path: features\community-paper\components\PaperDetailStateBoundary.tsx

```tsx
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import type { CommunityPaper } from "@/types/community"
import { StatePanel } from "@/ui/state-panel/StatePanel"

import { PaperDetailSkeleton } from "./PaperDetailSkeleton"

interface PaperDetailStateBoundaryProps {
  loading: boolean
  error: string | null
  notFound: boolean
  paper: CommunityPaper | null
  children: (paper: CommunityPaper) => ReactNode
}

export function PaperDetailStateBoundary({
  loading,
  error,
  notFound,
  paper,
  children,
}: PaperDetailStateBoundaryProps) {
  const { t } = useTranslation()

  if (loading) {
    return <PaperDetailSkeleton />
  }

  if (error && !notFound) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <StatePanel
          tone="danger"
          className="w-full max-w-lg py-12"
          title={t("community.detail.errorTitle")}
          description={t("community.detail.errorDescription")}
          detail={<p className="text-sm text-[color:var(--px-shell-danger)]">{error}</p>}
        />
      </div>
    )
  }

  if (notFound || !paper) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <StatePanel
          className="w-full max-w-lg py-12"
          title={t("community.detail.notFoundTitle")}
          description={t("community.detail.notFoundDescription")}
        />
      </div>
    )
  }

  return <>{children(paper)}</>
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperDetailWorkspace.tsx
Relative path: features\community-paper\components\PaperDetailWorkspace.tsx

```tsx
import DOMPurify from "dompurify"
import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { getCommunityPaperSimilar } from "@/features/community-paper/services/community-paper-api"
import { stripLeadingDuplicatePaperHeaderHtml } from "@/lib/paper-reader-html"
import { cn } from "@/lib/utils"
import { DisclosureCard } from "@/ui/disclosure-card/DisclosureCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import type {
  CommunityPaper,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  CommunityPaperReaderMode,
  CommunityPaperSimilarItem,
  StructuredInsightBlock,
  StructuredInsightSection,
  StructuredInsightSectionKey,
  StructuredInsightsPayload,
} from "@/types/community"

const SPLIT_STORAGE_KEY = "community-paper-reader-split-ratio-v2"
const DEFAULT_SPLIT_RATIO = 0.8
const MIN_READER_WIDTH = 720
const MIN_SIDEBAR_WIDTH = 260
const GUIDE_SECTION_ORDER = [
  "problem",
  "solution",
  "innovation",
  "experiment",
  "future",
] as const

interface PaperDetailWorkspaceProps {
  paper: CommunityPaper
  preview: CommunityPaperPreviewResponse | null
  readerState: "ready" | "warming" | "unavailable"
  reader: CommunityPaperReader | null
  preferredMode: CommunityPaperReaderMode
  structuredInsights: StructuredInsightsPayload | null
  originalSourceUrl: string | null
  abstractText: string
  canDownload: boolean
  actionError: string | null
}

function isTranslatedPdfMode(mode: CommunityPaperReaderMode) {
  return mode === "translated" || mode === "translated_pdf"
}

function isBilingualCompareMode(mode: CommunityPaperReaderMode) {
  return mode === "bilingual_compare"
}

function buildPdfViewerUrl(url: string) {
  const viewerParams = "page=1&view=Fit&pagemode=none&toolbar=0&navpanes=0&scrollbar=0"
  return url.includes("#") ? `${url}&${viewerParams}` : `${url}#${viewerParams}`
}

function resolvePdfDocumentUrl(
  fallbackUrl: string,
  resource: { kind?: string | null; url?: string | null } | null | undefined,
  expectedKind: "source_pdf" | "translated_pdf",
) {
  const candidateUrl = String(resource?.url || "").trim()
  if ((resource?.kind ?? null) !== expectedKind || !candidateUrl) {
    return fallbackUrl
  }
  if (candidateUrl.startsWith("http://") || candidateUrl.startsWith("https://")) {
    return candidateUrl
  }
  if (candidateUrl.startsWith("/")) {
    return `${API_BASE_URL}${candidateUrl}`
  }
  return fallbackUrl
}

function clampSplitRatio(ratio: number, width: number) {
  if (!Number.isFinite(ratio) || !Number.isFinite(width) || width <= 0) {
    return DEFAULT_SPLIT_RATIO
  }

  const minRatio = MIN_READER_WIDTH / width
  const maxRatio = 1 - MIN_SIDEBAR_WIDTH / width

  return Math.min(Math.max(ratio, minRatio), maxRatio)
}

function isGuideSectionKey(sectionKey: string): sectionKey is StructuredInsightSectionKey {
  return GUIDE_SECTION_ORDER.includes(sectionKey as StructuredInsightSectionKey)
}

function getInsightLabel(sectionKey: StructuredInsightSectionKey, t: (key: string) => string) {
  switch (sectionKey) {
    case "problem":
      return t("community.detail.insights.section.problem")
    case "solution":
      return t("community.detail.insights.section.solution")
    case "innovation":
      return t("community.detail.insights.section.innovation")
    case "experiment":
      return t("community.detail.insights.section.experiment")
    case "future":
      return t("community.detail.insights.section.future")
  }
}

interface ParsedInsightContent {
  summary: string | null
  sections: Array<{
    title: string
    body: string
  }>
  paragraphs: string[]
}

const INLINE_INSIGHT_SECTION_TITLES = [
  "问题本质",
  "现有方法的局限",
  "现有方法的关键不足",
  "为什么重要",
  "研究动机",
  "核心难点",
  "核心思路",
  "方法整体",
  "关键流程",
  "整体流程",
  "模块协同",
  "方法机制",
  "Pipeline",
  "pipeline",
  "关键创新点",
  "本质差异",
  "为什么不一样",
  "新意所在",
  "差异来源",
  "核心指标",
  "对比结果",
  "实验结论",
  "主要结论",
  "评估方式",
  "实验设置",
  "当前局限",
  "真实局限",
  "潜在局限",
  "改进方向",
  "扩展方向",
  "研究启发",
] as const

const INLINE_INSIGHT_SECTION_TITLE_SET = new Set<string>(INLINE_INSIGHT_SECTION_TITLES)

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function normalizeInsightTitleLine(line: string) {
  const normalized = line
    .replace(/^[#*\-\s>\d.)]+/, "")
    .replace(/[：:]\s*$/, "")
    .trim()

  return INLINE_INSIGHT_SECTION_TITLE_SET.has(normalized) ? normalized : null
}

function extractHeuristicTitledBlock(block: string) {
  const lines = block
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length < 2) {
    return null
  }

  const firstLine = lines[0]
  if (firstLine.length > 14 || /[.?!:。！？：]/.test(firstLine)) {
    return null
  }

  return {
    lead: "",
    sections: [
      {
        title: firstLine,
        body: lines.slice(1).join("\n"),
      },
    ],
  }
}

function normalizeStructuredInsightBlock(block: StructuredInsightBlock | null | undefined) {
  const heading = block?.heading?.trim()
  const content = block?.content?.trim()
  if (!heading || !content) {
    return null
  }
  return {
    title: heading,
    body: content,
  }
}

function resolveInsightContent(section: StructuredInsightSection): ParsedInsightContent | null {
  const normalizedBlocks = (section.blocks ?? [])
    .map((block) => normalizeStructuredInsightBlock(block))
    .filter((block): block is NonNullable<ReturnType<typeof normalizeStructuredInsightBlock>> => Boolean(block))
  const normalizedSummary = section.summary?.trim() ?? null

  if (normalizedSummary || normalizedBlocks.length > 0) {
    return {
      summary: normalizedSummary,
      sections: normalizedBlocks,
      paragraphs: [],
    }
  }

  const fallbackContent = section.content?.trim() || section.raw_content?.trim() || ""
  return fallbackContent ? parseInsightContent(fallbackContent) : null
}

function extractLineTitledSections(block: string) {
  const lines = block
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length < 2) {
    return null
  }

  const sections: ParsedInsightContent["sections"] = []
  const introLines: string[] = []
  let currentTitle: string | null = null
  let currentBody: string[] = []

  const pushCurrentSection = () => {
    if (!currentTitle) {
      return
    }

    const body = currentBody.join("\n").trim()
    if (body) {
      sections.push({ title: currentTitle, body })
    }

    currentTitle = null
    currentBody = []
  }

  for (const line of lines) {
    const knownTitle = normalizeInsightTitleLine(line)
    if (knownTitle) {
      pushCurrentSection()
      currentTitle = knownTitle
      continue
    }

    if (currentTitle) {
      currentBody.push(line)
    } else {
      introLines.push(line)
    }
  }

  pushCurrentSection()

  if (sections.length === 0) {
    return null
  }

  return {
    lead: introLines.join("\n").trim(),
    sections,
  }
}

function extractInlineTitledSections(block: string) {
  const titlePattern = INLINE_INSIGHT_SECTION_TITLES
    .slice()
    .sort((left, right) => right.length - left.length)
    .map(escapeRegExp)
    .join("|")
  const matcher = new RegExp(`(?:^|\\s)(${titlePattern})(?:\\s*[：:]|\\s+)`, "g")
  const matches = Array.from(block.matchAll(matcher))

  if (matches.length === 0) {
    return null
  }

  const sections: ParsedInsightContent["sections"] = []
  const lead = block.slice(0, matches[0].index ?? 0).trim()

  for (let index = 0; index < matches.length; index += 1) {
    const currentMatch = matches[index]
    const nextMatch = matches[index + 1]
    const title = currentMatch[1]?.trim() ?? ""
    const bodyStart = (currentMatch.index ?? 0) + currentMatch[0].length
    const bodyEnd = nextMatch?.index ?? block.length
    const body = block.slice(bodyStart, bodyEnd).trim()

    if (title && body) {
      sections.push({ title, body })
    }
  }

  if (sections.length === 0) {
    return null
  }

  return { lead, sections }
}

function parseInsightContent(content: string): ParsedInsightContent {
  const normalized = content
    .split(/\r?\n\s*\r?\n/g)
    .map((block) => block.trim())
    .filter(Boolean)

  if (normalized.length === 0) {
    return { summary: null, sections: [], paragraphs: [] }
  }

  const [summaryBlock, ...restBlocks] = normalized
  const sections: ParsedInsightContent["sections"] = []
  const paragraphs: string[] = []
  let summary = summaryBlock || null

  const structuredSummaryBlock =
    extractLineTitledSections(summaryBlock) ??
    extractHeuristicTitledBlock(summaryBlock) ??
    extractInlineTitledSections(summaryBlock)

  if (structuredSummaryBlock) {
    summary = structuredSummaryBlock.lead || null
    sections.push(...structuredSummaryBlock.sections)
  }

  for (const block of restBlocks) {
    const lines = block
      .split(/\r?\n/g)
      .map((line) => line.trim())
      .filter(Boolean)

    if (
      lines.length >= 2 &&
      lines[0].length <= 14 &&
      !/[。！？：:；;]/.test(lines[0])
    ) {
      sections.push({
        title: lines[0],
        body: lines.slice(1).join("\n"),
      })
      continue
    }

    const inlineTitledContent = extractInlineTitledSections(block)
    if (inlineTitledContent) {
      if (inlineTitledContent.lead) {
        paragraphs.push(inlineTitledContent.lead)
      }

      sections.push(...inlineTitledContent.sections)
      continue
    }

    paragraphs.push(block)
  }

  return {
    summary,
    sections,
    paragraphs,
  }
}

export function PaperDetailWorkspace({
  paper,
  preview: _preview,
  readerState,
  reader,
  preferredMode,
  structuredInsights,
  originalSourceUrl,
  abstractText,
  canDownload,
  actionError,
}: PaperDetailWorkspaceProps) {
  void _preview
  void readerState
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [splitRatio, setSplitRatio] = useState(() => {
    if (typeof window === "undefined") {
      return DEFAULT_SPLIT_RATIO
    }

    const stored = Number(window.localStorage.getItem(SPLIT_STORAGE_KEY) ?? DEFAULT_SPLIT_RATIO)
    return Number.isFinite(stored) ? stored : DEFAULT_SPLIT_RATIO
  })
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window === "undefined" ? true : window.innerWidth >= 1024,
  )
  const [activeTab, setActiveTab] = useState<"insights" | "similar">("insights")
  const [expandedInsightKey, setExpandedInsightKey] = useState<string>("")
  const [similarState, setSimilarState] = useState<"idle" | "loading" | "ready" | "error">("idle")
  const [similarItems, setSimilarItems] = useState<CommunityPaperSimilarItem[]>([])
  const [expandedSimilarKey, setExpandedSimilarKey] = useState<string>("")

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SPLIT_STORAGE_KEY, String(splitRatio))
    }
  }, [splitRatio])

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined
    }

    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024)
    }

    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  function handleResizeStart(event: ReactPointerEvent<HTMLDivElement>) {
    const container = containerRef.current
    if (!container) {
      return
    }

    event.preventDefault()
    const rect = container.getBoundingClientRect()

    const handlePointerMove = (pointerEvent: PointerEvent) => {
      const nextWidth = pointerEvent.clientX - rect.left
      const nextRatio = clampSplitRatio(nextWidth / rect.width, rect.width)
      setSplitRatio(nextRatio)
    }

    const handlePointerUp = () => {
      window.removeEventListener("pointermove", handlePointerMove)
      window.removeEventListener("pointerup", handlePointerUp)
    }

    window.addEventListener("pointermove", handlePointerMove)
    window.addEventListener("pointerup", handlePointerUp)
  }

  useEffect(() => {
    if (activeTab !== "similar" || similarState !== "loading") {
      return
    }

    let cancelled = false
    void getCommunityPaperSimilar(paper.id)
      .then((response) => {
        if (cancelled) {
          return
        }
        setSimilarItems(response.items ?? [])
        setExpandedSimilarKey("")
        setSimilarState("ready")
      })
      .catch(() => {
        if (cancelled) {
          return
        }
        setSimilarItems([])
        setSimilarState("error")
      })

    return () => {
      cancelled = true
    }
  }, [activeTab, paper.id, similarState])

  const sourceHtmlContent =
    preferredMode === "source" && reader?.source?.kind === "source_html"
      ? (reader.source.html_content ?? null)
      : null
  const sourceDocumentUrl = resolvePdfDocumentUrl(
    `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`,
    reader?.source,
    "source_pdf",
  )
  const translatedPdfUrl = resolvePdfDocumentUrl(
    `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf`,
    reader?.translated,
    "translated_pdf",
  )
  const sourcePdfViewerUrl = buildPdfViewerUrl(sourceDocumentUrl)
  const translatedPdfViewerUrl = buildPdfViewerUrl(translatedPdfUrl)
  const sanitizedSourceHtml = useMemo(
    () =>
      sourceHtmlContent
        ? DOMPurify.sanitize(stripLeadingDuplicatePaperHeaderHtml(sourceHtmlContent, paper) ?? "")
        : null,
    [paper, sourceHtmlContent],
  )
  const selectedInsights = useMemo<StructuredInsightSection[]>(() => {
    const guideSections = structuredInsights?.sections ?? []
    const sectionMap = new Map<StructuredInsightSectionKey, StructuredInsightSection>()
    for (const section of guideSections) {
      if (isGuideSectionKey(section.section_key) && !sectionMap.has(section.section_key)) {
        sectionMap.set(section.section_key, section)
      }
    }

    return GUIDE_SECTION_ORDER.flatMap((sectionKey) => {
      const section = sectionMap.get(sectionKey)
      return section ? [section] : []
    })
  }, [structuredInsights?.sections])
  const hasGuideSections = selectedInsights.length > 0
  const desktopGridColumns = `${splitRatio}fr 12px ${Math.max(1 - splitRatio, 0.18)}fr`

  function handleSelectTab(nextTab: "insights" | "similar") {
    setActiveTab(nextTab)

    if (nextTab === "similar") {
      setSimilarState((currentState) => (currentState === "idle" ? "loading" : currentState))
    }
  }

  return (
    <div
      ref={containerRef}
      data-testid="paper-detail-top-panels"
      className={cn(
        "flex-1 min-h-0 min-w-0 w-full h-full relative",
        isDesktop ? "grid" : "flex flex-col overflow-y-auto",
      )}
      style={isDesktop ? { gridTemplateColumns: desktopGridColumns } : undefined}
    >
      <section
        data-testid="paper-detail-reader-panel"
        className={cn(
          "flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[color:var(--px-shell-panel-strong)]",
          isDesktop ? "" : "border-b border-[color:var(--px-shell-line)] min-h-[50vh]",
        )}
      >
        <div data-testid="paper-reader-scroll-root" className="relative flex-1 overflow-auto bg-[color:var(--px-shell-panel-strong)]">
          {preferredMode === "source" ? (
            sourceDocumentUrl ? (
              <iframe
                data-testid="paper-source-pdf-reader"
                title={`${paper.title} PDF`}
                src={sourcePdfViewerUrl}
                className="h-full w-full border-0 bg-[color:var(--px-shell-panel-strong)]"
              />
            ) : sanitizedSourceHtml ? (
              <article
                data-testid="paper-source-reader"
                className="h-full bg-[color:var(--px-shell-panel-strong)] px-6 py-6 text-[color:var(--px-shell-ink)] sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-[color:var(--px-shell-muted)] [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8"
                dangerouslySetInnerHTML={{ __html: sanitizedSourceHtml }}
              />
            ) : (
              <article data-testid="paper-source-reader" className="flex h-full flex-col gap-4 px-10 py-8">
                {originalSourceUrl ? (
                  <a
                    href={originalSourceUrl}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-2 text-sm text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                  >
                    {t("community.detail.originalSource")}
                  </a>
                ) : null}
              </article>
            )
          ) : isTranslatedPdfMode(preferredMode) && canDownload ? (
            <iframe
              data-testid="paper-translated-pdf-reader"
              title={`${paper.title} Translated PDF`}
              src={translatedPdfViewerUrl}
              className="h-full w-full border-0 bg-[color:var(--px-shell-panel-strong)]"
            />
          ) : isBilingualCompareMode(preferredMode) && canDownload ? (
            <div className="grid h-full min-h-0 grid-cols-2 gap-1 bg-[color:var(--px-shell-panel-strong)] p-1">
              <iframe
                data-testid="paper-bilingual-source-pdf-reader"
                title={`${paper.title} Source PDF`}
                src={sourcePdfViewerUrl}
                className="h-full w-full border-0 bg-[color:var(--px-shell-panel-strong)]"
              />
              <iframe
                data-testid="paper-bilingual-translated-pdf-reader"
                title={`${paper.title} Translated PDF Compare`}
                src={translatedPdfViewerUrl}
                className="h-full w-full border-0 bg-[color:var(--px-shell-panel-strong)]"
              />
            </div>
          ) : (
            <article className="flex h-full flex-col gap-4 px-10 py-8">
              <p className="max-w-4xl text-base leading-8 text-[color:var(--px-shell-muted)]">{abstractText}</p>
            </article>
          )}
        </div>
      </section>

      {isDesktop ? (
        <div
          data-testid="paper-detail-resize-handle"
          role="separator"
          aria-orientation="vertical"
          onPointerDown={handleResizeStart}
          className="group flex cursor-col-resize items-stretch justify-center w-3 h-full z-10 -ml-1.5"
        >
          <div className="flex h-full w-full items-center justify-center transition-colors group-hover:bg-[color:var(--px-shell-accent-soft)]">
            <div className="h-16 w-1 rounded-full bg-[color:var(--px-shell-line)] group-hover:bg-[color:var(--px-shell-accent)] transition-colors" />
          </div>
        </div>
      ) : null}

      <aside
        data-testid="paper-detail-agent-panel"
        className={cn(
          "relative flex min-h-0 min-w-0 shrink-0 flex-col overflow-hidden bg-[color:var(--px-shell-panel-strong)]",
          isDesktop ? "h-full px-3 py-3 pl-0" : "min-h-[500px] p-3",
        )}
      >
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-none border border-[color:color-mix(in_srgb,var(--px-shell-line)_82%,white)] bg-[color:var(--px-shell-panel)] shadow-[0_24px_60px_-42px_rgba(15,23,42,0.28)]">
          <div data-testid="paper-detail-insights-panel" className="contents" />
          <EditorialTabs
            value={activeTab}
            onValueChange={(nextValue) => handleSelectTab(nextValue as "insights" | "similar")}
            className="flex min-h-0 flex-1 flex-col"
          >
            <EditorialTabsList className="mx-4 mt-4 shrink-0 rounded-none bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_88%,white)]">
              <EditorialTabsTrigger value="insights" className="rounded-none">
                {t("community.detail.tab.insights")}
              </EditorialTabsTrigger>
              <EditorialTabsTrigger value="similar" className="rounded-none">
                {t("community.detail.tab.similar")}
              </EditorialTabsTrigger>
            </EditorialTabsList>

            {activeTab === "insights" ? (
              <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 pt-5 space-y-3">
                {actionError ? (
                  <NoticeBanner tone="danger" description={actionError} className="rounded-none" />
                ) : null}

                {structuredInsights?.state === "processing" || structuredInsights?.state === "queued" ? (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    title={t("community.detail.insightsPendingTitle")}
                    description={t("community.detail.insightsPendingDescription")}
                  />
                ) : hasGuideSections ? (
                  selectedInsights.map((section) => {
                    const expanded = expandedInsightKey === section.section_key
                    const parsedContent = resolveInsightContent(section)

                    return (
                      <DisclosureCard
                        key={section.section_key}
                        open={expanded}
                        onOpenChange={(nextOpen) => setExpandedInsightKey(nextOpen ? section.section_key : "")}
                        title={getInsightLabel(section.section_key, t)}
                      >
                        {parsedContent ? (
                          <div className="space-y-3">
                            {parsedContent.summary ? (
                              <p className="font-medium leading-7 text-[color:var(--px-shell-ink)] whitespace-pre-wrap">
                                {parsedContent.summary}
                              </p>
                            ) : null}
                            {parsedContent.sections.map((item) => (
                              <div
                                key={`${section.section_key}-${item.title}`}
                                className="space-y-1.5 border-l-2 border-[color:var(--px-shell-line)] pl-3"
                              >
                                <p className="text-[12px] font-semibold tracking-[0.06em] text-[color:var(--px-shell-ink)]/85">
                                  {item.title}
                                </p>
                                <p className="whitespace-pre-wrap leading-7 text-[color:var(--px-shell-ink)]">{item.body}</p>
                              </div>
                            ))}
                            {parsedContent.paragraphs.map((paragraph, index) => (
                              <p
                                key={`${section.section_key}-paragraph-${index}`}
                                className="whitespace-pre-wrap leading-7 text-[color:var(--px-shell-ink)]"
                              >
                                {paragraph}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p>{t("community.detail.insights.languagePending")}</p>
                        )}
                      </DisclosureCard>
                    )
                  })
                ) : (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    borderStyle="dashed"
                    title={t("community.detail.insightsEmptyTitle")}
                    description={t("community.detail.insightsEmptyDescription")}
                  />
                )}
              </div>
            ) : (
              <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 pt-5">
                {similarState === "loading" ? (
                  <NoticeBanner title={t("community.detail.similar.loading")} />
                ) : null}

                {similarState === "error" ? (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    tone="danger"
                    title={t("community.detail.similar.errorTitle")}
                    description={t("community.detail.similar.errorDescription")}
                  />
                ) : null}

                {similarState === "ready" && similarItems.length === 0 ? (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    borderStyle="dashed"
                    title={t("community.detail.similar.emptyTitle")}
                    description={t("community.detail.similar.emptyDescription")}
                  />
                ) : null}

                {similarState === "ready" && similarItems.length > 0 ? (
                  <div className="space-y-3">
                    {similarItems.map((item) => {
                      const itemKey = `${item.arxiv_id}-${item.community_paper_id ?? item.arxiv_url}`
                      const expanded = expandedSimilarKey === itemKey
                      const destination = item.community_paper_id ? (
                        <Link
                          to={`/paper/${item.community_paper_id}`}
                          className="inline-flex text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                        >
                          {t("community.detail.similar.openInCommunity")}
                        </Link>
                      ) : (
                        <a
                          href={item.arxiv_url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                        >
                          {t("community.detail.similar.openInArxiv")}
                        </a>
                      )

                      return (
                        <DisclosureCard
                          key={itemKey}
                          open={expanded}
                          onOpenChange={(nextOpen) => setExpandedSimilarKey(nextOpen ? itemKey : "")}
                          eyebrow={item.arxiv_id}
                          title={item.title}
                          headerAside={destination}
                        >
                          <p className="text-xs leading-6 text-[color:var(--px-shell-muted)]">{item.abstract}</p>
                        </DisclosureCard>
                      )
                    })}
                  </div>
                ) : null}
              </div>
            )}
          </EditorialTabs>
        </div>
      </aside>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperFeedEmptyState.tsx
Relative path: features\community-paper\components\PaperFeedEmptyState.tsx

```tsx
import { Inbox } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

export function PaperFeedEmptyState() {
  const { t } = useTranslation()

  return (
    <StatePanel
      borderStyle="dashed"
      icon={<Inbox className="h-7 w-7" />}
      title={t("community.empty.title")}
      description={t("community.empty.description")}
      actions={(
        <Button
          asChild
          variant="outline"
          className="h-11 rounded-2xl border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]"
        >
          <Link to="/translate">{t("community.empty.cta")}</Link>
        </Button>
      )}
    />
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperFeedErrorState.tsx
Relative path: features\community-paper\components\PaperFeedErrorState.tsx

```tsx
import { AlertTriangle, RefreshCcw } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

interface PaperFeedErrorStateProps {
  onRetry: () => void
}

export function PaperFeedErrorState({ onRetry }: PaperFeedErrorStateProps) {
  const { t } = useTranslation()

  return (
    <StatePanel
      tone="danger"
      icon={<AlertTriangle className="h-7 w-7" />}
      title={t("community.error.title")}
      description={t("community.error.description")}
      actions={(
        <Button
          type="button"
          onClick={onRetry}
          variant="outline"
          className="h-11 rounded-2xl border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-ink)]"
        >
          <RefreshCcw className="h-4 w-4" />
          {t("community.error.retry")}
        </Button>
      )}
    />
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperPreviewReader.tsx
Relative path: features\community-paper\components\PaperPreviewReader.tsx

```tsx
import DOMPurify from "dompurify"
import { forwardRef, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/ui/primitives/sheet"
import { getCommunityPaperPreview } from "@/features/community-paper/services/community-paper-api"
import { stripLeadingDuplicatePaperHeaderHtml, type PaperReaderMetadata } from "@/lib/paper-reader-html"
import { enhancePaperPreviewElement, preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaperPreviewResponse } from "@/types/community"
import { StatePanel } from "@/ui/state-panel/StatePanel"

interface PaperPreviewReaderProps {
  paperId: string
  paperMetadata?: PaperReaderMetadata | null
  initialPreview?: CommunityPaperPreviewResponse | null
  readerState?: "ready" | "warming" | "unavailable"
}

function getPreviewIdentity(preview: CommunityPaperPreviewResponse | null | undefined): string | null {
  if (!preview) {
    return null
  }

  return [
    preview.asset.id,
    preview.generated_at ?? preview.asset.created_at ?? "",
    preview.fetch_url ?? "",
  ].join("::")
}

function getPreviewSignature(preview: CommunityPaperPreviewResponse | null | undefined): string | null {
  if (!preview) {
    return null
  }

  return [
    getPreviewIdentity(preview),
    preview.html_content ?? "",
  ].join("::")
}

function normalizePreviewHtml(rawHtml: string): string {
  if (!rawHtml) {
    return ""
  }

  let normalized = rawHtml

  normalized = normalized.replace(
    /<pre class="paper-preview__latex">([\s\S]*?)<\/pre>/g,
    (_match, source: string) => {
      const cleanedSource = String(source || "").trim()
      if (!cleanedSource) {
        return ""
      }

      const isMathLike =
        /\\begin\{(?:equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD)\}/.test(
          cleanedSource,
        ) ||
        /\\\[/.test(cleanedSource) ||
        /\$\$/.test(cleanedSource)

      if (isMathLike) {
        return `<div class="paper-preview__math-block">${cleanedSource}</div>`
      }

      const prose = cleanedSource
        .replace(/\\begin\{(?:quote|snugshade\*?)\}/g, " ")
        .replace(/\\end\{(?:quote|snugshade\*?)\}/g, " ")
        .replace(/\\flushright\{([^}]*)\}/g, "$1")
        .replace(/\\lettrine(?:\[[^\]]*\])?\{([^}]*)\}\{([^}]*)\}/g, "$1$2")
        .replace(/\s+/g, " ")
        .trim()

      return prose ? `<p>${prose}</p>` : ""
    },
  )

  normalized = normalized.replace(
    /<p>\s*\\flushright\{([^}]*)\}(?:\s*\\n)?\s*\\end\{quote\}\s*<\/p>/g,
    "<p>$1</p>",
  )
  normalized = normalized.replace(
    /<p>\s*\\(?:begin|end)\{(?:quote|snugshade\*?)\}\s*<\/p>/g,
    "",
  )
  normalized = normalized.replace(
    /<p>\s*\\flushright\{([^}]*)\}\s*<\/p>/g,
    "<p>$1</p>",
  )
  normalized = normalized.replace(
    /<p>\s*\\lettrine(?:\[[^\]]*\])?\{([^}]*)\}\{([^}]*)\}\s*<\/p>/g,
    "<p>$1$2</p>",
  )
  normalized = normalized.replace(
    /<p>\s*\\end\{(?:quote|snugshade\*?)\}\s*<\/p>/g,
    "",
  )

  return normalized
}

export const PaperPreviewReader = forwardRef<HTMLDivElement, PaperPreviewReaderProps>(
  function PaperPreviewReader({ paperId, paperMetadata = null, initialPreview = null, readerState = "unavailable" }, ref) {
    const { t } = useTranslation()
    const contentRef = useRef<HTMLDivElement | null>(null)
    const preparedPreviewRef = useRef<{ signature: string; html: string } | null>(null)
    const [preview, setPreview] = useState<CommunityPaperPreviewResponse | null>(initialPreview)
    const [loading, setLoading] = useState(
      (!initialPreview || !initialPreview.html_content) && readerState !== "warming",
    )
    const [error, setError] = useState<string | null>(null)
    const [expandedTable, setExpandedTable] = useState<{ caption: string | null; html: string } | null>(null)

    useEffect(() => {
      if (initialPreview?.html_content) {
        const nextSignature = getPreviewSignature(initialPreview)
        setPreview((current) => {
          if (nextSignature && nextSignature === getPreviewSignature(current)) {
            return current
          }
          return initialPreview
        })
        setLoading(false)
        setError(null)
        return
      }

      if (initialPreview) {
        const nextIdentity = getPreviewIdentity(initialPreview)
        setPreview((current) => {
          if (
            current?.html_content &&
            nextIdentity &&
            nextIdentity === getPreviewIdentity(current)
          ) {
            return current
          }
          return initialPreview
        })
      }

      if (readerState === "warming") {
        setPreview(initialPreview ?? null)
        setLoading(false)
        setError(null)
        return
      }

      let cancelled = false
      setLoading(true)
      setError(null)

      void (async () => {
        try {
          const response = await getCommunityPaperPreview(paperId)
          if (cancelled) {
            return
          }
          const nextSignature = getPreviewSignature(response)
          setPreview((current) => {
            if (nextSignature && nextSignature === getPreviewSignature(current)) {
              return current
            }
            return response
          })
          setLoading(false)
        } catch (fetchError) {
          if (cancelled) {
            return
          }
          setPreview((current) => current?.html_content ? current : null)
          setLoading(false)
          setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
        }
      })()

      return () => {
        cancelled = true
      }
    }, [initialPreview, paperId, readerState])

    const previewSignature = useMemo(() => getPreviewSignature(preview), [preview])
    const previewAssetId = preview?.asset.id

    const sanitizedHtml = useMemo(() => {
      if (!preview?.html_content || !previewSignature) {
        return ""
      }

      if (preparedPreviewRef.current?.signature === previewSignature) {
        return preparedPreviewRef.current.html
      }

      const normalized = normalizePreviewHtml(preview.html_content)
      const stripped = stripLeadingDuplicatePaperHeaderHtml(normalized, paperMetadata) ?? normalized
      const sanitized = DOMPurify.sanitize(stripped)
      preparedPreviewRef.current = {
        signature: previewSignature,
        html: sanitized,
      }
      return sanitized
    }, [paperMetadata, preview?.html_content, previewSignature])

    useEffect(() => {
      if (!previewSignature) {
        return
      }

      void preloadPaperPreviewEnhancer()
    }, [previewSignature])

    useEffect(() => {
      if (!previewSignature) {
        setExpandedTable(null)
      }
    }, [previewSignature])

    useEffect(() => {
      if (!sanitizedHtml || !contentRef.current || !previewSignature) {
        return
      }

      let cancelled = false
      const target = contentRef.current
      void (async () => {
        const fallbackRenderMathBlocks = async () => {
          const katexModule = await import("katex")
          const katex = katexModule.default
          target.querySelectorAll<HTMLElement>(".paper-preview__math-block").forEach((block) => {
            const source = (block.textContent || "").trim()
            if (!source) {
              return
            }
            block.innerHTML = katex.renderToString(source, {
              displayMode: true,
              strict: "ignore",
              throwOnError: false,
            })
          })
        }

        try {
          await enhancePaperPreviewElement(target, {
            previewAssetId,
            previewSignature,
          })
        } catch {
          if (!cancelled) {
            await fallbackRenderMathBlocks()
          }
          return
        }

        if (cancelled) {
          return
        }

        const hasMathBlocks = target.querySelector(".paper-preview__math-block") !== null
        const hasKaTeX = target.querySelector(".katex, .katex-display") !== null
        if (hasMathBlocks && !hasKaTeX) {
          await fallbackRenderMathBlocks()
        }
      })()

      return () => {
        cancelled = true
      }
    }, [previewAssetId, previewSignature, sanitizedHtml])

    useEffect(() => {
      if (!contentRef.current || !previewSignature) {
        return
      }

      contentRef.current.querySelectorAll<HTMLElement>(".paper-preview__figure--table").forEach((figure) => {
        if (figure.querySelector("[data-paper-preview-expand-table='true']")) {
          return
        }

        const toolbar = document.createElement("div")
        toolbar.className = "paper-preview__table-toolbar"

        const button = document.createElement("button")
        button.type = "button"
        button.className = "paper-preview__table-expand"
        button.dataset.paperPreviewExpandTable = "true"
        button.textContent = t("community.reader.expandTable")

        toolbar.append(button)
        figure.prepend(toolbar)
      })
    }, [previewSignature, sanitizedHtml, t])

    useEffect(() => {
      if (!contentRef.current || !previewSignature) {
        return
      }

      const root = contentRef.current
      const handleClick = (event: MouseEvent) => {
        const target = event.target
        if (!(target instanceof Element)) {
          return
        }

        const expandButton = target.closest<HTMLButtonElement>("[data-paper-preview-expand-table='true']")
        if (expandButton) {
          const tableFigure = expandButton.closest<HTMLElement>(".paper-preview__figure--table")
          if (!tableFigure) {
            return
          }

          event.preventDefault()
          const clone = tableFigure.cloneNode(true) as HTMLElement
          clone.querySelector(".paper-preview__table-toolbar")?.remove()
          setExpandedTable({
            caption: clone.querySelector<HTMLElement>(".paper-preview__caption")?.textContent?.trim() ?? null,
            html: clone.outerHTML,
          })
          return
        }

        const anchor = target.closest<HTMLAnchorElement>("a[href^='#']")
        const href = anchor?.getAttribute("href")
        if (!anchor || !href || href === "#") {
          return
        }

        const linkedTarget = root.querySelector<HTMLElement>(href)
        if (!linkedTarget) {
          return
        }

        event.preventDefault()
        linkedTarget.scrollIntoView({
          behavior: "smooth",
          block: "center",
        })
      }

      root.addEventListener("click", handleClick)
      return () => {
        root.removeEventListener("click", handleClick)
      }
    }, [previewSignature])

    function attachRootRef(node: HTMLDivElement | null) {
      if (!ref) {
        return
      }
      if (typeof ref === "function") {
        ref(node)
        return
      }
      ref.current = node
    }

    if (loading) {
      return (
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-[320px] items-center rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-6 text-sm text-[color:var(--px-shell-muted)]"
        >
          {t("community.reader.loading")}
        </div>
      )
    }

    if (readerState === "warming") {
      return (
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="h-full min-h-[320px]"
        >
          <StatePanel
            className="h-full rounded-[24px] bg-[color:var(--px-shell-panel-strong)] shadow-none"
            title={t("community.reader.warmingTitle")}
            description={t("community.reader.warmingDescription")}
          />
        </div>
      )
    }

    if (!preview || error) {
      return (
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="h-full min-h-[320px]"
        >
          <StatePanel
            className="h-full rounded-[24px] border-dashed bg-[color:var(--px-shell-panel-strong)] shadow-none"
            title={t("community.reader.emptyTitle")}
            description={t("community.reader.emptyDescription")}
          />
        </div>
      )
    }

    return (
      <>
        <div
          ref={attachRootRef}
          id="paper-preview-reader"
          className="flex h-full min-h-0 flex-col text-[color:var(--px-shell-ink)]"
        >
          <div
            data-testid="paper-preview-viewport"
            className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-6 py-5 xl:px-8 xl:py-6"
          >
            <div
              ref={contentRef}
              data-testid="paper-preview-content"
              data-reader-layout="scholarly"
              className="paper-preview-shell prose max-w-none text-[color:var(--px-shell-ink)] [&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold [&_h4]:mt-5 [&_h4]:text-lg [&_h4]:font-semibold [&_img]:rounded-2xl [&_img]:shadow-sm [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:border [&_pre]:p-4 [&_table]:w-full [&_td]:align-top [&_th]:align-bottom"
              dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
            />
          </div>
        </div>

        <Sheet open={Boolean(expandedTable)} onOpenChange={(open) => !open && setExpandedTable(null)}>
          <SheetContent
            side="right"
            className="w-[min(96vw,1160px)] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6 text-[color:var(--px-shell-ink)] sm:max-w-none"
          >
            <SheetHeader className="pr-10">
              <SheetTitle className="text-[color:var(--px-shell-ink)]">
                {expandedTable?.caption || t("community.reader.expandedTableTitle")}
              </SheetTitle>
              <SheetDescription className="text-[color:var(--px-shell-muted)]">
                {t("community.reader.expandedTableDescription")}
              </SheetDescription>
            </SheetHeader>

            <div
              data-testid="paper-preview-expanded-table"
              className="mt-6 h-[calc(100vh-8rem)] overflow-auto rounded-[20px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_82%,rgba(23,20,17,0.2))] bg-[color:var(--px-shell-panel-strong)] p-4"
            >
              <div
                className="paper-preview-shell prose max-w-none text-[color:var(--px-shell-ink)]"
                dangerouslySetInnerHTML={{ __html: expandedTable?.html ?? "" }}
              />
            </div>
          </SheetContent>
        </Sheet>
      </>
    )
  },
)

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperStatusBadge.tsx
Relative path: features\community-paper\components\PaperStatusBadge.tsx

```tsx
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import type { CommunityStatus, TranslationStatus } from "@/types/community"

interface PaperStatusBadgeProps {
  kind: "community" | "translation"
  value: CommunityStatus | TranslationStatus
}

function getCommunityLabel(value: CommunityStatus, t: (key: string) => string) {
  switch (value) {
    case "official":
      return t("community.status.community.official")
    case "user_fallback":
      return t("community.status.community.user_fallback")
  }
}

function getTranslationLabel(value: TranslationStatus, t: (key: string) => string) {
  switch (value) {
    case "not_started":
      return t("community.status.translation.not_started")
    case "queued":
      return t("community.status.translation.queued")
    case "processing":
      return t("community.status.translation.processing")
    case "completed":
      return t("community.status.translation.completed")
    case "failed":
      return t("community.status.translation.failed")
  }
}

export function PaperStatusBadge({ kind, value }: PaperStatusBadgeProps) {
  const { t } = useTranslation()

  if (kind === "community") {
    const isOfficial = value === "official"
    const colorClass = isOfficial 
      ? "text-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]" 
      : "text-[color:var(--px-shell-muted)] bg-[color:var(--px-shell-panel-strong)]"
      
    return (
      <span className={cn(
        "px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase",
        colorClass
      )}>
        {getCommunityLabel(value as CommunityStatus, t)}
      </span>
    )
  }

  const config: Record<
    TranslationStatus,
    string
  > = {
    not_started: "text-[color:var(--px-shell-muted)] bg-[color:var(--px-shell-panel-strong)]",
    queued: "text-[color:var(--px-shell-warning)] bg-[color:var(--px-shell-warning-soft)]",
    processing: "text-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]",
    completed: "text-[color:var(--px-shell-success)] bg-[color:var(--px-shell-success-soft)]",
    failed: "text-[color:var(--px-shell-danger)] bg-[color:var(--px-shell-danger-soft)]",
  }

  const selectedClass = config[value as TranslationStatus]

  return (
    <span
      className={cn(
        "px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase",
        selectedClass,
      )}
    >
      {getTranslationLabel(value as TranslationStatus, t)}
    </span>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\hooks\use-paper-detail.ts
Relative path: features\community-paper\hooks\use-paper-detail.ts

```ts
import { useEffect, useMemo, useRef, useState } from "react"

import {
  getCachedCommunityPaperDetail,
  getCommunityPaperDetail,
  recordCommunityPaperView,
} from "@/features/community-paper/services/community-paper-api"
import type {
  CommunityPaper,
  CommunityPaperExperience,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  StructuredInsightsPayload,
} from "@/types/community"

interface PaperDetailRemoteState {
  paperId: string | null
  paper: CommunityPaper | null
  preview: CommunityPaperPreviewResponse | null
  readerState: "ready" | "warming" | "unavailable"
  error: string | null
  notFound: boolean
  reader: CommunityPaperReader | null
  experience: CommunityPaperExperience | null
  structuredInsights: StructuredInsightsPayload | null
}

const EMPTY_REMOTE_STATE: PaperDetailRemoteState = {
  paperId: null,
  paper: null,
  preview: null,
  readerState: "unavailable",
  error: null,
  notFound: false,
  reader: null,
  experience: null,
  structuredInsights: null,
}

export function usePaperDetail(paperId: string | undefined) {
  const cachedDetail = useMemo(
    () => (paperId ? getCachedCommunityPaperDetail(paperId) : null),
    [paperId],
  )
  const viewedPaperIdRef = useRef<string | null>(null)
  const [remoteState, setRemoteState] = useState<PaperDetailRemoteState>(() =>
    paperId && cachedDetail
      ? {
          paperId,
          paper: cachedDetail.paper ?? null,
          preview: cachedDetail.preview ?? null,
          readerState: cachedDetail.reader_state ?? "unavailable",
          error: null,
          notFound: false,
          reader: cachedDetail.reader ?? null,
          experience: cachedDetail.experience ?? null,
          structuredInsights: cachedDetail.structured_insights ?? null,
        }
      : EMPTY_REMOTE_STATE,
  )

  useEffect(() => {
    if (!paperId) {
      return undefined
    }

    let isCancelled = false

    const fetchDetail = async () => {
      try {
        const response = await getCommunityPaperDetail(paperId)
        if (isCancelled) {
          return
        }

        setRemoteState({
          paperId,
          paper: response.paper ?? null,
          preview: response.preview ?? null,
          readerState: response.reader_state ?? "unavailable",
          error: null,
          notFound: false,
          reader: response.reader ?? null,
          experience: response.experience ?? null,
          structuredInsights: response.structured_insights ?? null,
        })

        if (viewedPaperIdRef.current !== paperId) {
          viewedPaperIdRef.current = paperId
          void recordCommunityPaperView(paperId).catch(() => undefined)
        }
      } catch (fetchError) {
        if (isCancelled) {
          return
        }

        const message = fetchError instanceof Error ? fetchError.message : "unknown_error"
        setRemoteState({
          paperId,
          paper: null,
          preview: null,
          readerState: "unavailable",
          error: message,
          notFound: /404/.test(message) || /not found/i.test(message),
          reader: null,
          experience: null,
          structuredInsights: null,
        })
      }
    }

    void fetchDetail()

    return () => {
      isCancelled = true
    }
  }, [paperId])

  const effectiveState = useMemo<PaperDetailRemoteState>(() => {
    if (!paperId) {
      return {
        ...EMPTY_REMOTE_STATE,
        notFound: true,
      }
    }

    if (cachedDetail) {
      return {
        paperId,
        paper: cachedDetail.paper ?? null,
        preview: cachedDetail.preview ?? null,
        readerState: cachedDetail.reader_state ?? "unavailable",
        error: null,
        notFound: false,
        reader: cachedDetail.reader ?? null,
        experience: cachedDetail.experience ?? null,
        structuredInsights: cachedDetail.structured_insights ?? null,
      }
    }

    return remoteState.paperId === paperId ? remoteState : EMPTY_REMOTE_STATE
  }, [cachedDetail, paperId, remoteState])

  return {
    paper: effectiveState.paper,
    preview: effectiveState.preview,
    readerState: effectiveState.readerState,
    loading: Boolean(paperId) && !cachedDetail && remoteState.paperId !== paperId,
    error: effectiveState.error,
    notFound: effectiveState.notFound,
    reader: effectiveState.reader,
    experience: effectiveState.experience,
    structuredInsights: effectiveState.structuredInsights,
    refetch: async () => {
      if (!paperId) {
        return
      }

      const response = await getCommunityPaperDetail(paperId)
      setRemoteState({
        paperId,
        paper: response.paper ?? null,
        preview: response.preview ?? null,
        readerState: response.reader_state ?? "unavailable",
        error: null,
        notFound: false,
        reader: response.reader ?? null,
        experience: response.experience ?? null,
        structuredInsights: response.structured_insights ?? null,
      })
    },
  }
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\hooks\useCommunityPapers.ts
Relative path: features\community-paper\hooks\useCommunityPapers.ts

```ts
import { useEffect, useMemo, useState } from "react"

import { getCommunityPapers } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"

const SEARCH_DEBOUNCE_MS = 250
const COMMUNITY_PAGE_SIZE = 12

function getBootstrappedFeed(sort: CommunityFeedSort, query: string) {
  if (sort !== "latest" || query.trim()) {
    return null
  }
  return window.__COMMUNITY_BOOTSTRAP__?.feed ?? null
}

export function useCommunityPapers(sort: CommunityFeedSort, query: string) {
  const bootstrappedFeed = getBootstrappedFeed(sort, query)
  const [items, setItems] = useState<CommunityPaper[]>(bootstrappedFeed?.items ?? [])
  const [total, setTotal] = useState(bootstrappedFeed?.total ?? 0)
  const [hasMore, setHasMore] = useState(Boolean(bootstrappedFeed?.has_more))
  const [nextOffset, setNextOffset] = useState<number | null>(bootstrappedFeed?.next_offset ?? null)
  const [loading, setLoading] = useState(!bootstrappedFeed)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const normalizedQuery = useMemo(() => query.trim(), [query])

  useEffect(() => {
    let isCancelled = false
    const shouldUseBootstrap = sort === "latest" && !normalizedQuery
    const bootstrapPromise = shouldUseBootstrap ? window.__COMMUNITY_BOOTSTRAP_PROMISE__ : undefined

    setLoading(!bootstrappedFeed)
    setLoadingMore(false)
    setError(null)

    const load = async () => {
      try {
        if (bootstrapPromise && !window.__COMMUNITY_BOOTSTRAP__?.feed) {
          const bootstrapResponse = await bootstrapPromise
          if (!isCancelled && bootstrapResponse) {
            setItems(bootstrapResponse.items)
            setTotal(bootstrapResponse.total)
            setHasMore(Boolean(bootstrapResponse.has_more))
            setNextOffset(bootstrapResponse.next_offset ?? null)
            setLoading(false)
          }
        }

        const response = await getCommunityPapers({
          sort,
          q: normalizedQuery || undefined,
          limit: COMMUNITY_PAGE_SIZE,
          offset: 0,
        })
        if (!isCancelled) {
          setItems(response.items)
          setTotal(response.total)
          setHasMore(Boolean(response.has_more))
          setNextOffset(response.next_offset ?? null)
        }
      } catch (fetchError) {
        if (!isCancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
          setItems([])
          setTotal(0)
          setHasMore(false)
          setNextOffset(null)
        }
      } finally {
        if (!isCancelled) {
          setLoading(false)
        }
      }
    }

    const shouldDebounce = Boolean(normalizedQuery)
    const timer = shouldDebounce ? window.setTimeout(() => void load(), SEARCH_DEBOUNCE_MS) : null
    if (!shouldDebounce) {
      void load()
    }

    return () => {
      isCancelled = true
      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [bootstrappedFeed, normalizedQuery, reloadToken, sort])

  return {
    items,
    total,
    hasMore,
    loading,
    loadingMore,
    error,
    loadMore: async () => {
      if (loading || loadingMore || !hasMore || nextOffset === null) {
        return
      }
      setLoadingMore(true)
      setError(null)
      try {
        const response = await getCommunityPapers({
          sort,
          q: normalizedQuery || undefined,
          limit: COMMUNITY_PAGE_SIZE,
          offset: nextOffset,
        })
        setItems((current) => [...current, ...response.items])
        setTotal(response.total)
        setHasMore(Boolean(response.has_more))
        setNextOffset(response.next_offset ?? null)
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : "unknown_error")
      } finally {
        setLoadingMore(false)
      }
    },
    refetch: () => setReloadToken((current) => current + 1),
  }
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\services\community-paper-api.ts
Relative path: features\community-paper\services\community-paper-api.ts

```ts
export {
  clearCommunityPaperDetailCache,
  createCommunityPaperDownloadSession,
  getCachedCommunityPaperDetail,
  getCommunityPaperDetail,
  getCommunityPaperPreview,
  getCommunityPaperSimilar,
  prefetchCommunityPaperDetail,
  primeCommunityPaperDetailCache,
  recordCommunityPaperView,
  translateCommunityPaper,
} from "@/lib/community-api"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\utils\paper-detail-mode-resolution.ts
Relative path: features\community-paper\utils\paper-detail-mode-resolution.ts

```ts
import type { CommunityPaperReaderMode } from "@/types/community"

function hasTranslatedPdfResource(
  paper: {
    assets?: { translated_pdf?: unknown } | null
    latest_asset?: { asset_type?: string | null } | null
    trans_status?: string | null
  } | null | undefined,
  reader: {
    translated?: { kind?: string | null } | null
  } | null | undefined,
) {
  return Boolean(
    paper?.assets?.translated_pdf ||
      reader?.translated?.kind === "translated_pdf" ||
      paper?.latest_asset?.asset_type === "translated_pdf" ||
      paper?.trans_status === "completed",
  )
}

function hasSourcePdfResource(
  paper: {
    arxiv_id?: string | null
  } | null | undefined,
  reader: {
    source?: { kind?: string | null } | null
  } | null | undefined,
) {
  return Boolean(reader?.source?.kind === "source_pdf" || paper?.arxiv_id)
}

export function resolveAvailableModes(
  paper: {
    arxiv_id?: string | null
    trans_status?: string | null
    assets?: { translated_pdf?: unknown } | null
    latest_asset?: { asset_type?: string | null } | null
  } | null | undefined,
  preview: { html_content?: string | null } | null | undefined,
  reader: {
    available_modes?: CommunityPaperReaderMode[] | null
    source?: { kind?: string | null } | null
    translated?: { kind?: string | null; html_content?: string | null } | null
  } | null | undefined,
): CommunityPaperReaderMode[] {
  void preview
  const modes: CommunityPaperReaderMode[] = ["source"]
  const rawModes = reader?.available_modes ?? []
  const allowTranslatedPdf =
    rawModes.includes("translated_pdf") ||
    (rawModes.includes("translated") && hasTranslatedPdfResource(paper, reader)) ||
    hasTranslatedPdfResource(paper, reader)

  if (allowTranslatedPdf) {
    modes.push("translated_pdf")
  }
  if (allowTranslatedPdf && hasSourcePdfResource(paper, reader)) {
    modes.push("bilingual_compare")
  }

  return modes
}

export function resolvePreferredMode(
  preferredMode: CommunityPaperReaderMode | undefined,
  availableModes: CommunityPaperReaderMode[],
): CommunityPaperReaderMode {
  if (preferredMode === "translated") {
    if (availableModes.includes("bilingual_compare")) {
      return "bilingual_compare"
    }
    if (availableModes.includes("translated_pdf")) {
      return "translated_pdf"
    }
    if (availableModes.includes("source")) {
      return "source"
    }
  }
  if (preferredMode && availableModes.includes(preferredMode)) {
    return preferredMode
  }
  if (availableModes.includes("bilingual_compare")) {
    return "bilingual_compare"
  }
  if (availableModes.includes("source")) {
    return "source"
  }
  if (availableModes.includes("translated_pdf")) {
    return "translated_pdf"
  }
  return "source"
}

export function resolveStageLabel(
  transStatus: string | undefined,
  readerState: "ready" | "warming" | "unavailable",
  hasTranslatedMode: boolean,
  t: (key: string) => string,
) {
  if (hasTranslatedMode && readerState === "ready") {
    return t("community.detail.stage.translatedReady")
  }
  if (transStatus === "queued" || transStatus === "processing" || readerState === "warming") {
    return t("community.detail.stage.generating")
  }
  if (readerState === "ready") {
    return t("community.detail.stage.sourceReady")
  }
  return t("community.detail.stage.unavailable")
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\AdvancedConfig.tsx
Relative path: features\translation-workflow\components\AdvancedConfig.tsx

```tsx
import { BookText, CheckCircle2, Info, Languages, Mail, Palette, Settings2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Input } from "@/ui/input/Input"
import { InfoTile } from "@/ui/info-tile/InfoTile"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import { Label } from "@/ui/primitives/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/primitives/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/ui/primitives/tooltip"
import { useAuth } from "@/contexts/AuthContext"
import { getLocalizedLanguageOptions } from "@/i18n/config"
import { FormattingPanel } from "@/features/translation-workflow/components/FormattingPanel"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import type { CompileStrategy, FormattingConfig, TranslationMode } from "@/types/config"

export function AdvancedConfig() {
  const { config, setConfig, setAdvancedConfig, hasSystemApiKey } = useTranslationConfig()
  const { user } = useAuth()
  const { advanced_config, source_language, target_language } = config
  const { t } = useTranslation()
  const languages = getLocalizedLanguageOptions(t)

  function updateConfig(key: keyof typeof advanced_config, value: unknown) {
    setAdvancedConfig({ [key]: value })
  }

  function updateFormatting(patch: Partial<FormattingConfig>) {
    setAdvancedConfig({
      formatting: { ...(advanced_config.formatting ?? {}), ...patch },
    })
  }

  return (
    <PanelShell className="space-y-6 p-4">
      <div className="flex items-center gap-2 border-b border-[color:var(--px-shell-line)] pb-2">
        <Settings2 className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
        <h3 className="text-lg font-medium text-[color:var(--px-shell-ink)]">{t("dashboard.advancedConfig")}</h3>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="space-y-4 md:col-span-2">
          <div className="flex items-center gap-2">
            <Languages className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
            <h4 className="text-sm font-medium text-[color:var(--px-shell-muted)]">{t("common.sections.languageSettings")}</h4>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>{t("common.labels.sourceLanguage")}</Label>
              <Select value={source_language} onValueChange={(value) => setConfig({ source_language: value })}>
                <SelectTrigger>
                  <SelectValue placeholder={t("dashboard.config.choose_source_language")} />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((language) => (
                    <SelectItem key={language.code} value={language.code}>
                      {language.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{t("common.labels.targetLanguage")}</Label>
              <Select value={target_language} onValueChange={(value) => setConfig({ target_language: value })}>
                <SelectTrigger>
                  <SelectValue placeholder={t("dashboard.config.choose_target_language")} />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((language) => (
                    <SelectItem key={language.code} value={language.code}>
                      {language.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>{t("common.labels.translationMode")}</Label>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-4 w-4 text-[color:var(--px-shell-muted)] transition-colors hover:text-[color:var(--px-shell-ink)]" />
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t("dashboard.config.choose_how_to_translate_the_document")}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <Select
            value={advanced_config.translation_mode}
            onValueChange={(value: TranslationMode) => updateConfig("translation_mode", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("dashboard.config.choose_translation_mode")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="full">{t("task.translationMode.full")}</SelectItem>
              <SelectItem value="quick_scan">{t("dashboard.config.quick_scan_abstract_conclusion")}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>{t("common.labels.compileStrategy")}</Label>
          <Select
            value={advanced_config.compile_strategy}
            onValueChange={(value: CompileStrategy) => updateConfig("compile_strategy", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("dashboard.config.choose_compile_strategy")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">{t("task.compileStrategy.auto")}</SelectItem>
              <SelectItem value="pdflatex">PDFLaTeX</SelectItem>
              <SelectItem value="xelatex">XeLaTeX</SelectItem>
              <SelectItem value="lualatex">LuaLaTeX</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="translation-model">{t("common.labels.translationModel")}</Label>
          <Input
            id="translation-model"
            placeholder={t("dashboard.config.for_example_deepseek_chat_gpt_4o_claude_3_sonnet")}
            value={advanced_config.translation_model}
            onChange={(event) => updateConfig("translation_model", event.target.value)}
            className="font-mono"
            disabled={advanced_config.use_author_api}
          />
          {advanced_config.use_author_api ? (
            <NoticeBanner
              tone="warning"
              icon={<Info className="h-4 w-4" />}
              description={t("dashboard.config.when_the_default_api_is_enabled_the_system_controls_the_model")}
              className="rounded-lg px-3 py-2 text-xs"
            />
          ) : (
            <p className="text-xs text-[color:var(--px-shell-muted)]">
              {t("dashboard.config.model_names_vary_by_api_provider_use_the_provider_s_documented_name")}
            </p>
          )}
        </div>

        <div className="space-y-4 md:col-span-2">
          <div className="flex flex-col gap-4 md:flex-row">
            <InfoTile
              className="flex-1"
              title={t("dashboard.config.use_default_api")}
              description={t("dashboard.config.turn_off_to_enter_a_custom_api_endpoint_and_key")}
              trailing={(
                <ToggleSwitch
                  checked={advanced_config.use_author_api}
                  onCheckedChange={(checked) => updateConfig("use_author_api", checked)}
                />
              )}
            />

            <InfoTile
              className="flex-1"
              icon={<BookText className="h-4 w-4" />}
              title={t("common.generate_glossary")}
              description={t("dashboard.config.output_a_source_translation_terminology_table")}
              trailing={(
                <ToggleSwitch
                  checked={advanced_config.generate_terminology_table}
                  onCheckedChange={(checked) => updateConfig("generate_terminology_table", checked)}
                />
              )}
            />
          </div>

          {user ? (
            <InfoTile
              icon={<Mail className="h-4 w-4" />}
              title={t("dashboard.config.email_notifications")}
              description={t("dashboard.config.send_an_email_when_a_task_completes_or_fails")}
              trailing={(
                <ToggleSwitch
                  id="email-notification"
                  checked={advanced_config.email_notification ?? false}
                  onCheckedChange={(checked) => updateConfig("email_notification", checked)}
                />
              )}
            />
          ) : null}

          {!advanced_config.use_author_api ? (
            <div className="animate-in slide-in-from-top-2 space-y-4 duration-200">
              <NoticeBanner
                tone="warning"
                icon={<Info className="h-4 w-4" />}
                description={t("dashboard.config.if_you_already_saved_api_settings_in_settings_you_can_leave_these_blank_and_reuse_them_automatically")}
                className="rounded-lg px-3 py-2 text-xs"
              />
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="base-url">{t("dashboard.config.custom_base_url_optional")}</Label>
                  <Input
                    id="base-url"
                    placeholder="https://api.example.com/v1"
                    value={advanced_config.custom_base_url || ""}
                    onChange={(event) => updateConfig("custom_base_url", event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="api-key">{t("dashboard.config.custom_api_key_optional")}</Label>
                    {hasSystemApiKey ? (
                      <StatusBadge
                        tone="success"
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                        className="gap-1 px-2 py-1 text-[9px]"
                      >
                        {t("dashboard.config.saved_in_settings")}
                      </StatusBadge>
                    ) : null}
                  </div>
                  <Input
                    id="api-key"
                    type="password"
                    placeholder={hasSystemApiKey ? t("dashboard.config.leave_blank_to_reuse_the_saved_key") : t("dashboard.config.enter_api_key_sk")}
                    value={advanced_config.custom_api_key || ""}
                    onChange={(event) => updateConfig("custom_api_key", event.target.value)}
                  />
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="space-y-3 border-t border-[color:var(--px-shell-line)] pt-2 md:col-span-2">
        <div className="flex items-center gap-2">
          <Palette className="h-4 w-4 text-[color:var(--px-shell-accent)]" />
          <h4 className="text-sm font-medium text-[color:var(--px-shell-ink)]">{t("dashboard.config.formatting_settings")}</h4>
          <span className="ml-1 text-xs text-[color:var(--px-shell-muted)]">
            {t("dashboard.config.optional_injected_into_the_latex_preamble")}
          </span>
        </div>
        <FormattingPanel
          value={advanced_config.formatting ?? {}}
          onChange={updateFormatting}
          targetLanguage={target_language}
        />
      </div>
    </PanelShell>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\BatchTranslation.tsx
Relative path: features\translation-workflow\components\BatchTranslation.tsx

```tsx
import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef, type ChangeEvent, type Dispatch, type SetStateAction } from "react"
import { useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "framer-motion"
import { useTranslation } from "react-i18next"
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileArchive,
  Info,
  Layers,
  Loader2,
  Upload,
  X,
  XCircle,
} from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/ui/button/Button"
import { cn } from "@/lib/utils"
import { Badge } from "@/ui/primitives/badge"
import { Progress } from "@/ui/primitives/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/primitives/tabs"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { RecordRow } from "@/ui/record-row/RecordRow"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { Textarea } from "@/ui/input/Textarea"
import { UploadDropSurface } from "@/ui/upload-card/UploadDropSurface"
import { getTaskCopy } from "@/i18n/task-copy"
import { getTaskStatus, startBatchTranslation, startTranslation, uploadFile } from "@/lib/api"
import { DEFAULT_CONFIG } from "@/types/config"
import type { AdvancedConfig } from "@/types/config"

const MAX_BATCH = 9
const VALID_EXTS = [".zip", ".rar", ".tar", ".gz", ".tgz", ".tex"]
const BATCH_POLL_INTERVAL_MS = 3000
const TERMINAL_BATCH_STATUSES = new Set([
  "completed",
  "completed_with_warnings",
  "failed",
  "failed_compilation",
  "structure_invalid",
])

type Translate = (key: string, options?: Record<string, unknown>) => string

interface BatchTask {
  task_id: string
  label: string
  status: string
  progress: number
  stage?: string | null
  message: string
  detail_code?: string | null
  detail_params?: Record<string, string | number | boolean | null> | null
  warnings?: string | null
  failure_reason_code?: string | null
}

interface QueuedFile {
  file: File
  id: string
}

export interface BatchTranslationHandle {
  submitCurrent: () => void
}

export interface BatchTranslationState {
  isSubmitting: boolean
  activeTab: "arxiv" | "upload"
  canSubmit: boolean
}

interface BatchTranslationProps {
  advancedConfig?: AdvancedConfig
  targetLanguage?: string
  sourceLanguage?: string
  onStateChange?: (state: BatchTranslationState) => void
}

const uid = () => Math.random().toString(36).slice(2, 9)

function statusIcon(status: string) {
  switch (status) {
    case "completed":
    case "completed_with_warnings":
      return <CheckCircle2 className="h-4 w-4 text-[color:var(--px-shell-success)]" />
    case "failed":
    case "failed_compilation":
      return <XCircle className="h-4 w-4 text-[color:var(--px-shell-danger)]" />
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin text-[color:var(--px-shell-accent)]" />
    case "queued":
      return <Clock className="h-4 w-4 text-[color:var(--px-shell-warning)]" />
    default:
      return <Clock className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
  }
}

function statusBadgeTone(status: string): "success" | "danger" | "accent" | "warning" | "muted" {
  if (status === "completed" || status === "completed_with_warnings") {
    return "success"
  }
  if (status === "failed" || status === "failed_compilation") {
    return "danger"
  }
  if (status === "processing") {
    return "accent"
  }
  if (status === "queued") {
    return "warning"
  }
  return "muted"
}

function TaskList({ tasks, translate }: { tasks: BatchTask[]; translate: Translate }) {
  const navigate = useNavigate()

  if (tasks.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-[color:var(--px-shell-muted)]">{translate("batch.taskList")}</p>
      {tasks.map((task) => {
        const copy = getTaskCopy(translate, {
          status: task.status,
          stage: task.stage,
          detailCode: task.detail_code,
          detailParams: task.detail_params,
          failureReasonCode: task.failure_reason_code,
          warnings: task.warnings,
        })

        return (
          <RecordRow
            key={task.task_id}
            icon={statusIcon(task.status)}
            title={<span className="font-mono">{task.label}</span>}
            badge={<StatusBadge tone={statusBadgeTone(task.status)}>{copy.statusLabel}</StatusBadge>}
            action={task.status === "completed" || task.status === "completed_with_warnings" ? (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 gap-1 px-2 text-xs"
                onClick={() => navigate(`/processing?taskId=${task.task_id}`)}
              >
                <ExternalLink className="h-3 w-3" />
                {translate("common.actions.view")}
              </Button>
            ) : null}
            detail={task.status === "processing" || task.status === "queued" ? (
              <div className="space-y-1">
                <Progress
                  value={task.progress}
                  className={cn("h-1.5", copy.isRateLimited && "animate-pulse [&>div]:bg-[color:var(--px-shell-warning)]!")}
                />
                <p className={cn(
                  "text-xs",
                  copy.isRateLimited ? "font-medium text-[color:var(--px-shell-warning)]" : "text-[color:var(--px-shell-muted)]",
                )}>
                  {copy.detailLabel || copy.stageLabel || copy.statusLabel}
                </p>
              </div>
            ) : task.status === "failed" || task.status === "failed_compilation" ? (
              <p className="text-xs text-[color:var(--px-shell-danger)]">{copy.failureLabel || copy.statusLabel}</p>
            ) : null}
            alert={task.warnings ? (
              <p className="mt-1 flex items-center gap-1 text-xs text-[color:var(--px-shell-warning)]">
                <AlertCircle className="h-3 w-3 shrink-0" />
                {translate("task.detail.formattingWarning", { warningText: task.warnings })}
              </p>
            ) : null}
          />
        )
      })}
    </div>
  )
}

export const BatchTranslation = forwardRef<BatchTranslationHandle, BatchTranslationProps>(function BatchTranslation({
  advancedConfig = DEFAULT_CONFIG.advanced_config,
  targetLanguage = "ch",
  sourceLanguage = "en",
  onStateChange,
}, ref) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<"arxiv" | "upload">("arxiv")
  const [arxivText, setArxivText] = useState("")
  const [isArxivSubmitting, setIsArxivSubmitting] = useState(false)
  const [arxivTasks, setArxivTasks] = useState<BatchTask[]>([])
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([])
  const [isDragActive, setIsDragActive] = useState(false)
  const [isUploadSubmitting, setIsUploadSubmitting] = useState(false)
  const [uploadTasks, setUploadTasks] = useState<BatchTask[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const parsedIds = arxivText.split("\n").map((line) => line.trim()).filter(Boolean).slice(0, MAX_BATCH)
  const isOverLimit = arxivText.split("\n").map((line) => line.trim()).filter(Boolean).length > MAX_BATCH
  const submitRef = useRef<() => void>(() => {})
  submitRef.current = () => {
    if (activeTab === "arxiv") {
      void handleArxivSubmit()
    } else {
      void handleUploadSubmit()
    }
  }

  useImperativeHandle(ref, () => ({
    submitCurrent: () => submitRef.current(),
  }), [])

  useEffect(() => {
    onStateChange?.({
      isSubmitting: activeTab === "arxiv" ? isArxivSubmitting : isUploadSubmitting,
      activeTab,
      canSubmit: activeTab === "arxiv"
        ? parsedIds.length > 0 && !isArxivSubmitting
        : queuedFiles.length > 0 && !isUploadSubmitting,
    })
  }, [activeTab, isArxivSubmitting, isUploadSubmitting, onStateChange, parsedIds.length, queuedFiles.length])

  const warnedPersistFailed = useRef<Set<string>>(new Set())
  const activePollsRef = useRef<Set<string>>(new Set())
  const isMountedRef = useRef(true)

  useEffect(() => {
    const activePolls = activePollsRef.current
    isMountedRef.current = true

    return () => {
      isMountedRef.current = false
      activePolls.clear()
    }
  }, [])

  const pollTask = useCallback(async (task_id: string, setter: Dispatch<SetStateAction<BatchTask[]>>) => {
    if (activePollsRef.current.has(task_id)) {
      return
    }

    activePollsRef.current.add(task_id)

    try {
      while (isMountedRef.current) {
        await new Promise((resolve) => setTimeout(resolve, BATCH_POLL_INTERVAL_MS))
        if (!isMountedRef.current) {
          break
        }

        let status
        try {
          status = await getTaskStatus(task_id)
        } catch {
          continue
        }

        if (!isMountedRef.current) {
          break
        }

        if (status.persist_failed && !warnedPersistFailed.current.has(task_id)) {
          warnedPersistFailed.current.add(task_id)
          toast.warning(
            t("batch.due_to_a_backend_network_issue_the_result_could_not_be_saved_to_the_database_please_make_sure_to_save_your_translation_results"),
            { duration: 8000 },
          )
        }

        setter((prev) => prev.map((task) => (
          task.task_id === task_id
            ? {
                ...task,
                status: status.status,
                progress: status.progress,
                stage: status.stage ?? task.stage,
                message: status.message,
                detail_code: status.detail_code ?? task.detail_code,
                detail_params: status.detail_params ?? task.detail_params,
                warnings: status.warnings ?? task.warnings,
                failure_reason_code: status.failure_reason_code ?? task.failure_reason_code,
              }
            : task
        )))

        if (TERMINAL_BATCH_STATUSES.has(String(status.status || "").toLowerCase())) {
          break
        }
      }
    } finally {
      activePollsRef.current.delete(task_id)
    }
  }, [t])

  async function handleArxivSubmit() {
    if (parsedIds.length === 0) {
      toast.error(t("batch.enter_at_least_one_arxiv_id"))
      return
    }

    setIsArxivSubmitting(true)
    try {
      const response = await startBatchTranslation({
        arxiv_ids: parsedIds,
        target_language: targetLanguage,
        source_language: sourceLanguage,
        advanced_config: advancedConfig,
      })
      const initial: BatchTask[] = response.task_ids.map((taskId, index) => ({
        task_id: taskId,
        label: parsedIds[index] ?? taskId,
        status: "processing",
        stage: "downloading",
        progress: 0,
        message: t("task.detail.taskWaiting"),
        detail_code: "task_waiting",
        detail_params: null,
      }))
      setArxivTasks(initial)
      setArxivText("")
      toast.success(t("batch.batch_translation_submitted_tasks_created_successfully", { count: response.queued_count }))
      for (const task of initial) {
        void pollTask(task.task_id, setArxivTasks)
      }
    } catch (error: unknown) {
      console.error("[BatchTranslation] Failed to submit arXiv batch", error)
      toast.error(t("batch.submission_failed"))
    } finally {
      setIsArxivSubmitting(false)
    }
  }

  const addFiles = useCallback((files: FileList | File[]) => {
    const arr = Array.from(files)
    const valid = arr.filter((file) => {
      const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()
      if (!VALID_EXTS.includes(ext)) {
        toast.error(t("batch.unsupported_file_type", { name: file.name }))
        return false
      }
      if (file.size > 50 * 1024 * 1024) {
        toast.error(t("batch.file_exceeds_50_mb", { name: file.name }))
        return false
      }
      return true
    })
    setQueuedFiles((prev) => {
      const combined = [...prev, ...valid.map((file) => ({ file, id: uid() }))]
      if (combined.length > MAX_BATCH) {
        toast.warning(t("batch.maximum_files_extra_files_were_removed", { count: MAX_BATCH }))
        return combined.slice(0, MAX_BATCH)
      }
      return combined
    })
  }, [t])

  const handleDrag = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(event.type === "dragenter" || event.type === "dragover")
  }, [])

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(false)
    if (event.dataTransfer.files.length) {
      addFiles(event.dataTransfer.files)
    }
  }, [addFiles])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files?.length) {
      addFiles(event.target.files)
    }
    event.target.value = ""
  }

  function removeFile(id: string) {
    setQueuedFiles((prev) => prev.filter((file) => file.id !== id))
  }

  async function handleUploadSubmit() {
    if (queuedFiles.length === 0) {
      toast.error(t("batch.add_files_first"))
      return
    }

    setIsUploadSubmitting(true)
    const snapshot = [...queuedFiles]
    setQueuedFiles([])

    function appendTask(task: BatchTask) {
      setUploadTasks((prev) => [...prev, task])
    }

    await Promise.all(snapshot.map(async (queuedFile) => {
      try {
        const uploadResponse = await uploadFile(queuedFile.file)
        const taskId = uploadResponse.task_id

        appendTask({
          task_id: taskId,
          label: queuedFile.file.name,
          status: "processing",
          stage: "parsing",
          progress: 0,
          message: t("task.detail.translationStarting"),
          detail_code: "translation_starting",
          detail_params: null,
        })

        void pollTask(taskId, setUploadTasks)

        await startTranslation(taskId, {
          target_language: targetLanguage,
          source_language: sourceLanguage,
          advanced_config: advancedConfig,
        })
      } catch (error: unknown) {
        console.error("[BatchTranslation] Failed to process uploaded file", error)
        appendTask({
          task_id: `failed-${queuedFile.id}`,
          label: queuedFile.file.name,
          status: "failed",
          progress: 0,
          message: t("batch.submission_failed"),
          failure_reason_code: null,
        })
      }
    }))

    setIsUploadSubmitting(false)
    toast.success(t("batch.all_files_have_been_submitted_for_translation"))
  }

  return (
    <div className="space-y-5">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "arxiv" | "upload")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="arxiv" className="gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            {t("batch.batch_arxiv_ids")}
          </TabsTrigger>
          <TabsTrigger value="upload" className="gap-1.5">
            <Upload className="h-3.5 w-3.5" />
            {t("batch.batch_file_upload")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="arxiv" className="mt-4 space-y-4">
          <NoticeBanner
            tone="info"
            icon={<Info className="h-4 w-4" />}
            description={(
              <span>
              {t("batch.enter_one_arxiv_id_per_line_for_example_up_to_total", { example: "2401.00001", count: MAX_BATCH })}{" "}
              {t("batch.full_urls_or_plain_ids_are_supported")}
              </span>
            )}
          />

          <div className="space-y-1.5">
            <label htmlFor="batch-arxiv-input" className="text-sm font-medium text-[color:var(--px-shell-ink)]">
              {t("batch.arxiv_id_list")}
            </label>
            <Textarea
              id="batch-arxiv-input"
              value={arxivText}
              onChange={(event) => setArxivText(event.target.value)}
              placeholder={"2401.00001\n2401.00002\n2401.00003"}
              rows={7}
              spellCheck={false}
              className="min-h-[188px] font-mono text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            {parsedIds.length > 0 ? (
              <Badge variant="secondary">{t("batch.ids", { current: parsedIds.length, total: MAX_BATCH })}</Badge>
            ) : null}
            {isOverLimit ? (
                <span className="flex items-center gap-1 text-xs text-[color:var(--px-shell-danger)]">
                <AlertCircle className="h-3 w-3" />
                {t("batch.limit_exceeded_only_the_first_will_be_submitted", { count: MAX_BATCH })}
              </span>
            ) : null}
          </div>

          <TaskList tasks={arxivTasks} translate={t} />
        </TabsContent>

        <TabsContent value="upload" className="mt-4 space-y-4">
          <NoticeBanner
            tone="info"
            icon={<Info className="h-4 w-4" />}
            description={(
              <span>
              {t("batch.supports_zip_rar_tar_gz_and_tex_files_up_to_50_mb_each_and_files_total", { count: MAX_BATCH })}
              </span>
            )}
          />

          <motion.div
            className="cursor-pointer"
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault()
                fileInputRef.current?.click()
              }
            }}
            role="button"
            tabIndex={0}
            whileHover={{ scale: 1.005 }}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".zip,.rar,.tar,.tar.gz,.tgz,.tex"
              className="hidden"
              onChange={handleFileChange}
            />
            <UploadDropSurface
              isDragActive={isDragActive}
              heading={t("batch.click_to_choose_files_or_drag_them_here")}
              body={t("batch.zip_rar_tar_gz_tex_up_to", { count: MAX_BATCH })}
              icon={<Upload className="h-8 w-8 text-[color:var(--px-shell-accent)]" />}
            />
          </motion.div>

          <AnimatePresence>
            {queuedFiles.length > 0 ? (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-2"
              >
                <p className="text-sm font-medium text-[color:var(--px-shell-muted)]">
                  {t("batch.files_queued_for_upload", { selected: queuedFiles.length, total: MAX_BATCH })}
                </p>
                {queuedFiles.map((queuedFile) => (
                  <RecordRow
                    key={queuedFile.id}
                    className="py-2.5"
                    icon={<FileArchive className="h-4 w-4 shrink-0 text-[color:var(--px-shell-accent)]" />}
                    title={<span className="font-mono">{queuedFile.file.name}</span>}
                    meta={`${(queuedFile.file.size / 1024 / 1024).toFixed(1)} MB`}
                    action={(
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={(event) => {
                          event.stopPropagation()
                          removeFile(queuedFile.id)
                        }}
                        className="h-7 w-7 rounded-full text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-danger-soft)] hover:text-[color:var(--px-shell-danger)]"
                        aria-label={t("batch.remove_file")}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  />
                ))}
              </motion.div>
            ) : null}
          </AnimatePresence>

          <div className="flex items-center gap-2">
            {queuedFiles.length > 0 ? (
              <span className="text-sm text-[color:var(--px-shell-muted)]">
                {t("batch.selected_files", { selected: queuedFiles.length, total: MAX_BATCH })}
              </span>
            ) : null}
          </div>

          <TaskList tasks={uploadTasks} translate={t} />
        </TabsContent>
      </Tabs>
    </div>
  )
})

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\ComparisonWorkbench.tsx
Relative path: features\translation-workflow\components\ComparisonWorkbench.tsx

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Columns, Download, FileText, Plus, Smartphone } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/ui/primitives/resizable"
import { ToggleGroup, ToggleGroupItem } from "@/ui/primitives/toggle-group"
import { API_BASE_URL } from "@/api-base"
import { TerminologyTable } from "@/features/translation-workflow/components/TerminologyTable"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"
import { Button } from "@/ui/button/Button"
import { Card, CardContent } from "@/ui/card/Card"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { StatePanel } from "@/ui/state-panel/StatePanel"

type ViewMode = "split" | "single"

interface PdfViewerProps {
  emptyMessage: string
  title: string
  url: string | null
}

function PdfViewer({ emptyMessage, title, url }: PdfViewerProps) {
  const { t } = useTranslation()

  if (!url) {
    return (
      <div className="h-full p-4">
        <StatePanel
          className="h-full min-h-[520px] justify-center rounded-[24px] border-dashed bg-[color:var(--px-shell-panel-strong)] shadow-none"
          icon={<FileText className="h-7 w-7" />}
          title={title}
          description={emptyMessage}
          meta={t("comparison.no_documents_available")}
        />
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-[color:var(--px-shell-panel-strong)]">
      <div className="border-b border-[color:var(--px-shell-line)] px-4 py-3 text-center text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--px-shell-muted)]">
        {title}
      </div>
      <iframe src={url} className="h-full w-full border-0" title={title} />
    </div>
  )
}

export function ComparisonWorkbench() {
  const [viewMode, setViewMode] = useState<ViewMode>("split")
  const { taskId, arxivId, resetTranslationState } = useTranslationTask()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const sourceUrl = taskId
    ? `${API_BASE_URL}/api/preview/${taskId}/source-pdf`
    : (arxivId ? `https://arxiv.org/pdf/${arxivId}.pdf` : null)
  const previewUrl = taskId ? `${API_BASE_URL}/api/preview/${taskId}/pdf` : null
  const downloadUrl = taskId ? `${API_BASE_URL}/api/download/${taskId}/pdf` : null

  const handleDownload = () => {
    if (downloadUrl) {
      window.open(downloadUrl, "_blank")
    }
  }

  const handleNewTranslation = () => {
    resetTranslationState()
    navigate("/")
  }

  const handleViewModeChange = (value: string) => {
    if (value === "split" || value === "single") {
      setViewMode(value)
    }
  }

  const emptyMessage = t("comparison.no_documents_available")
  const sourceTitle = t("comparison.original_pdf_source_document")
  const translatedTitle = t("comparison.translated_pdf_translation_result")

  return (
    <div className="flex h-full min-h-0 flex-col gap-6">
      <PageIntro
        title={t("comparison.title")}
        description={t("comparison.description")}
        actions={(
          <>
            <TerminologyTable taskId={taskId} />
            <Button variant="outline" size="sm" onClick={handleNewTranslation}>
              <Plus className="mr-2 h-4 w-4" />
              {t("common.new_translation")}
            </Button>
            <Button size="sm" onClick={handleDownload} disabled={!downloadUrl}>
              <Download className="mr-2 h-4 w-4" />
              {t("comparison.download_pdf")}
            </Button>
          </>
        )}
      />

      <Card className="overflow-hidden rounded-[28px] shadow-none">
        <CardContent className="flex flex-col gap-4 p-4 sm:p-5">
          <div className="flex flex-col gap-4 border-b border-[color:var(--px-shell-line)] pb-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
                {t("comparison.layoutLabel")}
              </p>
              <p className="text-sm text-[color:var(--px-shell-muted)]">
                {t("comparison.layoutDescription")}
              </p>
            </div>

            <ToggleGroup type="single" value={viewMode} onValueChange={handleViewModeChange} className="justify-start">
              <ToggleGroupItem value="split" aria-label={t("comparison.split_view")} className="gap-2">
                <Columns className="h-4 w-4" />
                <span>{t("comparison.split_view")}</span>
              </ToggleGroupItem>
              <ToggleGroupItem value="single" aria-label={t("comparison.single_view")} className="gap-2">
                <Smartphone className="h-4 w-4" />
                <span>{t("comparison.single_view")}</span>
              </ToggleGroupItem>
            </ToggleGroup>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)]">
            {viewMode === "split" ? (
              <ResizablePanelGroup orientation="horizontal">
                <ResizablePanel defaultSize={50} minSize={30}>
                  <div className="h-full min-h-0 overflow-hidden">
                    <PdfViewer emptyMessage={emptyMessage} title={sourceTitle} url={sourceUrl} />
                  </div>
                </ResizablePanel>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={50} minSize={30}>
                  <div className="h-full min-h-0 overflow-hidden">
                    <PdfViewer emptyMessage={emptyMessage} title={translatedTitle} url={previewUrl} />
                  </div>
                </ResizablePanel>
              </ResizablePanelGroup>
            ) : (
              <div className="h-full min-h-0 overflow-hidden">
                <PdfViewer emptyMessage={emptyMessage} title={translatedTitle} url={previewUrl} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\DropZone.tsx
Relative path: features\translation-workflow\components\DropZone.tsx

```tsx
import type { ChangeEvent } from "react"
import { useCallback, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, CheckCircle2, File, X } from "lucide-react"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { UploadCard } from "@/ui/upload-card/UploadCard"
import { uploadFile } from "@/lib/api"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"

type UploadErrorShape = {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

export function DropZone() {
  const { setTaskId, setArxivId, resetTranslationState } = useTranslationTask()
  const { setLatexValidation, latexValidation } = useTranslationConfig()
  const { t } = useTranslation()
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle")
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrag = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    if (event.type === "dragenter" || event.type === "dragover") {
      setIsDragActive(true)
    } else if (event.type === "dragleave") {
      setIsDragActive(false)
    }
  }, [])

  const processFile = useCallback(async (file: File) => {
    const validExtensions = [".zip", ".rar", ".tar", ".gz", ".tgz", ".tex"]
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()

    if (!validExtensions.includes(ext)) {
      toast.error(t("upload.unsupported_file_type_upload_a_zip_rar_tar_gz_or_tex_file"))
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      toast.error(t("upload.file_size_exceeds_the_50_mb_limit"))
      return
    }

    resetTranslationState()
    setFileName(file.name)
    setUploadStatus("uploading")
    setProgress(0)

    const interval = window.setInterval(() => {
      setProgress((prev) => (prev >= 90 ? prev : prev + 10))
    }, 200)

    try {
      const response = await uploadFile(file)

      window.clearInterval(interval)
      setProgress(100)
      setUploadStatus("success")
      setTaskId(response.task_id)

      if (response.latex_validation) {
        setLatexValidation(response.latex_validation)
        if (response.latex_validation.is_valid) {
          toast.success(t("upload.file_uploaded_successfully_and_passed_validation"))
        } else {
          toast.warning(t("upload.file_uploaded_successfully_but_validation_found_issues"))
        }
      } else {
        toast.success(t("upload.file_uploaded_successfully"))
      }

      setArxivId(null)
    } catch (error: unknown) {
      window.clearInterval(interval)
      setUploadStatus("error")
      const uploadError = error as UploadErrorShape
      console.error("[DropZone] Upload failed", uploadError)
      toast.error(t("upload.upload_failed"))
    }
  }, [resetTranslationState, setArxivId, setLatexValidation, setTaskId, t])

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(false)

    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      void processFile(event.dataTransfer.files[0])
    }
  }, [processFile])

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    event.preventDefault()
    if (event.target.files && event.target.files[0]) {
      void processFile(event.target.files[0])
    }
  }

  function resetUpload(event: React.MouseEvent) {
    event.stopPropagation()
    setUploadStatus("idle")
    setFileName("")
    setProgress(0)
    if (inputRef.current) {
      inputRef.current.value = ""
    }
    setLatexValidation(null)
  }

  function openFileDialog() {
    inputRef.current?.click()
  }

  return (
    <div className="w-full space-y-4">
      <motion.div
        layout
        className="cursor-pointer"
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            openFileDialog()
          }
        }}
        role="button"
        tabIndex={0}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".zip,.rar,.tar,.tar.gz,.tgz,.tex"
          onChange={handleChange}
        />

        <UploadCard
          isDragActive={isDragActive}
          fileName={fileName}
          progress={progress}
          status={uploadStatus}
          idleTitle={t("upload.click_to_upload_or_drag_a_file_here")}
          idleDescription={t("upload.supports_zip_rar_tar_gz_archives_or_a_single_tex_file_max_50_mb")}
          uploadingLabel={t("upload.uploading_and_validating")}
          successActionLabel={t("upload.replace_file")}
          errorLabel={t("upload.upload_failed")}
          retryLabel={t("common.actions.retry")}
          onReset={resetUpload}
        />
      </motion.div>

      <AnimatePresence>
        {uploadStatus === "success" && latexValidation ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <NoticeBanner
              tone={latexValidation.is_valid ? "success" : "danger"}
              icon={latexValidation.is_valid ? <CheckCircle2 className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
              title={latexValidation.is_valid ? t("upload.valid_latex_project") : t("upload.invalid_latex_project")}
              description={
                latexValidation.main_file ? (
                  <span className="flex items-center gap-2">
                    <File className="h-4 w-4 shrink-0" />
                    <span>
                      {t("upload.main_entry_file")}
                      <span className="ml-1 font-mono">{latexValidation.main_file}</span>
                    </span>
                  </span>
                ) : undefined
              }
            >
              {latexValidation.warnings.length > 0 || latexValidation.errors.length > 0 ? (
                <div className="space-y-1 border-t border-current/15 pt-2 text-sm">
                  {latexValidation.errors.map((err, index) => (
                    <div key={`err-${index}`} className="flex items-center gap-2">
                      <X className="h-3 w-3 shrink-0" />
                      <span>{err}</span>
                    </div>
                  ))}
                  {latexValidation.warnings.map((warn, index) => (
                    <div key={`warn-${index}`} className="flex items-center gap-2">
                      <AlertTriangle className="h-3 w-3 shrink-0" />
                      <span>{warn}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </NoticeBanner>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\FormattingPanel.tsx
Relative path: features\translation-workflow\components\FormattingPanel.tsx

```tsx
import type { ReactNode } from "react"
import { AlignJustify, BookOpen, Columns2, FileText, Indent, Maximize2, Quote, Type } from "lucide-react"
import { useTranslation } from "react-i18next"

import { FormFieldShell } from "@/ui/form-field-shell/FormFieldShell"
import { Input } from "@/ui/input/Input"
import { ToggleSwitch } from "@/ui/toggle-switch/ToggleSwitch"
import { cn } from "@/lib/utils"
import { Label } from "@/ui/primitives/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/primitives/select"
import type { FormattingConfig } from "@/types/config"

interface NumericFieldProps {
  id: string
  label: string
  icon: ReactNode
  value: number | undefined | null
  onChange: (value: number | null) => void
  min?: number
  max?: number
  step?: number
  placeholder?: string
  tooltip?: string
}

function NumericField({
  id,
  label,
  icon,
  value,
  onChange,
  min,
  max,
  step,
  placeholder,
  tooltip,
}: NumericFieldProps) {
  const { t } = useTranslation()
  const enabled = value !== undefined && value !== null

  return (
    <FormFieldShell
      label={(
        <Label htmlFor={id} className="flex cursor-pointer select-none items-center gap-2 text-sm">
          {label}
        </Label>
      )}
      icon={icon}
      headerAside={(
        <ToggleSwitch
          id={`${id}-switch`}
          checked={enabled}
          onCheckedChange={(on) => onChange(on ? (value ?? (min ?? 1)) : null)}
        />
      )}
    >
      <Input
        id={id}
        type="number"
        min={min}
        max={max}
        step={step ?? 0.1}
        placeholder={enabled ? "" : (placeholder ?? t("formatting.keepOriginal"))}
        value={enabled ? (value ?? "") : ""}
        disabled={!enabled}
        onChange={(event) => {
          const nextValue = parseFloat(event.target.value)
          onChange(Number.isNaN(nextValue) ? null : nextValue)
        }}
        className={cn("h-8 text-sm transition-opacity duration-200", !enabled && "cursor-not-allowed opacity-40")}
        title={tooltip}
      />
    </FormFieldShell>
  )
}

interface SelectFieldProps {
  id: string
  label: string
  icon: ReactNode
  value: string | undefined | null
  onChange: (value: string | null) => void
  options: { value: string; label: string }[]
}

function SelectField({ id, label, icon, value, onChange, options }: SelectFieldProps) {
  const { t } = useTranslation()

  return (
    <FormFieldShell
      label={<Label htmlFor={id} className="flex items-center gap-2 text-sm">{label}</Label>}
      icon={icon}
    >
      <Select value={value ?? "__keep__"} onValueChange={(nextValue) => onChange(nextValue === "__keep__" ? null : nextValue)}>
        <SelectTrigger id={id} className="h-8 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__keep__">{t("formatting.keepOriginal")}</SelectItem>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FormFieldShell>
  )
}

interface ToggleRowProps {
  id: string
  label: string
  description: string
  icon: ReactNode
  value: boolean | undefined | null
  onChange: (value: boolean | null) => void
}

function ToggleRow({ id, label, description, icon, value, onChange }: ToggleRowProps) {
  return (
    <FormFieldShell
      label={<Label htmlFor={id} className="cursor-pointer text-sm">{label}</Label>}
      icon={icon}
      description={description}
      headerAside={<ToggleSwitch id={id} checked={value === true} onCheckedChange={(on) => onChange(on ? true : null)} />}
      bodyClassName="mt-0"
    />
  )
}

export interface FormattingPanelProps {
  value: FormattingConfig
  onChange: (patch: Partial<FormattingConfig>) => void
  targetLanguage?: string
  className?: string
}

const CJK_LANGS = new Set(["zh", "ja", "ko"])

export function FormattingPanel({ value, onChange, targetLanguage, className }: FormattingPanelProps) {
  const isCjk = targetLanguage ? CJK_LANGS.has(targetLanguage) : false
  const { t } = useTranslation()

  return (
    <div className={cn("space-y-3", className)}>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <NumericField
          id="fmt-line-spacing"
          label={t("formatting.lineSpacing")}
          icon={<AlignJustify className="h-4 w-4" />}
          value={value.line_spacing}
          onChange={(nextValue) => onChange({ line_spacing: nextValue ?? undefined })}
          min={1.0}
          max={2.5}
          step={0.1}
          placeholder={t("formatting.keepOriginalLineSpacing")}
          tooltip={t("formatting.line_spacing_multiplier_recommended_range_1_0_2_5")}
        />
        <NumericField
          id="fmt-font-size"
          label={t("formatting.fontSize")}
          icon={<Type className="h-4 w-4" />}
          value={value.font_size}
          onChange={(nextValue) => onChange({ font_size: nextValue ?? undefined })}
          min={8}
          max={14}
          step={0.5}
          placeholder={t("formatting.keepOriginalFontSize")}
          tooltip={t("formatting.global_font_size_recommended_range_8_14_pt")}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectField
          id="fmt-column-mode"
          label={t("formatting.columnMode")}
          icon={<Columns2 className="h-4 w-4" />}
          value={value.column_mode}
          onChange={(nextValue) => onChange({ column_mode: nextValue ?? undefined })}
          options={[
            { value: "single", label: t("formatting.column.single") },
            { value: "double", label: t("formatting.column.double") },
          ]}
        />
        <SelectField
          id="fmt-margin"
          label={t("formatting.pageMargin")}
          icon={<Maximize2 className="h-4 w-4" />}
          value={value.margin}
          onChange={(nextValue) => onChange({ margin: nextValue ?? undefined })}
          options={[
            { value: "narrow", label: t("formatting.margin.narrow") },
            { value: "normal", label: t("formatting.margin.standard") },
            { value: "wide", label: t("formatting.margin.wide") },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectField
          id="fmt-bib-style"
          label={t("formatting.bibliographyStyle")}
          icon={<BookOpen className="h-4 w-4" />}
          value={value.bib_style}
          onChange={(nextValue) => onChange({ bib_style: nextValue ?? undefined })}
          options={[
            { value: "gbt7714-numerical", label: t("formatting.bibliography.gbtNumerical") },
            { value: "gbt7714-author-year", label: t("formatting.bibliography.gbtAuthorYear") },
            { value: "ieeetr", label: "IEEE" },
            { value: "apalike", label: "APA" },
          ]}
        />
        <SelectField
          id="fmt-cite-style"
          label={t("formatting.citationStyle")}
          icon={<Quote className="h-4 w-4" />}
          value={value.cite_style}
          onChange={(nextValue) => onChange({ cite_style: nextValue ?? undefined })}
          options={[
            { value: "numbers", label: t("formatting.citationStyle.numeric") },
            { value: "super", label: t("formatting.citationStyle.superscript") },
            { value: "authoryear", label: t("formatting.citationStyle.authorYear") },
          ]}
        />
      </div>

      {isCjk ? (
        <SelectField
          id="fmt-cjk-font"
          label={t("formatting.chineseFont")}
          icon={<FileText className="h-4 w-4" />}
          value={value.cjk_font}
          onChange={(nextValue) => onChange({ cjk_font: nextValue ?? undefined })}
          options={[
            { value: "songti", label: t("formatting.font.songti") },
            { value: "heiti", label: t("formatting.font.heiti") },
          ]}
        />
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ToggleRow
          id="fmt-paragraph-indent"
          label={t("formatting.firstLineIndent")}
          description={t("formatting.use_a_2em_first_line_indent_when_enabled")}
          icon={<Indent className="h-4 w-4" />}
          value={value.paragraph_indent}
          onChange={(nextValue) => onChange({ paragraph_indent: nextValue ?? undefined })}
        />
        <ToggleRow
          id="fmt-localize-captions"
          label={t("formatting.localizeCaptions")}
          description={t("formatting.localizeCaptionsDescription")}
          icon={<FileText className="h-4 w-4" />}
          value={value.localize_captions}
          onChange={(nextValue) => onChange({ localize_captions: nextValue ?? undefined })}
        />
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\ProcessingLogViewer.tsx
Relative path: features\translation-workflow\components\ProcessingLogViewer.tsx

```tsx
import type { HTMLAttributes } from "react"
import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"

interface ProcessingLogViewerProps extends HTMLAttributes<HTMLDivElement> {
  logs: string[]
  className?: string
}

export function ProcessingLogViewer({ logs, className, ...props }: ProcessingLogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { t } = useTranslation()

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div
      className={cn(
        "h-[300px] overflow-y-auto overflow-x-hidden rounded-md border border-[color:color-mix(in_srgb,var(--px-shell-line)_88%,rgba(23,20,17,0.14))] bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_85%,var(--px-shell-surface))] p-4 font-mono text-xs text-[color:var(--px-shell-ink)] shadow-inner",
        className,
      )}
      ref={scrollRef}
      {...props}
    >
      {logs.length === 0 ? (
        <div className="italic text-[color:var(--px-shell-muted)]">{t("logs.waiting_for_logs")}</div>
      ) : null}
      {logs.map((log, index) => (
        <div
          key={index}
          className="whitespace-pre-wrap border-b border-[color:color-mix(in_srgb,var(--px-shell-line)_88%,rgba(23,20,17,0.14))]/80 py-0.5 last:border-0 hover:bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_76%,black_24%)]"
        >
          {log}
        </div>
      ))}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\ProcessingWorkspace.tsx
Relative path: features\translation-workflow\components\ProcessingWorkspace.tsx

```tsx
import { AlertTriangle, CheckCircle2, Code, Download, LogIn, RotateCw } from "lucide-react"
import { useEffect } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { useAuth } from "@/contexts/AuthContext"
import { getTaskCopy } from "@/i18n/task-copy"
import { Button } from "@/ui/button/Button"
import { CardDescription, CardTitle } from "@/ui/card/Card"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { Pill } from "@/ui/pill/Pill"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { WorkflowStepper, type WorkflowStepState } from "@/ui/workflow-stepper/WorkflowStepper"
import { useTranslationTask } from "../hooks/useTranslationTask"
import { ProcessingLogViewer } from "./ProcessingLogViewer"

const stepOrder = ["downloading", "translating", "validating", "compiling"] as const

export function ProcessingWorkspace() {
  const {
    taskId: storeTaskId,
    status,
    stage,
    detailCode,
    detailParams,
    failureReasonCode,
    logs,
    pollStatus,
    stopPolling,
    setTaskId,
    taskWarnings,
  } = useTranslationTask()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useTranslation()

  const urlTaskId = searchParams.get("taskId")
  const effectiveTaskId = urlTaskId || storeTaskId
  const isGuest = !user

  useEffect(() => {
    if (urlTaskId && urlTaskId !== storeTaskId) {
      setTaskId(urlTaskId)
    }
  }, [urlTaskId, storeTaskId, setTaskId])

  useEffect(() => {
    if (effectiveTaskId) {
      pollStatus()
    }
    return () => stopPolling()
  }, [effectiveTaskId, pollStatus, stopPolling])

  const normalizedStatus = (status || "").toLowerCase()
  const normalizedStage = ((stage === "extracting" ? "downloading" : stage) || "").toLowerCase()
  const canPreview =
    normalizedStatus === "completed" || normalizedStatus === "completed_with_warnings"
  const isFailed = ["failed", "failed_compilation", "structure_invalid"].includes(normalizedStatus)

  const copy = getTaskCopy(t, {
    status,
    stage: normalizedStage,
    detailCode,
    detailParams,
    failureReasonCode,
    warnings: taskWarnings,
  })

  const steps = [
    { id: "downloading", label: t("task.stage.downloading") },
    { id: "translating", label: t("task.stage.translating") },
    { id: "validating", label: t("task.stage.validating") },
    { id: "compiling", label: t("task.stage.compiling") },
  ]

  const currentStepIndex = (() => {
    if (canPreview) {
      return stepOrder.length
    }

    if (normalizedStage === "downloading" || normalizedStage === "downloading_pdf") {
      return 0
    }
    if (normalizedStage === "parsing" || normalizedStage === "translating") {
      return 1
    }
    if (normalizedStage === "validating") {
      return 2
    }
    if (normalizedStage === "compiling" || normalizedStage === "compilation_failed") {
      return 3
    }
    if (isFailed) {
      return Math.max(0, stepOrder.indexOf("translating"))
    }

    return 0
  })()

  const activeTaskId = effectiveTaskId
  const currentDetail = copy.detailLabel || copy.stageLabel || copy.statusLabel
  const failureText = copy.failureLabel || copy.statusLabel
  const summaryStepCount = canPreview ? steps.length : Math.min(currentStepIndex + 1, steps.length)
  const summaryAccent = canPreview
    ? "text-[color:var(--px-shell-success)]"
    : isFailed
      ? "text-[color:var(--px-shell-danger)]"
      : "text-[color:var(--px-shell-accent)]"
  const summaryTone = canPreview ? "success" : isFailed ? "danger" : "accent"
  const stepperItems = steps.map((step, index) => {
    const state: WorkflowStepState = index < currentStepIndex || canPreview
      ? "complete"
      : isFailed && index === currentStepIndex
        ? "error"
        : !canPreview && !isFailed && index === currentStepIndex
          ? "current"
          : "upcoming"

    return {
      id: step.id,
      label: step.label,
      description:
        !canPreview && !isFailed && index === currentStepIndex
          ? currentDetail
          : isFailed && index === currentStepIndex
            ? failureText
            : null,
      state,
    }
  })

  return (
    <div
      data-testid="processing-shell"
      className="mx-auto flex h-full min-h-0 w-full max-w-[1480px] flex-1 flex-col gap-4 overflow-hidden px-4 py-4 sm:px-6 lg:px-8 xl:px-10 xl:py-6"
    >
      {isGuest ? (
        <NoticeBanner
          tone="warning"
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t("processing.guest_mode")}
          description={t("processing.you_won_t_be_able_to_access_the_translation_results_again_after_leaving_this_page")}
          action={(
            <Button type="button" variant="ghost" size="sm" onClick={() => navigate("/login")}>
              <LogIn className="h-3 w-3" />
              {t("processing.sign_in_to_save_to_history")}
            </Button>
          )}
        />
      ) : null}

      {taskWarnings ? (
        <NoticeBanner
          tone="warning"
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t("processing.formatting_note")}
          description={t("task.detail.formattingWarning", { warningText: taskWarnings })}
        />
      ) : null}

      <PanelShell
        data-testid="processing-hero-panel"
        tone="hero"
        className="flex shrink-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between lg:px-6"
      >
        <div className="max-w-2xl">
          <h1 className="text-2xl font-bold tracking-tight text-[color:var(--px-shell-ink)] lg:text-3xl">
            {canPreview ? t("task.result.completed") : t("task.result.inProgress")}
          </h1>
          <p className="mt-1.5 text-sm text-[color:var(--px-shell-muted)] lg:text-base">
            {t("processing.track_translation_task_status_in_real_time")}
          </p>
        </div>

        {canPreview ? (
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <Button
              variant="outline"
              onClick={() => window.open(`${API_BASE_URL}/api/download/${activeTaskId}/source`, "_blank")}
            >
              <Download className="mr-2 h-4 w-4" />
              {t("task.steps.downloadSource")}
            </Button>
            <Button onClick={() => navigate("/preview")}>
              {t("common.actions.viewResult")}
            </Button>
          </div>
        ) : isFailed ? (
          <Button variant="outline" onClick={() => navigate("/")}>
            {t("common.actions.backToHome")}
          </Button>
        ) : (
          <Button variant="destructive" onClick={() => navigate("/")}>
            {t("processing.cancel_task")}
          </Button>
        )}
      </PanelShell>

      <div
        data-testid="processing-workbench"
        className="grid min-h-0 flex-1 grid-cols-1 gap-4 xl:grid-cols-[minmax(380px,0.92fr)_minmax(480px,1.08fr)]"
      >
        <div
          data-testid="processing-summary-panel"
          className="grid min-h-0 content-start gap-4 xl:grid-rows-[minmax(0,1.2fr)_minmax(176px,0.8fr)]"
        >
          <PanelShell
            data-testid="processing-status-card"
            padding="none"
            className="flex min-h-0 flex-col overflow-hidden"
          >
            <div className="flex flex-col gap-1.5 border-b border-[color:var(--px-shell-line)] px-6 py-5">
              <CardTitle>{t("processing.task_status")}</CardTitle>
              <CardDescription>{currentDetail}</CardDescription>
            </div>
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-4 pt-4">
              <WorkflowStepper items={stepperItems} />
            </div>
          </PanelShell>

          <PanelShell
            data-testid="processing-summary-card"
            tone={summaryTone}
            className="overflow-hidden"
          >
            <div className="flex h-full min-h-[176px] flex-col justify-between p-5">
              <div className="flex items-start justify-between gap-3">
                <PanelShell
                  tone="panel"
                  padding="compact"
                  className="rounded-2xl bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_88%,white)]"
                >
                  {canPreview ? (
                    <CheckCircle2 className="h-12 w-12 text-[color:var(--px-shell-success)]" />
                  ) : isFailed ? (
                    <AlertTriangle className="h-12 w-12 text-[color:var(--px-shell-danger-strong)]" />
                  ) : (
                    <RotateCw className="h-12 w-12 animate-spin text-[color:var(--px-shell-accent)]" />
                  )}
                </PanelShell>
                <Pill tone="muted" className="px-3 py-1 text-sm font-semibold tracking-normal">
                  {summaryStepCount}/{steps.length}
                </Pill>
              </div>

              {canPreview ? (
                <div className="space-y-2">
                  <p className={`text-sm font-medium ${summaryAccent}`}>{copy.statusLabel}</p>
                  <div className="space-y-1">
                    <p className="text-[1.75rem] font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
                      {t("task.result.completed")}
                    </p>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">{currentDetail}</p>
                  </div>
                </div>
              ) : isFailed ? (
                <div className="space-y-2">
                  <p className={`text-sm font-medium ${summaryAccent}`}>{copy.statusLabel}</p>
                  <div className="space-y-1">
                    <p className="text-[1.75rem] font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
                      {t("task.result.failed")}
                    </p>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">{failureText}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className={`text-sm font-medium ${summaryAccent}`}>
                    {copy.stageLabel || copy.statusLabel}
                  </p>
                  <div className="space-y-1">
                    <p className="text-[1.75rem] font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
                      {currentDetail}
                    </p>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">{copy.statusLabel}</p>
                  </div>
                  {copy.isRateLimited ? (
                    <div className="flex animate-pulse items-center gap-2 rounded-lg border border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] px-3 py-2">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-[color:var(--px-shell-warning)]" />
                      <p className="text-left text-xs text-[color:var(--px-shell-warning)]">
                        {copy.detailLabel}
                      </p>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </PanelShell>
        </div>

        <div data-testid="processing-log-panel" className="min-h-0 min-w-0">
          <PanelShell padding="none" className="flex h-full min-h-0 flex-col overflow-hidden">
            <div className="flex shrink-0 flex-col gap-3 border-b border-[color:var(--px-shell-line)] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-2">
                <CardTitle>{t("processing.live_logs")}</CardTitle>
                <CardDescription>{currentDetail}</CardDescription>
              </div>
              <div className="flex gap-2 self-start sm:self-auto">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Code className="h-4 w-4" />
                </Button>
                <StatusBadge tone={canPreview ? "success" : isFailed ? "danger" : "accent"} size="md">
                  {copy.statusLabel}
                </StatusBadge>
              </div>
            </div>
            <div className="flex min-h-0 flex-1 px-6 pb-6 pt-5">
              <ProcessingLogViewer
                data-testid="processing-log-scroll-region"
                logs={logs}
                className="h-full min-h-0 w-full flex-1 rounded-2xl px-4 py-4 text-[13px] leading-6"
              />
            </div>
          </PanelShell>
        </div>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\TerminologyTable.tsx
Relative path: features\translation-workflow\components\TerminologyTable.tsx

```tsx
import { useCallback, useEffect, useState } from "react"
import { AlertCircle, BookText, Download } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { API_BASE_URL } from "@/api-base"
import { ScrollArea } from "@/ui/primitives/scroll-area"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/ui/primitives/sheet"
import { Skeleton } from "@/ui/primitives/skeleton"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"

interface TermPair {
  source: string
  target: string
}

interface TerminologyTableProps {
  taskId: string | null
}

function parseCSV(text: string): TermPair[] {
  const lines = text.split("\n")
  const pairs: TermPair[] = []
  const startIndex = lines[0]?.toLowerCase().includes("source term") ? 1 : 0

  for (let index = startIndex; index < lines.length; index += 1) {
    const line = lines[index].trim()
    if (!line) {
      continue
    }

    const parts = line.split(",")
    if (parts.length < 2) {
      continue
    }

    const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g)
    let source = ""
    let target = ""

    if (matches && matches.length >= 2) {
      source = matches[0]
      target = matches.slice(1).join(",")
    } else {
      source = parts[0]
      target = parts.slice(1).join(",")
    }

    source = source.replace(/^"|"$/g, "").trim()
    target = target.replace(/^"|"$/g, "").trim()

    if (source && target) {
      pairs.push({ source, target })
    }
  }

  return pairs
}

export function TerminologyTable({ taskId }: TerminologyTableProps) {
  const { t } = useTranslation()
  const [data, setData] = useState<TermPair[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)

  const downloadUrl = taskId ? `${API_BASE_URL}/api/download/${taskId}/terminology` : null

  const fetchTerminology = useCallback(async () => {
    if (!taskId || !downloadUrl) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(downloadUrl)

      if (!response.ok) {
        if (response.status === 404) {
          setError(t("glossary.no_glossary_was_found_for_this_task"))
        } else {
          setError(t("glossary.failed_to_load_glossary"))
        }
        setData([])
        return
      }

      const text = await response.text()
      setData(parseCSV(text))
    } catch {
      setError(t("glossary.a_network_error_occurred_while_loading_the_glossary"))
      setData([])
    } finally {
      setLoading(false)
    }
  }, [downloadUrl, taskId, t])

  useEffect(() => {
    if (isOpen && taskId) {
      void fetchTerminology()
    }
  }, [fetchTerminology, isOpen, taskId])

  function handleDownload() {
    if (downloadUrl) {
      window.open(downloadUrl, "_blank")
    }
  }

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" disabled={!taskId}>
          <BookText className="mr-2 h-4 w-4" />
          {t("glossary.glossary")}
        </Button>
      </SheetTrigger>
      <SheetContent className="flex h-full w-[400px] flex-col bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <BookText className="h-5 w-5" />
            {t("glossary.glossary_2")}
          </SheetTitle>
          <SheetDescription>
            {t("glossary.technical_terms_extracted_from_and_used_in_this_document")}
          </SheetDescription>
        </SheetHeader>

        <DataTable className="mt-6 flex-1 rounded-[20px] shadow-none">
          {loading ? (
            <div className="space-y-4 p-4">
              {[1, 2, 3, 4, 5].map((item) => (
                <div key={item} className="flex gap-4">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="p-4">
              <NoticeBanner
                tone="danger"
                icon={<AlertCircle className="h-4 w-4" />}
                title={t("glossary.failed_to_load_glossary")}
                description={error}
                className="rounded-[18px]"
              />
            </div>
          ) : data.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center p-6 text-center text-[color:var(--px-shell-muted)]">
              <BookText className="mb-2 h-10 w-10 opacity-25" />
              <p>{t("glossary.no_glossary_data_found")}</p>
              <p className="mt-1 text-xs opacity-70">
                {t("glossary.make_sure_generate_glossary_was_enabled_during_translation")}
              </p>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <div className="w-full text-sm">
                <DataTableHeader className="sticky top-0 z-10">
                  <DataTableHeaderRow className="grid-cols-2 gap-0 px-0 py-0">
                    <DataTableHeaderCell className="border-r border-[color:var(--px-shell-line)] p-3 text-left normal-case tracking-normal">
                      {t("glossary.source")}
                    </DataTableHeaderCell>
                    <DataTableHeaderCell className="p-3 text-left normal-case tracking-normal">
                      {t("glossary.translation")}
                    </DataTableHeaderCell>
                  </DataTableHeaderRow>
                </DataTableHeader>
                <DataTableBody className="divide-y divide-[color:var(--px-shell-line)]">
                  {data.map((pair, index) => (
                    <DataTableRow
                      key={`${pair.source}-${pair.target}-${index}`}
                      className="grid-cols-2 gap-0 px-0 py-0 transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
                    >
                      <DataTableCell className="wrap-break-words border-r border-[color:var(--px-shell-line)] p-3 font-medium text-[color:var(--px-shell-ink)]">
                        {pair.source}
                      </DataTableCell>
                      <DataTableCell className="wrap-break-words p-3 text-[color:var(--px-shell-muted)]">
                        {pair.target}
                      </DataTableCell>
                    </DataTableRow>
                  ))}
                </DataTableBody>
              </div>
            </ScrollArea>
          )}
        </DataTable>

        <div className="mt-6 flex justify-end">
          <Button onClick={handleDownload} disabled={!downloadUrl || loading || data.length === 0} className="w-full sm:w-auto">
            <Download className="mr-2 h-4 w-4" />
            {t("glossary.download_glossary_csv")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\TranslationWorkspace.tsx
Relative path: features\translation-workflow\components\TranslationWorkspace.tsx

```tsx
import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { ChevronDown, Download, FileText, Info, Loader2, RefreshCw, X, Zap } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/ui/primitives/collapsible"
import { Card, CardContent } from "@/ui/card/Card"
import { InfoTile } from "@/ui/info-tile/InfoTile"
import { Input } from "@/ui/input/Input"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { TabsContent } from "@/ui/primitives/tabs"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import { useAuth } from "@/contexts/AuthContext"
import { AdvancedConfig } from "@/features/translation-workflow/components/AdvancedConfig"
import {
  BatchTranslation,
  type BatchTranslationHandle,
  type BatchTranslationState,
} from "@/features/translation-workflow/components/BatchTranslation"
import { DropZone } from "@/features/translation-workflow/components/DropZone"
import { useTranslationConfig } from "@/features/translation-workflow/hooks/useTranslationConfig"
import { useTranslationTask } from "@/features/translation-workflow/hooks/useTranslationTask"
import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { cn } from "@/lib/utils"

export function TranslationWorkspace() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useTranslation()
  const isAuthenticated = !!user
  const { config, loadUserSettings } = useTranslationConfig()
  const {
    taskId,
    status,
    downloadProgress,
    downloadStage,
    isDownloading,
    startArxivDownload,
    startTranslation,
  } = useTranslationTask()
  const canStartSingleTranslation = Boolean(taskId && status === "ready")

  const [activeTab, setActiveTab] = useState("arxiv")
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [localArxivId, setLocalArxivId] = useState("")
  const [isLoadingSource, setIsLoadingSource] = useState(false)
  const [showArxivTip, setShowArxivTip] = useState(true)
  const [showApiWarning, setShowApiWarning] = useState(true)
  const batchRef = useRef<BatchTranslationHandle>(null)
  const [batchState, setBatchState] = useState<BatchTranslationState>({
    isSubmitting: false,
    activeTab: "arxiv",
    canSubmit: false,
  })

  const stageMap: Record<string, string> = {
    downloading: t("dashboard.downloading_source_files_from_arxiv"),
    extracting: t("dashboard.extracting_source_files_2"),
    downloading_pdf: t("dashboard.downloading_the_original_pdf"),
    validating: t("dashboard.validating_latex_structure_2"),
  }

  const stageTitleMap: Record<string, string> = {
    downloading: t("task.steps.downloadSource"),
    extracting: t("dashboard.extracting_source_files"),
    downloading_pdf: t("dashboard.downloading_original_pdf"),
    validating: t("dashboard.validating_latex_structure"),
  }

  useEffect(() => {
    loadUserSettings()
  }, [loadUserSettings])

  async function handleLoadArxiv() {
    if (!localArxivId.trim()) {
      return
    }

    setIsLoadingSource(true)
    toast.info(t("dashboard.loading_source_document_please_wait"))
    try {
      await startArxivDownload(localArxivId)
    } finally {
      setIsLoadingSource(false)
    }
  }

  async function handleStart() {
    if (!taskId) {
      return
    }

    await startTranslation({
      source_language: config.source_language,
      target_language: config.target_language,
      advanced_config: config.advanced_config,
    })
    navigate("/processing")
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <EditorialTabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <div className="flex justify-start">
          <EditorialTabsList className="gap-1">
            <EditorialTabsTrigger value="arxiv">
              {t("dashboard.arxiv_id")}
            </EditorialTabsTrigger>
            <EditorialTabsTrigger value="upload">
              {t("dashboard.local_upload")}
            </EditorialTabsTrigger>
            <EditorialTabsTrigger value="batch">
              {t("dashboard.batch_translation")}
            </EditorialTabsTrigger>
          </EditorialTabsList>
        </div>

        <Card className="overflow-visible rounded-[28px] shadow-none">
          <CardContent className="p-6 sm:p-8">
            <TabsContent value="arxiv" className="mt-0 space-y-6">
              <div className="max-w-2xl">
                <div className="mb-2 flex items-center gap-3">
                  <FileText className="h-5 w-5 text-[color:var(--px-shell-accent)]" />
                  <h3 className="text-lg font-bold text-[color:var(--px-shell-ink)]">{t("dashboard.arxiv_paper")}</h3>
                </div>
                <p className="mb-6 text-sm text-[color:var(--px-shell-muted)]">
                  {t("dashboard.enter_an_arxiv_id_for_example_2310_xxxxx_to_download_source_files")}
                </p>

                <div className="flex flex-col gap-4 sm:flex-row">
                  <Input
                    placeholder={t("dashboard.enter_an_arxiv_id_for_example_2301_12345")}
                    value={localArxivId}
                    onChange={(event) => setLocalArxivId(event.target.value)}
                    className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)] px-4 py-6 font-mono text-base"
                  />
                  <Button
                    onClick={handleLoadArxiv}
                    disabled={!localArxivId || isLoadingSource || isDownloading || status === "processing"}
                    className="h-auto rounded-[22px] px-8 font-medium"
                  >
                    {isLoadingSource || isDownloading ? (
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="mr-2 h-4 w-4" />
                    )}
                    {t("dashboard.load_source")}
                  </Button>
                </div>

                {showArxivTip ? (
                  <div
                    className="mt-4 animate-in fade-in zoom-in-95 duration-200"
                    onClick={() => setShowArxivTip(false)}
                  >
                    <NoticeBanner
                      tone="neutral"
                      icon={<Info className="h-4 w-4 text-[color:var(--px-shell-accent)]" />}
                      title={t("dashboard.tip")}
                      description={t("dashboard.large_papers_can_take_longer_to_download_through_the_official_arxiv_channel_please_be_patient")}
                      className="relative cursor-pointer transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
                      action={<X className="h-4 w-4 opacity-50 transition-opacity hover:opacity-100" />}
                    />
                  </div>
                ) : null}

                {isLoadingSource || isDownloading ? (
                  <PanelShell
                    tone="glass"
                    className="mt-4 animate-in fade-in space-y-3 duration-200"
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-bold text-[color:var(--px-shell-ink)]">
                        {stageTitleMap[downloadStage] ?? t("dashboard.preparing")}
                      </span>
                      <span className="font-mono text-[color:var(--px-shell-muted)]">{Math.round(downloadProgress)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-[color:var(--px-shell-line)]">
                      <div
                        className="h-full rounded-full bg-[color:var(--px-shell-accent)] transition-all duration-300 ease-out"
                        style={{ width: `${Math.round(downloadProgress)}%` }}
                      />
                    </div>
                    <p className="text-xs text-[color:var(--px-shell-muted)]">
                      {stageMap[downloadStage] ?? t("dashboard.preparing_download")}
                    </p>
                  </PanelShell>
                ) : null}
              </div>
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

            {taskId && status === "ready" && activeTab !== "batch" ? (
              <NoticeBanner
                tone="success"
                icon={<FileText className="h-5 w-5" />}
                title={t("dashboard.source_document_ready")}
                description={
                  <span className="font-mono text-sm">
                    {t("dashboard.task_id", { taskId })}
                  </span>
                }
                className="mt-6 animate-in fade-in slide-in-from-top-2"
              />
            ) : null}
          </CardContent>
        </Card>
      </EditorialTabs>

      <Card className="overflow-hidden rounded-[28px] shadow-none">
        <CardContent className="p-6 sm:p-8">
            <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
              <div className="flex flex-1 items-center gap-6 opacity-70 cursor-not-allowed">
                <div className="flex-1">
                  <InfoTile
                    title={t("dashboard.summary.sourceLanguage")}
                    description={t("dashboard.summary.detectAutomatically")}
                    tone="panel"
                    valueClassName="text-[color:var(--px-shell-muted)]"
                  />
                </div>
                <div className="flex-1">
                  <InfoTile
                    title={t("dashboard.summary.targetLanguage")}
                    description={t("dashboard.summary.followGlobalSettings")}
                    tone="panel"
                    valueClassName="text-[color:var(--px-shell-muted)]"
                  />
                </div>
              </div>
            {activeTab === "batch" ? (
              <Button
                size="lg"
                onClick={() => batchRef.current?.submitCurrent()}
                disabled={!batchState.canSubmit}
                className="w-full gap-3 px-10 py-6 text-base font-bold md:w-auto"
              >
                {batchState.isSubmitting ? t("dashboard.submitting") : t("dashboard.start_batch_translation")}
                {batchState.isSubmitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Zap className="h-5 w-5 fill-current" />
                )}
              </Button>
            ) : (
              <Button
                size="lg"
                onClick={handleStart}
                disabled={!canStartSingleTranslation}
                className="w-full gap-3 px-10 py-6 text-base font-bold md:w-auto disabled:scale-100 disabled:shadow-none disabled:opacity-50"
              >
                {t("dashboard.start_translation")}
                <Zap className="h-5 w-5 fill-current" />
              </Button>
            )}
          </div>
        </CardContent>

        <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen} className="group border-t border-[color:var(--px-shell-line)]">
          <CollapsibleTrigger asChild>
            <div className="flex cursor-pointer select-none items-center justify-center gap-2 py-4 text-sm font-bold text-[color:var(--px-shell-muted)] transition-colors hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]">
              <span>{t("dashboard.advancedConfig")}</span>
              <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", isConfigOpen ? "rotate-180" : "")} />
            </div>
          </CollapsibleTrigger>

          <CollapsibleContent className="p-6 pt-2 sm:p-8">
            {showApiWarning ? (
              <div className="mb-6 animate-in fade-in zoom-in-95 duration-200" onClick={() => setShowApiWarning(false)}>
                <NoticeBanner
                  tone="warning"
                  icon={<Info className="h-4 w-4" />}
                  description={t("dashboard.the_default_api_uses_a_free_tier_and_may_affect_quality_and_speed_a_custom_api_is_recommended")}
                  className="group cursor-pointer transition-opacity hover:opacity-95"
                  action={<X className="h-4 w-4 opacity-50 transition-opacity group-hover:opacity-100" />}
                />
              </div>
            ) : null}
            <AdvancedConfig />
          </CollapsibleContent>
        </Collapsible>
      </Card>

      <div className="pb-12" />
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\hooks\useTranslationConfig.ts
Relative path: features\translation-workflow\hooks\useTranslationConfig.ts

```ts
import { useTranslationStore } from "@/features/translation-workflow/store/useTranslationStore"

export function useTranslationConfig() {
  const config = useTranslationStore((state) => state.config)
  const latexValidation = useTranslationStore((state) => state.latexValidation)
  const hasSystemApiKey = useTranslationStore((state) => state.hasSystemApiKey)
  const userSettingsLoaded = useTranslationStore((state) => state.userSettingsLoaded)
  const setConfig = useTranslationStore((state) => state.setConfig)
  const setAdvancedConfig = useTranslationStore((state) => state.setAdvancedConfig)
  const resetConfig = useTranslationStore((state) => state.resetConfig)
  const setLatexValidation = useTranslationStore((state) => state.setLatexValidation)
  const loadUserSettings = useTranslationStore((state) => state.loadUserSettings)
  const invalidateUserSettings = useTranslationStore((state) => state.invalidateUserSettings)

  return {
    config,
    latexValidation,
    hasSystemApiKey,
    userSettingsLoaded,
    setConfig,
    setAdvancedConfig,
    resetConfig,
    setLatexValidation,
    loadUserSettings,
    invalidateUserSettings,
  }
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\hooks\useTranslationTask.ts
Relative path: features\translation-workflow\hooks\useTranslationTask.ts

```ts
import { useTranslationStore } from "@/features/translation-workflow/store/useTranslationStore"

export function useTranslationTask() {
  const taskId = useTranslationStore((state) => state.taskId)
  const arxivId = useTranslationStore((state) => state.arxivId)
  const status = useTranslationStore((state) => state.status)
  const stage = useTranslationStore((state) => state.stage)
  const progress = useTranslationStore((state) => state.progress)
  const message = useTranslationStore((state) => state.message)
  const detailCode = useTranslationStore((state) => state.detailCode)
  const detailParams = useTranslationStore((state) => state.detailParams)
  const failureReasonCode = useTranslationStore((state) => state.failureReasonCode)
  const logs = useTranslationStore((state) => state.logs)
  const error = useTranslationStore((state) => state.error)
  const isPolling = useTranslationStore((state) => state.isPolling)
  const taskWarnings = useTranslationStore((state) => state.taskWarnings)
  const outputMetrics = useTranslationStore((state) => state.outputMetrics)
  const downloadProgress = useTranslationStore((state) => state.downloadProgress)
  const downloadStage = useTranslationStore((state) => state.downloadStage)
  const isDownloading = useTranslationStore((state) => state.isDownloading)
  const setTaskId = useTranslationStore((state) => state.setTaskId)
  const setArxivId = useTranslationStore((state) => state.setArxivId)
  const reset = useTranslationStore((state) => state.reset)
  const resetTranslationState = useTranslationStore((state) => state.resetTranslationState)
  const startArxivDownload = useTranslationStore((state) => state.startArxivDownload)
  const pollDownloadProgress = useTranslationStore((state) => state.pollDownloadProgress)
  const startTranslation = useTranslationStore((state) => state.startTranslation)
  const pollStatus = useTranslationStore((state) => state.pollStatus)
  const stopPolling = useTranslationStore((state) => state.stopPolling)

  return {
    taskId,
    arxivId,
    status,
    stage,
    progress,
    message,
    detailCode,
    detailParams,
    failureReasonCode,
    logs,
    error,
    isPolling,
    taskWarnings,
    outputMetrics,
    downloadProgress,
    downloadStage,
    isDownloading,
    setTaskId,
    setArxivId,
    reset,
    resetTranslationState,
    startArxivDownload,
    pollDownloadProgress,
    startTranslation,
    pollStatus,
    stopPolling,
  }
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\store\useTranslationStore.ts
Relative path: features\translation-workflow\store\useTranslationStore.ts

```ts
import { create } from "zustand"
import { toast } from "sonner"

import { API_BASE_URL } from "@/api-base"
import i18n from "@/i18n"
import { downloadArxiv, getTaskStatus, startTranslation } from "@/lib/api"
import { getAccessToken, isLocalAuthConfigured } from "@/lib/local-auth"
import { DEFAULT_CONFIG } from "@/types/config"
import type { AdvancedConfig, LatexValidation, TranslationConfig } from "@/types/config"
import type { TranslateRequest } from "@/lib/api"

type TaskDetailParams = Record<string, string | number | boolean | null> | null

interface TranslationWorkflowState {
  taskId: string | null
  arxivId: string | null
  status: string
  stage: string
  progress: number
  message: string
  detailCode: string | null
  detailParams: TaskDetailParams
  failureReasonCode: string | null
  logs: string[]
  error: string | null
  isPolling: boolean
  taskWarnings: string | null
  outputMetrics: {
    pdfPath?: string
    translationQuality?: number
  }
  downloadProgress: number
  downloadStage: string
  isDownloading: boolean
  config: TranslationConfig
  latexValidation: LatexValidation | null
  userSettingsLoaded: boolean
  hasSystemApiKey: boolean
  setTaskId: (id: string) => void
  setArxivId: (id: string | null) => void
  reset: () => void
  resetTranslationState: () => void
  setConfig: (config: Partial<TranslationConfig>) => void
  setAdvancedConfig: (config: Partial<AdvancedConfig>) => void
  resetConfig: () => void
  setLatexValidation: (validation: LatexValidation | null) => void
  loadUserSettings: (forceReload?: boolean) => Promise<void>
  invalidateUserSettings: () => void
  startArxivDownload: (arxivId: string) => Promise<void>
  pollDownloadProgress: () => void
  startTranslation: (config: TranslateRequest) => Promise<void>
  pollStatus: () => void
  stopPolling: () => void
}

let pollingInterval: ReturnType<typeof setInterval> | null = null
let downloadPollingInterval: ReturnType<typeof setInterval> | null = null

export const useTranslationStore = create<TranslationWorkflowState>((set, get) => ({
  taskId: null,
  arxivId: null,
  status: "idle",
  stage: "idle",
  progress: 0,
  message: "",
  detailCode: null,
  detailParams: null,
  failureReasonCode: null,
  logs: [],
  error: null,
  isPolling: false,
  taskWarnings: null,
  outputMetrics: {},
  downloadProgress: 0,
  downloadStage: "",
  isDownloading: false,
  config: { ...DEFAULT_CONFIG },
  latexValidation: null,
  userSettingsLoaded: false,
  hasSystemApiKey: false,

  setTaskId: (id) => set({ taskId: id }),
  setArxivId: (id) => set({ arxivId: id }),

  reset: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    if (downloadPollingInterval) clearInterval(downloadPollingInterval)
    pollingInterval = null
    downloadPollingInterval = null
    set({
      taskId: null,
      arxivId: null,
      status: "idle",
      stage: "idle",
      progress: 0,
      message: "",
      detailCode: null,
      detailParams: null,
      failureReasonCode: null,
      logs: [],
      error: null,
      isPolling: false,
      outputMetrics: {},
      config: { ...DEFAULT_CONFIG },
      latexValidation: null,
      isDownloading: false,
      downloadProgress: 0,
      downloadStage: "",
      userSettingsLoaded: false,
      hasSystemApiKey: false,
    })
  },

  resetTranslationState: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    if (downloadPollingInterval) clearInterval(downloadPollingInterval)
    pollingInterval = null
    downloadPollingInterval = null
    set({
      taskId: null,
      arxivId: null,
      status: "idle",
      stage: "idle",
      progress: 0,
      message: "",
      detailCode: null,
      detailParams: null,
      failureReasonCode: null,
      logs: [],
      error: null,
      isPolling: false,
      taskWarnings: null,
      outputMetrics: {},
      latexValidation: null,
      isDownloading: false,
      downloadProgress: 0,
      downloadStage: "",
    })
  },

  setConfig: (newConfig) =>
    set((state) => ({
      config: {
        ...state.config,
        ...newConfig,
        advanced_config: newConfig.advanced_config
          ? { ...state.config.advanced_config, ...newConfig.advanced_config }
          : state.config.advanced_config,
      },
    })),

  setAdvancedConfig: (advancedConfig) =>
    set((state) => ({
      config: {
        ...state.config,
        advanced_config: {
          ...state.config.advanced_config,
          ...advancedConfig,
        },
      },
    })),

  resetConfig: () =>
    set({
      config: { ...DEFAULT_CONFIG },
    }),

  setLatexValidation: (validation) => set({ latexValidation: validation }),

  loadUserSettings: async (forceReload = false) => {
    if (get().userSettingsLoaded && !forceReload) return

    try {
      if (!isLocalAuthConfigured()) {
        set({ userSettingsLoaded: true })
        return
      }

      const token = await getAccessToken()
      if (!token) {
        set({ userSettingsLoaded: true })
        return
      }

      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })

      if (!response.ok) {
        console.warn("[Settings] Failed to load user settings:", response.status)
        set({ userSettingsLoaded: true })
        return
      }

      const settings = await response.json()

      const hasSystemApiKey = settings.has_custom_api_key || false
      const newConfig: Partial<TranslationConfig> = {
        source_language: settings.default_source_language || "en",
        target_language: settings.default_target_language || "zh",
        advanced_config: {
          translation_mode: settings.translation_mode || "full",
          compile_strategy: settings.compile_strategy || "auto",
          generate_terminology_table: settings.generate_glossary ?? true,
          translation_model: settings.translation_model || "deepseek-ai/deepseek-v3.2",
          use_author_api: settings.use_author_api ?? true,
          custom_base_url: settings.custom_base_url || undefined,
          formatting: settings.default_formatting || undefined,
        },
      }

      set((state) => ({
        config: {
          ...state.config,
          ...newConfig,
          advanced_config: {
            ...state.config.advanced_config,
            ...newConfig.advanced_config,
          },
        },
        userSettingsLoaded: true,
        hasSystemApiKey,
      }))
    } catch (error) {
      console.error("[Settings] Error loading user settings:", error)
      set({ userSettingsLoaded: true })
    }
  },

  invalidateUserSettings: () => {
    set({ userSettingsLoaded: false })
  },

  startArxivDownload: async (arxivId) => {
    get().resetTranslationState()

    set({ userSettingsLoaded: false })
    await get().loadUserSettings()

    try {
      set({
        status: "downloading",
        stage: "downloading",
        message: i18n.t("task.detail.downloadSourceStarting"),
        detailCode: "download_source_starting",
        detailParams: null,
        error: null,
        logs: [i18n.t("task.detail.downloadSourceStarting")],
        arxivId,
        isDownloading: true,
        downloadProgress: 0,
        downloadStage: "downloading",
      })

      const response = await downloadArxiv(arxivId)

      set({
        taskId: response.task_id,
        logs: [...get().logs, response.message].filter(
          (value, index, values) => values.indexOf(value) === index,
        ),
      })

      get().pollDownloadProgress()
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : i18n.t("dashboard.arxivDownloadFailed")
      set({
        error: message,
        status: "failed",
        stage: "downloading",
        isDownloading: false,
        downloadProgress: 0,
      })
      toast.error(i18n.t("dashboard.arxivDownloadFailed"))
      throw error
    }
  },

  pollDownloadProgress: () => {
    const { taskId } = get()
    if (!taskId) return

    let eventSource: EventSource | null = null
    let sseRetryCount = 0
    const maxSseRetries = 3

    const markDownloadFailed = (message?: string) => {
      const errorMessage = message || i18n.t("dashboard.arxivDownloadFailed")
      set({
        status: "failed",
        stage: get().downloadStage || "downloading",
        isDownloading: false,
        error: errorMessage,
        message: errorMessage,
      })
      toast.error(i18n.t("dashboard.arxivDownloadFailed"))
    }

    const startPollingFallback = () => {
      if (downloadPollingInterval) return

      downloadPollingInterval = setInterval(async () => {
        const currentTaskId = get().taskId
        if (!currentTaskId) {
          if (downloadPollingInterval) clearInterval(downloadPollingInterval)
          downloadPollingInterval = null
          return
        }

        try {
          const statusData = await getTaskStatus(currentTaskId)

          set({
            downloadProgress: statusData.progress,
            downloadStage: statusData.stage || "downloading",
            stage: statusData.stage || get().stage,
            detailCode: statusData.detail_code ?? null,
            detailParams: statusData.detail_params ?? null,
            message: statusData.message,
          })

          if (statusData.status.toLowerCase() === "pending" && statusData.progress === 100) {
            if (downloadPollingInterval) {
              clearInterval(downloadPollingInterval)
              downloadPollingInterval = null
            }

            if (get().status !== "ready") {
              set({
                status: "ready",
                stage: statusData.stage || "done",
                isDownloading: false,
                downloadProgress: 100,
                detailCode: "download_source_complete",
                detailParams: null,
                message: statusData.message,
                logs: [...get().logs, statusData.message].filter(
                  (value, index, values) => values.indexOf(value) === index,
                ),
              })
              toast.success(i18n.t("dashboard.sourceDocumentReady"))
            }
            return
          }

          if (statusData.status.toLowerCase() === "failed") {
            if (downloadPollingInterval) clearInterval(downloadPollingInterval)
            downloadPollingInterval = null
            markDownloadFailed(statusData.error || statusData.message)
          }
        } catch (error) {
          console.error("Download polling error", error)
        }
      }, 2000)
    }

    const connectSSE = () => {
      if (downloadPollingInterval) return

      try {
        eventSource = new EventSource(`${API_BASE_URL}/api/task/${taskId}/stream`)

        eventSource.onopen = () => {
          sseRetryCount = 0
        }

        eventSource.addEventListener("update", (event) => {
          try {
            const data = JSON.parse(event.data)
            const currentStatus = String(data.status || "").toLowerCase()

            set({
              downloadProgress: data.progress,
              downloadStage: data.stage || "downloading",
              stage: data.stage || get().stage,
              detailCode: data.detail_code ?? null,
              detailParams: data.detail_params ?? null,
              message: data.message,
            })

            if (data.status?.toLowerCase() === "pending" && data.progress === 100) {
              if (get().status !== "ready") {
                set({
                  status: "ready",
                  stage: data.stage || "done",
                  isDownloading: false,
                  downloadProgress: 100,
                  detailCode: "download_source_complete",
                  detailParams: null,
                  message: data.message,
                  logs: [...get().logs, data.message].filter(
                    (value, index, values) => values.indexOf(value) === index,
                  ),
                })
                toast.success(i18n.t("dashboard.sourceDocumentReady"))
              }
              eventSource?.close()
              eventSource = null
            } else if (currentStatus === "failed") {
              markDownloadFailed(data.error || data.message)
              eventSource?.close()
              eventSource = null
            }
          } catch (error) {
            console.error("[Download SSE] Parse error:", error)
          }
        })

        eventSource.addEventListener("complete", (event) => {
          try {
            const data = JSON.parse(event.data)
            const currentStatus = String(data.status || "").toLowerCase()

            if (
              currentStatus === "failed" ||
              currentStatus === "failed_compilation" ||
              currentStatus === "structure_invalid"
            ) {
              markDownloadFailed(data.error || data.message)
            } else if (get().status !== "ready") {
              set({
                status: "ready",
                stage: data.stage || "done",
                isDownloading: false,
                downloadProgress: 100,
                detailCode: "download_source_complete",
                detailParams: null,
                message: data.message,
                logs: [...get().logs, data.message].filter(
                  (value, index, values) => values.indexOf(value) === index,
                ),
              })
              toast.success(i18n.t("dashboard.sourceDocumentReady"))
            }
            eventSource?.close()
            eventSource = null
          } catch (error) {
            console.error("[Download SSE] Parse error:", error)
          }
        })

        eventSource.addEventListener("error", (event) => {
          try {
            const data = JSON.parse((event as MessageEvent).data)
            markDownloadFailed(data.error || data.message)
            eventSource?.close()
            eventSource = null
          } catch {
            // Connection errors fall through to the shared handler below.
          }
        })

        eventSource.onerror = () => {
          eventSource?.close()
          eventSource = null

          if (sseRetryCount < maxSseRetries) {
            sseRetryCount += 1
            setTimeout(connectSSE, 1000 * sseRetryCount)
          } else {
            startPollingFallback()
          }
        }
      } catch (error) {
        console.error("[Download SSE] Setup error:", error)
        startPollingFallback()
      }
    }

    connectSSE()
  },

  startTranslation: async (config) => {
    const { taskId } = get()
    if (!taskId) {
      toast.error(i18n.t("task.error.missingTaskId"))
      throw new Error(i18n.t("task.error.missingTaskId"))
    }

    try {
      set({
        status: "processing",
        stage: "parsing",
        message: i18n.t("task.detail.translationStarting"),
        detailCode: "translation_starting",
        detailParams: null,
        failureReasonCode: null,
        error: null,
      })
      const response = await startTranslation(taskId, config)
      set({
        message: response.message,
        logs: [...get().logs, response.message].filter(
          (value, index, values) => values.indexOf(value) === index,
        ),
      })
      toast.success(i18n.t("task.toast.translationStarted"))
      get().pollStatus()
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : i18n.t("task.error.startFailed")
      set({ error: message, status: "failed" })
      toast.error(i18n.t("task.error.startFailed"))
      throw error
    }
  },

  pollStatus: () => {
    if (get().isPolling) return
    set({ isPolling: true })

    pollingInterval = setInterval(async () => {
      const { taskId, isPolling, stopPolling } = get()
      if (!taskId || !isPolling) {
        stopPolling()
        return
      }

      try {
        const statusData = await getTaskStatus(taskId)

        set((state) => ({
          status: statusData.status,
          stage: statusData.stage || state.stage,
          progress: statusData.progress,
          message: statusData.message,
          detailCode: statusData.detail_code ?? state.detailCode,
          detailParams: statusData.detail_params ?? state.detailParams,
          failureReasonCode: statusData.failure_reason_code ?? state.failureReasonCode,
          error: statusData.error || null,
          taskWarnings: statusData.warnings ?? state.taskWarnings,
          logs: statusData.logs
            ? statusData.logs
            : [...state.logs, statusData.message].filter((value, index, values) => values.indexOf(value) === index),
        }))

        if (
          ["completed", "failed", "completed_with_warnings", "failed_compilation"].includes(
            statusData.status.toLowerCase(),
          )
        ) {
          const wasPolling = get().isPolling
          stopPolling()
          if (wasPolling) {
            if (statusData.status.toLowerCase() === "completed") {
              toast.success(i18n.t("task.toast.completed"), { id: `task-completed-${taskId}` })
            } else if (statusData.status.toLowerCase() === "failed") {
              toast.error(i18n.t("task.toast.failed"), { id: `task-failed-${taskId}` })
            } else if (statusData.status.toLowerCase() === "failed_compilation") {
              toast.error(i18n.t("task.toast.failedCompilation"), {
                id: `task-failed-compilation-${taskId}`,
              })
            }
          }
        }
      } catch (error) {
        console.error("Polling error", error)
      }
    }, 2000)
  },

  stopPolling: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    pollingInterval = null
    set({ isPolling: false })
  },
}))

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\user-workspace\components\GlossaryWorkspace.tsx
Relative path: features\user-workspace\components\GlossaryWorkspace.tsx

```tsx
import { BookOpenText } from "lucide-react"
import { useTranslation } from "react-i18next"

import { PageIntro } from "@/ui/page-intro/PageIntro"
import { StatePanel } from "@/ui/state-panel/StatePanel"

export function GlossaryWorkspace() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-5xl space-y-6 py-2">
      <PageIntro
        title={t("glossary.glossary_management")}
        description={t("glossary.managementComingSoon")}
      />

      <StatePanel
        className="py-14"
        icon={<BookOpenText className="h-7 w-7" />}
        title={t("glossary.glossary_management")}
        description={t("glossary.managementComingSoon")}
      />
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\user-workspace\components\HistoryWorkspace.tsx
Relative path: features\user-workspace\components\HistoryWorkspace.tsx

```tsx
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/ui/button/Button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/ui/primitives/collapsible'
import { Loader2, FileText, RefreshCw, Settings2, Languages, Wrench, Sparkles, CheckCircle2, XCircle, Trash2, Eye, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/primitives/alert-dialog'
import { Checkbox } from '@/ui/primitives/checkbox'
import { deleteTask, deleteTasksBatch } from '@/lib/api'
import { API_BASE_URL } from '@/api-base'
import { useTranslation } from 'react-i18next'
import { useTranslationTask } from '@/features/translation-workflow/hooks/useTranslationTask'
import { getCompileStrategyLabel, getFormattingValueLabel, getTaskStatusLabel, getTranslationModeLabel } from '@/i18n/ui-text'
import { getAccessToken } from '@/lib/local-auth'
import { LoginPrompt } from '@/features/auth-shell/components/LoginPrompt'
import { PageIntro } from '@/ui/page-intro/PageIntro'
import { StatePanel } from '@/ui/state-panel/StatePanel'
import { NoticeBanner } from '@/ui/notice-banner/NoticeBanner'
import { InfoTile } from '@/ui/info-tile/InfoTile'
import { PanelShell } from '@/ui/panel-shell/PanelShell'
import { StatusBadge } from '@/ui/status-badge/StatusBadge'
import { LoadingState } from '@/ui/loading-state/LoadingState'
import { Pill } from '@/ui/pill/Pill'
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from '@/ui/data-table/DataTable'

interface TaskHistoryItem {
  task_id: string
  source_type: string
  arxiv_id?: string
  translation_mode: string
  status: string
  progress: number
  created_at: string
  completed_at?: string
  source_language: string
  target_language: string
  compile_strategy: string
  translation_model?: string
  generate_glossary: boolean
  use_author_api: boolean
  formatting?: Record<string, unknown> | null
}

interface HistoryResponse {
  tasks: TaskHistoryItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

const statusTones: Record<string, "warning" | "info" | "success" | "danger"> = {
  pending: 'warning',
  processing: 'info',
  completed: 'success',
  completed_with_warnings: 'success',
  failed: 'danger',
  failed_compilation: 'danger',
  structure_invalid: 'danger',
}

const TERMINAL_FAIL_STATUSES = new Set(['failed', 'failed_compilation', 'structure_invalid'])

export function HistoryWorkspace() {
  const navigate = useNavigate()
  const { isAuthenticated, loading: authLoading, session } = useAuth()
  const { setTaskId, setArxivId } = useTranslationTask()
  const { t, i18n } = useTranslation()

  const [tasks, setTasks] = useState<TaskHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null)

  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())
  const retryTimeoutRef = useRef<number | null>(null)

  const HISTORY_RETRY_DELAY_MS = 1000
  const MAX_HISTORY_RETRIES = 2

  const clearScheduledRetry = useCallback(() => {
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [])

  const toggleExpand = (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const fetchHistory = useCallback(async (pageNum: number, append = false, attempt = 0) => {
    clearScheduledRetry()
    setLoading(true)
    if (attempt === 0) {
      setError(null)
    }

    try {
      const token = session?.access_token ?? await getAccessToken()
      if (!token) {
        if (attempt < MAX_HISTORY_RETRIES) {
          retryTimeoutRef.current = window.setTimeout(() => {
            void fetchHistory(pageNum, append, attempt + 1)
          }, HISTORY_RETRY_DELAY_MS)
          return
        }
        throw new Error(t('history.failed_to_load_history'))
      }

      const response = await fetch(`${API_BASE_URL}/api/history?page=${pageNum}&page_size=10`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        if ((response.status >= 500 || response.status === 401) && attempt < MAX_HISTORY_RETRIES) {
          retryTimeoutRef.current = window.setTimeout(() => {
            void fetchHistory(pageNum, append, attempt + 1)
          }, HISTORY_RETRY_DELAY_MS)
          return
        }
        throw new Error(t('history.failed_to_load_history'))
      }

      const data: HistoryResponse = await response.json()

      if (append) {
        setTasks((prev) => [...prev, ...data.tasks])
      } else {
        setTasks(data.tasks)
      }
      setHasMore(data.has_more)
      setTotal(data.total)
      setPage(pageNum)
    } catch (err) {
      if (attempt < MAX_HISTORY_RETRIES) {
        retryTimeoutRef.current = window.setTimeout(() => {
          void fetchHistory(pageNum, append, attempt + 1)
        }, HISTORY_RETRY_DELAY_MS)
        return
      }
      setError(err instanceof Error ? err.message : t('history.failed_to_load_history'))
    } finally {
      if (retryTimeoutRef.current === null) {
        setLoading(false)
      }
    }
  }, [clearScheduledRetry, session?.access_token, t])

  const loadMore = () => {
    if (!loading && hasMore) {
      void fetchHistory(page + 1, true)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      void fetchHistory(1)
    }
    return clearScheduledRetry
  }, [clearScheduledRetry, fetchHistory, isAuthenticated])

  const handleDeleteClick = (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setTaskToDelete(taskId)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = async () => {
    if (!taskToDelete) return

    const deletingId = taskToDelete
    setDeleteDialogOpen(false)
    setTaskToDelete(null)

    const toastId = toast.loading(t('history.deleting_task'))

    try {
      await deleteTask(deletingId)
      setTasks((prev) => prev.filter((task) => task.task_id !== deletingId))
      setTotal((prev) => prev - 1)
      setSelectedTasks((prev) => {
        const next = new Set(prev)
        next.delete(deletingId)
        return next
      })
      toast.success(t('history.task_deleted'), { id: toastId })
    } catch {
      toast.error(t('history.delete_failed_please_try_again'), { id: toastId })
    }
  }

  const handleBatchDelete = async () => {
    if (selectedTasks.size === 0) return

    const deletingIds = Array.from(selectedTasks)
    const count = deletingIds.length

    setSelectedTasks(new Set())
    setSelectionMode(false)

    const toastId = toast.loading(t('history.deleting_tasks', { count }))

    try {
      const result = await deleteTasksBatch(deletingIds)
      const successCount = result.results.filter((item) => item.success).length
      const successIds = new Set(result.results.filter((item) => item.success).map((item) => item.task_id))

      if (successCount > 0) {
        setTasks((prev) => prev.filter((task) => !successIds.has(task.task_id)))
        setTotal((prev) => prev - successCount)
      }

      if (successCount === count) {
        toast.success(t('history.successfully_deleted_tasks', { count: successCount }), { id: toastId })
      } else if (successCount > 0) {
        toast.warning(t('history.deleted_tasks_some_failed_please_try_again', { successCount, count }), { id: toastId })
      } else {
        toast.error(t('history.delete_failed_0_please_try_again', { count }), { id: toastId })
      }
    } catch {
      toast.error(t('history.batch_delete_failed_please_try_again'), { id: toastId })
    }
  }

  const toggleSelection = (taskId: string) => {
    setSelectedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const selectAll = () => {
    if (selectedTasks.size === tasks.length) {
      setSelectedTasks(new Set())
    } else {
      setSelectedTasks(new Set(tasks.map((task) => task.task_id)))
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const locale = i18n.resolvedLanguage === 'zh' ? 'zh-CN' : i18n.resolvedLanguage
    return date.toLocaleString(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleTaskClick = (task: TaskHistoryItem) => {
    setTaskId(task.task_id)
    if (task.arxiv_id) {
      setArxivId(task.arxiv_id)
    }

    if (task.status === 'completed' || task.status === 'completed_with_warnings') {
      navigate('/preview')
    } else if (TERMINAL_FAIL_STATUSES.has(task.status)) {
      navigate(`/processing?taskId=${task.task_id}`)
    } else {
      navigate(`/processing?taskId=${task.task_id}`)
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center">
        <LoadingState label={t('common.status.loading')} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 py-12 animate-in fade-in duration-500">
        <LoginPrompt
          messageKey="history.sign_in_to_view_translation_history"
          descriptionKey="history.sign_in_to_view_and_manage_all_translation_task_records"
          actionLabelKey="common.go_to_sign_in"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <PageIntro
        title={t('history.history')}
        description={t('history.total_translation_tasks', { count: total })}
        actions={selectionMode ? (
          <>
            <Button variant="outline" size="sm" onClick={selectAll} className="rounded-full shadow-sm">
              {selectedTasks.size === tasks.length ? t('history.clear_selection') : t('history.select_all')}
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              disabled={selectedTasks.size === 0}
              className="min-w-[90px] rounded-full shadow-sm"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('history.delete_selected', { count: selectedTasks.size })}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectionMode(false)
                setSelectedTasks(new Set())
              }}
              className="rounded-full"
            >
              {t('common.actions.cancel')}
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectionMode(true)}
              disabled={tasks.length === 0}
              className="rounded-full shadow-sm"
            >
              {t('history.select')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void fetchHistory(1)}
              disabled={loading}
              className="rounded-full shadow-sm"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {t('history.refresh')}
            </Button>
          </>
        )}
      />

      {error ? (
        <NoticeBanner
          tone="danger"
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t('history.failed_to_load_history')}
          description={error}
        />
      ) : null}

      <DataTable className="shadow-sm">
        <DataTableHeader className="hidden md:block">
          <DataTableHeaderRow className="grid-cols-12">
            <DataTableHeaderCell className="col-span-1" />
            <DataTableHeaderCell className="col-span-4">{t('history.table.document')}</DataTableHeaderCell>
            <DataTableHeaderCell className="col-span-3">{t('history.table.timestampMode')}</DataTableHeaderCell>
            <DataTableHeaderCell className="col-span-2">{t('task.status')}</DataTableHeaderCell>
            <DataTableHeaderCell className="col-span-2 text-right">{t('history.table.actions')}</DataTableHeaderCell>
          </DataTableHeaderRow>
        </DataTableHeader>

        <DataTableBody>
          {loading && tasks.length === 0 ? (
            <LoadingState className="m-6 py-10" layout="panel" label={t('common.status.loading')} />
          ) : null}
          {tasks.length === 0 && !loading ? (
            <StatePanel
              className="m-6 py-10 shadow-none"
              icon={<FileText className="h-7 w-7" />}
              title={t('history.no_translation_history_yet')}
              description={t('history.sign_in_to_view_and_manage_all_translation_task_records')}
            />
          ) : (
            tasks.map((task) => (
              <Collapsible
                key={task.task_id}
                open={expandedTasks.has(task.task_id)}
                onOpenChange={() => {}}
                  className="group transition-colors hover:bg-[color:var(--px-shell-panel-strong)]/70"
              >
                <DataTableRow className="flex flex-col items-start gap-4 p-4 md:grid md:grid-cols-12 md:items-center sm:px-6 sm:py-5">
                    <DataTableCell className="pt-1 md:col-span-1 md:pt-0">
                      {selectionMode ? (
                        <Checkbox
                          checked={selectedTasks.has(task.task_id)}
                          onCheckedChange={() => toggleSelection(task.task_id)}
                          aria-label={t('history.select_task', { task: task.arxiv_id || task.task_id.slice(0, 8) })}
                        />
                      ) : (
                        <FileText className="h-5 w-5 text-[color:var(--px-shell-accent)] opacity-80" />
                      )}
                    </DataTableCell>

                    <DataTableCell
                      className="md:col-span-4 flex min-w-0 self-stretch items-center cursor-pointer"
                      onClick={() => !selectionMode && handleTaskClick(task)}
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-bold text-[color:var(--px-shell-ink)]">
                          {task.arxiv_id || task.task_id.slice(0, 8)}
                        </div>
                        <div className="truncate text-[10px] text-[color:var(--px-shell-muted)]">
                          {task.source_type === 'upload' ? t('history.source.localProject') : t('history.source.arxiv')}
                        </div>
                      </div>
                    </DataTableCell>

                    <DataTableCell className="md:col-span-3 flex flex-col text-sm text-[color:var(--px-shell-muted)] md:block">
                      <span className="md:block">{formatDate(task.created_at)}</span>
                      <span className="text-[11px] text-[color:var(--px-shell-muted)] md:mt-0.5">
                        {getTranslationModeLabel(t, task.translation_mode)}
                      </span>
                    </DataTableCell>

                    <DataTableCell className="md:col-span-2">
                      <StatusBadge tone={statusTones[task.status] || 'danger'}>
                        {getTaskStatusLabel(t, task.status)}
                      </StatusBadge>
                    </DataTableCell>

                    <DataTableCell className="md:col-span-2 flex w-full items-center justify-end gap-1 md:w-auto">
                      {!selectionMode ? (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 rounded-lg p-0 text-[color:var(--px-shell-muted)] transition-all hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-accent)]"
                            onClick={(event) => {
                              event.stopPropagation()
                              handleTaskClick(task)
                            }}
                            title={t('common.actions.view')}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 rounded-lg p-0 text-[color:var(--px-shell-muted)] transition-all hover:bg-[color:var(--px-shell-danger-soft)] hover:text-[color:var(--px-shell-danger)]"
                            onClick={(event) => handleDeleteClick(task.task_id, event)}
                            title={t('history.delete_task')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                          <CollapsibleTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 rounded-lg p-0 text-[color:var(--px-shell-muted)] transition-all hover:bg-[color:var(--px-shell-panel-strong)]"
                              onClick={(event) => toggleExpand(task.task_id, event)}
                              title={t('history.expand_configuration_details')}
                            >
                              <Settings2 className="h-4 w-4" />
                            </Button>
                          </CollapsibleTrigger>
                        </>
                      ) : null}
                    </DataTableCell>
                </DataTableRow>

                  <CollapsibleContent className="mt-4 animate-in fade-in slide-in-from-top-2 duration-200 md:mt-2">
                    <div className="space-y-3 border-t border-[color:var(--px-shell-line)] pt-4 md:ml-12 lg:ml-[11.1%]">
                      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">
                        <Settings2 className="h-3 w-3" />
                        {t('history.translation_configuration')}
                      </div>

                      <div className="grid grid-cols-1 gap-3 pb-2 text-sm md:grid-cols-2">
                        <InfoTile
                          icon={<Languages className="h-4 w-4" />}
                          title={t('history.language')}
                          value={`${task.source_language} → ${task.target_language}`}
                        />

                        <InfoTile
                          icon={<Wrench className="h-4 w-4" />}
                          title={t('history.compile_strategy')}
                          value={getCompileStrategyLabel(t, task.compile_strategy)}
                          valueClassName="capitalize"
                        />

                        {task.translation_model ? (
                          <InfoTile
                            className="md:col-span-2"
                            icon={<Sparkles className="h-4 w-4" />}
                            title={t('history.translation_model')}
                            value={task.translation_model}
                            valueClassName="font-mono text-xs"
                          />
                        ) : null}

                        <div className="md:col-span-2 mt-1 flex flex-wrap gap-2">
                          <Pill className="px-3 py-1.5 text-[11px] font-bold normal-case tracking-normal">
                            {task.generate_glossary ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />
                            ) : (
                              <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-muted)]" />
                            )}
                            <span className="text-[11px] font-bold text-[color:var(--px-shell-ink)]">{t('common.generate_glossary')}</span>
                          </Pill>

                          <Pill className="px-3 py-1.5 text-[11px] font-bold normal-case tracking-normal">
                            {task.use_author_api ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />
                            ) : (
                              <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-muted)]" />
                            )}
                            <span className="text-[11px] font-bold text-[color:var(--px-shell-ink)]">{t('history.use_author_api')}</span>
                          </Pill>
                        </div>

                        {task.formatting && Object.keys(task.formatting).length > 0 ? (
                          <PanelShell className="md:col-span-2 mt-3">
                            <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">
                              {t('history.formatting_settings')}
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {task.formatting.line_spacing != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.line_spacing', { value: String(task.formatting.line_spacing) })}
                                </Pill>
                              ) : null}
                              {task.formatting.font_size != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.font_size_pt', { value: String(task.formatting.font_size) })}
                                </Pill>
                              ) : null}
                              {task.formatting.column_mode != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {getFormattingValueLabel(t, 'column_mode', String(task.formatting.column_mode))}
                                </Pill>
                              ) : null}
                              {task.formatting.margin != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.margins', { value: getFormattingValueLabel(t, 'margin', String(task.formatting.margin)) })}
                                </Pill>
                              ) : null}
                              {task.formatting.cjk_font != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.font', { value: getFormattingValueLabel(t, 'cjk_font', String(task.formatting.cjk_font)) })}
                                </Pill>
                              ) : null}
                              {task.formatting.paragraph_indent === true ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('formatting.firstLineIndent')}
                                </Pill>
                              ) : null}
                              {task.formatting.localize_captions === true ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.localize_figures_tables')}
                                </Pill>
                              ) : null}
                              {task.formatting.bib_style != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.bibliography', { value: String(task.formatting.bib_style) })}
                                </Pill>
                              ) : null}
                              {task.formatting.cite_style != null ? (
                                <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                  {t('history.citation', { value: getFormattingValueLabel(t, 'cite_style', String(task.formatting.cite_style)) })}
                                </Pill>
                              ) : null}
                            </div>
                          </PanelShell>
                        ) : null}
                      </div>
                    </div>
                  </CollapsibleContent>
              </Collapsible>
            ))
          )}
        </DataTableBody>
      </DataTable>

      {hasMore ? (
        <div className="flex justify-center pt-2">
          <Button variant="outline" onClick={loadMore} disabled={loading} className="rounded-full shadow-sm">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('common.status.loading')}
              </>
            ) : (
              t('common.actions.loadMore')
            )}
          </Button>
        </div>
      ) : null}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('history.dialog.confirmDeleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              {t('history.this_action_deletes_all_data_for_this_task_source_files_translated_results_glossary_and_cannot_be_undone_continue')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2 sm:gap-0">
            <AlertDialogCancel>{t('common.actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} variant="destructive">
              {t('common.actions.confirmDelete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\user-workspace\components\ProfileWorkspace.tsx
Relative path: features\user-workspace\components\ProfileWorkspace.tsx

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Loader2, LogOut, Mail, Settings, User } from "lucide-react"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"
import { Button } from "@/ui/button/Button"
import { Card, CardContent } from "@/ui/card/Card"
import { LoadingState } from "@/ui/loading-state/LoadingState"
import { PageIntro } from "@/ui/page-intro/PageIntro"
import { SectionCard } from "@/ui/section-card/SectionCard"

export function ProfileWorkspace() {
  const navigate = useNavigate()
  const { user, isAuthenticated, loading, signOut } = useAuth()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const { t } = useTranslation()
  const profileValue = user?.email || user?.display_name || user?.external_user_id || ""

  const handleLogout = async () => {
    setIsLoggingOut(true)
    await signOut()
    toast.success(t("profile.signed_out"))
    navigate("/")
  }

  if (loading) {
    return (
      <div className="container mx-auto flex min-h-[60vh] max-w-md flex-col justify-center p-6">
        <LoadingState label={t("common.status.loading")} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto max-w-md space-y-6 p-6 animate-in fade-in duration-500">
        <LoginPrompt
          messageKey="profile.not_signed_in"
          descriptionKey="profile.sign_in_to_manage_your_account"
          actionLabelKey="common.go_to_sign_in"
        />
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-3xl space-y-6 p-6 animate-in fade-in duration-500">
      <PageIntro
        icon={<User className="h-6 w-6" />}
        title={t("profile.profile")}
        description={t("profile.manage_your_account_information")}
      />

      <SectionCard
        icon={<Mail className="h-5 w-5" />}
        title={t("common.labels.user")}
        description={t("auth.labels.emailAddress")}
      >
        <Card variant="strong" className="rounded-2xl shadow-none">
          <CardContent className="px-4 py-4">
            <p className="truncate text-base font-semibold text-[color:var(--px-shell-ink)]">{profileValue}</p>
          </CardContent>
        </Card>
      </SectionCard>

      <SectionCard
        icon={<Settings className="h-5 w-5" />}
        title={t("profile.account_actions")}
        description={t("profile.manage_your_account_information")}
        contentClassName="space-y-3"
      >
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => navigate("/workspace/settings")}
        >
          <Settings className="mr-2 h-4 w-4" />
          {t("settings.title")}
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
              {t("profile.signing_out")}
            </>
          ) : (
            <>
              <LogOut className="mr-2 h-4 w-4" />
              {t("profile.sign_out")}
            </>
          )}
        </Button>
      </SectionCard>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\user-workspace\components\TranslationSettingsWorkspace.tsx
Relative path: features\user-workspace\components\TranslationSettingsWorkspace.tsx

```tsx
import { useState, useEffect, useCallback } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/ui/button/Button'
import { Input } from '@/ui/input/Input'
import { Label } from '@/ui/primitives/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/primitives/select'
import { Switch } from '@/ui/primitives/switch'
import { Loader2, Save, CheckCircle2, Globe, Sparkles, SlidersHorizontal, Key, Wrench, AlertTriangle, Info } from 'lucide-react'
import { toast } from 'sonner'
import type { FormattingConfig } from '@/types/config'
import { API_BASE_URL } from '@/api-base'
import { useTranslation } from 'react-i18next'
import { FormattingPanel } from '@/features/translation-workflow/components/FormattingPanel'
import { LoginPrompt } from '@/features/auth-shell/components/LoginPrompt'
import { useTranslationConfig } from '@/features/translation-workflow/hooks/useTranslationConfig'
import { getLocalizedLanguageOptions } from '@/i18n/config'
import { getAccessToken } from '@/lib/local-auth'
import { PageIntro } from '@/ui/page-intro/PageIntro'
import { SectionCard } from '@/ui/section-card/SectionCard'
import { NoticeBanner } from '@/ui/notice-banner/NoticeBanner'
import { InfoTile } from '@/ui/info-tile/InfoTile'
import { FormFieldShell } from '@/ui/form-field-shell/FormFieldShell'
import { LanguageSelector } from '@/ui/language-selector/LanguageSelector'
import { LoadingState } from '@/ui/loading-state/LoadingState'
import { ThemeToggle } from '@/ui/theme-toggle/ThemeToggle'

interface UserSettings {
  default_source_language: string
  default_target_language: string
  translation_mode: string
  compile_strategy: string
  translation_model: string | null
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
  generate_glossary: true,
  use_author_api: true,
  custom_base_url: null,
  has_custom_api_key: false,
  default_formatting: null,
}

export function TranslationSettingsWorkspace() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const { t } = useTranslation()
  const languages = getLocalizedLanguageOptions(t)
  const { invalidateUserSettings } = useTranslationConfig()

  const [settings, setSettings] = useState<UserSettings>(defaultSettings)
  const [customApiKey, setCustomApiKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const token = await getAccessToken()

      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(t('settings.failed_to_load_settings'))
      }

      const data: UserSettings = await response.json()
      setSettings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.failed_to_load_settings'))
    } finally {
      setLoading(false)
    }
  }, [t])

  const handleSave = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)

    if (!settings.use_author_api) {
      if (!settings.custom_base_url || settings.custom_base_url.trim() === '') {
        setError(t('settings.a_custom_api_endpoint_is_required_when_the_default_author_api_is_disabled'))
        setSaving(false)
        return
      }
      if (!settings.has_custom_api_key && !customApiKey) {
        setError(t('settings.an_api_key_is_required_when_the_default_author_api_is_disabled'))
        setSaving(false)
        return
      }
    }

    try {
      const token = await getAccessToken()
      const updateData: Record<string, unknown> = {
        default_source_language: settings.default_source_language,
        default_target_language: settings.default_target_language,
        translation_mode: settings.translation_mode,
        compile_strategy: settings.compile_strategy,
        translation_model: settings.translation_model,
        generate_glossary: settings.generate_glossary,
        use_author_api: settings.use_author_api,
        custom_base_url: settings.custom_base_url,
      }

      if (customApiKey) {
        updateData.custom_api_key = customApiKey
      }

      if (settings.default_formatting !== undefined) {
        updateData.default_formatting = settings.default_formatting
      }

      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      })

      if (!response.ok) {
        throw new Error(t('settings.failed_to_save_settings'))
      }

      const data: UserSettings = await response.json()
      setSettings(data)
      setCustomApiKey('')
      invalidateUserSettings()
      toast.success(t('settings.settings_saved'))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.failed_to_save_settings'))
      toast.error(t('settings.save_failed'))
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      void fetchSettings()
    }
  }, [fetchSettings, isAuthenticated])

  if (authLoading) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center">
        <LoadingState label={t('common.status.loading')} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 py-12 animate-in fade-in duration-500">
        <LoginPrompt
          messageKey="settings.sign_in_to_save_settings"
          descriptionKey="settings.after_signing_in_you_can_save_default_translation_settings_and_reuse_them_next_time"
          actionLabelKey="common.go_to_sign_in"
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-in fade-in duration-500">
      <PageIntro
        title={t('settings.title')}
        description={t('settings.system_preferences_description')}
        actions={(
          <Button type="submit" form="settings-form" disabled={saving} className="rounded-full shadow-sm" size="sm">
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('settings.actions.saving')}
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                {t('settings.actions.save')}
              </>
            )}
          </Button>
        )}
      />

      {error ? (
        <NoticeBanner
          tone="danger"
          icon={<AlertTriangle className="h-4 w-4" />}
          description={error}
        />
      ) : null}

      {loading ? (
        <LoadingState className="justify-center py-12" label={t('common.status.loading')} />
      ) : (
        <form id="settings-form" onSubmit={handleSave} className="space-y-6 pb-20">
          <SectionCard
            icon={<Globe className="h-5 w-5" />}
            title={t('settings.appearance')}
            description={t('settings.system_preferences_description')}
            contentClassName="flex flex-col gap-4 md:flex-row md:items-center md:justify-between"
          >
            <div className="flex flex-col gap-3">
              <Label className="text-xs font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">
                {t('common.choose_global_interface_language')}
              </Label>
              <LanguageSelector />
            </div>

            <div className="flex flex-col gap-3 md:items-end">
              <Label className="text-xs font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">
                {t('settings.appearance')}
              </Label>
              <ThemeToggle />
            </div>
          </SectionCard>

          <SectionCard
            icon={<Globe className="h-5 w-5" />}
            title={t('common.sections.languageSettings')}
            description={t('settings.set_the_default_source_and_target_languages')}
            contentClassName="grid grid-cols-1 gap-6 md:grid-cols-2"
          >
            <div className="space-y-3">
              <FormFieldShell label={t('common.labels.sourceLanguage')} size="compact">
                <Select
                  value={settings.default_source_language}
                  onValueChange={(value) => setSettings((prev) => ({ ...prev, default_source_language: value }))}
                >
                  <SelectTrigger id="source_language" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    {languages.map((language) => (
                      <SelectItem key={`source-${language.code}`} value={language.code} className="rounded-lg">
                        {language.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormFieldShell>
            </div>

            <div className="space-y-3">
              <FormFieldShell label={t('common.labels.targetLanguage')} size="compact">
                <Select
                  value={settings.default_target_language}
                  onValueChange={(value) => setSettings((prev) => ({ ...prev, default_target_language: value }))}
                >
                  <SelectTrigger id="target_language" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    {languages.map((language) => (
                      <SelectItem key={`target-${language.code}`} value={language.code} className="rounded-lg">
                        {language.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormFieldShell>
            </div>
          </SectionCard>

          <SectionCard
            icon={<Sparkles className="h-5 w-5" />}
            title={t('settings.translation_settings')}
            description={t('settings.configure_translation_mode_and_compile_options')}
            iconClassName="bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]"
            contentClassName="space-y-6"
          >
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <FormFieldShell label={t('common.labels.translationMode')} size="compact">
                  <Select
                    value={settings.translation_mode}
                    onValueChange={(value) => setSettings((prev) => ({ ...prev, translation_mode: value }))}
                  >
                    <SelectTrigger id="translation_mode" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="full" className="rounded-lg">{t('task.translationMode.full')}</SelectItem>
                      <SelectItem value="quick_scan" className="rounded-lg">{t('task.translationMode.quickScan')}</SelectItem>
                    </SelectContent>
                  </Select>
                </FormFieldShell>
              </div>

              <div className="space-y-3">
                <FormFieldShell label={t('common.labels.compileStrategy')} size="compact">
                  <Select
                    value={settings.compile_strategy}
                    onValueChange={(value) => setSettings((prev) => ({ ...prev, compile_strategy: value }))}
                  >
                    <SelectTrigger id="compile_strategy" className="rounded-[20px] bg-[color:var(--px-shell-panel-strong)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="auto" className="rounded-lg">{t('task.compileStrategy.auto')}</SelectItem>
                      <SelectItem value="pdflatex" className="rounded-lg">PDFLaTeX</SelectItem>
                      <SelectItem value="xelatex" className="rounded-lg">XeLaTeX</SelectItem>
                      <SelectItem value="lualatex" className="rounded-lg">LuaLaTeX</SelectItem>
                    </SelectContent>
                  </Select>
                </FormFieldShell>
              </div>
            </div>

            <div className="border-t border-[color:var(--px-shell-line)] pt-2">
              <FormFieldShell label={t('common.labels.translationModel')} size="compact">
                <Input
                  id="translation_model"
                  placeholder={t('settings.leave_blank_to_use_the_system_default')}
                  value={settings.translation_model || ''}
                  onChange={(event) => setSettings((prev) => ({ ...prev, translation_model: event.target.value || null }))}
                  disabled={settings.use_author_api}
                  className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)]"
                />
              </FormFieldShell>
              {settings.use_author_api ? (
                <NoticeBanner
                  tone="info"
                  icon={<Info className="h-4 w-4" />}
                  description={t('settings.when_the_author_api_is_enabled_the_model_is_locked_and_does_not_need_configuration')}
                />
              ) : null}
            </div>
          </SectionCard>

          <SectionCard
            icon={<SlidersHorizontal className="h-5 w-5" />}
            title={t('settings.advancedSettings')}
            description={t('settings.configure_glossary_and_api_options')}
            iconClassName="bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_82%,var(--px-shell-surface))] text-[color:var(--px-shell-ink)]"
            contentClassName="space-y-6"
          >
            <InfoTile
              title={t('common.generate_glossary')}
              description={t('settings.generate_a_terminology_table_csv_during_translation')}
              trailing={(
                <Switch
                  id="generate_glossary"
                  checked={settings.generate_glossary}
                  onCheckedChange={(checked) => setSettings((prev) => ({ ...prev, generate_glossary: checked }))}
                />
              )}
            />

            <div className="h-px w-full bg-outline-variant/10" />

            <InfoTile
              title={t('settings.use_default_author_api')}
              description={t('settings.turning_this_off_requires_a_custom_api_endpoint_and_key')}
              trailing={(
                <Switch
                  id="use_author_api"
                  checked={settings.use_author_api}
                  onCheckedChange={(checked) => setSettings((prev) => ({ ...prev, use_author_api: checked }))}
                />
              )}
            />
          </SectionCard>

          <SectionCard
            icon={<Wrench className="h-5 w-5" />}
            title={t('settings.formatting_defaults')}
            description={t('settings.set_the_default_output_formatting_for_translated_documents_manual_translation_time_settings_override_these_values')}
            iconClassName="bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-success)]"
            contentClassName="p-0"
          >
            <div className="bg-[color:var(--px-shell-panel-strong)]/60 px-0 py-0">
              <FormattingPanel
                value={settings.default_formatting ?? {}}
                onChange={(patch) => setSettings((prev) => ({
                  ...prev,
                  default_formatting: { ...(prev.default_formatting ?? {}), ...patch },
                }))}
                targetLanguage={settings.default_target_language}
              />
            </div>
          </SectionCard>

          {!settings.use_author_api ? (
            <SectionCard
              icon={<Key className="h-5 w-5" />}
              title={t('settings.custom_api')}
              description={t('settings.use_your_own_api_endpoint_and_key')}
              className="animate-in zoom-in-95 duration-200"
              headerClassName="bg-[color:var(--px-shell-danger-soft)]"
              iconClassName="border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]"
              contentClassName="space-y-4"
            >
              <FormFieldShell label={t('settings.api_endpoint')} size="compact">
                <Input
                  id="custom_base_url"
                  placeholder="https://api.openai.com/v1"
                  value={settings.custom_base_url || ''}
                  onChange={(event) => setSettings((prev) => ({ ...prev, custom_base_url: event.target.value || null }))}
                  className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)]"
                />
              </FormFieldShell>

              <FormFieldShell
                label={t('settings.api_key')}
                size="compact"
                headerAside={settings.has_custom_api_key ? (
                  <span className="ml-2 flex items-center rounded bg-[color:var(--px-shell-success-soft)] px-2 py-0.5 text-[10px] font-bold text-[color:var(--px-shell-success)]">
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    {t('settings.set')}
                  </span>
                ) : null}
              >
                <Input
                  id="custom_api_key"
                  type="password"
                  placeholder={settings.has_custom_api_key ? t('settings.enter_a_new_key_to_update') : 'sk-...'}
                  value={customApiKey}
                  onChange={(event) => setCustomApiKey(event.target.value)}
                  className="rounded-[22px] bg-[color:var(--px-shell-panel-strong)]"
                />
                <p className="text-[11px] font-medium text-[color:var(--px-shell-muted)]">
                  {t('settings.the_api_key_is_stored_encrypted_and_is_never_returned_to_the_client')}
                </p>
              </FormFieldShell>
            </SectionCard>
          ) : null}
        </form>
      )}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\features\user-workspace\components\WorkspaceAccountMenu.tsx
Relative path: features\user-workspace\components\WorkspaceAccountMenu.tsx

```tsx
import { useMemo } from "react"
import { LogOut, Settings, Shield, User as UserIcon, Wrench } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/ui/button/Button"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"

export function WorkspaceAccountMenu({ collapsed = false }: { collapsed?: boolean }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { user, isAuthenticated, signOut } = useAuth()
  const isAdmin = hasAdminRole(user?.roles)

  const profileLabel = useMemo(
    () =>
      user?.display_name?.trim() ||
      user?.email?.split("@")[0] ||
      user?.external_user_id ||
      t("common.labels.user"),
    [t, user?.display_name, user?.email, user?.external_user_id],
  )
  const profileInitial = profileLabel.charAt(0).toUpperCase()

  async function handleSignOut() {
    await signOut()
    navigate("/")
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={profileLabel}
          title={profileLabel}
          className={`flex w-full items-center rounded-[18px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] transition-all duration-200 hover:border-[color:var(--px-shell-accent)]/24 hover:bg-white ${
            collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-3"
          }`}
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-sm font-bold uppercase text-[color:var(--px-shell-accent)]">
            {profileInitial}
          </span>
          <span className={collapsed ? "sr-only" : "min-w-0 flex-1 text-left"}>
            <span className="block truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {profileLabel}
            </span>
            <span className="block text-xs text-[color:var(--px-shell-muted)]">
              {isAuthenticated ? t("profile.profile") : t("common.actions.signIn")}
            </span>
          </span>
        </button>
      </PopoverTrigger>

      <PopoverContent
        side="top"
        align="start"
        sideOffset={12}
        className="w-72 rounded-[24px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_30px_70px_-42px_rgba(15,23,42,0.45)]"
      >
        <div className="rounded-[18px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-3">
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {t("common.labels.user")}
          </p>
          <p className="mt-1 truncate text-base font-semibold text-[color:var(--px-shell-ink)]">
            {profileLabel}
          </p>
        </div>

        <div className="mt-3 space-y-2">
          {isAuthenticated ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
              >
                <UserIcon className="h-4 w-4" />
                <span>{t("profile.profile")}</span>
              </Link>
              <Link
                to="/workspace/settings"
                className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
              >
                <Settings className="h-4 w-4" />
                <span>{t("settings.title")}</span>
              </Link>
              {isAdmin ? (
                <>
                  <Link
                    to="/admin/curation"
                    className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
                  >
                    <Shield className="h-4 w-4" />
                    <span>{t("community.admin.nav.curation", "Admin curation")}</span>
                  </Link>
                  <Link
                    to="/admin/curation/tasks"
                    className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
                  >
                    <Wrench className="h-4 w-4" />
                    <span>{t("community.admin.nav.tasks", "Admin tasks")}</span>
                  </Link>
                </>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                className="w-full justify-start rounded-[16px] border border-transparent px-3"
                onClick={() => void handleSignOut()}
              >
                <LogOut className="h-4 w-4" />
                {t("profile.sign_out")}
              </Button>
            </>
          ) : (
            <Button
              type="button"
              className="w-full justify-start rounded-[16px]"
              onClick={() => navigate("/login")}
            >
              <UserIcon className="h-4 w-4" />
              {t("common.actions.signIn")}
            </Button>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\i18n.ts
Relative path: i18n.ts

```ts
import i18n from "i18next"
import { initReactI18next } from "react-i18next"

import de from "@/locales/de/common.json"
import en from "@/locales/en/common.json"
import es from "@/locales/es/common.json"
import fr from "@/locales/fr/common.json"
import ja from "@/locales/ja/common.json"
import ko from "@/locales/ko/common.json"
import ru from "@/locales/ru/common.json"
import zh from "@/locales/zh/common.json"
import { getInitialLanguage } from "@/i18n/config"

const resources = {
  en: { translation: en },
  zh: { translation: zh },
  ja: { translation: ja },
  ko: { translation: ko },
  de: { translation: de },
  fr: { translation: fr },
  es: { translation: es },
  ru: { translation: ru },
} as const

if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: ["en", "zh"],
    interpolation: {
      escapeValue: false,
    },
    returnNull: false,
    keySeparator: false,
    react: {
      useSuspense: false,
    },
  })
}

export default i18n

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\i18n\config.ts
Relative path: i18n\config.ts

```ts
export const UI_LANGUAGE_STORAGE_KEY = "latextrans.ui-language"

export const UI_LANGUAGES = [
  { code: "en", nativeLabel: "English", translationKey: "language.name.en" },
  { code: "zh", nativeLabel: "中文", translationKey: "language.name.zh" },
  { code: "ja", nativeLabel: "日本語", translationKey: "language.name.ja" },
  { code: "ko", nativeLabel: "한국어", translationKey: "language.name.ko" },
  { code: "de", nativeLabel: "Deutsch", translationKey: "language.name.de" },
  { code: "fr", nativeLabel: "Français", translationKey: "language.name.fr" },
  { code: "es", nativeLabel: "Español", translationKey: "language.name.es" },
  { code: "ru", nativeLabel: "Русский", translationKey: "language.name.ru" },
] as const

export type UILanguage = (typeof UI_LANGUAGES)[number]["code"]

const supportedLanguageCodes = new Set<UILanguage>(UI_LANGUAGES.map(({ code }) => code))

export function normalizeLanguageCode(language?: string | null): UILanguage {
  if (!language) {
    return "zh"
  }

  const normalizedLanguage = language.replace("_", "-").split("-")[0].toLowerCase() as UILanguage
  return supportedLanguageCodes.has(normalizedLanguage) ? normalizedLanguage : "zh"
}

export function getInitialLanguage(browserLanguage?: string): UILanguage {
  if (typeof window !== "undefined") {
    const storedLanguage = window.localStorage.getItem(UI_LANGUAGE_STORAGE_KEY)
    if (storedLanguage) {
      return normalizeLanguageCode(storedLanguage)
    }
  }

  if (browserLanguage) {
    return normalizeLanguageCode(browserLanguage)
  }

  if (typeof navigator !== "undefined") {
    return normalizeLanguageCode(navigator.language)
  }

  return "zh"
}

export function persistLanguage(language: UILanguage) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, language)
  }
}

export function getLocalizedLanguageOptions(
  translate: (key: string) => string,
) {
  return UI_LANGUAGES.map((language) => ({
    code: language.code,
    label: translate(language.translationKey),
    nativeLabel: language.nativeLabel,
  }))
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\i18n\formatting-copy.ts
Relative path: i18n\formatting-copy.ts

```ts
type Translate = (key: string, options?: Record<string, unknown>) => string

export function getTranslationModeLabel(translate: Translate, mode: string) {
  return mode === "full"
    ? translate("task.translationMode.full")
    : translate("task.translationMode.quickScan")
}

export function getCompileStrategyLabel(translate: Translate, strategy: string) {
  const strategyMap: Record<string, string> = {
    auto: translate("task.compileStrategy.auto"),
    pdflatex: "PDFLaTeX",
    xelatex: "XeLaTeX",
    lualatex: "LuaLaTeX",
  }

  return strategyMap[strategy] ?? strategy
}

export function getFormattingValueLabel(
  translate: Translate,
  type: "column_mode" | "margin" | "cjk_font" | "cite_style",
  value: string,
) {
  const dictionary: Record<string, Record<string, string>> = {
    column_mode: {
      single: translate("formatting.column.single"),
      double: translate("formatting.column.double"),
    },
    margin: {
      narrow: translate("formatting.margin.narrowShort"),
      normal: translate("formatting.margin.standardShort"),
      wide: translate("formatting.margin.wideShort"),
    },
    cjk_font: {
      songti: translate("formatting.font.songti"),
      heiti: translate("formatting.font.heiti"),
    },
    cite_style: {
      numbers: translate("formatting.citationStyle.numericShort"),
      super: translate("formatting.citationStyle.superscript"),
      authoryear: translate("formatting.citationStyle.authorYearShort"),
    },
  }

  return dictionary[type][value] ?? value
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\i18n\task-copy.ts
Relative path: i18n\task-copy.ts

```ts
type Translate = (key: string, options?: Record<string, unknown>) => string

export type TaskDetailParams = Record<string, string | number | boolean | null> | null | undefined

export interface TaskCopyInput {
  status?: string | null
  stage?: string | null
  detailCode?: string | null
  detailParams?: TaskDetailParams
  failureReasonCode?: string | null
  warnings?: string | null
}

const statusKeyMap: Record<string, string> = {
  pending: "task.status.pending",
  queued: "task.status.queued",
  processing: "task.status.processing",
  completed: "task.status.completed",
  completed_with_warnings: "task.status.completedWithWarnings",
  failed: "task.status.failed",
  failed_compilation: "task.status.failedCompilation",
  structure_invalid: "task.status.structureInvalid",
}

const stageKeyMap: Record<string, string> = {
  idle: "task.stage.idle",
  downloading: "task.stage.downloading",
  downloading_pdf: "task.stage.downloadingPdf",
  validating: "task.stage.validating",
  parsing: "task.stage.parsing",
  translating: "task.stage.translating",
  compiling: "task.stage.compiling",
  compilation_failed: "task.stage.compilationFailed",
  done: "task.stage.done",
}

const detailKeyMap: Record<string, string> = {
  task_queued: "task.detail.taskQueued",
  task_waiting: "task.detail.taskWaiting",
  download_source_starting: "task.detail.downloadSourceStarting",
  download_source_progress: "task.detail.downloadSourceProgress",
  download_source_complete: "task.detail.downloadSourceComplete",
  download_pdf_starting: "task.detail.downloadPdfStarting",
  download_pdf_progress: "task.detail.downloadPdfProgress",
  download_pdf_complete: "task.detail.downloadPdfComplete",
  validate_source_starting: "task.detail.validateSourceStarting",
  validate_source_complete: "task.detail.validateSourceComplete",
  translation_starting: "task.detail.translationStarting",
  translation_running: "task.detail.translationRunning",
  translation_retry_failed_chunks: "task.detail.translationRetryFailedChunks",
  translation_restore_structure: "task.detail.translationRestoreStructure",
  translation_restore_environment: "task.detail.translationRestoreEnvironment",
  translation_apply_fallback: "task.detail.translationApplyFallback",
  translation_validate_results: "task.detail.translationValidateResults",
  formatting_apply_config: "task.detail.formattingApplyConfig",
  formatting_warning: "task.detail.formattingWarning",
  compile_prepare_pdf: "task.detail.compilePreparePdf",
  compile_running: "task.detail.compileRunning",
  compile_complete: "task.detail.compileComplete",
  task_rate_limited_retrying: "task.detail.rateLimitedRetrying",
}

const failureKeyMap: Record<string, string> = {
  structure_env_stack_mismatch: "task.failure.structureEnvStackMismatch",
  structure_latexwalker_unexpected_closing_env: "task.failure.structureUnexpectedClosingEnv",
}

function normalizeStatus(status?: string | null) {
  return status?.toLowerCase() ?? ""
}

function normalizeStage(stage?: string | null) {
  if (!stage) {
    return ""
  }
  return stage === "extracting" ? "downloading" : stage.toLowerCase()
}

function getDetailValues(detailCode?: string | null, detailParams?: TaskDetailParams) {
  if (!detailParams) {
    return undefined
  }

  const params = { ...detailParams }
  const current = params.current
  const total = params.total

  if (
    (detailCode === "translation_running" ||
      detailCode === "translation_retry_failed_chunks" ||
      detailCode === "translation_restore_structure" ||
      detailCode === "translation_restore_environment" ||
      detailCode === "translation_apply_fallback") &&
    current != null &&
    total != null
  ) {
    return {
      ...params,
      value: `${current}/${total}`,
    }
  }

  if (typeof params.warning_text === "string") {
    return {
      ...params,
      warningText: params.warning_text,
    }
  }

  if (typeof params.retry_in_seconds === "number") {
    return {
      ...params,
      retryInSeconds: params.retry_in_seconds,
    }
  }

  return params
}

export function getTaskStatusLabel(
  translate: Translate,
  status?: string | null,
  stage?: string | null,
) {
  const normalizedStatus = normalizeStatus(status)
  const normalizedStage = normalizeStage(stage)

  if (normalizedStatus === "processing") {
    if (normalizedStage === "downloading" || normalizedStage === "downloading_pdf") {
      return translate("task.status.downloading")
    }
    if (normalizedStage === "translating" || normalizedStage === "parsing") {
      return translate("task.status.translating")
    }
  }

  const key = statusKeyMap[normalizedStatus]
  return key ? translate(key) : (status ?? "")
}

export function getTaskStageLabel(translate: Translate, stage?: string | null) {
  const normalizedStage = normalizeStage(stage)
  const key = stageKeyMap[normalizedStage]
  return key ? translate(key) : (stage ?? "")
}

export function getTaskFailureLabel(
  translate: Translate,
  failureReasonCode?: string | null,
) {
  const key = failureReasonCode ? failureKeyMap[failureReasonCode] : undefined
  return key ? translate(key) : translate("task.failure.generic")
}

export function getTaskDetailLabel(
  translate: Translate,
  detailCode?: string | null,
  detailParams?: TaskDetailParams,
  stage?: string | null,
) {
  if (!detailCode) {
    return getTaskStageLabel(translate, stage)
  }

  const key = detailKeyMap[detailCode]
  if (!key) {
    return getTaskStageLabel(translate, stage)
  }

  return translate(key, getDetailValues(detailCode, detailParams))
}

export function getTaskCopy(
  translate: Translate,
  {
    status,
    stage,
    detailCode,
    detailParams,
    failureReasonCode,
  }: TaskCopyInput,
) {
  const normalizedStatus = normalizeStatus(status)
  const detailLabel = getTaskDetailLabel(translate, detailCode, detailParams, stage)
  const stageLabel = getTaskStageLabel(translate, stage)
  const statusLabel = getTaskStatusLabel(translate, status, stage)
  const failureLabel =
    normalizedStatus === "failed" ||
    normalizedStatus === "failed_compilation" ||
    normalizedStatus === "structure_invalid"
      ? getTaskFailureLabel(translate, failureReasonCode)
      : null

  return {
    statusLabel,
    stageLabel,
    detailLabel,
    failureLabel,
    isRateLimited: detailCode === "task_rate_limited_retrying",
  }
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\i18n\ui-text.ts
Relative path: i18n\ui-text.ts

```ts
export { getCompileStrategyLabel, getFormattingValueLabel, getTranslationModeLabel } from "@/i18n/formatting-copy"
export { getTaskStatusLabel } from "@/i18n/task-copy"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\index.css
Relative path: index.css

```css
@import "tailwindcss";
@import "./styles/tokens.css";

@plugin "tailwindcss-animate";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --radius-2xl: calc(var(--radius) + 8px);
  --radius-3xl: calc(var(--radius) + 12px);
  --radius-4xl: calc(var(--radius) + 16px);
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
}

:root {
  --radius: 0.875rem;
  --background: var(--px-shell-bg);
  --foreground: var(--px-shell-ink);
  --card: var(--px-shell-panel-strong);
  --card-foreground: var(--px-shell-ink);
  --popover: var(--px-shell-panel-strong);
  --popover-foreground: var(--px-shell-ink);
  --primary: var(--px-shell-accent);
  --primary-foreground: var(--px-shell-accent-contrast);
  --secondary: color-mix(in srgb, var(--px-shell-accent) 10%, var(--px-shell-panel-strong));
  --secondary-foreground: var(--px-shell-ink);
  --muted: color-mix(in srgb, var(--px-shell-panel-strong) 84%, var(--px-shell-bg));
  --muted-foreground: var(--px-shell-muted);
  --accent: var(--px-shell-accent-soft);
  --accent-foreground: var(--px-shell-accent-strong);
  --destructive: #ba1a1a;
  --border: var(--px-shell-line);
  --input: var(--px-shell-line);
  --ring: var(--px-shell-accent);
  --chart-1: oklch(0.646 0.222 41.116);
  --chart-2: oklch(0.6 0.118 184.704);
  --chart-3: oklch(0.398 0.07 227.392);
  --chart-4: oklch(0.828 0.189 84.429);
  --chart-5: oklch(0.769 0.188 70.08);
  --sidebar: var(--px-shell-panel);
  --sidebar-foreground: var(--px-shell-ink);
  --sidebar-primary: var(--px-shell-accent);
  --sidebar-primary-foreground: var(--px-shell-accent-contrast);
  --sidebar-accent: var(--px-shell-accent-soft);
  --sidebar-accent-foreground: var(--px-shell-ink);
  --sidebar-border: var(--px-shell-line);
  --sidebar-ring: var(--px-shell-accent);
  --shell-bg: var(--px-shell-bg);
  --shell-surface: var(--px-shell-panel);
  --shell-surface-strong: var(--px-shell-panel-strong);
  --shell-surface-muted: var(--px-shell-surface);
  --shell-border: var(--px-shell-line);
  --shell-border-strong: var(--px-shell-line-strong);
  --shell-pill: color-mix(in srgb, var(--px-shell-panel-strong) 82%, white);
  --shell-pill-hover: white;
  --shell-heading: var(--px-shell-ink);
  --shell-text: var(--px-shell-ink);
  --shell-text-soft: color-mix(in srgb, var(--px-shell-muted) 86%, black 14%);
  --shell-text-muted: var(--px-shell-muted);
  --shell-icon: var(--px-shell-muted);
  --shell-accent: var(--px-shell-accent);
  --shell-accent-hover: var(--px-shell-accent-strong);
  --shell-accent-foreground: var(--px-shell-accent-contrast);
  --shell-info: var(--px-shell-info);
  --shell-info-soft: var(--px-shell-info-soft);
  --shell-info-line: var(--px-shell-info-line);
  --shell-success: var(--px-shell-success);
  --shell-success-soft: var(--px-shell-success-soft);
  --shell-success-line: var(--px-shell-success-line);
  --shell-warning: var(--px-shell-warning);
  --shell-warning-soft: var(--px-shell-warning-soft);
  --shell-warning-line: var(--px-shell-warning-line);
  --shell-danger: var(--px-shell-danger);
  --shell-danger-strong: var(--px-shell-danger-strong);
  --shell-danger-soft: var(--px-shell-danger-soft);
  --shell-danger-line: var(--px-shell-danger-line);
  --shell-shadow: var(--px-shell-shadow);
  --shell-panel-shadow: var(--px-shell-shadow);
  --shell-panel-shadow-strong: var(--px-shell-shadow);
  --shell-code-bg: color-mix(in srgb, var(--px-shell-panel-strong) 85%, var(--px-shell-surface));
  --shell-code-border: color-mix(in srgb, var(--px-shell-line) 88%, rgba(23, 20, 17, 0.14));
}

.dark {
  --background: var(--px-shell-bg);
  --foreground: var(--px-shell-ink);
  --card: var(--px-shell-panel-strong);
  --card-foreground: var(--px-shell-ink);
  --popover: var(--px-shell-panel-strong);
  --popover-foreground: var(--px-shell-ink);
  --primary: var(--px-shell-accent);
  --primary-foreground: var(--px-shell-accent-contrast);
  --secondary: color-mix(in srgb, var(--px-shell-accent) 18%, var(--px-shell-panel-strong));
  --secondary-foreground: var(--px-shell-ink);
  --muted: color-mix(in srgb, var(--px-shell-panel-strong) 90%, black 10%);
  --muted-foreground: var(--px-shell-muted);
  --accent: var(--px-shell-accent-soft);
  --accent-foreground: var(--px-shell-ink);
  --destructive: #ffdad6;
  --border: var(--px-shell-line);
  --input: var(--px-shell-line);
  --ring: var(--px-shell-accent);
  --chart-1: oklch(0.488 0.243 264.376);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.627 0.265 303.9);
  --chart-5: oklch(0.645 0.246 16.439);
  --sidebar: var(--px-shell-panel);
  --sidebar-foreground: var(--px-shell-ink);
  --sidebar-primary: var(--px-shell-accent);
  --sidebar-primary-foreground: var(--px-shell-accent-contrast);
  --sidebar-accent: var(--px-shell-accent-soft);
  --sidebar-accent-foreground: var(--px-shell-ink);
  --sidebar-border: var(--px-shell-line);
  --sidebar-ring: var(--px-shell-accent);
  --shell-bg: var(--px-shell-bg);
  --shell-surface: var(--px-shell-panel);
  --shell-surface-strong: var(--px-shell-panel-strong);
  --shell-surface-muted: var(--px-shell-surface);
  --shell-border: var(--px-shell-line);
  --shell-border-strong: var(--px-shell-line-strong);
  --shell-pill: color-mix(in srgb, var(--px-shell-panel-strong) 92%, black 8%);
  --shell-pill-hover: color-mix(in srgb, var(--px-shell-panel-strong) 96%, white 4%);
  --shell-heading: var(--px-shell-ink);
  --shell-text: var(--px-shell-ink);
  --shell-text-soft: color-mix(in srgb, var(--px-shell-muted) 82%, white 18%);
  --shell-text-muted: var(--px-shell-muted);
  --shell-icon: var(--px-shell-muted);
  --shell-accent: var(--px-shell-accent);
  --shell-accent-hover: var(--px-shell-accent-strong);
  --shell-accent-foreground: var(--px-shell-accent-contrast);
  --shell-info: var(--px-shell-info);
  --shell-info-soft: var(--px-shell-info-soft);
  --shell-info-line: var(--px-shell-info-line);
  --shell-success: var(--px-shell-success);
  --shell-success-soft: var(--px-shell-success-soft);
  --shell-success-line: var(--px-shell-success-line);
  --shell-warning: var(--px-shell-warning);
  --shell-warning-soft: var(--px-shell-warning-soft);
  --shell-warning-line: var(--px-shell-warning-line);
  --shell-danger: var(--px-shell-danger);
  --shell-danger-strong: var(--px-shell-danger-strong);
  --shell-danger-soft: var(--px-shell-danger-soft);
  --shell-danger-line: var(--px-shell-danger-line);
  --shell-shadow: var(--px-shell-shadow);
  --shell-panel-shadow: var(--px-shell-shadow);
  --shell-panel-shadow-strong: var(--px-shell-shadow);
  --shell-code-bg: color-mix(in srgb, var(--px-shell-panel-strong) 88%, black 12%);
  --shell-code-border: color-mix(in srgb, var(--px-shell-line) 90%, rgba(247, 240, 231, 0.12));
}

@layer base {
  html,
  body,
  #root {
    min-height: 100%;
  }

  * {
    @apply border-border outline-ring/50;
  }

  body {
    background-color: var(--px-shell-surface);
    color: var(--px-shell-ink);
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    background-image:
      radial-gradient(circle at top left, rgba(88, 201, 255, 0.12), transparent 28%),
      radial-gradient(circle at top right, rgba(18, 118, 199, 0.08), transparent 24%),
      linear-gradient(180deg, color-mix(in srgb, var(--px-shell-surface) 94%, white) 0%, var(--px-shell-bg) 100%);
    background-attachment: fixed;
  }

  :where(h1, h2, h3, .font-display) {
    font-family: "Rajdhani", "IBM Plex Sans", sans-serif;
    letter-spacing: 0.01em;
  }

  :where(
    button:not(:disabled),
    [role="button"]:not([aria-disabled="true"]),
    a[href],
    summary,
    label[for],
    input[type="checkbox"]:not(:disabled),
    input[type="radio"]:not(:disabled)
  ) {
    cursor: pointer;
  }

  :where(button:disabled, input:disabled, textarea:disabled, select:disabled) {
    cursor: not-allowed;
  }

  :where(button, [role="button"], a[href]) {
    -webkit-tap-highlight-color: transparent;
  }

  :where(button:not(:disabled), [role="button"]:not([aria-disabled="true"]), a[href]) {
    transition:
      transform 0.18s ease,
      background-color 0.18s ease,
      border-color 0.18s ease,
      color 0.18s ease,
      opacity 0.18s ease,
      box-shadow 0.18s ease;
  }

  :where(button:not(:disabled), [role="button"]:not([aria-disabled="true"]), a[href]):active {
    transform: translateY(1px);
  }

  .paper-preview {
    color: var(--shell-text);
  }

  .paper-preview :is(h1, h2, h3, h4, strong, th) {
    color: var(--shell-heading);
  }

  .paper-preview :is(a, code) {
    color: var(--shell-heading);
  }

  .paper-preview pre {
    background: var(--shell-code-bg);
    border-color: var(--shell-code-border);
    color: var(--shell-text);
  }

  .paper-preview blockquote {
    border-left-color: var(--shell-border);
    color: var(--shell-text-soft);
  }

  .paper-preview .paper-preview__section + .paper-preview__section {
    margin-top: 1.75rem;
  }

  .paper-preview-shell {
    max-width: 100%;
    overflow-x: hidden;
  }

  .paper-preview-shell .paper-preview {
    max-width: 100%;
    margin: 0 auto;
    overflow-wrap: anywhere;
  }

  .paper-preview-shell .paper-preview__section,
  .paper-preview-shell .paper-preview__block {
    min-width: 0;
    max-width: 100%;
  }

  .paper-preview .paper-preview__block + .paper-preview__block {
    margin-top: 1rem;
  }

  .paper-preview .paper-preview__block[id] {
    scroll-margin-top: 7rem;
  }

  .paper-preview .paper-preview__anchor-target {
    display: block;
    position: relative;
    top: -5rem;
    height: 0;
    visibility: hidden;
  }

  .paper-preview .paper-preview__figure {
    margin: 1.5rem 0;
    border: 1px solid var(--shell-border);
    border-radius: 1rem;
    background: var(--shell-surface-muted);
    padding: 1rem 1.1rem;
  }

  .paper-preview .paper-preview__figure-grid {
    display: grid;
    gap: 1rem;
  }

  .paper-preview .paper-preview__figure-item {
    overflow: hidden;
    border-radius: 0.9rem;
    background: color-mix(in srgb, var(--shell-surface-strong) 88%, transparent);
    border: 1px solid color-mix(in srgb, var(--shell-border) 82%, transparent);
  }

  .paper-preview .paper-preview__figure-image {
    display: block;
    width: 100%;
    height: auto;
    object-fit: contain;
    background: white;
  }

  .paper-preview .paper-preview__note {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--shell-heading);
  }

  .paper-preview .paper-preview__caption {
    margin-top: 0.65rem;
    font-size: 0.95rem;
    line-height: 1.75;
    color: var(--shell-text-soft);
  }

  .paper-preview .paper-preview__subheading {
    margin-top: 1rem;
    margin-bottom: 0.6rem;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--shell-heading);
  }

  .paper-preview .paper-preview__math-block {
    overflow-x: auto;
    border: 1px solid color-mix(in srgb, var(--shell-border) 78%, transparent);
    border-radius: 1rem;
    background: color-mix(in srgb, var(--shell-surface-strong) 92%, transparent);
    padding: 1rem 1.15rem;
  }

  .paper-preview .paper-preview__math-block .katex-display {
    margin: 0;
  }

  .paper-preview .paper-preview__algorithm,
  .paper-preview .paper-preview__algorithm-block {
    border: 1px solid color-mix(in srgb, var(--shell-border) 78%, transparent);
    border-radius: 1rem;
    background: color-mix(in srgb, var(--shell-surface-muted) 92%, transparent);
    padding: 1rem 1.15rem;
  }

  .paper-preview .paper-preview__algorithm-title {
    margin-bottom: 0.8rem;
    font-size: 1rem;
    font-weight: 700;
    color: var(--shell-heading);
  }

  .paper-preview .paper-preview__algorithm-steps {
    margin: 0;
    padding-left: 1.2rem;
  }

  .paper-preview .paper-preview__algorithm-step {
    margin: 0.5rem 0;
    line-height: 1.8;
  }

  .paper-preview .paper-preview__command-block {
    overflow-x: auto;
    border: 1px solid color-mix(in srgb, var(--shell-border) 78%, transparent);
    border-radius: 1rem;
    background: color-mix(in srgb, var(--shell-surface-strong) 94%, transparent);
    padding: 0.95rem 1.1rem;
  }

  .paper-preview .paper-preview__command-block code {
    display: block;
    font-family: "JetBrains Mono", "Fira Code", "SFMono-Regular", Consolas, monospace;
    font-size: 0.94rem;
    line-height: 1.8;
    color: var(--shell-heading);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .paper-preview .paper-preview__algorithm-block p + p {
    margin-top: 0.55rem;
  }

  .paper-preview .paper-preview__list {
    margin: 1rem 0 1.25rem;
    padding-left: 1.4rem;
    color: var(--shell-text);
  }

  .paper-preview .paper-preview__list li {
    margin: 0.45rem 0;
    line-height: 1.9;
  }

  .paper-preview .paper-preview__table-wrap {
    max-width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .paper-preview .paper-preview__table-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.75rem;
  }

  .paper-preview .paper-preview__table-expand {
    border: 1px solid color-mix(in srgb, var(--shell-border) 82%, transparent);
    border-radius: 9999px;
    background: color-mix(in srgb, var(--shell-surface-strong) 84%, transparent);
    color: var(--shell-heading);
    padding: 0.45rem 0.85rem;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }

  .paper-preview .paper-preview__table-expand:hover {
    background: color-mix(in srgb, var(--shell-pill) 82%, transparent);
    border-color: color-mix(in srgb, var(--shell-accent) 40%, var(--shell-border));
    color: var(--shell-accent-hover);
  }

  .paper-preview .paper-preview__table {
    width: max-content;
    min-width: 100%;
    border-collapse: collapse;
    table-layout: auto;
    font-size: 0.98rem;
    line-height: 1.7;
  }

  .paper-preview .paper-preview__table th,
  .paper-preview .paper-preview__table td {
    border-bottom: 1px solid color-mix(in srgb, var(--shell-border) 78%, transparent);
    padding: 0.75rem 0.85rem;
    text-align: left;
    vertical-align: top;
  }

  .paper-preview .paper-preview__table th {
    font-weight: 700;
    white-space: nowrap;
    color: var(--shell-heading);
    background: color-mix(in srgb, var(--shell-surface-strong) 76%, transparent);
  }

  .paper-preview .paper-preview__block--table,
  .paper-preview .paper-preview__block--figure {
    overflow-x: clip;
  }

  .paper-preview .paper-preview__references {
    margin: 1.75rem 0 0;
    padding-top: 0.5rem;
  }

  .paper-preview .paper-preview__references-title {
    margin-bottom: 0.9rem;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--shell-heading);
  }

  .paper-preview .paper-preview__references-list {
    margin: 0;
    padding-left: 1.4rem;
  }

  .paper-preview .paper-preview__reference-item {
    margin: 0.55rem 0;
    line-height: 1.85;
    color: var(--shell-text-soft);
  }

  .paper-preview .paper-preview__xref,
  .paper-preview .paper-preview__reference-link {
    color: var(--shell-accent-hover);
    text-decoration: none;
    border-bottom: 1px dashed color-mix(in srgb, var(--shell-accent) 45%, transparent);
    transition: color 0.2s ease, border-color 0.2s ease;
  }

  .paper-preview .paper-preview__xref:hover,
  .paper-preview .paper-preview__reference-link:hover {
    color: var(--shell-heading);
    border-bottom-color: color-mix(in srgb, var(--shell-heading) 40%, transparent);
  }

  .paper-preview .paper-preview__reference-link {
    margin-left: 0.5rem;
    font-size: 0.9rem;
    white-space: nowrap;
  }

  @media (min-width: 1400px) {
    .paper-preview-shell[data-reader-layout="scholarly"] .paper-preview {
      max-width: min(100%, 78rem);
    }
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }

  100% {
    background-position: 200% 0;
  }
}
 .no-scrollbar::-webkit-scrollbar {
   display: none;
 }
 .no-scrollbar {
   -ms-overflow-style: none;
   scrollbar-width: none;
 }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\layout.tsx
Relative path: layout.tsx

```tsx
import { AppSidebar } from "@/layout/AppSidebar"
import { Outlet } from "react-router-dom"
import { Toaster } from "@/ui/primitives/sonner"

export default function Layout() {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-[color:var(--px-shell-bg)] text-[color:var(--px-shell-ink)] selection:bg-[color:var(--px-shell-accent)] selection:text-white">
      <AppSidebar />
      <main className="min-w-0 flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto flex flex-col min-h-0">
          <Outlet />
        </div>
      </main>
      <Toaster />
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\layout\AppSidebar.tsx
Relative path: layout\AppSidebar.tsx

```tsx
import { useEffect, useState } from "react"
import { Compass, PenTool } from "lucide-react"
import { useLocation, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { WorkspaceAccountMenu } from "@/features/user-workspace/components/WorkspaceAccountMenu"
import { SidebarBrandButton } from "@/ui/sidebar-shell/SidebarBrandButton"
import { SidebarNavItem } from "@/ui/sidebar-shell/SidebarNavItem"
import { SidebarShell } from "@/ui/sidebar-shell/SidebarShell"

function isCommunityRoute(pathname: string) {
  return pathname === "/" || pathname.startsWith("/paper/") || pathname.startsWith("/agent")
}

function isPaperToolRoute(pathname: string) {
  return (
    pathname === "/tools" ||
    pathname.startsWith("/translate") ||
    pathname.startsWith("/processing") ||
    pathname.startsWith("/preview") ||
    pathname.startsWith("/workspace/history") ||
    pathname.startsWith("/workspace/glossary")
  )
}

export function AppSidebar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const routeDefaultCollapsed = location.pathname.startsWith("/paper/")
  const [collapsed, setCollapsed] = useState(routeDefaultCollapsed)
  const brandName = t("brand.name")
  const brandSubtitle = t("brand.subtitle")

  useEffect(() => {
    setCollapsed(routeDefaultCollapsed)
  }, [routeDefaultCollapsed])

  return (
    <SidebarShell
      brand={
        <SidebarBrandButton
          brandName={brandName}
          subtitle={brandSubtitle}
          collapsed={collapsed}
          collapsedActionLabel="Expand sidebar"
          onClick={() => {
            if (collapsed) {
              setCollapsed(false)
              return
            }

            navigate("/")
          }}
        />
      }
      collapsed={collapsed}
      onToggleCollapse={() => setCollapsed((current) => !current)}
      collapseLabel="Collapse sidebar"
      nav={
        <nav aria-label={t("community.nav.explore")} className="space-y-2">
          <SidebarNavItem
            to="/"
            icon={<Compass className="h-5 w-5" />}
            label={t("community.nav.community", "Community")}
            collapsed={collapsed}
            active={isCommunityRoute(location.pathname)}
          />
          <SidebarNavItem
            to="/tools"
            icon={<PenTool className="h-5 w-5" />}
            label={t("community.nav.paperTool", "Paper Tool")}
            collapsed={collapsed}
            active={isPaperToolRoute(location.pathname)}
          />
        </nav>
      }
      utility={<WorkspaceAccountMenu collapsed={collapsed} />}
    />
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\api.ts
Relative path: lib\api.ts

```ts
﻿import axios from "axios"
import type { AdvancedConfig, LatexValidation } from "@/types/config"
import { API_BASE_URL } from "@/api-base"
import { getAccessToken } from "./local-auth"

export interface ArxivResponse {
    task_id: string
    arxiv_id: string
    status: string
    message: string
    source_path?: string
}

/**
 * Translation request with full advanced configuration.
 */
export interface TranslateRequest {
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

export interface TranslateResponse {
    task_id: string
    status: string
    message: string
}

export interface TaskStatusResponse {
    task_id: string
    status: string
    progress: number
    stage?: string
    message: string
    detail_code?: string | null
    detail_params?: Record<string, string | number | boolean | null> | null
    warnings?: string
    error?: string
    failure_reason_code?: string
    failure_class?: string
    guard_phase?: string
    replay_bundle_ref?: string
    output_path?: string
    logs?: string[]
    advanced_config?: AdvancedConfig
    latex_validation?: LatexValidation
    persist_failed?: boolean
}

/**
 * Upload response with LaTeX validation result.
 */
export interface UploadResponse {
    task_id: string
    status: string
    message: string
    source_path: string
    latex_validation?: LatexValidation
}

const api = axios.create({
    baseURL: `${API_BASE_URL}/api`,
    headers: {
        "Content-Type": "application/json",
    },
})

// Request interceptor to add auth token
api.interceptors.request.use(async (config) => {
    const token = await getAccessToken()

    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }

    return config
})

export const downloadArxiv = async (arxivId: string): Promise<ArxivResponse> => {
    const response = await api.post<ArxivResponse>("/arxiv", { arxiv_id: arxivId })
    return response.data
}

/**
 * Start translation with full configuration.
 * 
 * @param taskId - Task ID from upload or arxiv endpoint
 * @param config - Translation configuration including advanced options
 */
export const startTranslation = async (taskId: string, config: TranslateRequest): Promise<TranslateResponse> => {
    const response = await api.post<TranslateResponse>(`/translate/${taskId}`, config)
    return response.data
}

export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await api.get<TaskStatusResponse>(`/task/${taskId}`)
    return response.data
}

export const getTaskLogs = async (taskId: string): Promise<string[]> => {
    // Assuming there is an endpoint for logs, or it comes with status
    // Based on previous reading, task endpoint might return logs or separate
    // Let's assume separate or part of status for now.
    // If not implemented in backend, we might need to rely on polling status message or adding a log endpoint.
    // For MVP, using message updates as logs is fine, or check if /task/{taskId}/logs exists
    try {
        const response = await api.get<{ logs: string[] }>(`/task/${taskId}/logs`)
        return response.data.logs
    } catch {
        return []
    }
}

/**
 * Upload a file (ZIP, TAR.GZ, RAR, or .tex) for translation.
 * 
 * @param file - File to upload
 * @returns Upload response with task ID and LaTeX validation
 */
export const uploadFile = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append("file", file)

    const response = await api.post<UploadResponse>("/upload", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    })
    return response.data
}

/**
 * Get download URL for translated PDF.
 * 
 * @param taskId - Task ID
 * @returns URL to download the PDF
 */
export const getDownloadUrl = (taskId: string): string => {
    return `${API_BASE_URL}/api/download/${taskId}`
}

/**
 * Get preview URL for translated PDF (inline display).
 * 
 * @param taskId - Task ID
 * @returns URL to preview the PDF
 */
export const getPreviewUrl = (taskId: string): string => {
    return `${API_BASE_URL}/api/preview/${taskId}`
}

/**
 * Delete a single task from history.
 * 
 * @param taskId - Task ID to delete
 * @returns Deletion result with deleted directories and errors
 */
export const deleteTask = async (taskId: string): Promise<{
    message: string
    task_id: string
    deleted_dirs: string[]
    errors: string[]
}> => {
    const response = await api.delete(`/history/${taskId}`)
    return response.data
}

/**
 * Delete multiple tasks in batch.
 * 
 * @param taskIds - Array of task IDs to delete
 * @returns Batch deletion results
 */
export const deleteTasksBatch = async (taskIds: string[]): Promise<{
    message: string
    results: Array<{
        task_id: string
        success: boolean
        deleted_dirs?: string[]
        errors?: string[]
        error?: string
    }>
}> => {
    const response = await api.delete(`/history`, {
        data: { task_ids: taskIds }
    })
    return response.data
}

export interface BatchTranslateRequest {
    arxiv_ids: string[]
    target_language: string
    source_language: string
    advanced_config?: AdvancedConfig
}

export interface BatchTranslateResponse {
    batch_id: string
    task_ids: string[]
    message: string
    queued_count: number
}

export interface QueueStatusResponse {
    active_count: number
    queue_size: number
    max_concurrent: number
    total_pending: number
    user_quota_used: number
    user_quota_max: number
}

/**
 * Start batch translation for multiple arXiv IDs (authenticated users only).
 */
export const startBatchTranslation = async (
    request: BatchTranslateRequest
): Promise<BatchTranslateResponse> => {
    const response = await api.post<BatchTranslateResponse>('/batch-translate', request)
    return response.data
}

/**
 * Get current task queue status.
 */
export const getQueueStatus = async (): Promise<QueueStatusResponse> => {
    const response = await api.get<QueueStatusResponse>('/queue/status')
    return response.data
}

export default api



```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\community-agent-conversations.ts
Relative path: lib\community-agent-conversations.ts

```ts
import type {
  CommunityConversationRecord,
  CommunityConversationTurn,
  CommunityConversationTurnRole,
} from "@/types/community"

const STORAGE_PREFIX = "community-agent-conversations:"

function nowIso() {
  return new Date().toISOString()
}

function normalizeScope(userId?: string | null) {
  return userId?.trim() || "guest"
}

export function getConversationStorageKey(userId?: string | null) {
  return `${STORAGE_PREFIX}${normalizeScope(userId)}`
}

function normalizeTurn(entry: unknown): CommunityConversationTurn | null {
  if (!entry || typeof entry !== "object") {
    return null
  }

  const turn = entry as Partial<CommunityConversationTurn>
  if ((turn.role !== "user" && turn.role !== "assistant") || typeof turn.content !== "string" || !turn.content.trim()) {
    return null
  }

  return {
    id: typeof turn.id === "string" && turn.id ? turn.id : `turn-${Math.random().toString(36).slice(2, 10)}`,
    role: turn.role as CommunityConversationTurnRole,
    content: turn.content,
    created_at: typeof turn.created_at === "string" && turn.created_at ? turn.created_at : nowIso(),
    run: turn.run ?? null,
    status: turn.status ?? "completed",
    error: turn.error ?? null,
  }
}

function normalizeRecord(entry: unknown): CommunityConversationRecord | null {
  if (!entry || typeof entry !== "object") {
    return null
  }

  const record = entry as Partial<CommunityConversationRecord>
  if (typeof record.id !== "string" || !record.id) {
    return null
  }

  const turns = Array.isArray(record.turns)
    ? record.turns.map(normalizeTurn).filter((item): item is CommunityConversationTurn => Boolean(item))
    : []

  return {
    id: record.id,
    title: typeof record.title === "string" && record.title.trim() ? record.title : "New chat",
    created_at: typeof record.created_at === "string" && record.created_at ? record.created_at : nowIso(),
    updated_at: typeof record.updated_at === "string" && record.updated_at ? record.updated_at : nowIso(),
    turns,
  }
}

export function loadConversationRecords(userId?: string | null): CommunityConversationRecord[] {
  if (typeof window === "undefined") {
    return []
  }

  const raw = window.localStorage.getItem(getConversationStorageKey(userId))
  if (!raw) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed
      .map(normalizeRecord)
      .filter((item): item is CommunityConversationRecord => Boolean(item))
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
  } catch {
    return []
  }
}

export function saveConversationRecords(userId: string | null | undefined, records: CommunityConversationRecord[]): void {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(getConversationStorageKey(userId), JSON.stringify(records))
}

export function deriveConversationTitle(seedInput: string) {
  const normalized = seedInput.trim().replace(/\s+/g, " ")
  if (!normalized) {
    return "New chat"
  }
  return normalized.length > 48 ? `${normalized.slice(0, 48)}…` : normalized
}

export function createSeedConversationRecord(conversationId: string, seedInput: string): CommunityConversationRecord {
  const createdAt = nowIso()
  return {
    id: conversationId,
    title: deriveConversationTitle(seedInput),
    created_at: createdAt,
    updated_at: createdAt,
    turns: [
      {
        id: `${conversationId}-user-1`,
        role: "user",
        content: seedInput,
        created_at: createdAt,
        status: "completed",
      },
    ],
  }
}

export function upsertConversationRecord(
  userId: string | null | undefined,
  record: CommunityConversationRecord,
): CommunityConversationRecord[] {
  const current = loadConversationRecords(userId)
  const next = [record, ...current.filter((entry) => entry.id !== record.id)].sort((left, right) =>
    right.updated_at.localeCompare(left.updated_at),
  )
  saveConversationRecords(userId, next)
  return next
}

export function buildConversationHistory(turns: CommunityConversationTurn[]) {
  return turns
    .filter((turn) => turn.role === "user" || turn.role === "assistant")
    .map((turn) => ({
      role: turn.role,
      content: turn.content,
    }))
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\community-api.ts
Relative path: lib\community-api.ts

```ts
import { API_BASE_URL, PAPER_PREVIEW_API_BASE_URL } from "@/api-base"
import api from "@/lib/api"
import { getAccessToken } from "@/lib/local-auth"
import { retryOnTransientNetworkError } from "@/lib/network-retry"
import type {
  AdminBatchDeleteCurationJobsResponse,
  AdminCurationBatchResponse,
  AdminCurationJobHistoryResponse,
  AdminDeleteCurationJobResponse,
  AdminDeletePaperResponse,
  CommunityAgentAcceptedRun,
  CommunityAgentMode,
  CommunityAgentRun,
  CommunityAgentStreamEvent,
  CommunityAgentSkillToggles,
  CommunityConversationRecord,
  CommunityFeedSort,
  CommunityPaperDetailResponse,
  CommunityPaperDownloadSessionResponse,
  CommunityPaperImportRequest,
  CommunityPaperImportResponse,
  CommunityPaperListResponse,
  CommunityPaperPreviewResponse,
  CommunityPaperSimilarResponse,
  CommunityPaperSubmitResponse,
  CommunityPaperTranslateResponse,
} from "@/types/community"
import type { TranslateRequest } from "@/lib/api"

const communityPaperDetailCache = new Map<string, CommunityPaperDetailResponse>()
const communityPaperDetailInflight = new Map<string, Promise<CommunityPaperDetailResponse>>()

export async function getCommunityPapers(params: {
  sort: CommunityFeedSort
  q?: string
  limit?: number
  offset?: number
}): Promise<CommunityPaperListResponse> {
  const response = await retryOnTransientNetworkError(
    () =>
      api.get<CommunityPaperListResponse>("/papers", {
        params: {
          sort: params.sort,
          ...(params.q ? { q: params.q } : {}),
          ...(params.limit ? { limit: params.limit } : {}),
          ...(typeof params.offset === "number" ? { offset: params.offset } : {}),
        },
      }),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function createCommunityAgentRun(payload: {
  input: string
  paper_id?: string
  context?: Record<string, unknown>
  skill_toggles?: CommunityAgentSkillToggles
  mode?: CommunityAgentMode
}): Promise<CommunityAgentRun> {
  const response = await api.post<CommunityAgentRun>("/community-agent/runs", payload)
  return response.data
}

function parseSseFrame(frame: string): CommunityAgentStreamEvent | null {
  const lines = frame
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  if (!lines.length) {
    return null
  }

  let eventType = ""
  const dataLines: string[] = []
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim()
      continue
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim())
    }
  }

  if (!dataLines.length) {
    return null
  }

  const payload = JSON.parse(dataLines.join("\n")) as CommunityAgentStreamEvent
  if (!payload.type && eventType) {
    payload.type = eventType as CommunityAgentStreamEvent["type"]
  }
  return payload
}

async function fetchCommunityAgentRunResult(resultUrl: string): Promise<CommunityAgentRun> {
  const token = await getAccessToken()
  const response = await retryOnTransientNetworkError(
    () =>
      fetch(`${API_BASE_URL}${resultUrl}`, {
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : undefined,
      }),
    { attempts: 3, baseDelayMs: 150 },
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch run result: ${response.status}`)
  }
  return (await response.json()) as CommunityAgentRun
}

export async function streamCommunityAgentRun(
  payload: {
    input: string
    paper_id?: string
    context?: Record<string, unknown>
    skill_toggles?: CommunityAgentSkillToggles
    mode?: CommunityAgentMode
  },
  options: {
    onEvent?: (event: CommunityAgentStreamEvent) => void
  } = {},
): Promise<CommunityAgentRun> {
  const acceptedResponse = await api.post<CommunityAgentAcceptedRun>("/community-agent/runs", {
    ...payload,
    execution_mode: "async",
  })
  const acceptedRun = acceptedResponse.data
  const token = await getAccessToken()

  const response = await fetch(`${API_BASE_URL}${acceptedRun.stream_url}`, {
    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : undefined,
  })

  if (!response.ok || !response.body) {
    return fetchCommunityAgentRunResult(acceptedRun.result_url)
  }

  const decoder = new TextDecoder()
  let buffer = ""
  let completedRun: CommunityAgentRun | null = null

  const notify = (event: CommunityAgentStreamEvent) => {
    options.onEvent?.(event)
    if (event.type === "complete") {
      const snapshot = event.data.snapshot
      if (snapshot && typeof snapshot === "object") {
        completedRun = snapshot as CommunityAgentRun
      }
    }
  }

  const reader = response.body.getReader()
  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() ?? ""

    for (const frame of frames) {
      const event = parseSseFrame(frame)
      if (!event) {
        continue
      }
      notify(event)
    }
  }

  if (buffer.trim()) {
    const trailingEvent = parseSseFrame(buffer)
    if (trailingEvent) {
      notify(trailingEvent)
    }
  }

  if (completedRun) {
    return completedRun
  }

  return fetchCommunityAgentRunResult(acceptedRun.result_url)
}

export async function listCommunityAgentConversations(): Promise<CommunityConversationRecord[]> {
  const response = await api.get<CommunityConversationRecord[]>("/community-agent/conversations")
  return response.data
}

export async function upsertCommunityAgentConversation(
  record: CommunityConversationRecord,
): Promise<CommunityConversationRecord> {
  const response = await api.put<CommunityConversationRecord>(
    `/community-agent/conversations/${record.id}`,
    record,
  )
  return response.data
}

export async function deleteCommunityAgentConversation(conversationId: string): Promise<{ deleted: boolean }> {
  const response = await api.delete<{ deleted: boolean }>(`/community-agent/conversations/${conversationId}`)
  return response.data
}

export async function importCommunityPaper(
  payload: CommunityPaperImportRequest,
): Promise<CommunityPaperImportResponse> {
  const response = await api.post<CommunityPaperImportResponse>("/papers/import", payload)
  return response.data
}

export async function getCommunityPaperDetail(
  paperId: string,
): Promise<CommunityPaperDetailResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<CommunityPaperDetailResponse>(`/papers/${paperId}`),
    { attempts: 3, baseDelayMs: 150 },
  )
  communityPaperDetailCache.set(paperId, response.data)
  return response.data
}

export async function getCommunityPaperSimilar(
  paperId: string,
): Promise<CommunityPaperSimilarResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<CommunityPaperSimilarResponse>(`/papers/${paperId}/similar`),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function submitAdminArxivCurationBatch(
  payload: {
    arxiv_ids: string[]
    source_language: string
    target_language: string
  },
): Promise<AdminCurationBatchResponse> {
  const response = await api.post<AdminCurationBatchResponse>("/papers/admin/curation/arxiv", payload)
  return response.data
}

export async function submitAdminUploadCurationBatch(params: {
  files: File[]
  source_language: string
  target_language: string
}): Promise<AdminCurationBatchResponse> {
  const formData = new FormData()
  params.files.forEach((file) => {
    formData.append("files", file)
  })
  formData.append("source_language", params.source_language)
  formData.append("target_language", params.target_language)

  const response = await api.post<AdminCurationBatchResponse>("/papers/admin/curation/uploads", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

export async function getAdminCurationBatch(
  batchId: string,
): Promise<AdminCurationBatchResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<AdminCurationBatchResponse>(`/papers/admin/curation/batches/${batchId}`),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function listAdminCurationJobs(params: {
  status: string
  q: string
}): Promise<AdminCurationJobHistoryResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.get<AdminCurationJobHistoryResponse>("/papers/admin/curation/jobs", {
      params: {
        status: params.status,
        q: params.q,
      },
    }),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function deleteAdminCurationJob(
  jobId: string,
): Promise<AdminDeleteCurationJobResponse> {
  const response = await api.delete<AdminDeleteCurationJobResponse>(`/papers/admin/curation/jobs/${jobId}`)
  return response.data
}

export async function batchDeleteAdminCurationJobs(
  jobIds: string[],
): Promise<AdminBatchDeleteCurationJobsResponse> {
  const response = await api.post<AdminBatchDeleteCurationJobsResponse>(
    "/papers/admin/curation/jobs/batch-delete",
    { job_ids: jobIds },
  )
  return response.data
}

export function getCachedCommunityPaperDetail(paperId: string): CommunityPaperDetailResponse | null {
  return communityPaperDetailCache.get(paperId) ?? null
}

export function primeCommunityPaperDetailCache(
  paperId: string,
  payload: CommunityPaperDetailResponse,
): void {
  communityPaperDetailCache.set(paperId, payload)
}

export function clearCommunityPaperDetailCache(): void {
  communityPaperDetailCache.clear()
  communityPaperDetailInflight.clear()
}

export async function prefetchCommunityPaperDetail(
  paperId: string,
): Promise<CommunityPaperDetailResponse> {
  const cached = communityPaperDetailCache.get(paperId)
  if (cached) {
    return cached
  }

  const inflight = communityPaperDetailInflight.get(paperId)
  if (inflight) {
    return inflight
  }

  const request = getCommunityPaperDetail(paperId).finally(() => {
    communityPaperDetailInflight.delete(paperId)
  })
  communityPaperDetailInflight.set(paperId, request)
  return request
}

export async function recordCommunityPaperView(paperId: string): Promise<void> {
  await api.post(`/papers/${paperId}/view`)
}

export async function submitCommunityPaperFromArxiv(payload: {
  arxiv_id: string
  source_language: string
  target_language: string
}): Promise<CommunityPaperSubmitResponse> {
  const response = await api.post<CommunityPaperSubmitResponse>("/papers/submit", payload)
  return response.data
}

export async function submitCommunityPaperFromUpload(
  file: File,
  payload: {
    source_language: string
    target_language: string
  },
): Promise<CommunityPaperSubmitResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("source_language", payload.source_language)
  formData.append("target_language", payload.target_language)

  const response = await api.post<CommunityPaperSubmitResponse>("/papers/submit", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })
  return response.data
}

export async function translateCommunityPaper(
  paperId: string,
  config: TranslateRequest,
): Promise<CommunityPaperTranslateResponse> {
  const response = await api.post<CommunityPaperTranslateResponse>(`/papers/${paperId}/translate`, config)
  return response.data
}

export async function getCommunityPaperPreview(
  paperId: string,
): Promise<CommunityPaperPreviewResponse> {
  const relativePath = `/api/papers/${paperId}/preview`
  const preferredUrl = `${PAPER_PREVIEW_API_BASE_URL}${relativePath}`
  const fallbackUrl = `${API_BASE_URL}${relativePath}`

  const fetchPreview = async (url: string): Promise<CommunityPaperPreviewResponse> => {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch paper preview: ${response.status}`)
    }

    return (await response.json()) as CommunityPaperPreviewResponse
  }

  try {
    return await retryOnTransientNetworkError(
      () => fetchPreview(preferredUrl),
      { attempts: 3, baseDelayMs: 150 },
    )
  } catch (error) {
    if (preferredUrl === fallbackUrl) {
      throw error
    }

    return await retryOnTransientNetworkError(
      () => fetchPreview(fallbackUrl),
      { attempts: 3, baseDelayMs: 150 },
    )
  }
}

export async function createCommunityPaperDownloadSession(
  paperId: string,
): Promise<CommunityPaperDownloadSessionResponse> {
  const response = await retryOnTransientNetworkError(
    () => api.post<CommunityPaperDownloadSessionResponse>(`/papers/${paperId}/download-session`),
    { attempts: 3, baseDelayMs: 150 },
  )
  return response.data
}

export async function deleteCommunityPaper(
  paperId: string,
): Promise<AdminDeletePaperResponse> {
  const response = await api.delete<AdminDeletePaperResponse>(`/papers/admin/${paperId}`)
  return response.data
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\local-auth.ts
Relative path: lib\local-auth.ts

```ts
import { API_BASE_URL } from "@/api-base"
import { retryOnTransientNetworkError } from "@/lib/network-retry"

export interface LocalAuthUser {
    id: string
    external_provider: string
    external_user_id: string
    roles: string[]
    display_name?: string | null
    email?: string | null
}

export interface LocalAuthSession {
    access_token: string
    token_type: string
    expires_in: number
    user: LocalAuthUser
}

export interface LocalAuthError {
    message: string
    code?: string
    status?: number
}

const SESSION_STORAGE_KEY = "latextrans.localAuth.session"
const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>

const DEFAULT_NIUTRANS_LOGIN_URL = "https://niutrans.com/login?active=0"
const DEFAULT_NIUTRANS_REGISTER_URL = "https://niutrans.com/login?active=3"
const DEFAULT_NIUTRANS_ACCOUNT_URL = "https://niutrans.com/login?active=0"

function isBrowser(): boolean {
    return typeof window !== "undefined"
}

function normalizeUser(input: Partial<LocalAuthUser>): LocalAuthUser | null {
    if (typeof input.id !== "string" || !input.id.trim()) {
        return null
    }

    return {
        id: input.id,
        external_provider: String(input.external_provider ?? "niutrans"),
        external_user_id: String(input.external_user_id ?? ""),
        roles: Array.isArray(input.roles) ? input.roles.map((role) => String(role)) : ["user"],
        display_name: typeof input.display_name === "string" ? input.display_name : null,
        email: typeof input.email === "string" ? input.email : null,
    }
}

function parseErrorPayload(payload: unknown, fallbackMessage: string): LocalAuthError {
    if (!payload || typeof payload !== "object") {
        return { message: fallbackMessage }
    }

    const record = payload as Record<string, unknown>
    return {
        message: typeof record.message === "string" ? record.message : fallbackMessage,
        code: typeof record.code === "string" ? record.code : undefined,
    }
}

export function isLocalAuthConfigured(): boolean {
    return true
}

export function getStoredSession(): LocalAuthSession | null {
    if (!isBrowser()) {
        return null
    }

    const rawValue = window.localStorage.getItem(SESSION_STORAGE_KEY)
    if (!rawValue) {
        return null
    }

    try {
        const parsed = JSON.parse(rawValue) as Partial<LocalAuthSession>
        if (
            typeof parsed.access_token !== "string" ||
            typeof parsed.token_type !== "string" ||
            typeof parsed.expires_in !== "number"
        ) {
            return null
        }

        const user = normalizeUser((parsed.user as Partial<LocalAuthUser>) ?? {})
        if (!user) {
            return null
        }

        return {
            access_token: parsed.access_token,
            token_type: parsed.token_type,
            expires_in: parsed.expires_in,
            user,
        }
    } catch {
        return null
    }
}

export function persistSession(session: LocalAuthSession): void {
    if (!isBrowser()) {
        return
    }
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

export function clearStoredSession(): void {
    if (!isBrowser()) {
        return
    }
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
}

export async function getAccessToken(): Promise<string | null> {
    return getStoredSession()?.access_token ?? null
}

export async function signInWithPassword(
    identifier: string,
    password: string,
): Promise<{ session: LocalAuthSession | null; error: LocalAuthError | null }> {
    try {
        const response = await retryOnTransientNetworkError(
            () =>
                fetch(`${API_BASE_URL}/api/auth/login`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        identifier,
                        password,
                    }),
                }),
            { attempts: 3, baseDelayMs: 150 },
        )

        const payload = await response.json().catch(() => null)
        if (!response.ok) {
            return {
                session: null,
                error: {
                    ...parseErrorPayload(payload, "Unable to sign in."),
                    status: response.status,
                },
            }
        }

        const session = payload as Partial<LocalAuthSession>
        const user = normalizeUser((session.user as Partial<LocalAuthUser>) ?? {})
        if (
            typeof session.access_token !== "string" ||
            typeof session.token_type !== "string" ||
            typeof session.expires_in !== "number" ||
            !user
        ) {
            return {
                session: null,
                error: { message: "Unable to sign in." },
            }
        }

        const nextSession: LocalAuthSession = {
            access_token: session.access_token,
            token_type: session.token_type,
            expires_in: session.expires_in,
            user,
        }
        persistSession(nextSession)
        return { session: nextSession, error: null }
    } catch {
        return {
            session: null,
            error: { message: "Unable to sign in." },
        }
    }
}

export async function bootstrapLocalSession(): Promise<{
    session: LocalAuthSession | null
    user: LocalAuthUser | null
}> {
    const session = getStoredSession()
    if (!session) {
        return { session: null, user: null }
    }

    try {
        const response = await retryOnTransientNetworkError(
            () =>
                fetch(`${API_BASE_URL}/api/auth/me`, {
                    headers: {
                        Authorization: `Bearer ${session.access_token}`,
                        "Content-Type": "application/json",
                    },
                }),
            { attempts: 3, baseDelayMs: 150 },
        )

        const payload = await response.json().catch(() => null)
        const restoredUser = normalizeUser(
            payload && typeof payload === "object" ? ((payload as { user?: Partial<LocalAuthUser> }).user ?? {}) : {},
        )
        if (!response.ok || !restoredUser) {
            clearStoredSession()
            return { session: null, user: null }
        }

        const nextSession: LocalAuthSession = {
            ...session,
            user: restoredUser,
        }
        persistSession(nextSession)
        return { session: nextSession, user: restoredUser }
    } catch {
        clearStoredSession()
        return { session: null, user: null }
    }
}

export async function signOutCurrentSession(accessToken?: string | null): Promise<void> {
    const token = accessToken ?? (await getAccessToken())

    try {
        if (token) {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
            })
        }
    } finally {
        clearStoredSession()
    }
}

export function getNiuTransLoginUrl(): string {
    return viteEnv.VITE_NIUTRANS_LOGIN_URL || DEFAULT_NIUTRANS_LOGIN_URL
}

export function getNiuTransRegisterUrl(): string {
    return viteEnv.VITE_NIUTRANS_REGISTER_URL || DEFAULT_NIUTRANS_REGISTER_URL
}

export function getNiuTransAccountUrl(): string {
    return viteEnv.VITE_NIUTRANS_ACCOUNT_URL || DEFAULT_NIUTRANS_ACCOUNT_URL
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\network-retry.ts
Relative path: lib\network-retry.ts

```ts
import axios from "axios"

const RETRYABLE_AXIOS_CODES = new Set([
  "ECONNABORTED",
  "ECONNRESET",
  "ERR_NETWORK",
  "ETIMEDOUT",
])

const RETRYABLE_FETCH_MESSAGE_PATTERNS = [
  /failed to fetch/i,
  /networkerror/i,
  /connection closed/i,
  /connection reset/i,
  /empty response/i,
  /load failed/i,
]

function sleep(ms: number): Promise<void> {
  if (ms <= 0) {
    return Promise.resolve()
  }
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

export function isTransientNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      return false
    }
    return RETRYABLE_AXIOS_CODES.has(String(error.code || "").toUpperCase())
  }

  if (error instanceof TypeError) {
    return RETRYABLE_FETCH_MESSAGE_PATTERNS.some((pattern) => pattern.test(error.message))
  }

  if (error instanceof Error) {
    const code = String((error as Error & { code?: string }).code || "").toUpperCase()
    if (RETRYABLE_AXIOS_CODES.has(code)) {
      return true
    }
    return RETRYABLE_FETCH_MESSAGE_PATTERNS.some((pattern) => pattern.test(error.message))
  }

  return false
}

export async function retryOnTransientNetworkError<T>(
  operation: () => Promise<T>,
  options: {
    attempts?: number
    baseDelayMs?: number
  } = {},
): Promise<T> {
  const attempts = Math.max(1, options.attempts ?? 3)
  const baseDelayMs = Math.max(0, options.baseDelayMs ?? 200)

  let lastError: unknown
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation()
    } catch (error) {
      lastError = error
      if (attempt >= attempts || !isTransientNetworkError(error)) {
        throw error
      }
      await sleep(baseDelayMs * attempt)
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Retry failed")
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\paper-preview-enhancer.ts
Relative path: lib\paper-preview-enhancer.ts

```ts
type KatexModule = typeof import("katex")
type RenderMathInElement = typeof import("katex/contrib/auto-render").default

export interface PaperPreviewEnhancementContext {
  previewAssetId?: string
  previewSignature: string
}

interface PaperPreviewEnhancer {
  enhance: (element: HTMLElement, context: PaperPreviewEnhancementContext) => void
}

let paperPreviewEnhancerPromise: Promise<PaperPreviewEnhancer> | null = null
let paperPreviewEnhancerStylesPromise: Promise<unknown> | null = null

const READER_MATH_MACROS = {
  "\\mean": "\\operatorname{mean}",
  "\\argmax": "\\operatorname*{arg\\,max}",
  "\\argmin": "\\operatorname*{arg\\,min}",
  "\\trilerp": "\\operatorname{trilerp}",
  "\\softmax": "\\operatorname{softmax}",
  "\\Re": "\\mathbb{R}",
} as const

function normalizeDisplayMathSource(source: string): string {
  const trimmed = source.trim()
  if (trimmed.startsWith("$$") && trimmed.endsWith("$$")) {
    return trimmed.slice(2, -2).trim()
  }
  return trimmed
}

function getPaperPreviewEnhancerOptions() {
  return {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\begin{equation}", right: "\\end{equation}", display: true },
      { left: "\\begin{equation*}", right: "\\end{equation*}", display: true },
      { left: "\\begin{align}", right: "\\end{align}", display: true },
      { left: "\\begin{align*}", right: "\\end{align*}", display: true },
      { left: "\\begin{alignat}", right: "\\end{alignat}", display: true },
      { left: "\\begin{alignat*}", right: "\\end{alignat*}", display: true },
      { left: "\\begin{gather}", right: "\\end{gather}", display: true },
      { left: "\\begin{gather*}", right: "\\end{gather*}", display: true },
      { left: "\\begin{multline}", right: "\\end{multline}", display: true },
      { left: "\\begin{multline*}", right: "\\end{multline*}", display: true },
      { left: "\\begin{eqnarray}", right: "\\end{eqnarray}", display: true },
      { left: "\\begin{eqnarray*}", right: "\\end{eqnarray*}", display: true },
      { left: "\\begin{split}", right: "\\end{split}", display: true },
      { left: "\\begin{CD}", right: "\\end{CD}", display: true },
    ],
    ignoredClasses: ["paper-preview__math-block"],
    macros: READER_MATH_MACROS,
    strict: "ignore",
    throwOnError: false,
  } as Parameters<RenderMathInElement>[1]
}

async function loadPaperPreviewEnhancer(): Promise<PaperPreviewEnhancer> {
  if (!paperPreviewEnhancerStylesPromise) {
    paperPreviewEnhancerStylesPromise = import("katex/dist/katex.min.css")
  }

  if (!paperPreviewEnhancerPromise) {
    paperPreviewEnhancerPromise = Promise.all([
      import("katex") as Promise<KatexModule>,
      import("katex/contrib/auto-render"),
      paperPreviewEnhancerStylesPromise,
    ]).then(([katexModule, autoRenderModule]) => {
      const katex = katexModule.default
      const renderMathInElement = autoRenderModule.default
      const options = getPaperPreviewEnhancerOptions()

      return {
        enhance(element: HTMLElement) {
          element.querySelectorAll<HTMLElement>(".paper-preview__math-block").forEach((block) => {
            const source = normalizeDisplayMathSource(block.textContent || "")
            if (!source) {
              return
            }

            block.innerHTML = katex.renderToString(source, {
              displayMode: true,
              macros: READER_MATH_MACROS,
              strict: "ignore",
              throwOnError: false,
            })
          })
          renderMathInElement(element, options)
        },
      }
    })
  }

  return paperPreviewEnhancerPromise
}

export function preloadPaperPreviewEnhancer(): Promise<PaperPreviewEnhancer> {
  return loadPaperPreviewEnhancer()
}

export async function enhancePaperPreviewElement(
  element: HTMLElement,
  context: PaperPreviewEnhancementContext,
): Promise<void> {
  const enhancer = await loadPaperPreviewEnhancer()
  enhancer.enhance(element, context)
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\paper-reader-html.ts
Relative path: lib\paper-reader-html.ts

```ts
function extractAuthorNames(authors: unknown[]): string {
  return authors
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

function normalizeComparableText(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, " ").trim().toLowerCase()
}

function isDuplicatePaperHeaderElement(
  element: Element,
  normalizedTitle: string,
  normalizedAuthors: string,
) {
  const normalizedText = normalizeComparableText(element.textContent)
  if (!normalizedText) {
    return false
  }

  const containsTitle = Boolean(normalizedTitle) && normalizedText.includes(normalizedTitle)
  const containsAuthors = Boolean(normalizedAuthors) && normalizedText.includes(normalizedAuthors)
  if (containsTitle && containsAuthors) {
    return true
  }

  const childTexts = Array.from(element.children).map((child) => normalizeComparableText(child.textContent))
  const hasTitleChild = Boolean(normalizedTitle) && childTexts.some((text) => text === normalizedTitle)
  const hasAuthorChild = Boolean(normalizedAuthors) && childTexts.some((text) => text === normalizedAuthors)
  return hasTitleChild && hasAuthorChild
}

export interface PaperReaderMetadata {
  title?: string | null
  authors?: unknown[]
}

export function stripLeadingDuplicatePaperHeaderHtml(
  rawHtml: string | null | undefined,
  paper: PaperReaderMetadata | null | undefined,
) {
  if (!rawHtml || typeof DOMParser === "undefined") {
    return rawHtml ?? null
  }

  const parser = new DOMParser()
  const document = parser.parseFromString(rawHtml, "text/html")
  const root = document.body.querySelector("article") ?? document.body
  const normalizedTitle = normalizeComparableText(paper?.title)
  const normalizedAuthors = normalizeComparableText(extractAuthorNames(paper?.authors ?? []))

  let current = root.firstElementChild
  while (current) {
    const normalizedText = normalizeComparableText(current.textContent)
    const isDuplicateTitle = Boolean(normalizedTitle) && normalizedText === normalizedTitle
    const isDuplicateAuthors = Boolean(normalizedAuthors) && normalizedText === normalizedAuthors
    const isDuplicateHeader = isDuplicatePaperHeaderElement(current, normalizedTitle, normalizedAuthors)
    if (!isDuplicateTitle && !isDuplicateAuthors && !isDuplicateHeader) {
      break
    }
    const next = current.nextElementSibling
    current.remove()
    current = next
  }

  return root === document.body ? document.body.innerHTML : root.outerHTML
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\lib\utils.ts
Relative path: lib\utils.ts

```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\main.tsx
Relative path: main.tsx

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'

async function bootstrap() {
  const bootstrapPromise = window.__COMMUNITY_BOOTSTRAP_PROMISE__
  if (bootstrapPromise) {
    await Promise.race([
      bootstrapPromise.catch(() => undefined),
      new Promise((resolve) => window.setTimeout(resolve, 900)),
    ])
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\community-admin-curation-tasks\index.tsx
Relative path: pages\community-admin-curation-tasks\index.tsx

```tsx
import { AdminCurationTasksWorkspace } from "@/features/admin-curation/components/AdminCurationTasksWorkspace"

export default function CommunityAdminCurationTasksPage() {
  return <AdminCurationTasksWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\community-admin-curation\index.tsx
Relative path: pages\community-admin-curation\index.tsx

```tsx
import { AdminCurationWorkspace } from "@/features/admin-curation/components/AdminCurationWorkspace"

export default function CommunityAdminCurationPage() {
  return <AdminCurationWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\community-conversation\index.tsx
Relative path: pages\community-conversation\index.tsx

```tsx
import { CommunityConversationWorkspace } from "@/features/community-conversation/components/CommunityConversationWorkspace"

export default function CommunityConversationPage() {
  return <CommunityConversationWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\home\components\HomeFeedSection.tsx
Relative path: pages\home\components\HomeFeedSection.tsx

```tsx
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import { SectionHeading } from "@/ui/section-heading/SectionHeading"

export function HomeFeedSection({ children }: { children: ReactNode }) {
  const { t } = useTranslation()

  return (
    <section id="home-feed" className="space-y-3">
      <SectionHeading
        eyebrow={t("community.feed.sort.latest")}
        title={t("community.feed.title")}
        description={t("community.feed.officialPriorityHint")}
      />
      {children}
    </section>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\home\index.tsx
Relative path: pages\home\index.tsx

```tsx
import CommunityFeedSurface from "@/features/community-paper/components/CommunityFeedSurface"

export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-2 md:px-6 md:py-3">
      <CommunityFeedSurface />
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\login\index.tsx
Relative path: pages\login\index.tsx

```tsx
import { LoginWorkspace } from "@/features/auth-shell/components/LoginWorkspace"

export default function Login() {
  return <LoginWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\paper-detail\index.tsx
Relative path: pages\paper-detail\index.tsx

```tsx
import { useParams } from "react-router-dom"

import { PaperDetailScreen } from "@/features/community-paper/components/PaperDetailScreen"

export default function PaperDetailPage() {
  const { paperId } = useParams<{ paperId: string }>()
  return <PaperDetailScreen paperId={paperId ?? null} />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\preview\index.tsx
Relative path: pages\preview\index.tsx

```tsx
import { ComparisonWorkbench } from "@/features/translation-workflow/components/ComparisonWorkbench"

export default function PreviewPage() {
  return <ComparisonWorkbench />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\processing\index.tsx
Relative path: pages\processing\index.tsx

```tsx
import { ProcessingWorkspace } from "@/features/translation-workflow/components/ProcessingWorkspace"

export default function ProcessingPage() {
  return <ProcessingWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\profile\index.tsx
Relative path: pages\profile\index.tsx

```tsx
import { ProfileWorkspace } from "@/features/user-workspace/components/ProfileWorkspace"

export default function ProfilePage() {
  return <ProfileWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\tools-hub\index.tsx
Relative path: pages\tools-hub\index.tsx

```tsx
import { ArrowRight, BookOpenText, PenTool, ScrollText } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { PageIntro } from "@/ui/page-intro/PageIntro"

const TOOL_LINKS = [
  {
    key: "translate",
    to: "/translate",
    icon: PenTool,
    descriptionKey: "community.actions.sectionDescription",
  },
  {
    key: "history",
    to: "/workspace/history",
    icon: ScrollText,
    descriptionKey: "history.sign_in_to_view_and_manage_all_translation_task_records",
  },
  {
    key: "glossary",
    to: "/workspace/glossary",
    icon: BookOpenText,
    descriptionKey: "glossary.technical_terms_extracted_from_and_used_in_this_document",
  },
] as const

const ADMIN_LINKS = [
  {
    key: "curation",
    to: "/admin/curation",
    icon: PenTool,
    titleKey: "community.admin.nav.curation",
    descriptionKey: "community.admin.curation.description",
  },
  {
    key: "tasks",
    to: "/admin/curation/tasks",
    icon: ScrollText,
    titleKey: "community.admin.nav.tasks",
    descriptionKey: "community.admin.tasks.description",
  },
] as const

export default function ToolsHubPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const isAdmin = hasAdminRole(user?.roles)

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-5 md:px-6">
      <PanelShell tone="glass" className="space-y-5">
        <PageIntro
          eyebrow={t("community.nav.paperTool", "Paper Tool")}
          title={t("community.nav.paperTool", "Paper Tool")}
          description={t("community.feed.officialPriorityHint")}
          icon={<PenTool className="h-5 w-5" />}
        />

        <div className="grid gap-3 md:grid-cols-3">
          {TOOL_LINKS.map((item) => {
            const Icon = item.icon
            const title =
              item.key === "translate"
                ? t("community.actions.translate")
                : item.key === "history"
                  ? t("history.history")
                  : t("glossary.glossary_management")

            return (
              <Link
                key={item.key}
                to={item.to}
                className="group rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/28 hover:shadow-[0_18px_38px_-30px_rgba(15,23,42,0.35)]"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-accent)]">
                    <Icon className="h-4 w-4" />
                  </span>
                  <ArrowRight className="h-4 w-4 text-[color:var(--px-shell-muted)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[color:var(--px-shell-accent)]" />
                </div>
                <h2 className="mt-4 text-base font-semibold text-[color:var(--px-shell-ink)]">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                  {t(item.descriptionKey)}
                </p>
              </Link>
            )
          })}
        </div>

        {isAdmin ? (
          <div className="space-y-3 border-t border-[color:var(--px-shell-line)] pt-5">
            <PageIntro
              eyebrow={t("community.admin.nav.curation")}
              title={t("community.admin.nav.curation")}
              description={t("community.admin.tasks.description")}
              icon={<ScrollText className="h-5 w-5" />}
            />

            <div className="grid gap-3 md:grid-cols-2">
              {ADMIN_LINKS.map((item) => {
                const Icon = item.icon

                return (
                  <Link
                    key={item.key}
                    to={item.to}
                    className="group rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/28 hover:shadow-[0_18px_38px_-30px_rgba(15,23,42,0.35)]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="flex h-10 w-10 items-center justify-center rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-accent)]">
                        <Icon className="h-4 w-4" />
                      </span>
                      <ArrowRight className="h-4 w-4 text-[color:var(--px-shell-muted)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[color:var(--px-shell-accent)]" />
                    </div>
                    <h2 className="mt-4 text-base font-semibold text-[color:var(--px-shell-ink)]">
                      {t(item.titleKey)}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                      {t(item.descriptionKey)}
                    </p>
                  </Link>
                )
              })}
            </div>
          </div>
        ) : null}
      </PanelShell>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\translate\index.tsx
Relative path: pages\translate\index.tsx

```tsx
import { TranslationWorkspace } from "@/features/translation-workflow/components/TranslationWorkspace"

export default function TranslatePage() {
  return <TranslationWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\workspace-glossary\index.tsx
Relative path: pages\workspace-glossary\index.tsx

```tsx
import { GlossaryWorkspace } from "@/features/user-workspace/components/GlossaryWorkspace"

export default function WorkspaceGlossaryPage() {
  return <GlossaryWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\workspace-history\index.tsx
Relative path: pages\workspace-history\index.tsx

```tsx
import { HistoryWorkspace } from "@/features/user-workspace/components/HistoryWorkspace"

export default function WorkspaceHistoryPage() {
  return <HistoryWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\pages\workspace-settings\index.tsx
Relative path: pages\workspace-settings\index.tsx

```tsx
import { TranslationSettingsWorkspace } from "@/features/user-workspace/components/TranslationSettingsWorkspace"

export default function WorkspaceSettingsPage() {
  return <TranslationSettingsWorkspace />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\styles\tokens.css
Relative path: styles\tokens.css

```css
:root {
  --px-shell-bg: #edf4fb;
  --px-shell-surface: #f5f9fe;
  --px-shell-panel: rgba(250, 253, 255, 0.92);
  --px-shell-panel-strong: #ffffff;
  --px-shell-ink: #0d1b2a;
  --px-shell-muted: #5c6f88;
  --px-shell-line: rgba(13, 27, 42, 0.09);
  --px-shell-line-strong: rgba(13, 27, 42, 0.16);
  --px-shell-accent: #1276c7;
  --px-shell-accent-strong: #0a5da2;
  --px-shell-accent-soft: rgba(18, 118, 199, 0.12);
  --px-shell-accent-contrast: #f4fbff;
  --px-shell-info: #0f766e;
  --px-shell-info-soft: color-mix(in srgb, var(--px-shell-info) 10%, white);
  --px-shell-info-line: color-mix(in srgb, var(--px-shell-info) 18%, transparent);
  --px-shell-success: #0f766e;
  --px-shell-success-soft: color-mix(in srgb, var(--px-shell-success) 10%, white);
  --px-shell-success-line: color-mix(in srgb, var(--px-shell-success) 18%, transparent);
  --px-shell-warning: #9a6700;
  --px-shell-warning-soft: color-mix(in srgb, var(--px-shell-warning) 10%, white);
  --px-shell-warning-line: color-mix(in srgb, var(--px-shell-warning) 18%, transparent);
  --px-shell-danger: #b42318;
  --px-shell-danger-strong: #d92d20;
  --px-shell-danger-soft: color-mix(in srgb, var(--px-shell-danger-strong) 9%, white);
  --px-shell-danger-line: color-mix(in srgb, var(--px-shell-danger-strong) 18%, transparent);
  --px-shell-danger-contrast: #fff8f7;
  --px-shell-shadow: 0 26px 72px -46px rgba(8, 23, 38, 0.28);
  --px-shell-radius-xl: 20px;
  --px-shell-radius-2xl: 28px;
}

.dark {
  --px-shell-bg: #07111c;
  --px-shell-surface: #0a1624;
  --px-shell-panel: rgba(10, 22, 36, 0.94);
  --px-shell-panel-strong: #0f2032;
  --px-shell-ink: #ecf7ff;
  --px-shell-muted: #93abc4;
  --px-shell-line: rgba(236, 247, 255, 0.1);
  --px-shell-line-strong: rgba(236, 247, 255, 0.18);
  --px-shell-accent: #58c9ff;
  --px-shell-accent-strong: #8fe0ff;
  --px-shell-accent-soft: rgba(88, 201, 255, 0.16);
  --px-shell-accent-contrast: #07111c;
  --px-shell-info: #74d9cf;
  --px-shell-info-soft: color-mix(in srgb, var(--px-shell-info) 12%, var(--px-shell-panel-strong));
  --px-shell-info-line: color-mix(in srgb, var(--px-shell-info) 24%, transparent);
  --px-shell-success: #7fe0b7;
  --px-shell-success-soft: color-mix(in srgb, var(--px-shell-success) 12%, var(--px-shell-panel-strong));
  --px-shell-success-line: color-mix(in srgb, var(--px-shell-success) 24%, transparent);
  --px-shell-warning: #f4c26b;
  --px-shell-warning-soft: color-mix(in srgb, var(--px-shell-warning) 12%, var(--px-shell-panel-strong));
  --px-shell-warning-line: color-mix(in srgb, var(--px-shell-warning) 24%, transparent);
  --px-shell-danger: #ffb1a7;
  --px-shell-danger-strong: #ff8f80;
  --px-shell-danger-soft: color-mix(in srgb, var(--px-shell-danger) 12%, var(--px-shell-panel-strong));
  --px-shell-danger-line: color-mix(in srgb, var(--px-shell-danger) 24%, transparent);
  --px-shell-danger-contrast: #07111c;
  --px-shell-shadow: 0 28px 74px -42px rgba(2, 10, 19, 0.72);
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\theme\theme-provider.tsx
Relative path: theme\theme-provider.tsx

```tsx
import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes"

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      disableTransitionOnChange
      storageKey="latextrans-ui-theme-v2"
      {...props}
    >
      {children}
    </NextThemesProvider>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\types\community.ts
Relative path: types\community.ts

```ts
export type CommunityStatus = "official" | "user_fallback"

export type TranslationStatus =
  | "not_started"
  | "queued"
  | "processing"
  | "completed"
  | "failed"

export interface PaperAssetSummary {
  id: string
  task_id: string | null
  asset_type: string
  file_name: string
  mime_type: string
  created_at: string | null
}

export interface ViewerState {
  liked: boolean
  favorited: boolean
}

export interface CommunityPaper {
  id: string
  source: "upload" | "arxiv"
  arxiv_id: string | null
  arxiv_url?: string | null
  github_url?: string | null
  title: string
  authors: unknown[]
  categories: string[]
  abstract_raw?: string | null
  abstract_translated?: string | null
  community_status: CommunityStatus
  trans_status: TranslationStatus
  created_at: string | null
  official_published_at: string | null
  community_selected_task_id: string | null
  community_selected_asset_id: string | null
  visibility?: string
  status?: string
  like_count?: number
  favorite_count?: number
  comment_count?: number
  view_count?: number
  download_count?: number
  latest_asset?: PaperAssetSummary | null
  assets?: Partial<Record<PaperAssetSummary["asset_type"], PaperAssetSummary>> | null
  viewer_state?: ViewerState | null
}

export interface CommunityPaperListResponse {
  items: CommunityPaper[]
  total: number
  offset?: number
  limit?: number | null
  has_more?: boolean
  next_offset?: number | null
  source_mode?: "database" | "baseline_seed"
}

export type CommunityAgentIntent = "search" | "answer" | "translate"
export type CommunityAgentMode = "chat" | "deep_research"

export interface CommunityAgentSkillToggles {
  external_search: boolean
}

export interface CommunityAgentCitation {
  id: string
  title: string
  url?: string | null
  source: string
  arxiv_id?: string | null
  paper_id?: string | null
  anchor_id?: string | null
  snippet?: string | null
}

export interface CommunityAgentToolTrace {
  id: string
  kind: string
  label: string
  provider: string
  status: string
  detail?: string | null
}

export interface CommunityAgentProviderState {
  internal_search: string
  external_search: string
  reasoning: string
  translation_bridge: string
}

export interface CommunityAgentAction {
  type: "navigate_paper" | "open_url"
  paper_id?: string | null
  anchor_id?: string | null
  task_id?: string | null
  url?: string | null
  auto_started_translation?: boolean | null
  reused?: boolean | null
  imported?: boolean | null
}

export interface CommunityAgentReport {
  format: "markdown"
  body_markdown: string
  evidence_count: number
  target_min_evidence: number
  target_max_evidence: number
  context_pack_limit?: number
  timeout_seconds?: number
  partial_coverage: boolean
  coverage_note: string
}

export interface CommunityAgentAcceptedRun {
  run_id: string
  status: "accepted" | "queued" | "running"
  intent?: CommunityAgentIntent | null
  mode?: CommunityAgentMode | null
  message?: string | null
  summary?: string | null
  tool_trace?: CommunityAgentToolTrace[]
  citations?: CommunityAgentCitation[]
  provider_state?: CommunityAgentProviderState | null
  action?: CommunityAgentAction | null
  report?: CommunityAgentReport | null
  stream_url: string
  result_url: string
}

export interface CommunityAgentRun {
  run_id: string
  status: "accepted" | "queued" | "running" | "completed" | "failed"
  intent?: CommunityAgentIntent | null
  mode?: CommunityAgentMode | null
  message?: string | null
  summary?: string | null
  tool_trace?: CommunityAgentToolTrace[]
  citations?: CommunityAgentCitation[]
  provider_state?: CommunityAgentProviderState | null
  action?: CommunityAgentAction | null
  report?: CommunityAgentReport | null
  stream_url?: string | null
  result_url?: string | null
}

export type CommunityAgentStreamEventType =
  | "status"
  | "assistant_delta"
  | "tool_start"
  | "tool_result"
  | "citation"
  | "action"
  | "complete"
  | "error"
  | "heartbeat"

export interface CommunityAgentStreamEvent {
  type: CommunityAgentStreamEventType
  run_id?: string
  sequence?: number
  timestamp?: string
  data: Record<string, unknown>
}

export type CommunityConversationTurnRole = "user" | "assistant"

export interface CommunityConversationTurn {
  id: string
  role: CommunityConversationTurnRole
  content: string
  created_at: string
  run?: CommunityAgentRun | null
  status?: "running" | "completed" | "failed"
  error?: string | null
}

export interface CommunityConversationRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  turns: CommunityConversationTurn[]
}

export type CommunityPaperReaderMode =
  | "source"
  | "translated"
  | "translated_html"
  | "translated_pdf"
  | "bilingual_compare"
export type CommunityPaperReaderState =
  | "source_ready"
  | "translated_ready"
  | "warming"
  | "unavailable"
export type CommunityPaperFailureType =
  | "source_unavailable"
  | "queue_busy"
  | "translation_failed"
  | "external_search_unavailable"

export interface CommunityPaperReaderAnchor {
  anchor_id: string
  kind: "section" | "block" | "anchor" | string
  label?: string | null
}

export interface CommunityPaperExperience {
  stage_label: string
  can_leave_hint?: string | null
  failure_type?: CommunityPaperFailureType | null
}

export interface CommunityPaperReaderResource {
  kind: "source_html" | "source_pdf" | "external_arxiv_html" | "preview_html" | "translated_pdf"
  html_content?: string | null
  url?: string | null
  anchors?: CommunityPaperReaderAnchor[]
}

export interface CommunityPaperReader {
  preferred_mode: CommunityPaperReaderMode
  available_modes: CommunityPaperReaderMode[]
  source?: CommunityPaperReaderResource | null
  translated?: CommunityPaperReaderResource | null
  active_anchor_id?: string | null
  state: CommunityPaperReaderState
}

export interface ReaderSelectionContext {
  text: string
  anchor_id: string | null
  mode: CommunityPaperReaderMode
  position?: { x: number, y: number }
  range?: Range
  color?: string
  note?: string
}

export interface PaperAnnotation {
  id: string
  text: string
  range: Range
  anchor_id: string | null
  mode: CommunityPaperReaderMode
  color: string
  note: string
}

export interface PaperAnnotationOverlayRect {
  id: string
  color: string
  top: number
  left: number
  width: number
  height: number
}

export interface StructuredInsightSection {
  section_key: StructuredInsightSectionKey
  content?: string | null
  raw_content?: string | null
  summary?: string | null
  blocks?: StructuredInsightBlock[] | null
  status?: string | null
  updated_at?: string | null
}

export interface StructuredInsightBlock {
  heading: string
  content: string
}

export const STRUCTURED_INSIGHT_SECTION_KEYS = [
  "problem",
  "solution",
  "innovation",
  "experiment",
  "future",
] as const

export type StructuredInsightSectionKey = (typeof STRUCTURED_INSIGHT_SECTION_KEYS)[number]

export interface StructuredInsightsPayload {
  state: string
  sections: StructuredInsightSection[]
}

export interface CommunityPaperDetailResponse {
  paper: CommunityPaper
  preview?: CommunityPaperPreviewResponse | null
  reader_state?: "ready" | "warming" | "unavailable"
  reader?: CommunityPaperReader | null
  experience?: CommunityPaperExperience | null
  structured_insights?: StructuredInsightsPayload | null
}

export interface CommunityPaperSimilarItem {
  arxiv_id: string
  title: string
  abstract: string
  arxiv_url: string
  community_paper_id?: string | null
  link_type: "community" | "arxiv" | string
}

export interface CommunityPaperSimilarResponse {
  items: CommunityPaperSimilarItem[]
}

export interface CommunityPaperSubmitResponse {
  paper: CommunityPaper
  task: {
    task_id: string | null
    status: string | null
  }
  admission_result: string
}

export interface CommunityPaperTranslateResponse {
  paper_id: string
  task_id: string
  status: string
  reused_existing_task: boolean
  processing_url: string
}

export interface CommunityPaperPreviewResponse {
  paper_id: string
  task_id: string | null
  asset: PaperAssetSummary
  html_content?: string | null
  generated_at: string | null
  fetch_url?: string | null
}

export interface CommunityPaperDownloadSessionResponse {
  paper_id: string
  asset_id: string
  download_url: string
  expires_at: string
}

export interface AdminCurationBatchItem {
  job_id: string
  paper_id?: string | null
  source_type: string
  arxiv_id?: string | null
  original_filename?: string | null
  status: string
  error?: string | null
}

export interface AdminCurationBatchResponse {
  batch_id: string
  status: string
  items: AdminCurationBatchItem[]
}

export interface AdminCurationJobHistoryItem {
  job_id: string
  batch_id: string
  paper_id?: string | null
  published_paper_id?: string | null
  task_id?: string | null
  source_type: string
  arxiv_id?: string | null
  original_filename?: string | null
  status: string
  terminal_task_status?: string | null
  error?: string | null
  failed_artifact_path?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface AdminCurationJobHistoryResponse {
  items: AdminCurationJobHistoryItem[]
  total: number
}

export interface AdminDeletePaperResponse {
  job_id: string
  paper_id: string
  status: string
}

export interface AdminDeleteCurationJobResponse {
  job_id: string
  paper_id?: string | null
  status: string
}

export interface AdminBatchDeleteCurationJobsFailure {
  job_id: string
  status_code: number
  detail?: string | null
}

export interface AdminBatchDeleteCurationJobsResponse {
  deleted: AdminDeleteCurationJobResponse[]
  failed: AdminBatchDeleteCurationJobsFailure[]
  deleted_count: number
  failed_count: number
}

export interface CommunityPaperImportRequest {
  source: "arxiv"
  arxiv_id: string
}

export interface CommunityPaperImportResponse {
  paper_id: string
  reused: boolean
  imported: boolean
  reader_state: CommunityPaperReaderState
}

export type CommunityFeedSort = "latest" | "translated" | "hot"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\types\config.ts
Relative path: types\config.ts

```ts
/**
 * Translation Configuration Types
 * 
 * Type definitions for advanced translation configuration.
 * All configuration options are optional - users can translate without configuring anything.
 */

/** Translation mode options - 只保留全文翻译和快速筛查 */
export type TranslationMode = 'full' | 'quick_scan'

/** LaTeX compile strategy options */
export type CompileStrategy = 'pdflatex' | 'xelatex' | 'lualatex' | 'auto'

/**
 * Typography formatting configuration.
 * All fields default to undefined (keep original LaTeX source).
 */
export interface FormattingConfig {
    /** Line spacing multiplier, e.g. 1.5 */
    line_spacing?: number
    /** Font size in pt, e.g. 12 */
    font_size?: number
    /** CJK font preset: 'songti' | 'heiti' */
    cjk_font?: string
    /** Column layout: 'single' | 'double' */
    column_mode?: string
    /** Page margin preset: 'narrow' | 'normal' | 'wide' */
    margin?: string
    /** Enable 2em paragraph indent (CJK convention) */
    paragraph_indent?: boolean
    /** Bibliography style: 'gbt7714-numerical' | 'gbt7714-author-year' | 'ieeetr' | 'apalike' */
    bib_style?: string
    /** Citation style: 'numbers' | 'super' | 'authoryear' */
    cite_style?: string
    /** Localize figure/table captions */
    localize_captions?: boolean
}

/**
 * Advanced configuration options.
 * 
 * These options control translation behavior and API configuration.
 * All fields have sensible defaults.
 */
export interface AdvancedConfig {
    /** Translation mode: full document or quick_scan (abstract + conclusion only) */
    translation_mode: TranslationMode
    /** LaTeX compile strategy */
    compile_strategy: CompileStrategy
    /** Generate terminology reference table (CSV) */
    generate_terminology_table: boolean
    /** Translation LLM model name */
    translation_model: string
    /** Use author's API (default). When true, custom settings are ignored */
    use_author_api: boolean
    /** Custom API base URL (e.g., https://aicanapi.com) */
    custom_base_url?: string
    /** Custom API key */
    custom_api_key?: string
    /** Typography formatting for LaTeX preamble injection */
    formatting?: FormattingConfig
    /** Send email notification when task completes or fails */
    email_notification?: boolean
}

/**
 * Complete translation configuration including language settings.
 */
export interface TranslationConfig {
    /** Source language code */
    source_language: string
    /** Target language code */
    target_language: string
    /** Advanced configuration options */
    advanced_config: AdvancedConfig
}

/**
 * Default advanced configuration.
 * Users can start translating immediately without changing these.
 */
export const DEFAULT_ADVANCED_CONFIG: AdvancedConfig = {
    translation_mode: 'full',
    compile_strategy: 'auto',
    generate_terminology_table: true,  // 默认启用术语表生成
    translation_model: 'deepseek-ai/deepseek-v3.2',
    use_author_api: true,
    custom_base_url: undefined,
    custom_api_key: undefined,
    email_notification: undefined,
}

/**
 * Default translation configuration.
 */
export const DEFAULT_CONFIG: TranslationConfig = {
    source_language: 'en',
    target_language: 'zh',
    advanced_config: { ...DEFAULT_ADVANCED_CONFIG }
}

/**
 * LaTeX validation result from upload.
 */
export interface LatexValidation {
    is_valid: boolean
    main_file?: string
    tex_files: string[]
    warnings: string[]
    errors: string[]
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\types\katex-auto-render.d.ts
Relative path: types\katex-auto-render.d.ts

```ts
declare module "katex/contrib/auto-render" {
  interface DelimiterConfig {
    left: string
    right: string
    display: boolean
  }

  interface AutoRenderOptions {
    delimiters?: DelimiterConfig[]
    throwOnError?: boolean
  }

  export default function renderMathInElement(
    element: Element,
    options?: AutoRenderOptions,
  ): void
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\button\Button.tsx
Relative path: ui\button\Button.tsx

```tsx
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 disabled:pointer-events-none disabled:opacity-55 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent)] text-white shadow-[var(--px-shell-shadow)] hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent-strong)] hover:bg-[color:var(--px-shell-accent-strong)]",
        outline:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/30 hover:text-[color:var(--px-shell-accent)]",
        secondary:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] hover:-translate-y-0.5 hover:bg-[color:var(--px-shell-panel)]",
        ghost:
          "border-transparent bg-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
        ink:
          "border-[color:var(--px-shell-ink)] bg-[color:var(--px-shell-ink)] text-[color:var(--px-shell-surface)] hover:-translate-y-0.5 hover:opacity-95",
        destructive:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-strong)] text-[color:var(--px-shell-danger-contrast)] hover:-translate-y-0.5 hover:bg-[color:var(--px-shell-danger)]",
        action:
          "border-[color:color-mix(in_srgb,var(--px-shell-accent)_72%,white)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent)_60%,white),var(--px-shell-accent))] text-white shadow-[0_14px_28px_-18px_rgba(35,169,255,0.55)] hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent-strong)] hover:bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent)_42%,white),var(--px-shell-accent-strong))] hover:text-white hover:shadow-[0_18px_36px_-20px_rgba(35,169,255,0.62)]",
      },
      size: {
        default: "min-h-11 px-5 py-2.5",
        sm: "min-h-9 px-4 py-2 text-xs uppercase tracking-[0.16em]",
        lg: "min-h-12 px-6 py-3",
        chip: "min-h-9 px-3.5 py-2 text-[11px] uppercase tracking-[0.14em]",
        icon: "h-10 w-10 rounded-full p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"

    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    )
  },
)

Button.displayName = "Button"

export { Button, buttonVariants }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\card\Card.tsx
Relative path: ui\card\Card.tsx

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const cardVariants = cva(
  "rounded-[28px] border shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      variant: {
        panel: "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)]",
        strong:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]",
        soft: "border-[color:var(--px-shell-line)] bg-white/78 text-[color:var(--px-shell-ink)]",
        ink: "border-[color:var(--px-shell-ink)] bg-[color:var(--px-shell-ink)] text-[color:var(--px-shell-surface)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)] shadow-none",
      },
      padding: {
        default: "",
        compact: "",
      },
    },
    defaultVariants: {
      variant: "panel",
      padding: "default",
    },
  },
)

type CardProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof cardVariants>

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding }), className)}
      {...props}
    />
  ),
)

Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col gap-2 border-b border-[color:var(--px-shell-line)] px-6 py-5", className)}
    {...props}
  />
))

CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-lg font-black leading-tight tracking-[-0.02em]", className)}
    {...props}
  />
))

CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm leading-6 text-[color:var(--px-shell-muted)]", className)}
    {...props}
  />
))

CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("px-6 py-5", className)} {...props} />
))

CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center gap-3 border-t border-[color:var(--px-shell-line)] px-6 py-5", className)}
    {...props}
  />
))

CardFooter.displayName = "CardFooter"

export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\chat-bubble\ChatBubble.tsx
Relative path: ui\chat-bubble\ChatBubble.tsx

```tsx
import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const chatBubbleVariants = cva(
  "w-full whitespace-pre-wrap border px-5 py-4 text-[15px] leading-relaxed",
  {
    variants: {
      speaker: {
        assistant:
          "rounded-[22px] rounded-bl-none border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-[0_4px_20px_rgba(27,28,28,0.03)]",
        user:
          "rounded-[22px] rounded-br-none border-[color:var(--px-shell-accent)]/20 bg-[linear-gradient(135deg,var(--px-shell-accent),var(--px-shell-accent-strong))] text-white shadow-[0_8px_24px_rgba(182,23,34,0.15)]",
      },
    },
    defaultVariants: {
      speaker: "assistant",
    },
  },
)

interface ChatBubbleProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof chatBubbleVariants> {}

export function ChatBubble({
  speaker,
  className,
  ...props
}: ChatBubbleProps) {
  return (
    <div
      className={cn(chatBubbleVariants({ speaker }), className)}
      {...props}
    />
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\composer-shell\ComposerShell.tsx
Relative path: ui\composer-shell\ComposerShell.tsx

```tsx
import type { FormHTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

interface ComposerShellProps extends Omit<FormHTMLAttributes<HTMLFormElement>, "title"> {
  toolbar?: ReactNode
  actionSlot?: ReactNode
  footer?: ReactNode
  bodyClassName?: string
}

export function ComposerShell({
  toolbar,
  actionSlot,
  footer,
  bodyClassName,
  className,
  children,
  ...props
}: ComposerShellProps) {
  return (
    <form
      className={cn(
        "rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[0_8px_30px_rgba(27,28,28,0.06)] transition-all focus-within:border-[color:var(--px-shell-accent)]/30 focus-within:ring-1 focus-within:ring-[color:var(--px-shell-accent)]/10",
        className,
      )}
      {...props}
    >
      {toolbar ? (
        <div className="border-b border-[color:var(--px-shell-line)]/70 px-4 py-3">
          {toolbar}
        </div>
      ) : null}

      <div className={cn("relative flex items-end gap-2 p-2", bodyClassName)}>
        <div className="min-w-0 flex-1">{children}</div>
        {actionSlot ? (
          <div className="flex shrink-0 items-center gap-1 pb-1 pr-1">
            {actionSlot}
          </div>
        ) : null}
      </div>

      {footer ? (
        <div className="border-t border-[color:var(--px-shell-line)]/70 px-4 py-2.5">
          {footer}
        </div>
      ) : null}
    </form>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\data-table\DataTable.tsx
Relative path: ui\data-table\DataTable.tsx

```tsx
import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

export function DataTable({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]",
        className,
      )}
      {...props}
    />
  )
}

export function DataTableHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "border-b border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)]",
        className,
      )}
      {...props}
    />
  )
}

export function DataTableHeaderRow({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("grid gap-4 px-6 py-4", className)}
      {...props}
    />
  )
}

export function DataTableHeaderCell({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "text-[10px] font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]",
        className,
      )}
      {...props}
    />
  )
}

export function DataTableBody({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("divide-y divide-[color:var(--px-shell-line)]/60", className)}
      {...props}
    />
  )
}

export function DataTableRow({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("grid gap-4 px-4 py-4 sm:px-6 sm:py-4", className)}
      {...props}
    />
  )
}

export function DataTableCell({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("min-w-0", className)} {...props} />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\disclosure-card\DisclosureCard.tsx
Relative path: ui\disclosure-card\DisclosureCard.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/ui/primitives/collapsible"

interface DisclosureCardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  eyebrow?: ReactNode
  description?: ReactNode
  headerAside?: ReactNode
  contentClassName?: string
}

export function DisclosureCard({
  open,
  onOpenChange,
  title,
  eyebrow,
  description,
  headerAside,
  contentClassName,
  className,
  children,
  ...props
}: DisclosureCardProps) {
  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <div
        className={cn(
          "overflow-hidden rounded-none border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-none",
          className,
        )}
        {...props}
      >
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-start justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
          >
            <div className="min-w-0 flex-1 space-y-1.5">
              {eyebrow ? (
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[color:var(--px-shell-muted)]">
                  {eyebrow}
                </div>
              ) : null}
              <div className="text-sm font-semibold text-[color:var(--px-shell-ink)]">{title}</div>
              {description ? (
                <div className="text-xs leading-6 text-[color:var(--px-shell-muted)]">{description}</div>
              ) : null}
            </div>

            <div className="flex shrink-0 items-center gap-3 pl-2">
              {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
              {open ? (
                <ChevronUp className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
              ) : (
                <ChevronDown className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
              )}
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t border-[color:var(--px-shell-line)]">
          <div className={cn("px-4 py-4 text-sm text-[color:var(--px-shell-muted)]", contentClassName)}>
            {children}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\filter-toolbar\FilterToolbar.tsx
Relative path: ui\filter-toolbar\FilterToolbar.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"

import { Button } from "@/ui/button/Button"
import { cn } from "@/lib/utils"

interface FilterToolbarOption {
  value: string
  label: ReactNode
  icon?: ReactNode
}

interface FilterToolbarProps extends HTMLAttributes<HTMLDivElement> {
  options: FilterToolbarOption[]
  value: string
  onValueChange: (value: string) => void
  meta?: ReactNode
  actions?: ReactNode
}

export function FilterToolbar({
  options,
  value,
  onValueChange,
  meta,
  actions,
  className,
  ...props
}: FilterToolbarProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-b border-[color:var(--px-shell-line)] pb-3 lg:flex-row lg:items-center lg:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="inline-flex flex-wrap gap-2 rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-1 shadow-[0_12px_28px_rgba(15,23,42,0.05)]">
          {options.map((option) => {
            const active = option.value === value

            return (
              <Button
                key={option.value}
                type="button"
                variant={active ? "secondary" : "ghost"}
                onClick={() => onValueChange(option.value)}
                className={cn(
                  "min-h-10 rounded-full px-4 py-2 text-sm",
                  active
                    ? "bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)] shadow-[inset_0_0_0_1px_rgba(18,118,199,0.16)]"
                    : "text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-panel)] hover:text-[color:var(--px-shell-ink)]",
                )}
                aria-pressed={active}
              >
                {option.icon ? <span className="flex items-center">{option.icon}</span> : null}
                <span>{option.label}</span>
              </Button>
            )
          })}
        </div>

        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>

      {meta ? <div className="flex flex-wrap items-center gap-3">{meta}</div> : null}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\form-field-shell\FormFieldShell.tsx
Relative path: ui\form-field-shell\FormFieldShell.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const formFieldShellVariants = cva(
  "rounded-[20px] border transition-colors duration-200",
  {
    variants: {
      tone: {
        panel:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] hover:bg-[color:var(--px-shell-panel)]",
        muted:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)]",
      },
      size: {
        default: "p-3",
        compact: "px-3 py-2.5",
      },
    },
    defaultVariants: {
      tone: "panel",
      size: "default",
    },
  },
)

interface FormFieldShellProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof formFieldShellVariants> {
  label: ReactNode
  icon?: ReactNode
  description?: ReactNode
  headerAside?: ReactNode
  labelClassName?: string
  descriptionClassName?: string
  bodyClassName?: string
}

export function FormFieldShell({
  label,
  icon,
  description,
  headerAside,
  tone,
  size,
  className,
  labelClassName,
  descriptionClassName,
  bodyClassName,
  children,
  ...props
}: FormFieldShellProps) {
  return (
    <div
      className={cn(formFieldShellVariants({ tone, size }), className)}
      {...props}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {icon ? (
              <span className="text-[color:var(--px-shell-muted)]">{icon}</span>
            ) : null}
            <div className={cn("text-sm font-medium text-[color:var(--px-shell-ink)]", labelClassName)}>
              {label}
            </div>
          </div>
          {description ? (
            <div className={cn("mt-1 text-xs text-[color:var(--px-shell-muted)]", descriptionClassName)}>
              {description}
            </div>
          ) : null}
        </div>

        {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
      </div>

      <div className={cn("mt-2", bodyClassName)}>
        {children}
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\info-tile\InfoTile.tsx
Relative path: ui\info-tile\InfoTile.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const infoTileVariants = cva(
  "rounded-[22px] border",
  {
    variants: {
      tone: {
        panel:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]",
        muted:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)]",
        accent:
          "border-[color:var(--px-shell-accent)]/15 bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-ink)]",
        warning:
          "border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] text-[color:var(--px-shell-ink)]",
        success:
          "border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-ink)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-ink)]",
      },
      size: {
        default: "px-4 py-3",
        compact: "px-3 py-2.5",
      },
    },
    defaultVariants: {
      tone: "panel",
      size: "default",
    },
  },
)

interface InfoTileProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof infoTileVariants> {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  value?: ReactNode
  trailing?: ReactNode
  titleClassName?: string
  valueClassName?: string
}

export function InfoTile({
  icon,
  title,
  description,
  value,
  trailing,
  tone,
  size,
  className,
  titleClassName,
  valueClassName,
  children,
  ...props
}: InfoTileProps) {
  return (
    <div
      className={cn(infoTileVariants({ tone, size }), className)}
      {...props}
    >
      <div className="flex items-start gap-3">
        {icon ? (
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_78%,white)] text-[color:var(--px-shell-accent)] shadow-sm">
            {icon}
          </div>
        ) : null}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-1">
              <div
                className={cn(
                  "text-xs font-bold uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]",
                  titleClassName,
                )}
              >
                {title}
              </div>
              {description ? (
                <div className="text-sm leading-6 text-[color:var(--px-shell-ink)]">
                  {description}
                </div>
              ) : null}
            </div>

            {value || trailing ? (
              <div className="flex shrink-0 items-center gap-3">
                {value ? (
                  <div
                    className={cn(
                      "text-right text-sm font-semibold text-[color:var(--px-shell-ink)]",
                      valueClassName,
                    )}
                  >
                    {value}
                  </div>
                ) : null}
                {trailing}
              </div>
            ) : null}
          </div>

          {children ? <div className="mt-3">{children}</div> : null}
        </div>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\input\Input.tsx
Relative path: ui\input\Input.tsx

```tsx
import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex min-h-11 w-full rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)] px-4 py-2 text-base text-[color:var(--px-shell-ink)] shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/15 disabled:cursor-not-allowed disabled:opacity-50 file:mr-3 file:rounded-full file:border-0 file:bg-[color:var(--px-shell-accent-soft)] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-[color:var(--px-shell-accent)] placeholder:text-[color:var(--px-shell-muted)] md:text-sm",
        className,
      )}
      {...props}
    />
  ),
)

Input.displayName = "Input"

export { Input }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\input\Textarea.tsx
Relative path: ui\input\Textarea.tsx

```tsx
import * as React from "react"

import { cn } from "@/lib/utils"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[140px] w-full resize-none rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)] px-5 py-4 text-base text-[color:var(--px-shell-ink)] shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/15 disabled:cursor-not-allowed disabled:opacity-50 placeholder:text-[color:var(--px-shell-muted)]",
      className,
    )}
    {...props}
  />
))

Textarea.displayName = "Textarea"

export { Textarea }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\interactive-card\InteractiveCard.tsx
Relative path: ui\interactive-card\InteractiveCard.tsx

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const interactiveCardVariants = cva(
  "group w-full rounded-[24px] border text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      tone: {
        panel:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-line-strong)] hover:bg-[color:var(--px-shell-panel-strong)] hover:shadow-[0_14px_34px_rgba(15,23,42,0.06)]",
        strong:
          "border-[color:var(--px-shell-line)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel-strong)_94%,white),color-mix(in_srgb,var(--px-shell-accent-soft)_38%,white))] text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-line-strong)] hover:shadow-[0_18px_46px_rgba(15,23,42,0.08)]",
        selected:
          "border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-[0_16px_40px_rgba(15,23,42,0.06)]",
        ghost:
          "border-transparent bg-transparent text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel)]",
      },
      size: {
        sm: "px-4 py-3",
        md: "px-4 py-4",
        lg: "px-6 py-6",
      },
    },
    defaultVariants: {
      tone: "panel",
      size: "md",
    },
  },
)

export interface InteractiveCardProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof interactiveCardVariants> {
  element?: "button" | "div"
}

export const InteractiveCard = React.forwardRef<HTMLButtonElement, InteractiveCardProps>(
  ({ className, tone, size, type = "button", element = "button", ...props }, ref) => {
    if (element === "div") {
      return (
        <div
          className={cn(interactiveCardVariants({ tone, size }), className)}
          {...(props as React.HTMLAttributes<HTMLDivElement>)}
        />
      )
    }

    return (
      <button
        ref={ref}
        type={type}
        className={cn(interactiveCardVariants({ tone, size }), className)}
        {...props}
      />
    )
  },
)

InteractiveCard.displayName = "InteractiveCard"

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\language-selector\LanguageSelector.tsx
Relative path: ui\language-selector\LanguageSelector.tsx

```tsx
import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/ui/primitives/select"
import { UI_LANGUAGES, persistLanguage, type UILanguage } from "@/i18n/config"

export function LanguageSelector() {
  const { i18n, t } = useTranslation()
  const currentLanguage = (i18n.resolvedLanguage ?? i18n.language) as UILanguage

  const handleValueChange = async (language: string) => {
    const nextLanguage = language as UILanguage
    persistLanguage(nextLanguage)
    await i18n.changeLanguage(nextLanguage)
  }

  return (
    <Select value={currentLanguage} onValueChange={handleValueChange}>
      <SelectTrigger
        aria-label={t("common.choose_global_interface_language")}
        className="h-11 w-[176px] rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] pr-2 text-sm text-[color:var(--px-shell-ink)] shadow-sm transition-colors hover:bg-[color:var(--px-shell-panel)] focus:ring-2 focus:ring-[color:var(--px-shell-accent)]/20"
      >
        <div className="flex items-center gap-2">
          <Languages className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="min-w-[176px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]">
        {UI_LANGUAGES.map((language) => (
          <SelectItem
            key={language.code}
            value={language.code}
            className="cursor-pointer focus:bg-[color:var(--px-shell-accent-soft)] focus:text-[color:var(--px-shell-ink)]"
          >
            <div className="flex items-center gap-2">
              <span className="font-medium">{language.nativeLabel}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\loading-state\LoadingState.tsx
Relative path: ui\loading-state\LoadingState.tsx

```tsx
import { Loader2 } from "lucide-react"
import { cva, type VariantProps } from "class-variance-authority"
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

const loadingStateVariants = cva("text-[color:var(--px-shell-muted)]", {
  variants: {
    layout: {
      inline: "flex items-center justify-center gap-3",
      panel:
        "rounded-[28px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] px-6 py-10 text-center shadow-[var(--px-shell-shadow)]",
    },
  },
  defaultVariants: {
    layout: "inline",
  },
})

interface LoadingStateProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof loadingStateVariants> {
  label: ReactNode
  description?: ReactNode
}

export function LoadingState({
  label,
  description,
  layout = "inline",
  className,
  ...props
}: LoadingStateProps) {
  if (layout === "panel") {
    return (
      <div className={cn(loadingStateVariants({ layout }), className)} {...props}>
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-accent)]">
          <Loader2 data-testid="loading-state-spinner" className="h-6 w-6 animate-spin" />
        </div>
        <div className="mx-auto mt-4 max-w-xl space-y-2">
          <p className="text-lg font-semibold text-[color:var(--px-shell-ink)]">{label}</p>
          {description ? (
            <p className="text-sm leading-6 text-[color:var(--px-shell-muted)]">{description}</p>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className={cn(loadingStateVariants({ layout }), className)} {...props}>
      <Loader2 data-testid="loading-state-spinner" className="h-5 w-5 animate-spin text-[color:var(--px-shell-accent)]" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-[color:var(--px-shell-ink)]">{label}</p>
        {description ? (
          <p className="text-xs leading-5 text-[color:var(--px-shell-muted)]">{description}</p>
        ) : null}
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\notice-banner\NoticeBanner.tsx
Relative path: ui\notice-banner\NoticeBanner.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const noticeBannerVariants = cva(
  "flex items-start gap-3 rounded-xl border px-4 py-3",
  {
    variants: {
      tone: {
        neutral:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]",
        info:
          "border-[color:var(--px-shell-info-line)] bg-[color:var(--px-shell-info-soft)] text-[color:var(--px-shell-info)]",
        warning:
          "border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] text-[color:var(--px-shell-warning)]",
        success:
          "border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-success)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  },
)

interface NoticeBannerProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof noticeBannerVariants> {
  icon?: ReactNode
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
}

export function NoticeBanner({
  icon,
  title,
  description,
  action,
  tone,
  className,
  children,
  ...props
}: NoticeBannerProps) {
  return (
    <div className={cn(noticeBannerVariants({ tone }), className)} {...props}>
      {icon ? <div className="mt-0.5 shrink-0">{icon}</div> : null}

      <div className="min-w-0 flex-1 space-y-1">
        {title ? <p className="text-sm font-semibold text-current">{title}</p> : null}
        {description ? (
          <div className="text-sm leading-6 text-current/90">
            {description}
          </div>
        ) : null}
        {children}
      </div>

      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\page-intro\PageIntro.tsx
Relative path: ui\page-intro\PageIntro.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

interface PageIntroProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  meta?: ReactNode
  actions?: ReactNode
}

export function PageIntro({
  eyebrow,
  title,
  description,
  icon,
  meta,
  actions,
  className,
  ...props
}: PageIntroProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-[color:var(--px-shell-line)] pb-5 lg:flex-row lg:items-start lg:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <div className="rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-3 text-[color:var(--px-shell-ink)]">
            {icon}
          </div>
        ) : null}

        <div className="min-w-0 space-y-1.5">
          {eyebrow ? (
            <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
            {title}
          </h1>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-[color:var(--px-shell-muted)]">
              {description}
            </p>
          ) : null}
          {meta ? (
            <div className="text-xs text-[color:var(--px-shell-muted)]">
              {meta}
            </div>
          ) : null}
        </div>
      </div>

      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      ) : null}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\panel-shell\PanelShell.tsx
Relative path: ui\panel-shell\PanelShell.tsx

```tsx
import { createElement, type HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const panelShellVariants = cva(
  "border text-[color:var(--px-shell-ink)]",
  {
    variants: {
      tone: {
        panel:
          "rounded-[28px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]",
        glass:
          "rounded-[30px] border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_92%,white)] shadow-[0_22px_55px_rgba(15,23,42,0.08)] backdrop-blur-sm",
        hero:
          "rounded-[28px] border-[color:var(--px-shell-line)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel)_92%,white),color-mix(in_srgb,var(--px-shell-panel-strong)_86%,var(--px-shell-surface)))] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        accent:
          "rounded-[28px] border-[color:var(--px-shell-accent)]/18 bg-[color:var(--px-shell-accent-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        success:
          "rounded-[28px] border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        warning:
          "rounded-[28px] border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        danger:
          "rounded-[28px] border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
      },
      padding: {
        none: "",
        default: "px-5 py-5",
        compact: "px-4 py-4",
      },
    },
    defaultVariants: {
      tone: "panel",
      padding: "default",
    },
  },
)

interface PanelShellProps
  extends HTMLAttributes<HTMLElement>,
    VariantProps<typeof panelShellVariants> {
  as?: "div" | "section" | "aside"
}

export function PanelShell({
  as = "div",
  tone,
  padding,
  className,
  ...props
}: PanelShellProps) {
  return createElement(as, {
    className: cn(panelShellVariants({ tone, padding }), className),
    ...props,
  })
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\pill\Pill.tsx
Relative path: ui\pill\Pill.tsx

```tsx
import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const pillVariants = cva(
  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.18em]",
  {
    variants: {
      tone: {
        muted:
          "border-[color:var(--px-shell-line)] bg-white/70 text-[color:var(--px-shell-muted)]",
        accent:
          "border-[color:var(--px-shell-accent)]/20 bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]",
        ink: "border-transparent bg-[color:var(--px-shell-ink)] text-[color:var(--px-shell-surface)]",
      },
    },
    defaultVariants: {
      tone: "muted",
    },
  },
)

type PillProps = HTMLAttributes<HTMLDivElement> & VariantProps<typeof pillVariants>

export function Pill({ className, tone, ...props }: PillProps) {
  return <div className={cn(pillVariants({ tone }), className)} {...props} />
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\alert-dialog.tsx
Relative path: ui\primitives\alert-dialog.tsx

```tsx
import * as React from "react"
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog"
import { type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { buttonVariants } from "@/ui/button/Button"

const AlertDialog = AlertDialogPrimitive.Root

const AlertDialogTrigger = AlertDialogPrimitive.Trigger

const AlertDialogPortal = AlertDialogPrimitive.Portal

const AlertDialogOverlay = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Overlay
    className={cn(
      "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
    ref={ref}
  />
))
AlertDialogOverlay.displayName = AlertDialogPrimitive.Overlay.displayName

const AlertDialogContent = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Content>
>(({ className, ...props }, ref) => (
  <AlertDialogPortal>
    <AlertDialogOverlay />
    <AlertDialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 rounded-[28px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6 text-[color:var(--px-shell-ink)] shadow-[var(--px-shell-shadow)] duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
        className
      )}
      {...props}
    />
  </AlertDialogPortal>
))
AlertDialogContent.displayName = AlertDialogPrimitive.Content.displayName

const AlertDialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col space-y-2 text-center sm:text-left",
      className
    )}
    {...props}
  />
)
AlertDialogHeader.displayName = "AlertDialogHeader"

const AlertDialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
)
AlertDialogFooter.displayName = "AlertDialogFooter"

const AlertDialogTitle = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-[color:var(--px-shell-ink)]", className)}
    {...props}
  />
))
AlertDialogTitle.displayName = AlertDialogPrimitive.Title.displayName

const AlertDialogDescription = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Description
    ref={ref}
    className={cn("text-sm leading-6 text-[color:var(--px-shell-muted)]", className)}
    {...props}
  />
))
AlertDialogDescription.displayName =
  AlertDialogPrimitive.Description.displayName

interface AlertDialogActionProps
  extends React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Action>,
    VariantProps<typeof buttonVariants> {}

const AlertDialogAction = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Action>,
  AlertDialogActionProps
>(({ className, variant, size, ...props }, ref) => (
  <AlertDialogPrimitive.Action
    ref={ref}
    className={cn(buttonVariants({ variant, size }), className)}
    {...props}
  />
))
AlertDialogAction.displayName = AlertDialogPrimitive.Action.displayName

interface AlertDialogCancelProps
  extends React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Cancel>,
    VariantProps<typeof buttonVariants> {}

const AlertDialogCancel = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Cancel>,
  AlertDialogCancelProps
>(({ className, variant, size, ...props }, ref) => (
  <AlertDialogPrimitive.Cancel
    ref={ref}
    className={cn(
      buttonVariants({ variant: variant ?? "outline", size }),
      "mt-2 sm:mt-0",
      className
    )}
    {...props}
  />
))
AlertDialogCancel.displayName = AlertDialogPrimitive.Cancel.displayName

export {
  AlertDialog,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\badge.tsx
Relative path: ui\primitives\badge.tsx

```tsx
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] transition-colors focus:outline-none focus:ring-2 focus:ring-[color:var(--px-shell-accent)]/20 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent)] text-white shadow-[var(--px-shell-shadow)] hover:bg-[color:var(--px-shell-accent-strong)]",
        secondary:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-accent)]/30",
        destructive:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-strong)] text-[color:var(--px-shell-danger-contrast)] shadow-none hover:bg-[color:var(--px-shell-danger)]",
        outline:
          "border-[color:var(--px-shell-line)] bg-white/72 text-[color:var(--px-shell-muted)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\checkbox.tsx
Relative path: ui\primitives\checkbox.tsx

```tsx
import * as React from "react"
import * as CheckboxPrimitive from "@radix-ui/react-checkbox"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      "grid place-content-center peer h-4 w-4 shrink-0 rounded-sm border border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-panel-strong)] shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent-soft)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-[color:var(--px-shell-accent)] data-[state=checked]:bg-[color:var(--px-shell-accent)] data-[state=checked]:text-[color:var(--px-shell-accent-contrast)]",
      className
    )}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      className={cn("grid place-content-center text-current")}
    >
      <Check className="h-4 w-4" />
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
))
Checkbox.displayName = CheckboxPrimitive.Root.displayName

export { Checkbox }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\collapsible.tsx
Relative path: ui\primitives\collapsible.tsx

```tsx
"use client"

import * as CollapsiblePrimitive from "@radix-ui/react-collapsible"

const Collapsible = CollapsiblePrimitive.Root

const CollapsibleTrigger = CollapsiblePrimitive.CollapsibleTrigger

const CollapsibleContent = CollapsiblePrimitive.CollapsibleContent

export { Collapsible, CollapsibleTrigger, CollapsibleContent }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\label.tsx
Relative path: ui\primitives\label.tsx

```tsx
import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
)

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> &
    VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants(), className)}
    {...props}
  />
))
Label.displayName = LabelPrimitive.Root.displayName

export { Label }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\popover.tsx
Relative path: ui\primitives\popover.tsx

```tsx
"use client"

import * as React from "react"
import * as PopoverPrimitive from "@radix-ui/react-popover"

import { cn } from "@/lib/utils"

const Popover = PopoverPrimitive.Root

const PopoverTrigger = PopoverPrimitive.Trigger

const PopoverAnchor = PopoverPrimitive.Anchor

const PopoverContent = React.forwardRef<
  React.ElementRef<typeof PopoverPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>
>(({ className, align = "center", sideOffset = 4, ...props }, ref) => (
  <PopoverPrimitive.Portal>
    <PopoverPrimitive.Content
      ref={ref}
      align={align}
      sideOffset={sideOffset}
      className={cn(
        "z-50 w-72 rounded-md border bg-popover p-4 text-popover-foreground shadow-md outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-popover-content-transform-origin]",
        className
      )}
      {...props}
    />
  </PopoverPrimitive.Portal>
))
PopoverContent.displayName = PopoverPrimitive.Content.displayName

export { Popover, PopoverTrigger, PopoverContent, PopoverAnchor }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\progress.tsx
Relative path: ui\primitives\progress.tsx

```tsx
import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"

import { cn } from "@/lib/utils"

const Progress = React.forwardRef<
    React.ElementRef<typeof ProgressPrimitive.Root>,
    React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(({ className, value, ...props }, ref) => (
    <ProgressPrimitive.Root
        ref={ref}
        className={cn(
            "relative h-4 w-full overflow-hidden rounded-full bg-secondary",
            className
        )}
        {...props}
    >
        <ProgressPrimitive.Indicator
            className="h-full w-full flex-1 bg-gradient-to-r from-primary/80 to-primary transition-all duration-300 ease-out"
            style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
        />
    </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\resizable.tsx
Relative path: ui\primitives\resizable.tsx

```tsx
import { GripVertical } from "lucide-react"
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from "react-resizable-panels"

import { cn } from "@/lib/utils"

const ResizablePanelGroup = ({
  className,
  ...props
}: React.ComponentProps<typeof PanelGroup>) => (
  <PanelGroup
    className={cn(
      "flex h-full w-full data-[panel-group-direction=vertical]:flex-col",
      className
    )}
    {...props}
  />
)

const ResizablePanel = Panel

const ResizableHandle = ({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof PanelResizeHandle> & {
  withHandle?: boolean
}) => (
  <PanelResizeHandle
    className={cn(
      "relative flex w-px items-center justify-center bg-[color:var(--px-shell-line)] after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent-soft)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] data-[panel-group-direction=vertical]:h-px data-[panel-group-direction=vertical]:w-full data-[panel-group-direction=vertical]:after:left-0 data-[panel-group-direction=vertical]:after:h-1 data-[panel-group-direction=vertical]:after:w-full data-[panel-group-direction=vertical]:after:-translate-y-1/2 data-[panel-group-direction=vertical]:after:translate-x-0 [&[data-panel-group-direction=vertical]>div]:rotate-90",
      className
    )}
    {...props}
  >
    {withHandle && (
      <div className="z-10 flex h-4 w-3 items-center justify-center rounded-sm border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-muted)]">
        <GripVertical className="h-2.5 w-2.5" />
      </div>
    )}
  </PanelResizeHandle>
)

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\scroll-area.tsx
Relative path: ui\primitives\scroll-area.tsx

```tsx
import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"

import { cn } from "@/lib/utils"

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root
    ref={ref}
    className={cn("relative overflow-hidden", className)}
    {...props}
  >
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollBar />
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
))
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName

const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical" &&
        "h-full w-2.5 border-l border-l-transparent p-[1px]",
      orientation === "horizontal" &&
        "h-2.5 flex-col border-t border-t-transparent p-[1px]",
      className
    )}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-border" />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
))
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName

export { ScrollArea, ScrollBar }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\select.tsx
Relative path: ui\primitives\select.tsx

```tsx
import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { Check, ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"

const Select = SelectPrimitive.Root

const SelectGroup = SelectPrimitive.Group

const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex min-h-11 w-full items-center justify-between whitespace-nowrap rounded-[18px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)] px-4 py-2 text-sm text-[color:var(--px-shell-ink)] shadow-sm data-[placeholder]:text-[color:var(--px-shell-muted)] focus:outline-none focus:ring-2 focus:ring-[color:var(--px-shell-accent)]/15 focus:ring-offset-2 focus:ring-offset-[color:var(--px-shell-panel)] disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectScrollUpButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollUpButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollUpButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollUpButton
    ref={ref}
    className={cn(
      "flex cursor-default items-center justify-center py-1",
      className
    )}
    {...props}
  >
    <ChevronUp className="h-4 w-4" />
  </SelectPrimitive.ScrollUpButton>
))
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName

const SelectScrollDownButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollDownButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollDownButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollDownButton
    ref={ref}
    className={cn(
      "flex cursor-default items-center justify-center py-1",
      className
    )}
    {...props}
  >
    <ChevronDown className="h-4 w-4" />
  </SelectPrimitive.ScrollDownButton>
))
SelectScrollDownButton.displayName =
  SelectPrimitive.ScrollDownButton.displayName

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        "relative z-50 max-h-[--radix-select-content-available-height] min-w-[12rem] overflow-y-auto overflow-x-hidden rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] shadow-[var(--px-shell-shadow)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-select-content-transform-origin]",
        position === "popper" &&
          "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
        className
      )}
      position={position}
      {...props}
    >
      <SelectScrollUpButton />
      <SelectPrimitive.Viewport
        className={cn(
          "p-1",
          position === "popper" &&
            "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
      <SelectScrollDownButton />
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
))
SelectContent.displayName = SelectPrimitive.Content.displayName

const SelectLabel = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label
    ref={ref}
    className={cn("px-2 py-1.5 text-sm font-semibold", className)}
    {...props}
  />
))
SelectLabel.displayName = SelectPrimitive.Label.displayName

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center rounded-[14px] py-2.5 pl-3 pr-8 text-sm outline-none focus:bg-[color:var(--px-shell-accent-soft)] focus:text-[color:var(--px-shell-ink)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

const SelectSeparator = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator
    ref={ref}
    className={cn("-mx-1 my-1 h-px bg-[color:var(--px-shell-line)]", className)}
    {...props}
  />
))
SelectSeparator.displayName = SelectPrimitive.Separator.displayName

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\separator.tsx
Relative path: ui\primitives\separator.tsx

```tsx
"use client"

import * as React from "react"
import * as SeparatorPrimitive from "@radix-ui/react-separator"

import { cn } from "@/lib/utils"

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(
  (
    { className, orientation = "horizontal", decorative = true, ...props },
    ref
  ) => (
    <SeparatorPrimitive.Root
      ref={ref}
      decorative={decorative}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-border",
        orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
        className
      )}
      {...props}
    />
  )
)
Separator.displayName = SeparatorPrimitive.Root.displayName

export { Separator }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\sheet.tsx
Relative path: ui\primitives\sheet.tsx

```tsx
import * as React from "react"
import * as SheetPrimitive from "@radix-ui/react-dialog"
import { cva, type VariantProps } from "class-variance-authority"
import { X } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"

const Sheet = SheetPrimitive.Root

const SheetTrigger = SheetPrimitive.Trigger

const SheetClose = SheetPrimitive.Close

const SheetPortal = SheetPrimitive.Portal

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Overlay
    className={cn(
      "fixed inset-0 z-50 bg-black/80  data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
    ref={ref}
  />
))
SheetOverlay.displayName = SheetPrimitive.Overlay.displayName

const sheetVariants = cva(
  "fixed z-50 gap-4 border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-6 text-[color:var(--px-shell-ink)] shadow-[var(--px-shell-shadow)] transition ease-in-out data-[state=closed]:duration-300 data-[state=open]:duration-500 data-[state=open]:animate-in data-[state=closed]:animate-out",
  {
    variants: {
      side: {
        top: "inset-x-0 top-0 border-b data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top",
        bottom:
          "inset-x-0 bottom-0 border-t data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom",
        left: "inset-y-0 left-0 h-full w-3/4 border-r data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left sm:max-w-sm",
        right:
          "inset-y-0 right-0 h-full w-3/4 border-l data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right sm:max-w-sm",
      },
    },
    defaultVariants: {
      side: "right",
    },
  }
)

interface SheetContentProps
  extends React.ComponentPropsWithoutRef<typeof SheetPrimitive.Content>,
    VariantProps<typeof sheetVariants> {}

const SheetContent = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Content>,
  SheetContentProps
>(({ side = "right", className, children, ...props }, ref) => {
  const { t } = useTranslation()

  return (
    <SheetPortal>
      <SheetOverlay />
      <SheetPrimitive.Content
        ref={ref}
        className={cn(sheetVariants({ side }), className)}
        {...props}
      >
        <SheetPrimitive.Close className="absolute right-4 top-4 rounded-full border border-transparent p-2 text-[color:var(--px-shell-muted)] transition-colors hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)] focus:outline-none focus:ring-2 focus:ring-[color:var(--px-shell-accent)]/20 disabled:pointer-events-none">
          <X className="h-4 w-4" />
          <span className="sr-only">{t("common.actions.close")}</span>
        </SheetPrimitive.Close>
        {children}
      </SheetPrimitive.Content>
    </SheetPortal>
  )
})
SheetContent.displayName = SheetPrimitive.Content.displayName

const SheetHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col space-y-2 text-center sm:text-left",
      className
    )}
    {...props}
  />
)
SheetHeader.displayName = "SheetHeader"

const SheetFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
)
SheetFooter.displayName = "SheetFooter"

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Title>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-[color:var(--px-shell-ink)]", className)}
    {...props}
  />
))
SheetTitle.displayName = SheetPrimitive.Title.displayName

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Description>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Description
    ref={ref}
    className={cn("text-sm leading-6 text-[color:var(--px-shell-muted)]", className)}
    {...props}
  />
))
SheetDescription.displayName = SheetPrimitive.Description.displayName

export {
  Sheet,
  SheetPortal,
  SheetOverlay,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\skeleton.tsx
Relative path: ui\primitives\skeleton.tsx

```tsx
import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[color:color-mix(in_srgb,var(--px-shell-accent)_10%,transparent)]",
        className,
      )}
      {...props}
    />
  )
}

export { Skeleton }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\sonner.tsx
Relative path: ui\primitives\sonner.tsx

```tsx
import { useTheme } from "next-themes"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:border-[color:var(--px-shell-line)] group-[.toaster]:bg-[color:var(--px-shell-panel)] group-[.toaster]:text-[color:var(--px-shell-ink)] group-[.toaster]:shadow-[var(--px-shell-shadow)]",
          description: "group-[.toast]:text-[color:var(--px-shell-muted)]",
          actionButton:
            "group-[.toast]:border-[color:var(--px-shell-accent)] group-[.toast]:bg-[color:var(--px-shell-accent)] group-[.toast]:text-white",
          cancelButton:
            "group-[.toast]:border-[color:var(--px-shell-line)] group-[.toast]:bg-[color:var(--px-shell-panel-strong)] group-[.toast]:text-[color:var(--px-shell-muted)]",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\switch.tsx
Relative path: ui\primitives\switch.tsx

```tsx
import * as React from "react"
import * as SwitchPrimitives from "@radix-ui/react-switch"

import { cn } from "@/lib/utils"

const Switch = React.forwardRef<
    React.ElementRef<typeof SwitchPrimitives.Root>,
    React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
    <SwitchPrimitives.Root
        className={cn(
            "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-[color:var(--px-shell-accent)] data-[state=checked]:shadow-[0_0_0_4px_color-mix(in_srgb,var(--px-shell-accent)_16%,transparent)] data-[state=unchecked]:bg-[color:var(--px-shell-line)]",
            className
        )}
        {...props}
        ref={ref}
    >
        <SwitchPrimitives.Thumb
            className={cn(
                "pointer-events-none block h-5 w-5 rounded-full bg-white shadow-sm ring-1 ring-black/5 transition-transform duration-200 data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0"
            )}
        />
    </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\tabs.tsx
Relative path: ui\primitives\tabs.tsx

```tsx
import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-auto items-center justify-center rounded-[18px] border border-[color:var(--px-shell-line)] bg-white/72 p-1.5 text-[color:var(--px-shell-muted)] shadow-sm",
      className
    )}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-[14px] px-4 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-[color:var(--px-shell-panel)] data-[state=active]:text-[color:var(--px-shell-ink)] data-[state=active]:shadow-[0_12px_28px_-20px_rgba(8,23,38,0.28)]",
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent-soft)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)]",
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\toggle-group.tsx
Relative path: ui\primitives\toggle-group.tsx

```tsx
import * as React from "react"
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group"
import { type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { toggleVariants } from "@/ui/primitives/toggle"

const ToggleGroupContext = React.createContext<
  VariantProps<typeof toggleVariants>
>({
  size: "default",
  variant: "default",
})

const ToggleGroup = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive.Root> &
    VariantProps<typeof toggleVariants>
>(({ className, variant, size, children, ...props }, ref) => (
  <ToggleGroupPrimitive.Root
    ref={ref}
    className={cn("flex items-center justify-center gap-1", className)}
    {...props}
  >
    <ToggleGroupContext.Provider value={{ variant, size }}>
      {children}
    </ToggleGroupContext.Provider>
  </ToggleGroupPrimitive.Root>
))

ToggleGroup.displayName = ToggleGroupPrimitive.Root.displayName

const ToggleGroupItem = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive.Item> &
    VariantProps<typeof toggleVariants>
>(({ className, children, variant, size, ...props }, ref) => {
  const context = React.useContext(ToggleGroupContext)

  return (
    <ToggleGroupPrimitive.Item
      ref={ref}
      className={cn(
        toggleVariants({
          variant: context.variant || variant,
          size: context.size || size,
        }),
        className
      )}
      {...props}
    >
      {children}
    </ToggleGroupPrimitive.Item>
  )
})

ToggleGroupItem.displayName = ToggleGroupPrimitive.Item.displayName

export { ToggleGroup, ToggleGroupItem }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\toggle.tsx
Relative path: ui\primitives\toggle.tsx

```tsx
"use client"

import * as React from "react"
import * as TogglePrimitive from "@radix-ui/react-toggle"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const toggleVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full border border-transparent text-sm font-medium text-[color:var(--px-shell-muted)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 disabled:pointer-events-none disabled:opacity-50 data-[state=on]:border-[color:var(--px-shell-accent)]/18 data-[state=on]:bg-[color:var(--px-shell-accent-soft)] data-[state=on]:text-[color:var(--px-shell-accent)] [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-transparent",
        outline:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm hover:border-[color:var(--px-shell-accent)]/24 hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
      },
      size: {
        default: "h-9 px-2 min-w-9",
        sm: "h-8 px-1.5 min-w-8",
        lg: "h-10 px-2.5 min-w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

const Toggle = React.forwardRef<
  React.ElementRef<typeof TogglePrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TogglePrimitive.Root> &
    VariantProps<typeof toggleVariants>
>(({ className, variant, size, ...props }, ref) => (
  <TogglePrimitive.Root
    ref={ref}
    className={cn(toggleVariants({ variant, size, className }))}
    {...props}
  />
))

Toggle.displayName = TogglePrimitive.Root.displayName

export { Toggle, toggleVariants }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\primitives\tooltip.tsx
Relative path: ui\primitives\tooltip.tsx

```tsx
import * as React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"

import { cn } from "@/lib/utils"

const TooltipProvider = TooltipPrimitive.Provider

const Tooltip = TooltipPrimitive.Root

const TooltipTrigger = TooltipPrimitive.Trigger

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 overflow-hidden rounded-xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-1.5 text-xs text-[color:var(--px-shell-ink)] shadow-[0_18px_40px_rgba(15,23,42,0.16)] animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-tooltip-content-transform-origin]",
        className
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\record-row\RecordRow.tsx
Relative path: ui\record-row\RecordRow.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

interface RecordRowProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  icon?: ReactNode
  title: ReactNode
  meta?: ReactNode
  badge?: ReactNode
  action?: ReactNode
  detail?: ReactNode
  alert?: ReactNode
}

export function RecordRow({
  icon,
  title,
  meta,
  badge,
  action,
  detail,
  alert,
  className,
  children,
  ...props
}: RecordRowProps) {
  return (
    <div
      className={cn(
        "space-y-2 rounded-[20px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-sm",
        className,
      )}
      {...props}
    >
      <div className="flex items-start gap-2">
        {icon ? <div className="pt-0.5">{icon}</div> : null}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-0 flex-1 truncate text-sm font-medium text-[color:var(--px-shell-ink)]">
              {title}
            </div>
            {badge}
            {action}
          </div>
          {meta ? (
            <div className="mt-1 text-xs text-[color:var(--px-shell-muted)]">
              {meta}
            </div>
          ) : null}
        </div>
      </div>

      {detail ? <div>{detail}</div> : null}
      {children}
      {alert ? <div>{alert}</div> : null}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\search-bar\SearchBar.tsx
Relative path: ui\search-bar\SearchBar.tsx

```tsx
import type { FormEvent, KeyboardEvent, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"
import { Input } from "@/ui/input/Input"
import { Textarea } from "@/ui/input/Textarea"

const searchBarVariants = cva(
  "border border-[color:var(--px-shell-line)] text-[color:var(--px-shell-ink)] shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      variant: {
        inline:
          "rounded-md bg-[color:var(--px-shell-panel)] px-4 py-3",
        feature:
          "rounded-md bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel-strong)_96%,white),color-mix(in_srgb,var(--px-shell-accent-soft)_18%,white))] px-4 py-4 md:px-5 md:py-5",
      },
    },
    defaultVariants: {
      variant: "inline",
    },
  },
)

interface SearchBarProps extends VariantProps<typeof searchBarVariants> {
  value: string
  onValueChange: (value: string) => void
  onSubmit: (value: string) => void
  placeholder: string
  ariaLabel: string
  actionLabel: string
  actionIcon?: ReactNode
  auxiliaryAction?: ReactNode
  meta?: ReactNode
  disabled?: boolean
  multiline?: boolean
  className?: string
  inputClassName?: string
}

export function SearchBar({
  value,
  onValueChange,
  onSubmit,
  placeholder,
  ariaLabel,
  actionLabel,
  actionIcon,
  auxiliaryAction,
  meta,
  disabled = false,
  multiline = false,
  variant,
  className,
  inputClassName,
}: SearchBarProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit(value)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!multiline) {
      return
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSubmit(value)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(searchBarVariants({ variant }), className)}
    >
      <div className={cn("flex gap-3", variant === "feature" ? "items-start" : "items-center")}>
        <div className="min-w-0 flex-1 space-y-2.5">
          {multiline ? (
            <Textarea
              aria-label={ariaLabel}
              value={value}
              onChange={(event) => onValueChange(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              className={cn("min-h-[108px] border-none bg-transparent px-0 py-0 shadow-none focus-visible:ring-0", inputClassName)}
            />
          ) : (
            <Input
              aria-label={ariaLabel}
              value={value}
              onChange={(event) => onValueChange(event.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className={cn("min-h-9 border-none bg-transparent px-0 py-0 text-[15px] shadow-none focus-visible:ring-0", inputClassName)}
            />
          )}

          <div className="flex flex-col gap-2 border-t border-[color:var(--px-shell-line)]/75 pt-2.5 md:flex-row md:items-center md:justify-between">
            {meta ? (
              <div className="min-w-0">{meta}</div>
            ) : (
              <div />
            )}

            <div className="flex flex-wrap items-center justify-end gap-2">
              {auxiliaryAction}
              <Button
                type="submit"
                disabled={disabled}
                className={cn(variant === "feature" ? "px-7" : "px-5")}
              >
                {actionIcon}
                {actionLabel}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </form>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\section-card\SectionCard.tsx
Relative path: ui\section-card\SectionCard.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"

interface SectionCardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  headerAside?: ReactNode
  headerClassName?: string
  contentClassName?: string
  iconClassName?: string
}

export function SectionCard({
  icon,
  title,
  description,
  headerAside,
  headerClassName,
  contentClassName,
  iconClassName,
  className,
  children,
  ...props
}: SectionCardProps) {
  return (
    <Card className={cn("overflow-hidden shadow-none", className)} {...props}>
      <CardHeader
        className={cn(
          "flex flex-row items-start justify-between gap-4 bg-white/48",
          headerClassName,
        )}
      >
        <div className="flex min-w-0 items-start gap-3">
          {icon ? (
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-accent)]",
                iconClassName,
              )}
            >
              {icon}
            </div>
          ) : null}

          <div className="min-w-0 space-y-1">
            <CardTitle className="text-base font-bold tracking-tight">{title}</CardTitle>
            {description ? (
              <CardDescription className="text-xs leading-5">{description}</CardDescription>
            ) : null}
          </div>
        </div>

        {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
      </CardHeader>

      <CardContent className={cn("px-6 py-5", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\section-heading\SectionHeading.tsx
Relative path: ui\section-heading\SectionHeading.tsx

```tsx
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  aside?: ReactNode
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  aside,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-col gap-3 px-1 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[color:var(--px-shell-muted)]">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl font-black text-[color:var(--px-shell-ink)]">{title}</h2>
        {description ? (
          <p className="max-w-3xl text-sm leading-6 text-[color:var(--px-shell-muted)]">{description}</p>
        ) : null}
      </div>
      {aside ? <div>{aside}</div> : null}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\segmented-control\SegmentedControl.tsx
Relative path: ui\segmented-control\SegmentedControl.tsx

```tsx
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SegmentedControlItem<T extends string> {
  value: T
  label: ReactNode
  icon?: ReactNode
  disabled?: boolean
  testId?: string
}

interface SegmentedControlProps<T extends string> {
  value: T
  items: SegmentedControlItem<T>[]
  onValueChange: (value: T) => void
  className?: string
  itemClassName?: string
}

export function SegmentedControl<T extends string>({
  value,
  items,
  onValueChange,
  className,
  itemClassName,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={cn(
        "flex w-full items-center gap-1 rounded-md border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-1 shadow-inner",
        className,
      )}
    >
      {items.map((item) => {
        const active = item.value === value

        return (
          <button
            key={item.value}
            type="button"
            data-testid={item.testId}
            disabled={item.disabled}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "flex-1 inline-flex min-h-9 items-center justify-center gap-1.5 rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] transition-all duration-200",
              active
                ? "bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-sm border border-[color:var(--px-shell-line)]"
                : "text-[color:var(--px-shell-muted)] hover:text-[color:var(--px-shell-ink)] disabled:cursor-not-allowed disabled:opacity-45 border border-transparent",
              itemClassName,
            )}
          >
            {item.icon ? <span className="flex h-4 w-4 items-center justify-center">{item.icon}</span> : null}
            <span>{item.label}</span>
          </button>
        )
      })}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\sidebar-shell\SidebarBrandButton.tsx
Relative path: ui\sidebar-shell\SidebarBrandButton.tsx

```tsx
import type { MouseEventHandler } from "react"
import { ChevronRight } from "lucide-react"

interface SidebarBrandButtonProps {
  brandName: string
  subtitle: string
  collapsed: boolean
  collapsedActionLabel?: string
  onClick: MouseEventHandler<HTMLButtonElement>
}

export function SidebarBrandButton({
  brandName,
  subtitle,
  collapsed,
  collapsedActionLabel,
  onClick,
}: SidebarBrandButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={collapsed ? collapsedActionLabel ?? brandName : brandName}
      title={collapsed ? collapsedActionLabel ?? brandName : brandName}
      className={`group inline-flex min-w-0 items-start text-left outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25 ${
        collapsed
          ? "relative h-10 w-10 justify-center rounded-[16px] border border-transparent hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)]"
          : "flex-1"
      }`}
    >
      {collapsed ? (
        <>
          <span className="text-lg font-black uppercase tracking-[0.16em] text-[color:var(--px-shell-ink)] transition-all duration-200 group-hover:scale-90 group-hover:opacity-0 group-focus-visible:scale-90 group-focus-visible:opacity-0">
            PX
          </span>
          <span className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-0 transition-all duration-200 group-hover:opacity-100 group-focus-visible:opacity-100">
            <ChevronRight className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
          </span>
        </>
      ) : (
        <span className="min-w-0">
          <span className="block text-[1.7rem] font-black tracking-[0.24em] text-[color:var(--px-shell-ink)] transition-colors duration-200 group-hover:text-[color:var(--px-shell-accent)]">
            {brandName}
          </span>
          <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {subtitle}
          </span>
        </span>
      )}
    </button>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\sidebar-shell\SidebarNavItem.tsx
Relative path: ui\sidebar-shell\SidebarNavItem.tsx

```tsx
import type { ReactNode } from "react"
import { NavLink } from "react-router-dom"

export function SidebarNavItem({
  to,
  icon,
  label,
  collapsed = false,
  active,
}: {
  to: string
  icon: ReactNode
  label: string
  collapsed?: boolean
  active?: boolean
}) {
  return (
    <NavLink
      to={to}
      aria-label={label}
      title={label}
      className={({ isActive }) =>
        `flex items-center rounded-[16px] text-sm font-semibold transition-all duration-200 ${
          isActive || active
            ? "bg-[color:var(--px-shell-accent)] text-[color:var(--px-shell-accent-contrast)] shadow-[0_18px_38px_-26px_rgba(18,118,199,0.56)]"
            : "text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)]"
        } ${
          collapsed ? "justify-center px-0 py-3.5" : "gap-3 px-4 py-3"
        }`
      }
    >
      <span className="shrink-0">{icon}</span>
      <span className={collapsed ? "sr-only" : "truncate"}>{label}</span>
    </NavLink>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\sidebar-shell\SidebarProfileButton.tsx
Relative path: ui\sidebar-shell\SidebarProfileButton.tsx

```tsx
import type { MouseEventHandler } from "react"

interface SidebarProfileButtonProps {
  initial: string
  label: string
  subtitle: string
  onClick: MouseEventHandler<HTMLButtonElement>
  collapsed?: boolean
}

export function SidebarProfileButton({
  initial,
  label,
  subtitle,
  onClick,
  collapsed = false,
}: SidebarProfileButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`flex w-full rounded-[18px] text-left transition-all duration-200 hover:bg-[color:var(--px-shell-panel-strong)] ${
        collapsed ? "justify-center px-0 py-2" : "items-center gap-3 px-2 py-2"
      }`}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-sm font-bold uppercase text-[color:var(--px-shell-accent)]">
        {initial}
      </div>
      <div className={collapsed ? "sr-only" : "min-w-0"}>
        <div className="truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">
          {label}
        </div>
        <div className="text-xs text-[color:var(--px-shell-muted)]">
          {subtitle}
        </div>
      </div>
    </button>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\sidebar-shell\SidebarShell.tsx
Relative path: ui\sidebar-shell\SidebarShell.tsx

```tsx
import type { ReactNode } from "react"
import { ChevronLeft } from "lucide-react"

import { Button } from "@/ui/button/Button"

export function SidebarShell({
  brand,
  nav,
  utility,
  collapsed,
  onToggleCollapse,
  collapseLabel,
}: {
  brand: ReactNode
  nav: ReactNode
  utility: ReactNode
  collapsed: boolean
  onToggleCollapse: () => void
  collapseLabel: string
}) {
  return (
    <aside
      data-collapsed={collapsed ? "true" : "false"}
      className={`sticky top-0 flex h-screen shrink-0 flex-col justify-between border-r border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] backdrop-blur-xl transition-[width,padding] duration-300 ${
        collapsed ? "w-[92px] px-3 py-5" : "w-[272px] px-5 py-6"
      }`}
    >
      <div className={collapsed ? "space-y-6" : "space-y-8"}>
        <div
          className={
            collapsed
              ? "flex justify-center"
              : "flex items-start justify-between gap-3"
          }
        >
          {brand}
          {!collapsed ? (
            <div className="shrink-0 pt-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onToggleCollapse}
                aria-label={collapseLabel}
                title={collapseLabel}
                className="h-10 w-10 shrink-0 rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-muted)] hover:bg-white hover:text-[color:var(--px-shell-ink)]"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>
          ) : null}
        </div>
        {nav}
      </div>
      <div>{utility}</div>
    </aside>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\sidebar-shell\SidebarUtilityPanel.tsx
Relative path: ui\sidebar-shell\SidebarUtilityPanel.tsx

```tsx
import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

export function SidebarUtilityPanel({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "space-y-3 border-t border-[color:var(--px-shell-line)] pt-4",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\state-panel\StatePanel.tsx
Relative path: ui\state-panel\StatePanel.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const statePanelVariants = cva(
  "rounded-[32px] border px-6 py-14 text-center shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      tone: {
        neutral:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)] shadow-none",
      },
      borderStyle: {
        solid: "",
        dashed: "border-dashed",
      },
    },
    defaultVariants: {
      tone: "neutral",
      borderStyle: "solid",
    },
  },
)

const statePanelIconVariants = cva(
  "mx-auto flex h-16 w-16 items-center justify-center rounded-full border",
  {
    variants: {
      tone: {
        neutral:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  },
)

interface StatePanelProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof statePanelVariants> {
  icon?: ReactNode
  meta?: ReactNode
  title: ReactNode
  description?: ReactNode
  detail?: ReactNode
  actions?: ReactNode
}

export function StatePanel({
  icon,
  meta,
  title,
  description,
  detail,
  actions,
  tone = "neutral",
  borderStyle = "solid",
  className,
  ...props
}: StatePanelProps) {
  return (
    <div
      className={cn(statePanelVariants({ tone, borderStyle }), className)}
      {...props}
    >
      {icon ? (
        <div className={cn(statePanelIconVariants({ tone }))}>
          {icon}
        </div>
      ) : null}

      <div className={cn("mx-auto max-w-xl space-y-2", icon ? "mt-5" : "")}>
        {meta ? (
          <div className="text-[10px] font-black uppercase tracking-[0.22em] text-current/60">
            {meta}
          </div>
        ) : null}
        <h2 className="text-2xl font-semibold text-current">{title}</h2>
        {description ? (
          <p className="text-sm leading-7 text-current/80">{description}</p>
        ) : null}
        {detail ? (
          <div className="pt-1 text-sm text-current/75">{detail}</div>
        ) : null}
      </div>

      {actions ? (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {actions}
        </div>
      ) : null}
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\status-badge\StatusBadge.tsx
Relative path: ui\status-badge\StatusBadge.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em]",
  {
    variants: {
      tone: {
        muted:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-muted)]",
        accent:
          "border-[color:var(--px-shell-accent)]/20 bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]",
        info:
          "border-[color:var(--px-shell-info-line)] bg-[color:var(--px-shell-info-soft)] text-[color:var(--px-shell-info)]",
        success:
          "border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-success)]",
        warning:
          "border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] text-[color:var(--px-shell-warning)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]",
      },
      size: {
        sm: "px-2.5 py-1 text-[10px]",
        md: "px-3 py-1.5 text-[11px]",
      },
    },
    defaultVariants: {
      tone: "muted",
      size: "sm",
    },
  },
)

type StatusBadgeProps = HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof statusBadgeVariants> & {
    icon?: ReactNode
  }

export function StatusBadge({
  className,
  tone,
  size,
  icon,
  children,
  ...props
}: StatusBadgeProps) {
  return (
    <div className={cn(statusBadgeVariants({ tone, size }), className)} {...props}>
      {icon ? <span className="flex h-3.5 w-3.5 items-center justify-center">{icon}</span> : null}
      <span>{children}</span>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\tabs\EditorialTabs.tsx
Relative path: ui\tabs\EditorialTabs.tsx

```tsx
import * as React from "react"

import { cn } from "@/lib/utils"
import { Tabs, TabsList, TabsTrigger } from "@/ui/primitives/tabs"

type EditorialTabsProps = React.ComponentProps<typeof Tabs>
type EditorialTabsListProps = React.ComponentProps<typeof TabsList>
type EditorialTabsTriggerProps = React.ComponentProps<typeof TabsTrigger>

export function EditorialTabs(props: EditorialTabsProps) {
  return <Tabs {...props} />
}

export function EditorialTabsList({ className, ...props }: EditorialTabsListProps) {
  return (
    <TabsList
      className={cn(
        "h-auto rounded-[20px] border border-[color:var(--px-shell-line)] bg-white/72 p-1.5 shadow-sm",
        className,
      )}
      {...props}
    />
  )
}

export function EditorialTabsTrigger({ className, ...props }: EditorialTabsTriggerProps) {
  return (
    <TabsTrigger
      className={cn(
        "rounded-[14px] px-5 py-2.5 text-sm font-semibold text-[color:var(--px-shell-muted)] transition-all data-[state=active]:bg-[color:var(--px-shell-panel)] data-[state=active]:text-[color:var(--px-shell-ink)] data-[state=active]:shadow-[0_12px_28px_-20px_rgba(8,23,38,0.28)]",
        className,
      )}
      {...props}
    />
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\theme-toggle\ThemeToggle.tsx
Relative path: ui\theme-toggle\ThemeToggle.tsx

```tsx
import { MoonStar, SunMedium } from "lucide-react"
import { useTheme } from "next-themes"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"

export function ThemeToggle() {
  const { t } = useTranslation()
  const { theme, setTheme } = useTheme()

  const currentTheme = theme === "light" ? "light" : "dark"
  const isDark = currentTheme === "dark"
  const nextTheme = isDark ? "light" : "dark"
  const actionLabel = isDark
    ? t("theme.toggle.switchToLight")
    : t("theme.toggle.switchToDark")
  const modeLabel = isDark ? t("theme.mode.dark") : t("theme.mode.light")

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      aria-label={actionLabel}
      title={actionLabel}
      onClick={() => setTheme(nextTheme)}
      className="h-11 min-w-11 rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-panel)]"
    >
      {isDark ? (
        <MoonStar className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
      ) : (
        <SunMedium className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
      )}
      <span className="hidden text-sm sm:inline">{modeLabel}</span>
    </Button>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\toggle-switch\ToggleSwitch.tsx
Relative path: ui\toggle-switch\ToggleSwitch.tsx

```tsx
import type { ButtonHTMLAttributes } from "react"

import { cn } from "@/lib/utils"

interface ToggleSwitchProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}

export function ToggleSwitch({
  checked,
  onCheckedChange,
  className,
  disabled,
  ...props
}: ToggleSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        if (!disabled) {
          onCheckedChange(!checked)
        }
      }}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-transparent transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        checked
          ? "bg-[color:var(--px-shell-accent)] shadow-[0_0_0_4px_color-mix(in_srgb,var(--px-shell-accent)_16%,transparent)]"
          : "bg-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-line-strong)]",
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          "pointer-events-none block h-5 w-5 rounded-full bg-white shadow-sm ring-1 ring-black/5 transition-transform duration-200",
          checked ? "translate-x-5" : "translate-x-0",
        )}
      />
    </button>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\upload-card\UploadCard.tsx
Relative path: ui\upload-card\UploadCard.tsx

```tsx
import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, CheckCircle2, FileArchive, Loader2, Upload, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"

interface UploadCardProps {
  isDragActive: boolean
  fileName: string
  progress: number
  status: "idle" | "uploading" | "success" | "error"
  idleTitle: string
  idleDescription: string
  uploadingLabel: string
  successActionLabel: string
  errorLabel: string
  retryLabel: string
  onReset: (event: React.MouseEvent) => void
}

export function UploadCard({
  isDragActive,
  fileName,
  progress,
  status,
  idleTitle,
  idleDescription,
  uploadingLabel,
  successActionLabel,
  errorLabel,
  retryLabel,
  onReset,
}: UploadCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border-2 border-dashed transition-all duration-300 ease-in-out",
        isDragActive
          ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] shadow-[var(--px-shell-shadow)] scale-[1.01]"
          : "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] hover:border-[color:var(--px-shell-accent)]/45 hover:bg-[color:var(--px-shell-panel-strong)]",
        status === "error" && "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)]",
        status === "success" && "border-[color:var(--px-shell-accent)]/30 bg-[color:var(--px-shell-panel-strong)]",
      )}
    >
      <div className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
        <AnimatePresence mode="wait">
          {status === "idle" ? (
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.94 }}
              className="space-y-4"
            >
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-sm">
                <Upload className="h-8 w-8 text-[color:var(--px-shell-accent)]" />
              </div>
              <div className="space-y-1.5">
                <p className="text-lg font-black text-[color:var(--px-shell-ink)]">{idleTitle}</p>
                <p className="max-w-sm text-sm leading-6 text-[color:var(--px-shell-muted)]">{idleDescription}</p>
              </div>
            </motion.div>
          ) : null}

          {status === "uploading" ? (
            <motion.div
              key="uploading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-sm space-y-4"
            >
              <div className="relative mx-auto h-12 w-12">
                <Loader2 className="h-12 w-12 animate-spin text-[color:var(--px-shell-accent)]" />
                <div className="absolute inset-0 flex items-center justify-center text-[10px] font-black">
                  {progress}%
                </div>
              </div>
              <div className="space-y-1">
                <div className="truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">{fileName}</div>
                <div className="h-1.5 overflow-hidden rounded-full bg-black/8">
                  <motion.div
                    className="h-full rounded-full bg-[color:var(--px-shell-accent)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-[color:var(--px-shell-muted)]">{uploadingLabel}</p>
              </div>
            </motion.div>
          ) : null}

          {status === "success" ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="space-y-3"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]">
                <FileArchive className="h-7 w-7" />
              </div>
              <div className="flex items-center justify-center gap-2">
                <span className="max-w-xs truncate text-lg font-semibold text-[color:var(--px-shell-ink)]">{fileName}</span>
                <CheckCircle2 className="h-5 w-5 text-[color:var(--px-shell-success)]" />
              </div>
              <Button variant="ghost" size="sm" onClick={onReset}>
                <X className="h-4 w-4" />
                {successActionLabel}
              </Button>
            </motion.div>
          ) : null}

          {status === "error" ? (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger-strong)]">
                <AlertTriangle className="h-7 w-7" />
              </div>
              <p className="font-semibold text-[color:var(--px-shell-danger)]">{errorLabel}</p>
              <Button variant="outline" size="sm" onClick={onReset}>
                {retryLabel}
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\upload-card\UploadDropSurface.tsx
Relative path: ui\upload-card\UploadDropSurface.tsx

```tsx
import type { HTMLAttributes, ReactNode } from "react"
import { Upload } from "lucide-react"

import { cn } from "@/lib/utils"

interface UploadDropSurfaceProps extends HTMLAttributes<HTMLDivElement> {
  heading: ReactNode
  body: ReactNode
  icon?: ReactNode
  isDragActive?: boolean
}

export function UploadDropSurface({
  heading,
  body,
  icon,
  isDragActive = false,
  className,
  children,
  ...props
}: UploadDropSurfaceProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border-2 border-dashed transition-all duration-300 ease-in-out",
        isDragActive
          ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] shadow-[var(--px-shell-shadow)] scale-[1.01]"
          : "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] hover:border-[color:var(--px-shell-accent)]/45 hover:bg-[color:var(--px-shell-panel-strong)]",
        className,
      )}
      {...props}
    >
      <div className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
        <div className="space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-sm">
            {icon ?? <Upload className="h-8 w-8 text-[color:var(--px-shell-accent)]" />}
          </div>
          <div className="space-y-1.5">
            <p className="text-lg font-black text-[color:var(--px-shell-ink)]">{heading}</p>
            <p className="max-w-sm text-sm leading-6 text-[color:var(--px-shell-muted)]">{body}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}

```

## File: D:\future\antigravity\LaTexTrans\frontend\src\ui\workflow-stepper\WorkflowStepper.tsx
Relative path: ui\workflow-stepper\WorkflowStepper.tsx

```tsx
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

export type WorkflowStepState = "complete" | "current" | "error" | "upcoming"

interface WorkflowStepItem {
  id: string
  label: string
  description?: string | null
  state: WorkflowStepState
}

interface WorkflowStepperProps {
  items: WorkflowStepItem[]
  className?: string
}

function stepCircleClass(state: WorkflowStepState) {
  switch (state) {
    case "complete":
      return "border-[color:var(--px-shell-success)] bg-[color:var(--px-shell-success)] text-[color:var(--px-shell-danger-contrast)]"
    case "error":
      return "border-[color:var(--px-shell-danger-strong)] bg-[color:var(--px-shell-danger-strong)] text-[color:var(--px-shell-danger-contrast)]"
    case "current":
      return "border-[color:var(--px-shell-accent)] text-[color:var(--px-shell-accent)] shadow-[0_0_0_4px_color-mix(in_srgb,var(--px-shell-accent)_12%,transparent)]"
    default:
      return "border-[color:var(--px-shell-line)] text-[color:var(--px-shell-muted)]"
  }
}

function stepTextClass(state: WorkflowStepState) {
  switch (state) {
    case "complete":
      return "text-[color:var(--px-shell-success)]"
    case "error":
      return "text-[color:var(--px-shell-danger)]"
    case "current":
      return "text-[color:var(--px-shell-accent)]"
    default:
      return "text-[color:var(--px-shell-muted)]"
  }
}

function renderStepIcon(state: WorkflowStepState) {
  switch (state) {
    case "complete":
      return <CheckCircle2 className="h-3 w-3" />
    case "error":
      return <AlertTriangle className="h-3 w-3" />
    case "current":
      return <Loader2 className="h-3 w-3 animate-spin" />
    default:
      return <span className="h-2 w-2 rounded-full bg-current" />
  }
}

export function WorkflowStepper({ items, className }: WorkflowStepperProps) {
  return (
    <div className={cn("relative ml-2 space-y-5 border-l-2 border-[color:var(--px-shell-line)] py-1 pl-5", className)}>
      {items.map((item) => (
        <div key={item.id} className="relative">
          <span
            className={cn(
              "absolute -left-[23px] flex h-5 w-5 items-center justify-center rounded-full border-2 bg-[color:var(--px-shell-panel-strong)]",
              stepCircleClass(item.state),
            )}
          >
            {renderStepIcon(item.state)}
          </span>
          <div className="flex flex-col">
            <span className={cn("text-sm font-medium", stepTextClass(item.state))}>{item.label}</span>
            {item.description ? (
              <span className={cn("text-xs", item.state === "upcoming" ? "text-[color:var(--px-shell-muted)]/75" : stepTextClass(item.state))}>
                {item.description}
              </span>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  )
}

```

## Excluded Resources

- test: D:\future\antigravity\LaTexTrans\frontend\src\api-base.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\App.community-routing.test.tsx
- other: D:\future\antigravity\LaTexTrans\frontend\src\bootstrap-globals.d.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\branding.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\contexts\AuthContext.local-auth.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\features\auth-shell\components\LoginPrompt.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\CommunitySubmitPanel.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperCard.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\components\PaperPreviewReader.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\features\community-paper\hooks\useCommunityPapers.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\features\translation-workflow\components\BatchTranslation.test.tsx
- other: D:\future\antigravity\LaTexTrans\frontend\src\hooks\use-mobile.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\hooks\use-paper-detail.test.tsx
- other: D:\future\antigravity\LaTexTrans\frontend\src\hooks\use-task-status-sse.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\i18n\config.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\i18n\locale-completeness.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\i18n\locale-sanity.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\i18n\no-hardcoded-ui-copy.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\i18n\task-copy.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\layout.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\layout\AppSidebar.community-shell.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\lib\community-api.retry.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\lib\local-auth.retry.test.ts
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\de\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\en\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\es\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\fr\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\ja\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\ko\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\ru\common.json
- locale: D:\future\antigravity\LaTexTrans\frontend\src\locales\zh\common.json
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\CommunityAdminCuration.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\CommunityAdminCurationTasks.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\CommunityConversation.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\CommunityFeed.agent-first.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\CommunityFeed.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\Dashboard.legacy-workflow.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\History.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\home\index.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\Login.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\PaperDetail.reader-first.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\PaperDetail.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\Processing.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\remaining-pages-i18n.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\pages\tools-hub\index.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\styles\tokens.test.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\test\setup.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\test\theme.ts
- test: D:\future\antigravity\LaTexTrans\frontend\src\ui\language-selector\LanguageSelector.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\ui\loading-state\LoadingState.test.tsx
- test: D:\future\antigravity\LaTexTrans\frontend\src\ui\theme-toggle\ThemeToggle.test.tsx
