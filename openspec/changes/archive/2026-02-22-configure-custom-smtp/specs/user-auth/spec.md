## MODIFIED Requirements
### Requirement: User Registration
系统 SHALL 支持新用户通过邮箱密码进行注册。

#### Scenario: 用户注册成功
- **WHEN** 用户在注册页面输入有效邮箱和密码
- **AND** 点击注册按钮
- **THEN** 系统调用 Supabase Auth signUp()
- **AND** 通过自定义 SMTP 服务发送确认邮件到用户邮箱（无需绕过 VPN 限制即可稳定触发）
- **AND** 显示"请查收确认邮件"提示
