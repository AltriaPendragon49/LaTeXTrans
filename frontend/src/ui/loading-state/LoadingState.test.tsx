import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { LoadingState } from "@/ui/loading-state/LoadingState"

describe("LoadingState", () => {
  it("renders inline loading copy with the governed spinner", () => {
    render(<LoadingState label="Loading workspace" />)

    expect(screen.getByText("Loading workspace")).toBeInTheDocument()
    expect(screen.getByTestId("loading-state-spinner")).toBeInTheDocument()
  })

  it("renders the panel layout with optional description", () => {
    render(
      <LoadingState
        layout="panel"
        label="Loading paper"
        description="Fetching the latest reader data."
      />,
    )

    expect(screen.getByText("Loading paper")).toBeInTheDocument()
    expect(screen.getByText("Fetching the latest reader data.")).toBeInTheDocument()
  })
})
