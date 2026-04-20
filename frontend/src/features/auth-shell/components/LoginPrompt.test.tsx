import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { LoginPrompt } from "@/features/auth-shell/components/LoginPrompt"

describe("LoginPrompt", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
  })

  it("renders semantic i18n keys instead of implicit string keys", () => {
    render(
      <MemoryRouter>
        <LoginPrompt
          messageKey="dashboard.batch.loginRequired"
          descriptionKey="dashboard.batch.loginRequiredDescription"
        />
      </MemoryRouter>,
    )

    expect(screen.getByText("Sign in to use batch translation")).toBeInTheDocument()
    expect(
      screen.getByText(
        "Batch translation is available to signed-in users and supports up to 9 arXiv papers or multiple local files at once.",
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument()
  })
})
