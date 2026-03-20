import { lazy, Suspense, type ReactNode } from "react"
import { Loader2 } from "lucide-react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ThemeProvider } from "@/theme/theme-provider"

import { AuthProvider } from "./contexts/AuthContext"

const Layout = lazy(() => import("./layout"))
const Dashboard = lazy(() => import("./pages/Dashboard"))
const CommunityFeedPage = lazy(() => import("./pages/CommunityFeed"))
const ProcessingPage = lazy(() => import("./pages/Processing"))
const ComparisonsPage = lazy(() => import("./pages/Comparisons"))
const Login = lazy(() => import("./pages/Login"))
const HistoryPage = lazy(() => import("./pages/History"))
const SettingsPage = lazy(() => import("./pages/Settings"))
const ProfilePage = lazy(() => import("./pages/Profile"))
const PaperDetailPage = lazy(() => import("./pages/PaperDetail"))

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

function Glossary() {
  const { t } = useTranslation()

  return <div>{t("glossary.glossary_3")}</div>
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
              <Route path="translate" element={withSuspense(<Dashboard />)} />
              <Route path="paper/:paperId" element={withSuspense(<PaperDetailPage />)} />
              <Route path="processing" element={withSuspense(<ProcessingPage />)} />
              <Route path="preview" element={withSuspense(<ComparisonsPage />)} />
              <Route path="history" element={withSuspense(<HistoryPage />)} />
              <Route path="glossary" element={<Glossary />} />
              <Route path="settings" element={withSuspense(<SettingsPage />)} />
              <Route path="profile" element={withSuspense(<ProfilePage />)} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
