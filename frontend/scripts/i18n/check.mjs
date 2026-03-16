#!/usr/bin/env node

import { auditI18nProject, normalizeOptions, printAuditSummary } from "./core.mjs"

function parseArgs(argv) {
  const options = {}

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]

    switch (argument) {
      case "--src":
      case "--source-root":
        options.sourceRoot = argv[index + 1]
        index += 1
        break
      case "--locales":
      case "--locales-root":
        options.localesRoot = argv[index + 1]
        index += 1
        break
      case "--locale-file":
        options.localeFilename = argv[index + 1]
        index += 1
        break
      case "--base-locale":
        options.baseLocale = argv[index + 1]
        index += 1
        break
      case "--report-path":
        options.reportPath = argv[index + 1]
        index += 1
        break
      case "--pending-prefix":
        options.pendingPrefix = argv[index + 1]
        index += 1
        break
      case "--write-missing":
        options.writeMissing = true
        break
      case "--fail-on-pending":
        options.failOnPending = true
        break
      case "--no-report":
        options.reportPath = null
        break
      case "--help":
      case "-h":
        printHelp()
        process.exit(0)
        break
      default:
        throw new Error(`Unknown argument: ${argument}`)
    }
  }

  return options
}

function printHelp() {
  const options = normalizeOptions()

  console.log(`Usage: node ./scripts/i18n/check.mjs [options]

Options:
  --source-root, --src <dir>       Source directory to scan (default: ${options.sourceRoot})
  --locales-root, --locales <dir>  Locale directory root (default: ${options.localesRoot})
  --locale-file <name>             Locale file name under each locale dir (default: ${options.localeFilename})
  --base-locale <code>             Canonical locale used for unused-key checks (default: ${options.baseLocale})
  --report-path <path>             JSON report output path (default: ${options.reportPath})
  --write-missing                  Write missing keys into locale files as pending placeholders
  --pending-prefix <text>          Placeholder prefix for newly inserted keys (default: ${options.pendingPrefix})
  --fail-on-pending                Treat pending placeholders as errors
  --no-report                      Skip report file generation
  --help, -h                       Show this help
`)
}

try {
  const report = auditI18nProject({
    cwd: process.cwd(),
    ...parseArgs(process.argv.slice(2)),
  })

  printAuditSummary(report)
  process.exit(report.summary.hasErrors ? 1 : 0)
} catch (error) {
  console.error(`[i18n] ${error instanceof Error ? error.message : String(error)}`)
  process.exit(1)
}
