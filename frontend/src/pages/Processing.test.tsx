import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import ProcessingPage from "@/pages/Processing"

const storeState = vi.hoisted(() => ({
  taskId: "task-1",
  status: "processing",
  stage: "translating",
  detailCode: "translation_running",
  detailParams: { current: 2, total: 5 },
  failureReasonCode: null as string | null,
  logs: [] as string[],
  taskWarnings: null as string | null,
  pollStatus: vi.fn(),
  stopPolling: vi.fn(),
  setTaskId: vi.fn(),
}))

vi.mock("@/store/useStore", () => ({
  useStore: () => storeState,
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { email: "test@example.com" },
  }),
}))

describe("ProcessingPage", () => {
  beforeEach(async () => {
    storeState.pollStatus.mockReset()
    storeState.stopPolling.mockReset()
    storeState.setTaskId.mockReset()
    storeState.status = "processing"
    storeState.stage = "translating"
    storeState.detailCode = "translation_running"
    storeState.detailParams = { current: 2, total: 5 }
    storeState.failureReasonCode = null
    storeState.logs = []
    storeState.taskWarnings = null
    await i18n.changeLanguage("en")
  })

  it("renders structured task copy without parsing raw backend messages", () => {
    render(
      <MemoryRouter initialEntries={["/processing?taskId=task-1"]}>
        <Routes>
          <Route path="/processing" element={<ProcessingPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getAllByText("Translating (2/5)")[0]).toBeInTheDocument()
    expect(screen.getAllByText("Translating").length).toBeGreaterThan(0)
  })

  it("renders the balanced processing workbench structure", () => {
    render(
      <MemoryRouter initialEntries={["/processing?taskId=task-1"]}>
        <Routes>
          <Route path="/processing" element={<ProcessingPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByTestId("processing-workbench")).toBeInTheDocument()
    expect(screen.getByTestId("processing-summary-panel")).toBeInTheDocument()
    expect(screen.getByTestId("processing-log-panel")).toBeInTheDocument()
  })
})
