/**
 * 社区论文 API 服务层
 * 所有函数均从 @/lib/community-api 中重新导出，
 * 统一管理社区论文相关的后端 API 调用
 */
export {
  clearCommunityPaperDetailCache,
  createFavoriteFolder,
  createCommunityPaperDownloadSession,
  deleteFavoriteFolder,
  getFavoriteFolderPapers,
  getCachedCommunityPaperDetail,
  getCommunityPaperDetail,
  getCommunityPaperPreview,
  getCommunityPaperSimilar,
  getPaperFavoriteFolders,
  likeCommunityPaper,
  listFavoriteFolders,
  prefetchCommunityPaperDetail,
  primeCommunityPaperDetailCache,
  recordCommunityPaperView,
  renameFavoriteFolder,
  translateCommunityPaper,
  unlikeCommunityPaper,
  updatePaperFavoriteFolders,
} from "@/lib/community-api"
