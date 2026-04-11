import fs from "node:fs"
import path from "node:path"

import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarProvider } from "@/components/ui/sidebar"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
  }),
}))

describe("brand surfaces", () => {
  it("uses the PaperX favicon and document title in index.html", () => {
    const indexPath = path.resolve(import.meta.dirname, "../index.html")
    const html = fs.readFileSync(indexPath, "utf8")

    expect(html).toContain('href="./paperx.png"')
    expect(html).toContain("<title>PaperX</title>")
  })

  it("shows the PaperX brand in the shared sidebar", async () => {
    await i18n.changeLanguage("en")

    render(
      <MemoryRouter initialEntries={["/"]}>
        <SidebarProvider>
          <AppSidebar />
        </SidebarProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText("PaperX")).toBeInTheDocument()
  })
})
