import { lazy, Suspense, type ReactNode } from "react"
import { Loader2 } from "lucide-react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ThemeProvider } from "@/theme/theme-provider"

import { AuthProvider } from "./contexts/AuthContext"

const Layout = lazy(() => import("./layout"))
const CommunityFeedPage = lazy(() => import("./pages/CommunityFeed"))
const CommunityConversationPage = lazy(() => import("./pages/CommunityConversation"))
const ProcessingPage = lazy(() => import("./pages/Processing"))
const ComparisonsPage = lazy(() => import("./pages/Comparisons"))
const Login = lazy(() => import("./pages/Login"))
const ProfilePage = lazy(() => import("./pages/Profile"))
const PaperDetailPage = lazy(() => import("./pages/PaperDetail"))
const ToolsHubPage = lazy(() => import("./pages/ToolsHub"))

function RouteLoading() {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-[50vh] items-center justify-center gap-3 text-muted-foreground">
      <Loader2 className="h-5 w-5 animate-spin" />
      <span>{t("common.status.loading")}</span>
    </div>
  )
}

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<RouteLoading />}>{element}</Suspense>
}

function createConversationId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `conversation-${Date.now()}`
}

function AgentRedirect() {
  return <Navigate to={`/agent/${createConversationId()}`} replace />
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={withSuspense(<Login />)} />
            <Route path="/" element={withSuspense(<Layout />)}>
              <Route index element={withSuspense(<CommunityFeedPage />)} />
              <Route path="agent" element={<AgentRedirect />} />
              <Route path="agent/:conversationId" element={withSuspense(<CommunityConversationPage />)} />
              <Route path="tools" element={withSuspense(<ToolsHubPage />)} />
              <Route path="translate" element={<Navigate to="/tools?panel=translate" replace />} />
              <Route path="paper/:paperId" element={withSuspense(<PaperDetailPage />)} />
              <Route path="processing" element={withSuspense(<ProcessingPage />)} />
              <Route path="preview" element={withSuspense(<ComparisonsPage />)} />
              <Route path="history" element={<Navigate to="/tools?panel=history" replace />} />
              <Route path="glossary" element={<Navigate to="/tools?panel=glossary" replace />} />
              <Route path="settings" element={<Navigate to="/tools?panel=settings" replace />} />
              <Route path="profile" element={withSuspense(<ProfilePage />)} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
