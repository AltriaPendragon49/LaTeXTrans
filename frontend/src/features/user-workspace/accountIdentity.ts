import type { LocalAuthUser } from "@/lib/local-auth"

/** 标准化身份标识值（去除空白） */
function normalizeIdentityValue(value?: string | null): string {
  return typeof value === "string" ? value.trim() : ""
}

/**
 * 获取用户的登录标识信息
 * 优先级：login_identifier > email > phone
 */
export function getUserLoginInfo(user?: LocalAuthUser | null): string {
  return (
    normalizeIdentityValue(user?.login_identifier) ||
    normalizeIdentityValue(user?.email) ||
    normalizeIdentityValue(user?.phone)
  )
}
