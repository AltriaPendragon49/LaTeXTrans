import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { BatchTranslation } from "@/components/BatchTranslation"
import HistoryPage from "@/pages/History"
import LoginPage from "@/pages/Login"
import ProfilePage from "@/pages/Profile"

const authState = vi.hoisted(() => ({
  isAuthenticated: false,
  loading: false,
  isSupabaseAvailable: true,
  user: null as null | { email?: string },
  error: null as null | string,
  signOut: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  verifyOtp: vi.fn().mockResolvedValue({ error: null }),
  clearError: vi.fn(),
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authState,
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    setTaskId: vi.fn(),
    setArxivId: vi.fn(),
  }),
}))

describe("remaining page i18n", () => {
  beforeEach(async () => {
    authState.isAuthenticated = false
    authState.loading = false
    authState.isSupabaseAvailable = true
    authState.user = null
    authState.error = null
    authState.signIn.mockReset()
    authState.signUp.mockReset()
    authState.verifyOtp.mockReset()
    authState.verifyOtp.mockResolvedValue({ error: null })
    authState.clearError.mockReset()
    authState.signOut.mockReset()
    await i18n.changeLanguage("en")
  })

  it("renders translated guest copy on the history page", () => {
    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("History")).toBeInTheDocument()
    expect(screen.getByText("Sign in to view translation history")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Go to sign in" })).toBeInTheDocument()
  })

  it("renders translated guest copy on the profile page", () => {
    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Not signed in")).toBeInTheDocument()
    expect(screen.getByText("Sign in to manage your account")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Go to sign in" })).toBeInTheDocument()
  })

  it("renders translated login form copy", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Welcome back")).toBeInTheDocument()
    expect(screen.getByText("Sign in to save your translation history and settings")).toBeInTheDocument()
    expect(screen.getByLabelText("Email address")).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Continue in guest mode" })).toBeInTheDocument()
  })

  it("renders translated auth-unavailable copy on the login page", () => {
    authState.isSupabaseAvailable = false

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Authentication service unavailable")).toBeInTheDocument()
    expect(screen.getByText("Supabase authentication is not configured for this system, so sign-in is unavailable.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Back to home (guest mode)" })).toBeInTheDocument()
  })

  it("renders translated batch translation tabs", () => {
    render(
      <MemoryRouter>
        <BatchTranslation />
      </MemoryRouter>,
    )

    expect(screen.getByRole("tab", { name: "Batch arXiv IDs" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Batch file upload" })).toBeInTheDocument()
    expect(screen.getByText(/Enter one arXiv ID per line/)).toBeInTheDocument()
    expect(screen.getByText(/Full URLs or plain IDs are supported\./)).toBeInTheDocument()
    expect(screen.getByText("arXiv ID list")).toBeInTheDocument()
  })
})
