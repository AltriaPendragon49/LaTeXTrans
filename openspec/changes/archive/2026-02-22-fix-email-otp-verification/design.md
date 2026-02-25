# Design: Fix Email OTP Verification

## 问题分析

QQ 邮箱（及部分国内邮箱）的安全扫描器会自动访问邮件中的所有链接。Supabase 默认的确认链接是一次性 Token，被扫描器访问后即失效。Supabase 官方文档也承认了此问题，并推荐使用 OTP 验证码作为替代方案。

## 解决方案

### 方案选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| ❌ 中间页面（Supabase 推荐之一） | 不需要修改邮件模板 | 扫描器仍可能触发中间页面的请求 |
| ❌ 自定义 SMTP | 可改善送达率 | 配置复杂，不解决扫描器问题 |
| ✅ **OTP 验证码** | 彻底规避扫描器问题，UX 更好 | 需要修改前端 UI |

### 架构设计

```
用户注册 → Supabase 发送 OTP 邮件 → 用户在页面输入 8 位验证码 → verifyOtp() → 登录成功
```

### 改动范围

#### 1. Supabase Dashboard（手动配置）
- 修改 **Authentication → Email Templates → Confirm signup** 模板
- 将 `{{ .ConfirmationURL }}` 替换为 `{{ .Token }}`

#### 2. AuthContext.tsx
- 新增 `verifyOtp(email: string, token: string)` 方法
- 调用 `supabase.auth.verifyOtp({ email, token, type: 'email' })`
- 验证成功后触发 `loadUserSettings()`

#### 3. Login.tsx
- 修改 `emailSent` 状态下的渲染内容
- 新增 OTP 输入组件（单隐形输入框与 8 个视觉格子叠加的现代方案）
- UI 规范遵循 ui-ux-pro-max 移动端适配：
  - 44px 最小触摸目标
  - 自动聚焦与键盘导航
  - 粘贴自动填充
  - 150-300ms 过渡动画
  - 清晰的错误反馈
  - Loading 状态
  - 60 秒倒计时重发

### 不影响的功能
- 登录流程（signIn）：无改动
- 登出流程（signOut）：无改动
- 访客模式：无改动
- 已注册用户：不受影响（仅影响新注册流程）
