# Change: Fix Email OTP Verification

## Why
当前系统使用 Supabase 默认的邮件确认链接（Magic Link）来验证用户注册。QQ 邮箱等国内邮箱服务商的安全扫描机制会自动"点击"邮件中的链接进行反钓鱼检测，导致一次性确认 Token 被提前消耗。用户手动点击链接时已失效，无法完成注册。

## What Changes
- 将 Supabase 的 Confirm Signup 邮件模板从确认链接改为 8 位数字验证码（`{{ .Token }}`）。
- 在 `AuthContext.tsx` 中新增 `verifyOtp()` 方法，调用 `supabase.auth.verifyOtp()` API。
- 修改 `Login.tsx`，注册成功后将"已发送验证邮件"页面替换为内嵌式 OTP 验证码输入界面（单输入框+视觉格子渲染的现代方案），支持自动聚焦、粘贴、倒计时重发。

## Impact
- Affected specs: user-auth
- Affected code: `AuthContext.tsx`, `Login.tsx`
- Affected infra: Supabase Dashboard Email Templates
