import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import Dashboard from "@/pages/Dashboard"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
  }),
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => ({
    taskId: null,
    status: "idle",
    config: {
      source_language: "en",
      target_language: "zh",
      advanced_config: {},
    },
    downloadProgress: 0,
    downloadStage: null,
    isDownloading: false,
    startArxivDownload: vi.fn(),
    startTranslation: vi.fn(),
    loadUserSettings: vi.fn(),
  }),
}))

vi.mock("@/components/AdvancedConfig", () => ({
  AdvancedConfig: () => <div>Advanced Config</div>,
}))

vi.mock("@/components/DropZone", () => ({
  DropZone: () => <div>DropZone</div>,
}))

vi.mock("@/components/BatchTranslation", () => ({
  BatchTranslation: () => <div>BatchTranslation</div>,
}))

vi.mock("@/components/LoginPrompt", () => ({
  LoginPrompt: () => <div>LoginPrompt</div>,
}))

vi.mock("@/components/community/CommunitySubmitPanel", () => ({
  CommunitySubmitPanel: () => <div>CommunitySubmitPanel</div>,
}))

describe("Dashboard legacy workflow", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("shows only the old direct translation workflow and hides the community submit panel", () => {
    render(
      <MemoryRouter>
        <Dashboard />
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
