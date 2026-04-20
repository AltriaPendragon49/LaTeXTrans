const ADMIN_ROLES = new Set(["admin", "super_admin", "community_admin", "curation_admin"])

export function hasAdminRole(roles: string[] | null | undefined): boolean {
  if (!roles?.length) {
    return false
  }

  return roles.some((role) => ADMIN_ROLES.has(String(role).trim().toLowerCase()))
}
