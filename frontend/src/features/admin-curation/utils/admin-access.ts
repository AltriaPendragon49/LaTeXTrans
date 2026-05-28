/** 管理员角色集合 */
const ADMIN_ROLES = new Set(["admin", "super_admin", "community_admin", "curation_admin"])

/**
 * 判断用户是否拥有管理员角色
 * @param roles - 用户角色数组
 * @returns 是否拥有管理员权限
 */
export function hasAdminRole(roles: string[] | null | undefined): boolean {
  if (!roles?.length) {
    return false
  }

  return roles.some((role) => ADMIN_ROLES.has(String(role).trim().toLowerCase()))
}
