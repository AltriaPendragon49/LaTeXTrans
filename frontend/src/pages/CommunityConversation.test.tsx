import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import CommunityConversationPage from "@/pages/CommunityConversation"

const createCommunityAgentRunMock = vi.fn()
const streamCommunityAgentRunMock = vi.fn()
const deleteCommunityAgentConversationMock = vi.fn()
const importCommunityPaperMock = vi.fn()
const listCommunityAgentConversationsMock = vi.fn()
const upsertCommunityAgentConversationMock = vi.fn()

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "tester@example.com" },
    isAuthenticated: true,
    loading: false,
  }),
}))

vi.mock("@/lib/community-api", () => ({
  createCommunityAgentRun: (...args: unknown[]) => createCommunityAgentRunMock(...args),
  streamCommunityAgentRun: (...args: unknown[]) => streamCommunityAgentRunMock(...args),
  deleteCommunityAgentConversation: (...args: unknown[]) =>
    deleteCommunityAgentConversationMock(...args),
  importCommunityPaper: (...args: unknown[]) => importCommunityPaperMock(...args),
  listCommunityAgentConversations: (...args: unknown[]) =>
    listCommunityAgentConversationsMock(...args),
  upsertCommunityAgentConversation: (...args: unknown[]) =>
    upsertCommunityAgentConversationMock(...args),
}))

describe("CommunityConversationPage streaming", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")

    listCommunityAgentConversationsMock.mockResolvedValue([])
    deleteCommunityAgentConversationMock.mockResolvedValue({ deleted: true })
    upsertCommunityAgentConversationMock.mockImplementation(async (record: unknown) => record)
    importCommunityPaperMock.mockResolvedValue({ paper_id: "paper-1", reused: true, imported: false })
    createCommunityAgentRunMock.mockRejectedValue(
      new Error("blocking community agent endpoint should not be used here"),
    )

    streamCommunityAgentRunMock.mockImplementation(
      async (
        _payload: unknown,
        { onEvent }: { onEvent: (event: Record<string, unknown>) => void },
      ) => {
        const finalRun = {
          run_id: "run-stream-1",
          status: "completed",
          intent: "answer",
          mode: "chat",
          message: "Hello world",
          summary: "Hello world",
          citations: [
            {
              id: "paper-1",
              title: "Graph Neural Networks for Molecular Property Prediction",
              source: "community",
              paper_id: "paper-1",
              snippet: "A paper about graph neural network methods for molecules.",
            },
          ],
          tool_trace: [
            {
              id: "trace-1",
              kind: "search",
              label: "Community paper search",
              provider: "community_search_papers",
              status: "completed",
            },
          ],
          action: {
            type: "navigate_paper",
            paper_id: "paper-1",
            task_id: "task-1",
            auto_started_translation: true,
          },
        }

        onEvent({
          type: "status",
          run_id: "run-stream-1",
          sequence: 1,
          data: { status: "running" },
        })
        onEvent({
          type: "assistant_delta",
          run_id: "run-stream-1",
          sequence: 2,
          data: { delta: "Hello" },
        })

        await new Promise((resolve) => window.setTimeout(resolve, 10))

        onEvent({
          type: "citation",
          run_id: "run-stream-1",
          sequence: 3,
          data: {
            citation: finalRun.citations[0],
          },
        })
        onEvent({
          type: "tool_result",
          run_id: "run-stream-1",
          sequence: 4,
          data: {
            trace: finalRun.tool_trace[0],
          },
        })
        onEvent({
          type: "action",
          run_id: "run-stream-1",
          sequence: 5,
          data: {
            action: finalRun.action,
          },
        })
        onEvent({
          type: "assistant_delta",
          run_id: "run-stream-1",
          sequence: 6,
          data: { delta: " world" },
        })
        onEvent({
          type: "complete",
          run_id: "run-stream-1",
          sequence: 7,
          data: {
            snapshot: finalRun,
          },
        })

        return finalRun
      },
    )
  })

  it("renders streamed assistant content and hydrates metadata inline", async () => {
    render(
      <MemoryRouter initialEntries={["/agent/conversation-1"]}>
        <Routes>
          <Route path="/agent/:conversationId" element={<CommunityConversationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const input = await screen.findByLabelText("Ask the paper agent")
    await userEvent.type(input, "Explain this paper in Chinese")
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))

    expect(await screen.findByText("Hello world")).toBeInTheDocument()
    expect(
      await screen.findByText("Graph Neural Networks for Molecular Property Prediction"),
    ).toBeInTheDocument()
    expect(screen.queryByText("Community paper search")).not.toBeInTheDocument()
    expect(await screen.findByRole("button", { name: "Open reader" })).toBeInTheDocument()

    await waitFor(() => {
      expect(streamCommunityAgentRunMock).toHaveBeenCalledTimes(1)
    })
    expect(createCommunityAgentRunMock).not.toHaveBeenCalled()
  })

  it("sends only conversation-scoped paper_id instead of leaking ids from other conversations", async () => {
    listCommunityAgentConversationsMock.mockResolvedValueOnce([
      {
        id: "other-conversation",
        title: "Other",
        created_at: "2026-03-28T00:00:00.000Z",
        updated_at: "2026-03-28T00:01:00.000Z",
        turns: [
          {
            id: "assistant-other",
            role: "assistant",
            content: "Other context",
            created_at: "2026-03-28T00:00:30.000Z",
            status: "completed",
            run: {
              run_id: "run-other",
              status: "completed",
              intent: "answer",
              mode: "chat",
              message: "Other context",
              summary: "Other context",
              citations: [
                {
                  id: "citation-other",
                  title: "Other paper",
                  source: "community",
                  paper_id: "paper-other",
                },
              ],
              tool_trace: [],
              action: {
                type: "navigate_paper",
                paper_id: "paper-other",
              },
            },
            error: null,
          },
        ],
      },
      {
        id: "conversation-scoped",
        title: "Scoped",
        created_at: "2026-03-28T00:00:00.000Z",
        updated_at: "2026-03-28T00:02:00.000Z",
        turns: [
          {
            id: "assistant-scoped",
            role: "assistant",
            content: "Scoped context",
            created_at: "2026-03-28T00:01:30.000Z",
            status: "completed",
            run: {
              run_id: "run-scoped",
              status: "completed",
              intent: "answer",
              mode: "chat",
              message: "Scoped context",
              summary: "Scoped context",
              citations: [
                {
                  id: "citation-scoped",
                  title: "Scoped paper",
                  source: "community",
                  paper_id: "paper-current",
                },
              ],
              tool_trace: [],
              action: {
                type: "navigate_paper",
                paper_id: "paper-current",
              },
            },
            error: null,
          },
        ],
      },
    ])

    streamCommunityAgentRunMock.mockImplementationOnce(
      async (
        payload: Record<string, unknown>,
        { onEvent }: { onEvent: (event: Record<string, unknown>) => void },
      ) => {
        expect(payload.paper_id).toBe("paper-current")
        expect(payload.paper_id).not.toBe("paper-other")

        const finalRun = {
          run_id: "run-scoped-1",
          status: "completed",
          intent: "answer",
          mode: "chat",
          message: "Scoped reply",
          summary: "Scoped reply",
          citations: [],
          tool_trace: [],
          action: null,
        }
        onEvent({
          type: "complete",
          run_id: "run-scoped-1",
          sequence: 1,
          data: { snapshot: finalRun },
        })
        return finalRun
      },
    )

    render(
      <MemoryRouter initialEntries={["/agent/conversation-scoped"]}>
        <Routes>
          <Route path="/agent/:conversationId" element={<CommunityConversationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.type(await screen.findByLabelText("Ask the paper agent"), "Continue with translation")
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))

    await waitFor(() => {
      expect(streamCommunityAgentRunMock).toHaveBeenCalledTimes(1)
    })
  })

  it("sends deep research mode and renders report-style output", async () => {
    streamCommunityAgentRunMock.mockImplementationOnce(
      async (
        payload: Record<string, unknown>,
        { onEvent }: { onEvent: (event: Record<string, unknown>) => void },
      ) => {
        const finalRun = {
          run_id: "run-research-1",
          status: "completed",
          intent: "answer",
          mode: "deep_research",
          message: "## Executive Summary\nA long-form cited report.",
          summary: "## Executive Summary\nA long-form cited report.",
          citations: [
            {
              id: "paper-2",
              title: "Retrieval-Augmented Generation Survey",
              source: "community",
              paper_id: "paper-2",
              snippet: "Survey evidence for report grounding.",
            },
          ],
          tool_trace: [],
          action: null,
          report: {
            format: "markdown",
            body_markdown: "## Executive Summary\nA long-form cited report.",
            evidence_count: 16,
            target_min_evidence: 15,
            target_max_evidence: 20,
            partial_coverage: false,
            coverage_note: "Coverage reached target breadth.",
          },
        }

        onEvent({
          type: "complete",
          run_id: "run-research-1",
          sequence: 1,
          data: {
            snapshot: finalRun,
          },
        })

        expect(payload).toMatchObject({ mode: "deep_research" })
        return finalRun
      },
    )

    render(
      <MemoryRouter initialEntries={["/agent/conversation-2"]}>
        <Routes>
          <Route path="/agent/:conversationId" element={<CommunityConversationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(await screen.findByRole("button", { name: "Deep research" }))
    await userEvent.type(screen.getByLabelText("Ask the paper agent"), "Produce a deep literature review")
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))

    expect(await screen.findByText("Deep research report")).toBeInTheDocument()
    expect(await screen.findByText("Coverage reached target breadth.")).toBeInTheDocument()

    await waitFor(() => {
      expect(streamCommunityAgentRunMock).toHaveBeenCalledTimes(1)
    })
  })

  it("keeps deep research in progress until a completed snapshot provides the report payload", async () => {
    streamCommunityAgentRunMock.mockImplementationOnce(
      async (
        payload: Record<string, unknown>,
        { onEvent }: { onEvent: (event: Record<string, unknown>) => void },
      ) => {
        const finalRun = {
          run_id: "run-research-2",
          status: "completed",
          intent: "answer",
          mode: "deep_research",
          message: "## Executive Summary\nGrounded final report.",
          summary: "## Executive Summary\nGrounded final report.",
          citations: [],
          tool_trace: [],
          action: null,
          report: {
            format: "markdown",
            body_markdown: "## Executive Summary\nGrounded final report.",
            evidence_count: 15,
            target_min_evidence: 15,
            target_max_evidence: 20,
            partial_coverage: false,
            coverage_note: "Coverage reached target breadth.",
          },
        }

        onEvent({
          type: "status",
          run_id: "run-research-2",
          sequence: 1,
          data: { status: "running", mode: "deep_research" },
        })
        onEvent({
          type: "assistant_delta",
          run_id: "run-research-2",
          sequence: 2,
          data: { delta: "Collecting evidence..." },
        })

        await new Promise((resolve) => window.setTimeout(resolve, 40))

        onEvent({
          type: "complete",
          run_id: "run-research-2",
          sequence: 3,
          data: {
            snapshot: finalRun,
          },
        })

        expect(payload).toMatchObject({ mode: "deep_research" })
        return finalRun
      },
    )

    render(
      <MemoryRouter initialEntries={["/agent/conversation-3"]}>
        <Routes>
          <Route path="/agent/:conversationId" element={<CommunityConversationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(await screen.findByRole("button", { name: "Deep research" }))
    await userEvent.type(screen.getByLabelText("Ask the paper agent"), "Need a complete deep research brief")
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))

    expect(
      await screen.findByText("The paper agent is thinking across the current conversation context."),
    ).toBeInTheDocument()
    expect(screen.queryByText("Deep research report")).not.toBeInTheDocument()
    expect(await screen.findByText("Deep research report")).toBeInTheDocument()
    expect(await screen.findByText("Coverage reached target breadth.")).toBeInTheDocument()
  })
})
