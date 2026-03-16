import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs"
import path from "node:path"

import { NodeTypes, parse as parseVueTemplate } from "@vue/compiler-dom"
import { parse as parseVueSfc } from "@vue/compiler-sfc"
import ts from "typescript"

const DEFAULT_EXTENSIONS = new Set([".js", ".jsx", ".ts", ".tsx", ".vue"])
const DEFAULT_EXCLUDED_DIRECTORIES = new Set([
  ".git",
  ".idea",
  ".vscode",
  ".wrangler",
  "coverage",
  "dist",
  "build",
  "node_modules",
  "storybook-static",
])
const DEFAULT_EXCLUDED_FILE_PATTERNS = [/\.d\.ts$/i, /\.test\./i, /\.spec\./i]
const DEFAULT_TRANSLATION_CALLEES = new Set(["t", "translate", "i18n.t"])
const DEFAULT_PENDING_PREFIX = "[TODO_TRANSLATE] "
const KEY_CONTAINER_NAME_PATTERN = /(?:Keys|KeyMap)$/i
const TRANSLATION_KEY_SHAPE = /^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$/

export function normalizeOptions(rawOptions = {}) {
  const cwd = path.resolve(rawOptions.cwd ?? process.cwd())

  return {
    cwd,
    sourceRoot: path.resolve(cwd, rawOptions.sourceRoot ?? "src"),
    localesRoot: path.resolve(cwd, rawOptions.localesRoot ?? "src/locales"),
    localeFilename: rawOptions.localeFilename ?? "common.json",
    baseLocale: rawOptions.baseLocale ?? "en",
    writeMissing: Boolean(rawOptions.writeMissing),
    failOnPending: Boolean(rawOptions.failOnPending),
    reportPath:
      rawOptions.reportPath === null
        ? null
        : path.resolve(cwd, rawOptions.reportPath ?? ".i18n-cache/i18n-usage-report.json"),
    pendingPrefix: rawOptions.pendingPrefix ?? DEFAULT_PENDING_PREFIX,
    extensions: new Set(rawOptions.extensions ?? DEFAULT_EXTENSIONS),
    excludedDirectories: new Set(rawOptions.excludedDirectories ?? DEFAULT_EXCLUDED_DIRECTORIES),
    excludedFilePatterns: rawOptions.excludedFilePatterns ?? DEFAULT_EXCLUDED_FILE_PATTERNS,
    translationCallees: new Set(rawOptions.translationCallees ?? DEFAULT_TRANSLATION_CALLEES),
  }
}

export function auditI18nProject(rawOptions = {}) {
  const options = normalizeOptions(rawOptions)
  const usageMap = new Map()
  const unresolvedCalls = []
  const parseErrors = []
  const sourceFiles = collectSourceFiles(options.sourceRoot, options)

  for (const filePath of sourceFiles) {
    try {
      collectKeysFromFile(filePath, options, usageMap, unresolvedCalls)
    } catch (error) {
      parseErrors.push({
        file: toRelativePath(options.cwd, filePath),
        message: error instanceof Error ? error.message : String(error),
      })
    }
  }

  const localeCollection = loadLocales(options)
  const baseLocale = localeCollection.locales.get(options.baseLocale)

  if (!baseLocale) {
    throw new Error(
      `Base locale "${options.baseLocale}" not found under ${toRelativePath(options.cwd, options.localesRoot)}`,
    )
  }

  const usedKeys = [...usageMap.keys()].sort()
  const baseKeys = new Set(baseLocale.flattened.keys())
  const requiredKeys = new Set([...baseKeys, ...usedKeys])
  const writeSummary = {
    filesUpdated: [],
    addedPendingKeysByLocale: {},
  }

  if (options.writeMissing) {
    for (const localeRecord of localeCollection.locales.values()) {
      const missingKeys = [...requiredKeys].filter((key) => !localeRecord.flattened.has(key)).sort()

      if (missingKeys.length === 0) {
        continue
      }

      for (const key of missingKeys) {
        setLocaleMessage(localeRecord.messages, key, `${options.pendingPrefix}${key}`, localeRecord.style)
        localeRecord.flattened.set(key, `${options.pendingPrefix}${key}`)
      }

      writeLocaleFile(localeRecord)
      writeSummary.filesUpdated.push(toRelativePath(options.cwd, localeRecord.filePath))
      writeSummary.addedPendingKeysByLocale[localeRecord.locale] = missingKeys
    }
  }

  const locales = [...localeCollection.locales.values()].sort((left, right) =>
    left.locale.localeCompare(right.locale),
  )
  const missingUsedKeysByLocale = {}
  const missingStructureKeysByLocale = {}
  const extraStructureKeysByLocale = {}
  const pendingKeysByLocale = {}

  for (const localeRecord of locales) {
    const localeKeys = new Set(localeRecord.flattened.keys())
    const missingUsedKeys = usedKeys.filter((key) => !localeKeys.has(key))
    const missingStructureKeys = [...requiredKeys].filter((key) => !localeKeys.has(key)).sort()
    const extraStructureKeys = [...localeKeys].filter((key) => !requiredKeys.has(key)).sort()
    const pendingKeys = [...localeRecord.flattened.entries()]
      .filter(([, value]) => typeof value === "string" && value.startsWith(options.pendingPrefix))
      .map(([key]) => key)
      .sort()

    if (missingUsedKeys.length > 0) {
      missingUsedKeysByLocale[localeRecord.locale] = missingUsedKeys
    }

    if (missingStructureKeys.length > 0) {
      missingStructureKeysByLocale[localeRecord.locale] = missingStructureKeys
    }

    if (extraStructureKeys.length > 0) {
      extraStructureKeysByLocale[localeRecord.locale] = extraStructureKeys
    }

    if (pendingKeys.length > 0) {
      pendingKeysByLocale[localeRecord.locale] = pendingKeys
    }
  }

  const unusedBaseKeys = [...baseKeys].filter((key) => !usageMap.has(key)).sort()
  const usage = [...usageMap.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, references]) => ({ key, references }))

  const errorBuckets = {
    parseErrors,
    missingUsedKeysByLocale,
    missingStructureKeysByLocale,
    extraStructureKeysByLocale,
  }
  const warningBuckets = {
    unusedBaseKeys,
    pendingKeysByLocale,
    unresolvedCalls: unresolvedCalls.sort(compareLocations),
  }

  const hasErrors =
    parseErrors.length > 0 ||
    hasEntries(missingUsedKeysByLocale) ||
    hasEntries(missingStructureKeysByLocale) ||
    hasEntries(extraStructureKeysByLocale) ||
    (options.failOnPending && hasEntries(pendingKeysByLocale))

  const report = {
    generatedAt: new Date().toISOString(),
    config: {
      sourceRoot: toRelativePath(options.cwd, options.sourceRoot),
      localesRoot: toRelativePath(options.cwd, options.localesRoot),
      localeFilename: options.localeFilename,
      baseLocale: options.baseLocale,
      writeMissing: options.writeMissing,
      failOnPending: options.failOnPending,
      reportPath: options.reportPath ? toRelativePath(options.cwd, options.reportPath) : null,
      pendingPrefix: options.pendingPrefix,
      translationCallees: [...options.translationCallees].sort(),
    },
    summary: {
      filesScanned: sourceFiles.length,
      localesScanned: locales.length,
      usedKeyCount: usage.length,
      parseErrorCount: parseErrors.length,
      warningCount:
        unusedBaseKeys.length +
        countBucketEntries(pendingKeysByLocale) +
        unresolvedCalls.length,
      errorCount:
        parseErrors.length +
        countBucketEntries(missingUsedKeysByLocale) +
        countBucketEntries(missingStructureKeysByLocale) +
        countBucketEntries(extraStructureKeysByLocale) +
        (options.failOnPending ? countBucketEntries(pendingKeysByLocale) : 0),
      hasErrors,
    },
    usage,
    locales: locales.map((localeRecord) => ({
      locale: localeRecord.locale,
      file: toRelativePath(options.cwd, localeRecord.filePath),
      keyCount: localeRecord.flattened.size,
      pendingKeyCount: pendingKeysByLocale[localeRecord.locale]?.length ?? 0,
      style: localeRecord.style,
    })),
    writes: writeSummary,
    errors: errorBuckets,
    warnings: warningBuckets,
  }

  if (options.reportPath) {
    mkdirSync(path.dirname(options.reportPath), { recursive: true })
    writeFileSync(options.reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8")
  }

  return report
}

export function printAuditSummary(report) {
  const { summary, config, writes, errors, warnings } = report
  const missingUsedCount = countBucketEntries(errors.missingUsedKeysByLocale)
  const missingStructureCount = countBucketEntries(errors.missingStructureKeysByLocale)
  const extraStructureCount = countBucketEntries(errors.extraStructureKeysByLocale)

  logInfo(
    `Scanned ${summary.filesScanned} source files, ${summary.usedKeyCount} used keys, ${summary.localesScanned} locales.`,
  )

  if (writes.filesUpdated.length > 0) {
    logInfo(
      `Wrote pending placeholders into ${writes.filesUpdated.length} locale file(s): ${writes.filesUpdated.join(", ")}`,
    )
  }

  if (errors.parseErrors.length > 0) {
    logBucket("ERROR", "Parse failures", errors.parseErrors.map((entry) => `${entry.file} - ${entry.message}`))
  }

  if (missingUsedCount > 0) {
    logLocaleBucket("ERROR", "Missing used keys", errors.missingUsedKeysByLocale)
  }

  if (missingStructureCount > 0) {
    logLocaleBucket("ERROR", "Locale structure missing keys", errors.missingStructureKeysByLocale)
  }

  if (extraStructureCount > 0) {
    logLocaleBucket("ERROR", "Locale structure extra keys", errors.extraStructureKeysByLocale)
  }

  if (warnings.unusedBaseKeys.length > 0) {
    logBucket("WARN", "Unused base-locale keys", warnings.unusedBaseKeys)
  }

  if (hasEntries(warnings.pendingKeysByLocale)) {
    logLocaleBucket("WARN", "Pending translations", warnings.pendingKeysByLocale)
  }

  if (warnings.unresolvedCalls.length > 0) {
    logBucket(
      "WARN",
      "Dynamic translation calls skipped from extraction",
      warnings.unresolvedCalls.map((entry) => `${entry.file}:${entry.line}:${entry.column} (${entry.callee})`),
    )
  }

  if (summary.hasErrors) {
    logError(`Audit failed with ${summary.errorCount} error item(s).`)
  } else {
    logInfo(`Audit passed with ${summary.warningCount} warning item(s).`)
  }

  if (config.reportPath) {
    logInfo(`Report written to ${config.reportPath}`)
  }
}

function collectSourceFiles(rootDirectory, options) {
  if (!statExists(rootDirectory)) {
    throw new Error(`Source root does not exist: ${toRelativePath(options.cwd, rootDirectory)}`)
  }

  const files = []

  for (const entry of readdirSync(rootDirectory, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (options.excludedDirectories.has(entry.name)) {
        continue
      }

      files.push(...collectSourceFiles(path.join(rootDirectory, entry.name), options))
      continue
    }

    const filePath = path.join(rootDirectory, entry.name)
    const extension = path.extname(entry.name)

    if (!options.extensions.has(extension)) {
      continue
    }

    if (options.excludedFilePatterns.some((pattern) => pattern.test(entry.name))) {
      continue
    }

    files.push(filePath)
  }

  return files.sort((left, right) => left.localeCompare(right))
}

function collectKeysFromFile(filePath, options, usageMap, unresolvedCalls) {
  const source = readFileSync(filePath, "utf8")
  const extension = path.extname(filePath)

  if (extension === ".vue") {
    collectKeysFromVueFile(source, filePath, options, usageMap, unresolvedCalls)
    return
  }

  const scriptKind = getScriptKindForFile(filePath)
  collectKeysFromScript(source, filePath, scriptKind, options, usageMap, unresolvedCalls)
}

function collectKeysFromScript(source, filePath, scriptKind, options, usageMap, unresolvedCalls) {
  const sourceFile = ts.createSourceFile(filePath, source, ts.ScriptTarget.Latest, true, scriptKind)

  visitNode(sourceFile, (node) => {
    if (ts.isCallExpression(node)) {
      handleTranslationCall(node, sourceFile, options, usageMap, unresolvedCalls)
    }

    if (ts.isPropertyAssignment(node)) {
      handleStaticKeyProperty(node, sourceFile, usageMap, options.cwd)
    }

    if (ts.isJsxAttribute(node)) {
      handleJsxKeyAttribute(node, sourceFile, usageMap, options.cwd)
    }

    if (ts.isBindingElement(node)) {
      handleBindingElementKey(node, sourceFile, usageMap, options.cwd)
    }

    if (ts.isVariableDeclaration(node)) {
      handleKeyContainer(node, sourceFile, usageMap, options.cwd)
    }
  })
}

function collectKeysFromVueFile(source, filePath, options, usageMap, unresolvedCalls) {
  const { descriptor, errors } = parseVueSfc(source, { filename: filePath })

  if (errors.length > 0) {
    throw new Error(
      errors
        .map((entry) => (entry instanceof Error ? entry.message : JSON.stringify(entry)))
        .join("; "),
    )
  }

  for (const block of [descriptor.script, descriptor.scriptSetup].filter(Boolean)) {
    const paddedSource = padSourceToLocation(block.content, block.loc.start.line, block.loc.start.column)
    collectKeysFromScript(
      paddedSource,
      `${filePath}?${block.type}`,
      getScriptKindForVueBlock(block.lang),
      options,
      usageMap,
      unresolvedCalls,
    )
  }

  if (!descriptor.template) {
    return
  }

  const templateAst = parseVueTemplate(descriptor.template.content)

  walkVueNode(templateAst, (node) => {
    if (node.type === NodeTypes.INTERPOLATION) {
      collectKeysFromVueExpression(
        node.content.content,
        filePath,
        descriptor.template.loc.start.line,
        descriptor.template.loc.start.column,
        node.content.loc.start.line,
        node.content.loc.start.column,
        options,
        usageMap,
        unresolvedCalls,
      )
      return
    }

    if (node.type !== NodeTypes.ELEMENT) {
      return
    }

    for (const prop of node.props) {
      if (prop.type !== NodeTypes.DIRECTIVE || !prop.exp?.content) {
        continue
      }

      collectKeysFromVueExpression(
        prop.exp.content,
        filePath,
        descriptor.template.loc.start.line,
        descriptor.template.loc.start.column,
        prop.exp.loc.start.line,
        prop.exp.loc.start.column,
        options,
        usageMap,
        unresolvedCalls,
      )
    }
  })
}

function collectKeysFromVueExpression(
  expressionSource,
  filePath,
  blockStartLine,
  blockStartColumn,
  expressionLine,
  expressionColumn,
  options,
  usageMap,
  unresolvedCalls,
) {
  const absoluteLine = blockStartLine + expressionLine - 1
  const absoluteColumn = expressionLine === 1
    ? blockStartColumn + expressionColumn - 1
    : expressionColumn
  const paddedSource = padSourceToLocation(expressionSource, absoluteLine, absoluteColumn)

  collectKeysFromScript(
    paddedSource,
    `${filePath}?template`,
    ts.ScriptKind.TSX,
    options,
    usageMap,
    unresolvedCalls,
  )
}

function handleTranslationCall(node, sourceFile, options, usageMap, unresolvedCalls) {
  const callee = getCalleeName(node.expression)

  if (!callee || !options.translationCallees.has(callee)) {
    return
  }

  const key = getStaticStringValue(node.arguments[0])

  if (key == null) {
    if (isLikelyStaticKeyReference(node.arguments[0])) {
      return
    }

    unresolvedCalls.push({
      ...toRelativeLocation(options.cwd, getLocation(sourceFile, node.expression)),
      callee,
    })
    return
  }

  addUsage(usageMap, key, {
    ...toRelativeLocation(options.cwd, getLocation(sourceFile, node.arguments[0])),
    kind: "call",
    callee,
  })
}

function handleStaticKeyProperty(node, sourceFile, usageMap, cwd = process.cwd()) {
  const propertyName = getPropertyName(node.name)

  if (!isKeyLikeName(propertyName)) {
    return
  }

  const key = getStaticStringValue(node.initializer)

  if (key == null || !looksLikeTranslationKey(key)) {
    return
  }

  addUsage(usageMap, key, {
    ...toRelativeLocation(cwd, getLocation(sourceFile, node.initializer)),
    kind: "property",
    callee: "translationKey",
  })
}

function handleJsxKeyAttribute(node, sourceFile, usageMap, cwd = process.cwd()) {
  if (!isKeyLikeName(node.name.text)) {
    return
  }

  const key = getStaticStringValue(getJsxAttributeValue(node.initializer))

  if (key == null || !looksLikeTranslationKey(key)) {
    return
  }

  addUsage(usageMap, key, {
    ...toRelativeLocation(cwd, getLocation(sourceFile, node.initializer)),
    kind: "jsx-attribute",
    callee: node.name.text,
  })
}

function handleBindingElementKey(node, sourceFile, usageMap, cwd = process.cwd()) {
  if (!ts.isIdentifier(node.name) || !isKeyLikeName(node.name.text)) {
    return
  }

  const key = getStaticStringValue(node.initializer)

  if (key == null || !looksLikeTranslationKey(key)) {
    return
  }

  addUsage(usageMap, key, {
    ...toRelativeLocation(cwd, getLocation(sourceFile, node.initializer)),
    kind: "binding-default",
    callee: node.name.text,
  })
}

function handleKeyContainer(node, sourceFile, usageMap, cwd = process.cwd()) {
  const variableName = ts.isIdentifier(node.name) ? node.name.text : null

  if (!variableName || !KEY_CONTAINER_NAME_PATTERN.test(variableName) || !node.initializer) {
    return
  }

  collectStaticKeyCandidates(node.initializer, sourceFile, usageMap, "key-container", cwd)
}

function collectStaticKeyCandidates(node, sourceFile, usageMap, kind, cwd) {
  if (ts.isStringLiteralLike(node) && looksLikeTranslationKey(node.text)) {
    addUsage(usageMap, node.text, {
      ...toRelativeLocation(cwd, getLocation(sourceFile, node)),
      kind,
      callee: kind,
    })
    return
  }

  if (ts.isArrayLiteralExpression(node)) {
    for (const element of node.elements) {
      collectStaticKeyCandidates(element, sourceFile, usageMap, kind, cwd)
    }
    return
  }

  if (!ts.isObjectLiteralExpression(node)) {
    return
  }

  for (const property of node.properties) {
    if (!ts.isPropertyAssignment(property)) {
      continue
    }

    collectStaticKeyCandidates(property.initializer, sourceFile, usageMap, kind, cwd)
  }
}

function loadLocales(options) {
  if (!statExists(options.localesRoot)) {
    throw new Error(`Locales root does not exist: ${toRelativePath(options.cwd, options.localesRoot)}`)
  }

  const locales = new Map()

  for (const entry of readdirSync(options.localesRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) {
      continue
    }

    const filePath = path.join(options.localesRoot, entry.name, options.localeFilename)

    if (!statExists(filePath)) {
      continue
    }

    const messages = JSON.parse(readFileSync(filePath, "utf8"))
    const flattened = flattenMessages(messages)

    locales.set(entry.name, {
      locale: entry.name,
      filePath,
      messages,
      flattened,
      style: inferLocaleStyle(messages),
    })
  }

  return { locales }
}

function flattenMessages(messages, prefix = "", flattened = new Map()) {
  if (!isPlainObject(messages)) {
    if (prefix) {
      flattened.set(prefix, messages)
    }
    return flattened
  }

  for (const [key, value] of Object.entries(messages)) {
    const nextPrefix = prefix ? `${prefix}.${key}` : key

    if (isPlainObject(value)) {
      flattenMessages(value, nextPrefix, flattened)
      continue
    }

    flattened.set(nextPrefix, value)
  }

  return flattened
}

function inferLocaleStyle(messages) {
  return Object.keys(messages).some((key) => key.includes(".")) ? "flat" : "nested"
}

function setLocaleMessage(messages, key, value, style) {
  if (style === "flat") {
    messages[key] = value
    return
  }

  const segments = key.split(".")
  let pointer = messages

  for (const segment of segments.slice(0, -1)) {
    if (!isPlainObject(pointer[segment])) {
      pointer[segment] = {}
    }

    pointer = pointer[segment]
  }

  pointer[segments.at(-1)] = value
}

function writeLocaleFile(localeRecord) {
  mkdirSync(path.dirname(localeRecord.filePath), { recursive: true })
  writeFileSync(localeRecord.filePath, `${JSON.stringify(localeRecord.messages, null, 2)}\n`, "utf8")
}

function addUsage(usageMap, key, reference) {
  if (!usageMap.has(key)) {
    usageMap.set(key, [])
  }

  usageMap.get(key).push(reference)
}

function visitNode(node, visitor) {
  visitor(node)
  ts.forEachChild(node, (child) => visitNode(child, visitor))
}

function walkVueNode(node, visitor) {
  visitor(node)

  if (Array.isArray(node.children)) {
    for (const child of node.children) {
      walkVueNode(child, visitor)
    }
  }

  if (Array.isArray(node.branches)) {
    for (const branch of node.branches) {
      walkVueNode(branch, visitor)
    }
  }
}

function getScriptKindForFile(filePath) {
  const extension = path.extname(filePath).toLowerCase()

  switch (extension) {
    case ".js":
      return ts.ScriptKind.JS
    case ".jsx":
      return ts.ScriptKind.JSX
    case ".tsx":
      return ts.ScriptKind.TSX
    case ".ts":
    default:
      return ts.ScriptKind.TS
  }
}

function getScriptKindForVueBlock(lang) {
  switch ((lang ?? "js").toLowerCase()) {
    case "tsx":
      return ts.ScriptKind.TSX
    case "jsx":
      return ts.ScriptKind.JSX
    case "ts":
      return ts.ScriptKind.TS
    case "js":
    default:
      return ts.ScriptKind.JS
  }
}

function getCalleeName(expression) {
  if (ts.isIdentifier(expression)) {
    return expression.text
  }

  if (ts.isPropertyAccessExpression(expression) || ts.isPropertyAccessChain?.(expression)) {
    const left = getCalleeName(expression.expression)

    if (!left) {
      return null
    }

    return `${left}.${expression.name.text}`
  }

  if (ts.isParenthesizedExpression(expression)) {
    return getCalleeName(expression.expression)
  }

  return null
}

function getStaticStringValue(node) {
  if (!node) {
    return null
  }

  if (ts.isJsxExpression(node)) {
    return getStaticStringValue(node.expression)
  }

  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text
  }

  if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isTypeAssertionExpression(node)) {
    return getStaticStringValue(node.expression)
  }

  return null
}

function getPropertyName(nameNode) {
  if (ts.isIdentifier(nameNode) || ts.isStringLiteral(nameNode)) {
    return nameNode.text
  }

  return null
}

function getJsxAttributeValue(initializer) {
  if (!initializer) {
    return null
  }

  if (ts.isStringLiteral(initializer)) {
    return initializer
  }

  if (ts.isJsxExpression(initializer)) {
    return initializer.expression
  }

  return null
}

function getLocation(sourceFile, node) {
  const { line, character } = ts.getLineAndCharacterOfPosition(sourceFile, node.getStart(sourceFile))
  const file = sourceFile.fileName.split("?")[0]

  return {
    file,
    line: line + 1,
    column: character + 1,
  }
}

function compareLocations(left, right) {
  if (left.file !== right.file) {
    return left.file.localeCompare(right.file)
  }

  if (left.line !== right.line) {
    return left.line - right.line
  }

  if (left.column !== right.column) {
    return left.column - right.column
  }

  return left.callee.localeCompare(right.callee)
}

function looksLikeTranslationKey(value) {
  return TRANSLATION_KEY_SHAPE.test(value)
}

function isKeyLikeName(name) {
  return typeof name === "string" && /Key$/i.test(name)
}

function isLikelyStaticKeyReference(node) {
  if (!node) {
    return false
  }

  if (ts.isIdentifier(node)) {
    return isKeyLikeName(node.text) || node.text === "key"
  }

  if (ts.isPropertyAccessExpression(node) || ts.isPropertyAccessChain?.(node)) {
    return isKeyLikeName(node.name.text)
  }

  if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isTypeAssertionExpression(node)) {
    return isLikelyStaticKeyReference(node.expression)
  }

  return false
}

function countBucketEntries(bucket) {
  return Object.values(bucket).reduce((count, entries) => count + entries.length, 0)
}

function hasEntries(bucket) {
  return Object.keys(bucket).length > 0
}

function toRelativePath(cwd, filePath) {
  return path.relative(cwd, filePath).replace(/\\/g, "/") || "."
}

function toRelativeLocation(cwd, location) {
  return {
    ...location,
    file: toRelativePath(cwd, location.file),
  }
}

function padSourceToLocation(source, line, column) {
  return `${"\n".repeat(Math.max(line - 1, 0))}${" ".repeat(Math.max(column - 1, 0))}${source}`
}

function statExists(filePath) {
  try {
    statSync(filePath)
    return true
  } catch {
    return false
  }
}

function isPlainObject(value) {
  return value != null && typeof value === "object" && !Array.isArray(value)
}

function logInfo(message) {
  console.log(`[i18n] ${message}`)
}

function logError(message) {
  console.error(`[i18n] ${message}`)
}

function logBucket(level, title, entries) {
  if (entries.length === 0) {
    return
  }

  const printer = level === "ERROR" ? console.error : console.warn
  printer(`[i18n] ${title}:`)

  for (const entry of entries) {
    printer(`  - ${entry}`)
  }
}

function logLocaleBucket(level, title, bucket) {
  const printer = level === "ERROR" ? console.error : console.warn

  if (!hasEntries(bucket)) {
    return
  }

  printer(`[i18n] ${title}:`)

  for (const locale of Object.keys(bucket).sort()) {
    printer(`  - ${locale}: ${bucket[locale].join(", ")}`)
  }
}
