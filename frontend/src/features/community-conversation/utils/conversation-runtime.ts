import type { TFunction } from "i18next"

import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityAgentRun,
  CommunityAgentStreamEvent,
  CommunityAgentToolTrace,
  CommunityConversationRecord,
  CommunityConversationTurn,
} from "@/types/community"

/**
 * 创建唯一的对话 ID
 * 优先使用 crypto.randomUUID，回退到时间戳方案
 */
export function createConversationId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `conversation-${Date.now()}`
}

/**
 * 根据 Agent run 结果创建 assistant 对话轮次
 */
export function createAssistantTurnFromRun(
  run: CommunityAgentRun,
  id: string = `assistant-${Date.now()}`,
  createdAt: string = new Date().toISOString(),
): CommunityConversationTurn {
  const assistantMessage = run.message ?? run.summary ?? ""
  return {
    id,
    role: "assistant",
    content: assistantMessage,
    created_at: createdAt,
    run,
    status: run.status === "failed" ? "failed" : "completed",
    error: run.status === "failed" ? assistantMessage || null : null,
  }
}

/**
 * 创建运行中的 assistant 轮次（用于流式输出时的占位）
 */
export function createRunningAssistantTurn(mode: CommunityAgentMode): CommunityConversationTurn {
  const createdAt = new Date().toISOString()
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
    created_at: createdAt,
    run: {
      run_id: `pending-${Date.now()}`,
      status: "running",
      intent: "answer",
      mode,
      message: "",
      summary: "",
      citations: [],
      tool_trace: [],
      action: null,
    },
    status: "running",
    error: null,
  }
}

/**
 * 更新或插入工具追踪记录
 */
function upsertTrace(
  currentTrace: CommunityAgentToolTrace[] | undefined,
  nextTrace: CommunityAgentToolTrace,
): CommunityAgentToolTrace[] {
  const existing = currentTrace ?? []
  return [...existing.filter((trace) => trace.id !== nextTrace.id), nextTrace]
}

/**
 * 更新或插入引文记录
 */
function upsertCitation(
  currentCitations: CommunityAgentCitation[] | undefined,
  nextCitation: CommunityAgentCitation,
): CommunityAgentCitation[] {
  const existing = currentCitations ?? []
  return [...existing.filter((citation) => citation.id !== nextCitation.id), nextCitation]
}

/**
 * 将流式事件应用到当前 Agent run 状态上
 * 根据事件类型（status、assistant_delta、citation、tool_start/result、action、complete、error）更新对应字段
 */
export function applyStreamEventToRun(
  currentRun: CommunityAgentRun,
  event: CommunityAgentStreamEvent,
): CommunityAgentRun {
  const nextRunId = event.run_id ?? currentRun.run_id
  const data = event.data ?? {}

  switch (event.type) {
    case "status": {
      const status = typeof data.status === "string" ? data.status : currentRun.status
      const intent = typeof data.intent === "string" ? data.intent : currentRun.intent
      return {
        ...currentRun,
        run_id: nextRunId,
        status: status as CommunityAgentRun["status"],
        intent: intent as CommunityAgentRun["intent"],
      }
    }
    case "assistant_delta": {
      const delta = typeof data.delta === "string" ? data.delta : ""
      const nextMessage = `${currentRun.message ?? currentRun.summary ?? ""}${delta}`
      return {
        ...currentRun,
        run_id: nextRunId,
        status: "running",
        message: nextMessage,
        summary: nextMessage,
      }
    }
    case "citation": {
      const citation = data.citation
      if (!citation || typeof citation !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        citations: upsertCitation(currentRun.citations, citation as CommunityAgentCitation),
      }
    }
    case "tool_start":
    case "tool_result": {
      const trace = data.trace
      if (!trace || typeof trace !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        tool_trace: upsertTrace(currentRun.tool_trace, trace as CommunityAgentToolTrace),
      }
    }
    case "action": {
      const action = data.action
      if (!action || typeof action !== "object") {
        return currentRun
      }
      return {
        ...currentRun,
        run_id: nextRunId,
        action: action as CommunityAgentRun["action"],
      }
    }
    case "complete": {
      const snapshot = data.snapshot
      if (!snapshot || typeof snapshot !== "object") {
        return currentRun
      }
      return snapshot as CommunityAgentRun
    }
    case "error": {
      const message =
        typeof data.message === "string"
          ? data.message
          : currentRun.message ?? currentRun.summary ?? ""
      return {
        ...currentRun,
        run_id: nextRunId,
        status: "failed",
        message,
        summary: message,
      }
    }
    default:
      return currentRun
  }
}

/**
 * 创建用户对话轮次
 */
export function createUserTurn(content: string): CommunityConversationTurn {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    created_at: new Date().toISOString(),
    status: "completed",
  }
}

/**
 * 从对话记录中获取作用域内的论文 ID
 * 倒序遍历 assistant 轮次，查找 action.paper_id 或 citations 中的 paper_id
 */
export function getConversationScopedPaperId(
  record: CommunityConversationRecord,
): string | undefined {
  for (let index = record.turns.length - 1; index >= 0; index -= 1) {
    const turn = record.turns[index]
    if (turn.role !== "assistant" || !turn.run) {
      continue
    }

    const actionPaperId = turn.run.action?.paper_id
    if (typeof actionPaperId === "string" && actionPaperId.trim()) {
      return actionPaperId.trim()
    }

    const citationPaperId = turn.run.citations?.find(
      (citation) => typeof citation.paper_id === "string" && citation.paper_id.trim(),
    )?.paper_id
    if (typeof citationPaperId === "string" && citationPaperId.trim()) {
      return citationPaperId.trim()
    }
  }

  return undefined
}

/**
 * 获取意图徽章的本地化标签
 */
export function getIntentBadgeLabel(
  t: TFunction,
  run: CommunityAgentRun | null | undefined,
) {
  switch (run?.intent) {
    case "search":
      return t("community.agent.intent.search", "Search")
    case "translate":
      return t("community.agent.intent.translate", "Translate")
    case "answer":
    default:
      return t("community.agent.intent.answer", "Answer")
  }
}

/**
 * 获取模式徽章的本地化标签
 */
export function getModeBadgeLabel(
  t: TFunction,
  mode: CommunityAgentMode | null | undefined,
) {
  return mode === "deep_research"
    ? t("community.agent.mode.deepResearch", "Deep research")
    : t("community.agent.mode.chat", "Chat")
}

/**
 * 构建运行中进度步骤列表
 * deep_research 模式包含额外的报告综合和最终化步骤
 */
export function buildRunningProgressSteps(
  t: (key: string) => string,
  externalSearchEnabled: boolean,
  mode: CommunityAgentMode,
) {
  if (mode === "deep_research") {
    const steps = [
      t("community.conversation.progressStepAnalyze"),
      t("community.conversation.progressStepSearchLocal"),
    ]
    if (externalSearchEnabled) {
      steps.push(t("community.conversation.progressStepSearchExternal"))
    }
    steps.push(
      t("community.conversation.progressStepSynthesizeReport"),
      t("community.conversation.progressStepFinalizeReport"),
    )
    return steps
  }

  const steps = [
    t("community.conversation.progressStepAnalyze"),
    t("community.conversation.progressStepSearchLocal"),
  ]

  if (externalSearchEnabled) {
    steps.push(t("community.conversation.progressStepSearchExternal"))
  }

  steps.push(
    t("community.conversation.progressStepCompose"),
    t("community.conversation.progressStepFinalize"),
  )

  return steps
}
