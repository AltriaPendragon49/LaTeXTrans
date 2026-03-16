import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

describe("sidebar and sheet a11y copy", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
  })

  it("localizes the sidebar trigger label", () => {
    render(
      <SidebarProvider>
        <SidebarTrigger />
      </SidebarProvider>,
    )

    expect(screen.getByText("Toggle sidebar")).toBeInTheDocument()
  })

  it("localizes the sheet close label", () => {
    render(
      <Sheet open>
        <SheetContent>Body</SheetContent>
      </Sheet>,
    )

    expect(screen.getByText("Close")).toBeInTheDocument()
  })
})
