import fs from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

describe("PaperX shell tokens", () => {
  it("defines the strong border and accent contrast tokens used by governed UI primitives", () => {
    const tokensPath = path.resolve(import.meta.dirname, "../styles/tokens.css")
    const css = fs.readFileSync(tokensPath, "utf8")

    expect(css).toContain("--px-shell-line-strong:")
    expect(css).toContain("--px-shell-accent-contrast:")
  })
})
