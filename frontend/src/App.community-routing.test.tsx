import type { ReactNode } from "react"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { Navigate, Outlet } from "react-router-dom"

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

vi.mock("@/pages/home", () => ({
  default: () => <div>Community feed page</div>,
}))

vi.mock("@/pages/community-conversation", () => ({
  default: () => <div>Community conversation page</div>,
}))

vi.mock("@/pages/paper-detail", () => ({
  default: () => <div>Paper detail page</div>,
}))

vi.mock("@/pages/processing", () => ({
  default: () => <div>Processing page</div>,
}))

vi.mock("@/pages/preview", () => ({
  default: () => <div>Comparisons page</div>,
}))

vi.mock("@/pages/login", () => ({
  default: () => <div>Login page</div>,
}))

vi.mock("@/pages/translate", () => ({
  default: () => <div>Translate page</div>,
}))

vi.mock("@/pages/workspace-history", () => ({
  default: () => <div>Workspace history page</div>,
}))

vi.mock("@/pages/workspace-settings", () => ({
  default: () => <div>Workspace settings page</div>,
}))

vi.mock("@/pages/workspace-glossary", () => ({
  default: () => <div>Workspace glossary page</div>,
}))

vi.mock("@/pages/tools-hub", () => ({
  default: () => {
    const panel = new URLSearchParams(window.location.search).get("panel")

    if (panel === "history") {
      return <Navigate to="/workspace/history" replace />
    }
    if (panel === "settings") {
      return <Navigate to="/workspace/settings" replace />
    }
    if (panel === "glossary") {
      return <Navigate to="/workspace/glossary" replace />
    }

    return <Navigate to="/translate" replace />
  },
}))

vi.mock("@/pages/profile", () => ({
  default: () => <div>Profile page</div>,
}))

vi.mock("@/pages/community-admin-curation", () => ({
  default: () => <div>Admin curation page</div>,
}))

vi.mock("@/pages/community-admin-curation-tasks", () => ({
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

  it("routes /agent to the community conversation shell", async () => {
    window.history.pushState({}, "", "/agent")

    render(<App />)

    expect(await screen.findByText("Community conversation page")).toBeInTheDocument()
  })

  it("routes /agent/:conversationId to the community conversation shell", async () => {
    window.history.pushState({}, "", "/agent/conversation-123")

    render(<App />)

    expect(await screen.findByText("Community conversation page")).toBeInTheDocument()
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

  it("redirects unauthenticated users from /translate to login", async () => {
    window.history.pushState({}, "", "/translate")

    render(<App />)

    expect(await screen.findByText("Login page")).toBeInTheDocument()
    expect(screen.queryByText("Translate page")).not.toBeInTheDocument()
  })

  it("allows authenticated users to access /translate", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/translate")

    render(<App />)

    expect(await screen.findByText("Translate page")).toBeInTheDocument()
  })

  it("redirects unauthenticated users from /workspace/history to login", async () => {
    window.history.pushState({}, "", "/workspace/history")

    render(<App />)

    expect(await screen.findByText("Login page")).toBeInTheDocument()
    expect(screen.queryByText("Workspace history page")).not.toBeInTheDocument()
  })

  it("allows authenticated users to access /workspace/history", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/workspace/history")

    render(<App />)

    expect(await screen.findByText("Workspace history page")).toBeInTheDocument()
  })

  it("allows authenticated users to access /workspace/settings", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/workspace/settings")

    render(<App />)

    expect(await screen.findByText("Workspace settings page")).toBeInTheDocument()
  })

  it("allows authenticated users to access /workspace/glossary", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/workspace/glossary")

    render(<App />)

    expect(await screen.findByText("Workspace glossary page")).toBeInTheDocument()
  })

  it("keeps paper detail public for unauthenticated users", async () => {
    window.history.pushState({}, "", "/paper/paper-1")

    render(<App />)

    expect(await screen.findByText("Paper detail page")).toBeInTheDocument()
  })

  it("redirects legacy /history to the workspace history page", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/history")

    render(<App />)

    expect(await screen.findByText("Workspace history page")).toBeInTheDocument()
  })

  it("redirects legacy /glossary to the workspace glossary page", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/glossary")

    render(<App />)

    expect(await screen.findByText("Workspace glossary page")).toBeInTheDocument()
  })

  it("redirects legacy /settings to the workspace settings page", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/settings")

    render(<App />)

    expect(await screen.findByText("Workspace settings page")).toBeInTheDocument()
  })

  it("redirects legacy /tools?panel=glossary to the workspace glossary page", async () => {
    mockAuthState = {
      isAuthenticated: true,
      loading: false,
      user: { roles: ["user"] },
    }

    window.history.pushState({}, "", "/tools?panel=glossary")

    render(<App />)

    expect(await screen.findByText("Workspace glossary page")).toBeInTheDocument()
  })
})
