import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarProvider } from "@/components/ui/sidebar"

describe("AppSidebar community shell", () => {
  it("prioritizes community and exposes a tools entry", async () => {
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
    expect(screen.queryByRole("link", { name: "Profile" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "History" })).not.toBeInTheDocument()
  })

  it("applies the custom sidebar width on the desktop shell wrapper", async () => {
    await i18n.changeLanguage("en")

    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <SidebarProvider>
          <AppSidebar />
        </SidebarProvider>
      </MemoryRouter>,
    )

    const desktopSidebar = container.querySelector("[data-variant='floating'][data-side='left']")
    expect(desktopSidebar).toHaveStyle({
      "--sidebar-width": "13.5rem",
      "--sidebar-width-icon": "3.75rem",
      "--sidebar-gap-offset": "0.75rem",
    })
  })
})
