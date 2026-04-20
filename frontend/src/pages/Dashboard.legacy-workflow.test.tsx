import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import TranslatePage from "@/pages/translate"

const dashboardStoreState = vi.hoisted(() => ({
  taskId: null as string | null,
  status: "idle",
  config: {
    source_language: "en",
    target_language: "zh",
    advanced_config: {},
  },
  downloadProgress: 0,
  downloadStage: null as string | null,
  isDownloading: false,
  startArxivDownload: vi.fn(),
  startTranslation: vi.fn(),
  loadUserSettings: vi.fn(),
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
  }),
}))

vi.mock("@/features/translation-workflow/store/useTranslationStore", () => ({
  useTranslationStore: (selector?: (state: typeof dashboardStoreState) => unknown) =>
    selector ? selector(dashboardStoreState) : dashboardStoreState,
}))

vi.mock("@/features/translation-workflow/components/AdvancedConfig", () => ({
  AdvancedConfig: () => <div>Advanced Config</div>,
}))

vi.mock("@/features/translation-workflow/components/DropZone", () => ({
  DropZone: () => <div>DropZone</div>,
}))

vi.mock("@/features/translation-workflow/components/BatchTranslation", () => ({
  BatchTranslation: () => <div>BatchTranslation</div>,
}))

vi.mock("@/features/auth-shell/components/LoginPrompt", () => ({
  LoginPrompt: () => <div>LoginPrompt</div>,
}))

vi.mock("@/features/community-paper/components/CommunitySubmitPanel", () => ({
  CommunitySubmitPanel: () => <div>CommunitySubmitPanel</div>,
}))

describe("Translate page workflow", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    dashboardStoreState.loadUserSettings.mockReset()
    await i18n.changeLanguage("en")
  })

  it("shows only the old direct translation workflow and hides the community submit panel", () => {
    render(
      <MemoryRouter>
        <TranslatePage />
      </MemoryRouter>,
    )

    expect(screen.queryByText("CommunitySubmitPanel")).not.toBeInTheDocument()
    expect(screen.queryByText("Open legacy workflow")).not.toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "arXiv ID" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Local upload" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Batch translation" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Start translation" })).toBeInTheDocument()
  })
})
