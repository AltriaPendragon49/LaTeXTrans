import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarProvider } from "@/components/ui/sidebar"

type MockAuthState = {
  isAuthenticated: boolean
  user: {
    roles?: string[]
    display_name?: string | null
    email?: string | null
    external_user_id?: string | null
  } | null
}

let mockAuthState: MockAuthState = {
  isAuthenticated: false,
  user: null,
}

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuthState,
}))

describe("AppSidebar community shell", () => {
  beforeEach(() => {
    mockAuthState = {
      isAuthenticated: false,
      user: null,
    }
  })

  it("shows community and tools links but hides conversation/admin links for non-admin users", async () => {
    await i18n.changeLanguage("en")

    render(
      <MemoryRouter initialEntries={["/"]}>
        <SidebarProvider>
          <AppSidebar />
        </SidebarProvider>
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: "Community" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Paper tools" })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /Conversation/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /Admin curation/i })).not.toBeInTheDocument()
  })

  it("shows the admin curation link for admin users", async () => {
    await i18n.changeLanguage("en")
    mockAuthState = {
      isAuthenticated: true,
      user: {
        roles: ["community_admin"],
        display_name: "Admin",
        email: "admin@example.com",
        external_user_id: "admin-1",
      },
    }

    render(
      <MemoryRouter initialEntries={["/"]}>
        <SidebarProvider>
          <AppSidebar />
        </SidebarProvider>
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: /Admin curation/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Admin tasks/i })).toBeInTheDocument()
  })
})
