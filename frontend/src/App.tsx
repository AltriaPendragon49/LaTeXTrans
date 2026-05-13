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
const RagTerminologyAdminPage = lazy(() => import("./pages/rag-terminology-admin"))
const CommunityConversationPage = lazy(() => import("./pages/community-conversation"))
const ProcessingPage = lazy(() => import("./pages/processing"))
const Login = lazy(() => import("./pages/login"))
const FavoritesPage = lazy(() => import("./pages/favorites"))
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

function AdminRoute({ children, redirectTo = "/" }: { children: ReactNode; redirectTo?: string }) {
  const { user, loading, isAuthenticated } = useAuth()

  if (loading) {
    return <RouteLoading />
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  if (!hasAdminRole(user?.roles)) {
    return <Navigate to={redirectTo} replace />
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
              <Route
                path="agent"
                element={(
                  <AdminRoute redirectTo="/tools">
                    {withSuspense(<CommunityConversationPage />)}
                  </AdminRoute>
                )}
              />
              <Route
                path="agent/:conversationId"
                element={(
                  <AdminRoute redirectTo="/tools">
                    {withSuspense(<CommunityConversationPage />)}
                  </AdminRoute>
                )}
              />
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
              <Route
                path="admin/rag-terminology"
                element={
                  <AdminRoute>
                    {withSuspense(<RagTerminologyAdminPage />)}
                  </AdminRoute>
                }
              />
              <Route path="tools" element={withSuspense(<ToolsHubPage />)} />
              <Route
                path="favorites"
                element={
                  <AuthenticatedWorkspaceRoute>
                    {withSuspense(<FavoritesPage />)}
                  </AuthenticatedWorkspaceRoute>
                }
              />
              <Route
                path="favorites/:folderId"
                element={
                  <AuthenticatedWorkspaceRoute>
                    {withSuspense(<FavoritesPage />)}
                  </AuthenticatedWorkspaceRoute>
                }
              />
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
