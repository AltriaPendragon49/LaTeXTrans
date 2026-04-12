import type {
  CommunityConversationRecord,
  CommunityConversationTurn,
  CommunityConversationTurnRole,
} from "@/types/community"

const STORAGE_PREFIX = "community-agent-conversations:"

function nowIso() {
  return new Date().toISOString()
}

function normalizeScope(userId?: string | null) {
  return userId?.trim() || "guest"
}

export function getConversationStorageKey(userId?: string | null) {
  return `${STORAGE_PREFIX}${normalizeScope(userId)}`
}

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

export function saveConversationRecords(userId: string | null | undefined, records: CommunityConversationRecord[]): void {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(getConversationStorageKey(userId), JSON.stringify(records))
}

export function deriveConversationTitle(seedInput: string) {
  const normalized = seedInput.trim().replace(/\s+/g, " ")
  if (!normalized) {
    return "New chat"
  }
  return normalized.length > 48 ? `${normalized.slice(0, 48)}…` : normalized
}

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

export function buildConversationHistory(turns: CommunityConversationTurn[]) {
  return turns
    .filter((turn) => turn.role === "user" || turn.role === "assistant")
    .map((turn) => ({
      role: turn.role,
      content: turn.content,
    }))
}
