import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import os from "node:os"
import path from "node:path"

import { describe, expect, it } from "vitest"

import { auditI18nProject } from "./core.mjs"

function writeJson(filePath, value) {
  mkdirSync(path.dirname(filePath), { recursive: true })
  writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8")
}

function writeText(filePath, value) {
  mkdirSync(path.dirname(filePath), { recursive: true })
  writeFileSync(filePath, value, "utf8")
}

describe("auditI18nProject", () => {
  it("extracts keys from TSX and Vue, syncs missing locale keys, and reports unused keys", () => {
    const tempRoot = mkdtempSync(path.join(os.tmpdir(), "latextrans-i18n-"))

    try {
      writeText(
        path.join(tempRoot, "src", "components", "Example.tsx"),
        `
          import { useTranslation } from "react-i18next"

          export function Example() {
            const { t } = useTranslation()
            return (
              <section>
                <h1>{t("home.title")}</h1>
                <button>{translate("helper.label")}</button>
              </section>
            )
          }
        `,
      )

      writeText(
        path.join(tempRoot, "src", "i18n", "helper.ts"),
        `
          export const statusKeyMap = {
            ready: "task.status.ready",
          }

          export const UI_LANGUAGES = [
            { code: "en", translationKey: "language.name.en" },
            { code: "zh", translationKey: "language.name.zh" },
          ] as const
        `,
      )

      writeText(
        path.join(tempRoot, "src", "views", "Demo.vue"),
        `
          <template>
            <div :title="t('vue.cta')">{{ t("vue.title") }}</div>
          </template>
          <script setup lang="ts">
          const notice = i18n.t("vue.notice")
          </script>
        `,
      )

      writeJson(path.join(tempRoot, "src", "locales", "en", "common.json"), {
        "home.title": "Home",
        "helper.label": "Helper",
        "language.name.en": "English",
        "language.name.zh": "中文",
        "unused.orphan": "Unused",
      })

      writeJson(path.join(tempRoot, "src", "locales", "zh", "common.json"), {
        "home.title": "首页",
        "helper.label": "助手",
        "language.name.en": "英语",
        "language.name.zh": "中文",
      })

      const report = auditI18nProject({
        cwd: tempRoot,
        writeMissing: true,
        reportPath: ".i18n-cache/report.json",
      })

      const usedKeys = report.usage.map((entry) => entry.key)

      expect(usedKeys).toEqual([
        "helper.label",
        "home.title",
        "language.name.en",
        "language.name.zh",
        "task.status.ready",
        "vue.cta",
        "vue.notice",
        "vue.title",
      ])
      expect(report.summary.hasErrors).toBe(false)
      expect(report.writes.addedPendingKeysByLocale.en).toEqual([
        "task.status.ready",
        "vue.cta",
        "vue.notice",
        "vue.title",
      ])
      expect(report.writes.addedPendingKeysByLocale.zh).toEqual([
        "task.status.ready",
        "unused.orphan",
        "vue.cta",
        "vue.notice",
        "vue.title",
      ])
      expect(report.warnings.unusedBaseKeys).toEqual(["unused.orphan"])

      const zhLocale = readFileSync(path.join(tempRoot, "src", "locales", "zh", "common.json"), "utf8")

      expect(zhLocale).toContain('"vue.title": "[TODO_TRANSLATE] vue.title"')
      expect(zhLocale).toContain('"task.status.ready": "[TODO_TRANSLATE] task.status.ready"')
      expect(readFileSync(path.join(tempRoot, ".i18n-cache", "report.json"), "utf8")).toContain('"usedKeyCount": 8')
    } finally {
      rmSync(tempRoot, { force: true, recursive: true })
    }
  })
})
