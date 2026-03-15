import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AuthProvider } from "./contexts/AuthContext"
import Layout from "./layout"
import Dashboard from "./pages/Dashboard"
import ProcessingPage from "./pages/Processing"
import ComparisonsPage from "./pages/Comparisons"
import Login from "./pages/Login"
import HistoryPage from "./pages/History"
import SettingsPage from "./pages/Settings"
import ProfilePage from "./pages/Profile"

function Glossary() {
  return <div>术语库管理</div>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Login page without layout */}
          <Route path="/login" element={<Login />} />

          {/* Main app with layout */}
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="processing" element={<ProcessingPage />} />
            <Route path="preview" element={<ComparisonsPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="glossary" element={<Glossary />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="profile" element={<ProfilePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
