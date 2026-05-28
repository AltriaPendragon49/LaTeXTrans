/**
 * 对话记录工具函数
 * 所有函数均从 @/lib/community-agent-conversations 中重新导出，
 * 提供对话历史构建、种子对话记录创建和标题推导功能
 */
export {
  buildConversationHistory,
  createSeedConversationRecord,
  deriveConversationTitle,
} from "@/lib/community-agent-conversations"
