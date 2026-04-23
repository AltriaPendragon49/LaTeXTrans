import type { LocalAuthUser } from "@/lib/local-auth"

function normalizeIdentityValue(value?: string | null): string {
  return typeof value === "string" ? value.trim() : ""
}

export function getUserLoginInfo(user?: LocalAuthUser | null): string {
  return (
    normalizeIdentityValue(user?.login_identifier) ||
    normalizeIdentityValue(user?.email) ||
    normalizeIdentityValue(user?.phone)
  )
}
