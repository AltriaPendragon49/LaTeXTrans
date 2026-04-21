import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { AppSidebar } from "@/layout/AppSidebar"

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

  it("shows community, translate, and workspace links but hides admin links for non-admin users", async () => {
    await i18n.changeLanguage("en")

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: "Community" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Paper Tool" })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Favorites" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Translate" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "History" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Settings" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Glossary" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /Admin curation/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "User" })).toBeInTheDocument()
  })

  it("shows favorites in the sidebar only for authenticated users", async () => {
    await i18n.changeLanguage("en")
    mockAuthState = {
      isAuthenticated: true,
      user: {
        roles: ["user"],
        display_name: "Researcher",
        email: "researcher@example.com",
        external_user_id: "researcher-1",
      },
    }

    render(
      <MemoryRouter initialEntries={["/favorites"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: "Favorites" })).toBeInTheDocument()
  })

  it("defaults to the collapsed shell on paper detail routes", async () => {
    await i18n.changeLanguage("en")

    const { container } = render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    const shell = container.querySelector("aside")
    expect(shell).toHaveAttribute("data-collapsed", "true")
    expect(screen.getByRole("button", { name: /expand sidebar/i })).toBeInTheDocument()
  })

  it("uses the collapsed brand button as the expand control", async () => {
    const user = userEvent.setup()
    await i18n.changeLanguage("en")

    const { container } = render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    const expandButton = screen.getByRole("button", { name: /expand sidebar/i })
    const shell = container.querySelector("aside")

    expect(expandButton).toHaveTextContent("PX")
    await user.click(expandButton)
    expect(shell).toHaveAttribute("data-collapsed", "false")
  })

  it("shows the collapsed expand cue when hovering anywhere inside the collapsed sidebar", async () => {
    const user = userEvent.setup()
    await i18n.changeLanguage("en")

    const { container } = render(
      <MemoryRouter initialEntries={["/paper/paper-1"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    const shell = container.querySelector("aside")
    const expandButton = screen.getByRole("button", { name: /expand sidebar/i })
    const collapsedMark = within(expandButton).getByText("PX")
    const expandCue = expandButton.querySelector('[data-sidebar-expand-cue="true"]')

    expect(shell).not.toBeNull()
    expect(expandCue).not.toBeNull()
    expect(collapsedMark).not.toHaveClass("opacity-0")
    expect(expandCue).toHaveClass("opacity-0")

    await user.hover(shell!)

    expect(collapsedMark).toHaveClass("opacity-0")
    expect(expandCue).toHaveClass("opacity-100")
  })

  it("opens the account menu from the bottom-left avatar and exposes account settings actions", async () => {
    const user = userEvent.setup()
    await i18n.changeLanguage("en")
    mockAuthState = {
      isAuthenticated: true,
      user: {
        roles: ["user"],
        display_name: "Researcher",
        email: "researcher@example.com",
        external_user_id: "researcher-1",
      },
    }

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole("button", { name: /researcher/i }))

    expect(screen.getByRole("link", { name: "Profile" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "History" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Glossary" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /Admin curation/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /Admin tasks/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument()
  })

  it("surfaces admin links inside the account menu instead of the main navigation", async () => {
    const user = userEvent.setup()
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
        <AppSidebar />
      </MemoryRouter>,
    )

    expect(screen.queryByRole("link", { name: /Admin curation/i })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /admin/i }))
    expect(screen.getByRole("link", { name: /Admin curation/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Admin tasks/i })).toBeInTheDocument()
  })

  it("supports explicit sidebar collapse and expand controls", async () => {
    const user = userEvent.setup()
    await i18n.changeLanguage("en")

    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    const shell = container.querySelector("aside")
    expect(shell).toHaveAttribute("data-collapsed", "false")

    await user.click(screen.getByRole("button", { name: /collapse sidebar/i }))

    expect(shell).toHaveAttribute("data-collapsed", "true")
    expect(screen.getByRole("button", { name: /expand sidebar/i })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /expand sidebar/i }))

    expect(shell).toHaveAttribute("data-collapsed", "false")
  })
})
