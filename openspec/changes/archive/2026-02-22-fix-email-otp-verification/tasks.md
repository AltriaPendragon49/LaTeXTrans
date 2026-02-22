# Tasks for Fix Email OTP Verification

## 1. Supabase 邮件模板配置
- [ ] 在 Supabase Dashboard 修改 Confirm Signup 邮件模板，将确认链接替换为 8 位数字验证码 `{{ .Token }}`。

## 2. AuthContext 扩展
- [x] 在 `AuthContext.tsx` 中新增 `verifyOtp(email, token)` 方法。
- [x] 调用 `supabase.auth.verifyOtp({ email, token, type: 'email' })` 完成验证。
- [x] 在 `AuthContextType` 接口中暴露 `verifyOtp` 方法。

## 3. Login 页面 OTP UI
- [x] 在 `Login.tsx` 中新增 `emailSent` 状态下的 OTP 输入界面，替换原来的"请点击验证链接"提示。
- [x] 实现支持 8 个视觉格子的单数字输入框方案，完美支持自动聚焦、回车提交、原生粘贴及移动端自适应。
- [x] 添加验证码验证按钮及 loading 状态。
- [x] 添加"重新发送验证码"按钮，带 60 秒倒计时。
- [x] 验证成功后自动跳转到首页。

## 4. 验证与测试
- [ ] 构建前端并部署到 Cloudflare Pages。
- [ ] 使用 QQ 邮箱注册新用户，验证 OTP 流程完整性。
- [ ] 确认不影响已有登录、登出、访客模式功能。
