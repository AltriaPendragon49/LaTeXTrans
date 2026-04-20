import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import ToolsHubPage from "@/pages/tools-hub"

type MockAuthState = {
  user: {
    roles?: string[]
  } | null
}

let mockAuthState: MockAuthState = {
  user: null,
}

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuthState,
}))

describe("ToolsHubPage", () => {
  beforeEach(async () => {
    mockAuthState = {
      user: null,
    }
    await i18n.changeLanguage("en")
  })

  it("shows only workspace tools for non-admin users", () => {
    render(
      <MemoryRouter>
        <ToolsHubPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: /translate/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /history/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /glossary/i })).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /admin curation/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /admin tasks/i })).not.toBeInTheDocument()
  })

  it("surfaces admin tools inside the main workspace for admins", () => {
    mockAuthState = {
      user: {
        roles: ["community_admin"],
      },
    }

    render(
      <MemoryRouter>
        <ToolsHubPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole("link", { name: /submit arxiv ids or upload archives/i })).toHaveAttribute(
      "href",
      "/admin/curation",
    )
    expect(screen.getByRole("link", { name: /review queued, processing, completed/i })).toHaveAttribute(
      "href",
      "/admin/curation/tasks",
    )
  })
})
