import { beforeEach, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { getTaskCopy } from "@/i18n/task-copy"

describe("task copy mapping", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
  })

  it("renders structured translation detail from detail_code and params", () => {
    const copy = getTaskCopy(i18n.t.bind(i18n), {
      status: "processing",
      stage: "translating",
      detailCode: "translation_running",
      detailParams: { current: 2, total: 5 },
    })

    expect(copy.statusLabel).toBe("Translating")
    expect(copy.detailLabel).toBe("Translating (2/5)")
  })

  it("renders localized failure summaries from failure_reason_code", () => {
    const copy = getTaskCopy(i18n.t.bind(i18n), {
      status: "structure_invalid",
      stage: "compilation_failed",
      failureReasonCode: "structure_env_stack_mismatch",
    })

    expect(copy.failureLabel).toBe("The generated LaTeX structure is invalid")
  })
})
