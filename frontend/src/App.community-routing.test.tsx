import type { ReactNode } from "react"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { Outlet } from "react-router-dom"

import i18n from "@/i18n"
import App from "@/App"

type MockAuthState = {
  isAuthenticated: boolean
  loading: boolean
  user: {
    roles: string[]
  } | null
}

let mockAuthState: MockAuthState = {
  isAuthenticated: false,
  loading: false,
  user: null,
}

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useAuth: () => mockAuthState,
}))

vi.mock("@/pages/CommunityFeed", () => ({
  default: () => <div>Community feed page</div>,
}))

vi.mock("@/pages/PaperDetail", () => ({
  default: () => <div>Paper detail page</div>,
}))

vi.mock("@/pages/Processing", () => ({
  default: () => <div>Processing page</div>,
}))

vi.mock("@/pages/Comparisons", () => ({
  default: () => <div>Comparisons page</div>,
}))

vi.mock("@/pages/Login", () => ({
  default: () => <div>Login page</div>,
}))

vi.mock("@/pages/ToolsHub", () => ({
  default: () => <div>Tools page</div>,
}))

vi.mock("@/pages/Settings", () => ({
  default: () => <div>Settings page</div>,
}))

vi.mock("@/pages/Profile", () => ({
  default: () => <div>Profile page</div>,
}))

vi.mock("@/pages/CommunityAdminCuration", () => ({
  default: () => <div>Admin curation page</div>,
}))

vi.mock("@/pages/CommunityAdminCurationTasks", () => ({
  default: () => <div>Admin curation tasks page</div>,
}))

vi.mock("@/layout", () => ({
  default: () => (
    <div>
      <span>Layout shell</span>
      <Outlet />
    </div>
  ),
}))

describe("App community routing", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
    mockAuthState = {
      isAuthenticated: false,
      loading: false,
      user: null,
    }
  })

  it("routes the homepage to the community feed", async () => {
    window.history.pushState({}, "", "/")

    render(<App />)

    expect(await screen.findByText("Community feed page")).toBeInTheDocument()
  })

  it("redirects /agent to the community feed", async () => {
    window.history.pushState({}, "", "/agent")

    render(<App />)

    expect(await screen.findByText("Community feed page")).toBeInTheDocument()
  })

  it("redirects /agent/:conversationId to the community feed", async () => {
    window.history.pushState({}, "", "/agent/conversation-123")

    render(<App />)

    expect(await screen.findByText("Community feed page")).toBeInTheDocument()
  })

  it("redirects unauthenticated users from /admin/curation to login", async () => {
    window.history.pushState({}, "", "/admin/curation")

    render(<App />)

    expect(await screen.findByText("Login page")).toBeInTheDocument()
    expect(screen.queryByText("Admin curation page")).not.toBeInTheDocument()
  })

  it("redirects authenticated non-admin users away from /admin/curation", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/admin/curation")

    render(<App />)

    expect(await screen.findByText("Community feed page")).toBeInTheDocument()
    expect(screen.queryByText("Admin curation page")).not.toBeInTheDocument()
  })

  it("allows admin users to access /admin/curation", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["admin"] },
    }

    window.history.pushState({}, "", "/admin/curation")

    render(<App />)

    expect(await screen.findByText("Admin curation page")).toBeInTheDocument()
  })

  it("allows admin users to access /admin/curation/tasks", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["admin"] },
    }

    window.history.pushState({}, "", "/admin/curation/tasks")

    render(<App />)

    expect(await screen.findByText("Admin curation tasks page")).toBeInTheDocument()
  })

  it("keeps /translate routed through tools", async () => {
    window.history.pushState({}, "", "/translate")

    render(<App />)

    expect(await screen.findByText("Tools page")).toBeInTheDocument()
  })
})
