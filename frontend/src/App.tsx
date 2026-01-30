import { BrowserRouter, Routes, Route } from "react-router-dom"
import Layout from "./layout"
import Dashboard from "./pages/Dashboard"
import ProcessingPage from "./pages/Processing"
import ComparisonsPage from "./pages/Comparisons"

function History() {
  return <div>History Page</div>
}

function Glossary() {
  return <div>Glossary Management</div>
}

function Settings() {
  return <div>Settings Page</div>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="processing" element={<ProcessingPage />} />
          <Route path="preview" element={<ComparisonsPage />} />
          <Route path="history" element={<History />} />
          <Route path="glossary" element={<Glossary />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
