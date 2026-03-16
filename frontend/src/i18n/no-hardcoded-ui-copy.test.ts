/// <reference types="node" />

import { readdirSync, readFileSync, statSync } from "fs"
import { join } from "path"
import { describe, expect, it } from "vitest"

const srcRoot = join(process.cwd(), "src")
const scanRoots = ["pages", "components", "contexts", "store"].map((dir) => join(srcRoot, dir))
const excludedFiles = new Set([
  join(srcRoot, "components", "log-viewer.tsx"),
])
const forbiddenPatterns = [
  /message\?\.includes/g,
  /\.includes\("download"\)/g,
  /\.includes\('download'\)/g,
  /t\(message\)/g,
  /translate\(message\)/g,
  /i18n\.t\(message\)/g,
  /response\?\.data\?\.detail/g,
]

function walk(dir: string): string[] {
  const entries = readdirSync(dir)
  const files: string[] = []

  for (const entry of entries) {
    const fullPath = join(dir, entry)
    const stats = statSync(fullPath)

    if (stats.isDirectory()) {
      files.push(...walk(fullPath))
      continue
    }

    if (!/\.(ts|tsx)$/.test(entry) || /\.test\./.test(entry) || excludedFiles.has(fullPath)) {
      continue
    }

    files.push(fullPath)
  }

  return files
}

function stripComments(source: string) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1")
}

describe("no hardcoded UI copy", () => {
  const files = scanRoots.flatMap((dir) => walk(dir))

  it("keeps UI source files free from hardcoded CJK copy", () => {
    const offenders = files
      .map((file) => {
        const content = stripComments(readFileSync(file, "utf8"))
        return /[\p{Script=Han}]/u.test(content) ? file : null
      })
      .filter(Boolean)

    expect(offenders).toEqual([])
  })

  it("blocks message-driven UI parsing patterns", () => {
    const offenders = files
      .map((file) => {
        const content = stripComments(readFileSync(file, "utf8"))
        return forbiddenPatterns.some((pattern) => pattern.test(content)) ? file : null
      })
      .filter(Boolean)

    expect(offenders).toEqual([])
  })
})
