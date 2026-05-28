/**
 * 管理员策展 API 服务层
 * 所有函数均从 @/lib/community-api 中重新导出，
 * 统一管理管理员策展相关的后端 API 调用
 */
export {
  batchDeleteAdminCurationJobs,
  deleteAdminCurationJob,
  getAdminCurationBatch,
  listAdminCurationJobs,
  submitAdminArxivCurationBatch,
  submitAdminUploadCurationBatch,
} from "@/lib/community-api"
