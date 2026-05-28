/**
 * 社区 Agent 对话本地存储工具
 * 在 localStorage 中持久化社区 Agent 的对话记录，按用户 ID 分区
 */
import type {
  CommunityConversationRecord,
  CommunityConversationTurn,
  CommunityConversationTurnRole,
} from "@/types/community"

const STORAGE_PREFIX = "community-agent-conversations:"

/** 生成 ISO 格式的当前时间戳 */
function nowIso() {
  return new Date().toISOString()
}

/** 标准化用户 ID 作为存储范围 */
function normalizeScope(userId?: string | null) {
  return userId?.trim() || "guest"
}

/**
 * 获取指定用户的对话存储键名
 * @param userId - 用户 ID（空值使用 "guest"）
 */
export function getConversationStorageKey(userId?: string | null) {
  return `${STORAGE_PREFIX}${normalizeScope(userId)}`
}

/** 标准化并校验单个对话轮次数据 */
function normalizeTurn(entry: unknown): CommunityConversationTurn | null {
  if (!entry || typeof entry !== "object") {
    return null
  }

  const turn = entry as Partial<CommunityConversationTurn>
  if ((turn.role !== "user" && turn.role !== "assistant") || typeof turn.content !== "string" || !turn.content.trim()) {
    return null
  }

  return {
    id: typeof turn.id === "string" && turn.id ? turn.id : `turn-${Math.random().toString(36).slice(2, 10)}`,
    role: turn.role as CommunityConversationTurnRole,
    content: turn.content,
    created_at: typeof turn.created_at === "string" && turn.created_at ? turn.created_at : nowIso(),
    run: turn.run ?? null,
    status: turn.status ?? "completed",
    error: turn.error ?? null,
  }
}

/** 标准化并校验对话记录数据 */
function normalizeRecord(entry: unknown): CommunityConversationRecord | null {
  if (!entry || typeof entry !== "object") {
    return null
  }

  const record = entry as Partial<CommunityConversationRecord>
  if (typeof record.id !== "string" || !record.id) {
    return null
  }

  const turns = Array.isArray(record.turns)
    ? record.turns.map(normalizeTurn).filter((item): item is CommunityConversationTurn => Boolean(item))
    : []

  return {
    id: record.id,
    title: typeof record.title === "string" && record.title.trim() ? record.title : "New chat",
    created_at: typeof record.created_at === "string" && record.created_at ? record.created_at : nowIso(),
    updated_at: typeof record.updated_at === "string" && record.updated_at ? record.updated_at : nowIso(),
    turns,
  }
}

/**
 * 从 localStorage 加载指定用户的对话记录列表
 * @param userId - 用户 ID
 * @returns 按 updated_at 降序排列的对话记录
 */
export function loadConversationRecords(userId?: string | null): CommunityConversationRecord[] {
  if (typeof window === "undefined") {
    return []
  }

  const raw = window.localStorage.getItem(getConversationStorageKey(userId))
  if (!raw) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed
      .map(normalizeRecord)
      .filter((item): item is CommunityConversationRecord => Boolean(item))
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
  } catch {
    return []
  }
}

/**
 * 保存对话记录到 localStorage
 * @param userId - 用户 ID
 * @param records - 对话记录数组
 */
export function saveConversationRecords(userId: string | null | undefined, records: CommunityConversationRecord[]): void {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(getConversationStorageKey(userId), JSON.stringify(records))
}

/**
 * 根据用户输入生成对话标题，超过 48 字符截断并添加省略号
 * @param seedInput - 用户首次输入内容
 */
export function deriveConversationTitle(seedInput: string) {
  const normalized = seedInput.trim().replace(/\s+/g, " ")
  if (!normalized) {
    return "New chat"
  }
  return normalized.length > 48 ? `${normalized.slice(0, 48)}…` : normalized
}

/**
 * 创建种子对话记录（使用首次用户输入）
 * @param conversationId - 对话 ID
 * @param seedInput - 用户首次输入内容
 */
export function createSeedConversationRecord(conversationId: string, seedInput: string): CommunityConversationRecord {
  const createdAt = nowIso()
  return {
    id: conversationId,
    title: deriveConversationTitle(seedInput),
    created_at: createdAt,
    updated_at: createdAt,
    turns: [
      {
        id: `${conversationId}-user-1`,
        role: "user",
        content: seedInput,
        created_at: createdAt,
        status: "completed",
      },
    ],
  }
}

/**
 * 插入或更新对话记录，写入 localStorage 并返回更新后的列表
 * @param userId - 用户 ID
 * @param record - 待插入/更新的对话记录
 * @returns 更新后的对话列表
 */
export function upsertConversationRecord(
  userId: string | null | undefined,
  record: CommunityConversationRecord,
): CommunityConversationRecord[] {
  const current = loadConversationRecords(userId)
  const next = [record, ...current.filter((entry) => entry.id !== record.id)].sort((left, right) =>
    right.updated_at.localeCompare(left.updated_at),
  )
  saveConversationRecords(userId, next)
  return next
}

/**
 * 将对话轮次数组转换为 LLM API 可用的历史消息格式
 * @param turns - 对话轮次数组
 * @returns 仅包含 role 和 content 的消息历史
 */
export function buildConversationHistory(turns: CommunityConversationTurn[]) {
  return turns
    .filter((turn) => turn.role === "user" || turn.role === "assistant")
    .map((turn) => ({
      role: turn.role,
      content: turn.content,
    }))
}
