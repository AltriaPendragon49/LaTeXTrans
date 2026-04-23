import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { BatchTranslation } from "@/features/translation-workflow/components/BatchTranslation"
import HistoryPage from "@/pages/workspace-history"
import LoginPage from "@/pages/login"
import ProfilePage from "@/pages/profile"

const authState = vi.hoisted(() => ({
  isAuthenticated: false,
  loading: false,
  isAuthAvailable: true,
  user: null as null | {
    email?: string | null
    phone?: string | null
    login_identifier?: string | null
    external_user_id?: string | null
  },
  error: null as null | string,
  signOut: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  verifyOtp: vi.fn().mockResolvedValue({ error: null }),
  clearError: vi.fn(),
}))

const remainingPagesStoreState = vi.hoisted(() => ({
  setTaskId: vi.fn(),
  setArxivId: vi.fn(),
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authState,
}))

vi.mock("@/features/translation-workflow/store/useTranslationStore", () => ({
  useTranslationStore: (selector?: (state: typeof remainingPagesStoreState) => unknown) =>
    selector ? selector(remainingPagesStoreState) : remainingPagesStoreState,
}))

describe("remaining page i18n", () => {
  beforeEach(async () => {
    authState.isAuthenticated = false
    authState.loading = false
    authState.isAuthAvailable = true
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

    expect(screen.getByText("Sign in to view translation history")).toBeInTheDocument()
    expect(screen.getByText("Sign in to view and manage all translation task records")).toBeInTheDocument()
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

  it("renders the governed loading shell on the profile page while auth is resolving", () => {
    authState.loading = true

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Loading...")).toBeInTheDocument()
    expect(screen.getByTestId("loading-state-spinner")).toBeInTheDocument()
  })

  it("renders the persisted login identifier on the profile page without exposing the internal id", () => {
    authState.isAuthenticated = true
    authState.user = {
      email: null,
      login_identifier: "13800138000",
      external_user_id: "usr_local_1",
    }

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Profile")).toBeInTheDocument()
    expect(screen.getByText("Login information")).toBeInTheDocument()
    expect(screen.getByText("13800138000")).toBeInTheDocument()
    expect(screen.queryByText("usr_local_1")).not.toBeInTheDocument()
    expect(screen.queryByText("Email address")).not.toBeInTheDocument()
  })

  it("renders the login email on the profile page when it is available", () => {
    authState.isAuthenticated = true
    authState.user = {
      email: "reader@example.com",
      external_user_id: "usr_local_2",
    }

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    expect(screen.getByText("reader@example.com")).toBeInTheDocument()
    expect(screen.queryByText("usr_local_2")).not.toBeInTheDocument()
  })

  it("renders the intended chinese login copy on the profile page without question marks", async () => {
    await i18n.changeLanguage("zh")
    authState.isAuthenticated = true
    authState.user = {
      email: null,
      login_identifier: "13800138000",
      external_user_id: "usr_local_3",
    }

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    expect(screen.getByText("\u4e2a\u4eba\u8d44\u6599")).toBeInTheDocument()
    expect(screen.getByText("\u767b\u5f55\u4fe1\u606f")).toBeInTheDocument()
    expect(screen.getByText("13800138000")).toBeInTheDocument()
    expect(screen.queryByText("????")).not.toBeInTheDocument()
    expect(screen.queryByText("usr_local_3")).not.toBeInTheDocument()
  })

  it("renders translated login form copy", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Welcome back")).toBeInTheDocument()
    expect(screen.getByText("Sign in to save your translation history and settings")).toBeInTheDocument()
    expect(screen.getByLabelText("Email or phone number")).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Manage your account information" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Continue in guest mode" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Sign up now" })).not.toBeInTheDocument()
  })

  it("keeps the sign-in form available even when local auth availability flags are false", () => {
    authState.isAuthAvailable = false
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByText("Welcome back")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Manage your account information" })).toBeInTheDocument()
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
