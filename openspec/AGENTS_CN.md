# OpenSpec 说明

AI 编码助手使用 OpenSpec 进行规范驱动开发的说明。

## TL;DR 快速清单

- 搜索现有作品：`openspec spec list --long`, `openspec list`（使用`rg`仅用于全文检索）
- 决定范围：新功能与修改现有功能
- 选择一个独特的“change-id”：kebab-case，动词主导（“add-”，“update-”，“remove-”，“refactor-”）
- 脚手架：`proposal.md`, `tasks.md`, `design.md`（仅在需要时）以及每个受影响功能的增量规格
- 写入增量：使用`## ADDED|MODIFIED|REMOVED|RENAMED Requirements`; include at least one `#### Scenario:`根据要求
- 验证：`openspec validate [change-id] --strict --no-interactive`并解决问题
- 请求批准：提案获得批准之前不要开始实施

## 三阶段工作流程

### 第一阶段：创造改变
当您需要时创建提案：
- 添加特性或功能
- 进行重大更改（API、架构）
- 改变架构或模式  
- 优化性能（改变行为）
- 更新安全模式

触发器（示例）：
- “帮我创建一个变更提案”
- “帮我计划改变”
- “帮我创建一个提案”
- “我想创建一个规范提案”
- “我想创建一个规范”

松散匹配指导：
- 包含以下之一：“提案”、“变更”、“规范”
- 使用以下之一：`create`、`plan`、`make`、`start`、`help`

跳过建议：
- 错误修复（恢复预期行为）
- 拼写错误、格式、评论
- 依赖项更新（不间断）
- 配置变更
- 测试现有行为

**工作流程**
1. 回顾`openspec/project.md`, `openspec list`, and `openspec list --specs`了解当前的背景。
2.选择独特的动词主导`change-id`以及脚手架“proposal.md”、“tasks.md”、可选“design.md”以及“openspec/changes/<id>/”下的规范增量。
3. 使用草稿规格增量`## ADDED|MODIFIED|REMOVED Requirements`至少有一个`#### Scenario:`根据要求。
4. 跑步`openspec validate <id> --strict --no-interactive`并在分享提案之前解决任何问题。

### 第二阶段：实施变革
将这些步骤作为 TODO 进行跟踪并一一完成。
1. **阅读proposal.md** - 了解正在构建的内容
2. **阅读 design.md** （如果存在） - 审查技术决策
3. **阅读tasks.md** - 获取实施清单
4. **按顺序执行任务** - 按顺序完成
5. **确认完成** - 确保每一项都在`tasks.md`在更新状态之前已完成
6. **更新清单** - 完成所有工作后，将每个任务设置为`- [x]`所以这个列表反映了现实
7. **批准门** - 在提案得到审查和批准之前不要开始实施

### 第 3 阶段：归档更改
部署后，创建单独的 PR 以：
- 移动`changes/[name]/`→ `更改/存档/YYYY-MM-DD-[名称]/`
- 更新`specs/`如果能力改变
- 使用`openspec archive <change-id> --skip-specs --yes`对于仅工具更改（始终显式传递更改 ID）
- 运行`openspec validate --strict --no-interactive`确认存档的更改通过检查

## 在执行任何任务之前

**上下文清单：**
- [ ] 阅读 `specs/[capability]/spec.md` 中的相关规范
- [ ] 检查待处理的更改`changes/`对于冲突
- [ ] 阅读`openspec/project.md`用于会议
- [ ] 运行`openspec list`查看活跃的变化
- [ ] 运行`openspec list --specs`查看现有功能

**创建规格之前：**
- 始终检查能力是否已经存在
- 更喜欢修改现有规范而不是创建重复项
- 使用`openspec show [spec]`审查当前状态
- 如果请求不明确，请在搭建脚手架之前提出 1-2 个澄清问题

### 搜索指导
- 枚举规格：`openspec spec list --long`（或者`--json`对于脚本）
- 枚举更改：`openspec list`（或者`openspec change list --json`- 已弃用但可用）
- 显示详细信息：
  - 规格：`openspec show <spec-id> --type spec`（使用`--json`用于过滤器）
  - 更改：`openspec show <change-id> --json --deltas-only`
- 全文搜索（使用 ripgrep）：`rg -n "Requirement:|Scenario:" openspec/specs`

## 快速入门

### CLI 命令

````bash
# 基本命令
openspec list # 列出活动更改
openspec list --specs # 列出规格
openspec show [item] # 显示更改或规格
openspec validate [item] # 验证更改或规格
openspec archive <change-id> [--yes|-y] # 部署后存档（对于非交互式运行添加 --yes）

# 项目管理
openspec init [path] # 初始化 OpenSpec
openspec update [path] # 更新指令文件

# 交互模式
openspec show # 提示选择
openspec validate # 批量验证模式

# 调试
openspec show [change] --json --deltas-only
openspec 验证 [更改] --strict --no-interactive
````

### 命令标志

-`--json`- 机器可读的输出
-`--type change|spec`- 消除项目歧义
-`--strict`- 全面验证
-`--no-interactive`- 禁用提示
-`--skip-specs`- 没有规格更新的存档
-`--yes`/`-y`- 跳过确认提示（非交互式存档）

## 目录结构

````
开放规范/
├── project.md # 项目约定
├── 规格/ # 当前真相 - 构建了什么
│ └── [capability]/ # 单一聚焦能力
│ ├── spec.md # 需求和场景
│ └── design.md # 技术模式
├── 变化/ # 提案 - 应该改变什么
│ ├── [改名]/
│ │ ├──proposal.md # 为什么、什么、影响
│ │ ├──tasks.md # 实施清单
│ │ ├── design.md # 技术决策（可选；参见标准）
│ │ └── 规格/ # Delta 变化
│ │ └── 【能力】/
│ │ └── spec.md # 添加/修改/删除
│ └── archive/ # 已完成的更改
````

## 创建变更提案

### 决策树

````
新要求？
├─ 错误修复恢复规范行为？ → 直接修复
├─ 打字/格式/注释错误？ → 直接修复  
├─ 新特性/功能？ → 创建提案
├─ 重大改变？ → 创建提案
├─ 架构改变？ → 创建提案
└─ 不清楚？ → 创建提案（更安全）
````

### 提案结构

1. **创建目录：**`changes/[change-id]/`（kebab-case，动词主导，独特）

2. **编写proposal.md:**
``降价
# 变更：[变更简要说明]

## 为什么
[关于问题/机会的 1-2 句话]

## 有何变化
- [变更项目列表]
- [用 **BREAKING** 标记重大更改]

## 影响
- 受影响的规格：[列出功能]
- 受影响的代码：[关键文件/系统]
````

3. **创建规格增量：** `specs/[capability]/spec.md`
``降价
## 添加的要求
### 要求：新功能
系统应提供...

####场景：成功案例
- **何时** 用户执行操作
- **那么**预期结果

## 修改要求
### 要求：现有功能
[完整修改要求]

## 删除的要求
### 要求：旧功能
**原因**：[为什么删除]
**迁移**：【如何处理】
````
如果多个功能受到影响，请在“changes/[change-id]/specs/<capability>/spec.md”下创建多个增量文件 - 每个功能一个。

4. **创建任务.md:**
``降价
## 1. 实施
- [ ] 1.1 创建数据库模式
- [ ] 1.2 实现API端点
- [ ] 1.3 添加前端组件
- [ ] 1.4 编写测试
````

5. **需要时创建design.md：**
创建`design.md`如果以下任何一项适用；否则省略它：
- 横切变化（多个服务/模块）或新的架构模式
- 新的外部依赖项或重大数据模型更改
- 安全性、性能或迁移复杂性
- 编码前技术决策带来的歧义

最小`design.md`骨架：
``降价
## 上下文
[背景、限制因素、利益相关者]

## 目标/非目标
- 目标：[...]
- 非目标：[...]

## 决定
- 决定：[什么以及为什么]
- 考虑的替代方案：[选项+理由]

## 风险/权衡
- [风险] → 缓解措施

## 迁移计划
[步骤，回滚]

## 开放问题
- [...]
````

## 规格文件格式

### 关键：场景格式

**正确**（使用####标题）：
``降价
####场景：用户登录成功
- **何时** 提供有效凭证
- **然后** 返回 JWT 令牌
````

**错误**（不要使用项目符号或粗体）：
``降价
- **场景：用户登录** ❌
**场景**：用户登录❌
### 场景：用户登录❌
````

每个需求必须至少有一个场景。

### 要求措辞
- 使用 SHALL/MUST 来满足规范性要求（除非故意不规范，否则避免使用 should/may）

### 达美航空运营

-`## ADDED Requirements`- 新功能
-`## MODIFIED Requirements`- 行为改变
-`## REMOVED Requirements`- 已弃用的功能
-`## RENAMED Requirements`- 姓名变更

标头匹配`trim(header)`- 空白被忽略。

#### 何时使用 ADDED 与 MODIFIED
- 添加：引入了可以单独作为要求的新功能或子功能。当更改是正交的（例如，添加“斜线命令配置”）时，首选“添加”，而不是更改现有需求的语义。
- 修改：更改现有需求的行为、范围或验收标准。始终粘贴完整的、更新的需求内容（标题+所有场景）。归档程序将用您在此处提供的内容替换整个要求；部分增量将删除以前的详细信息。
- RENAMED：仅在名称更改时使用。如果您还更改行为，请使用 RENAMED（名称）加上 MODIFIED（内容）引用新名称。

常见陷阱：使用 MODIFIED 添加新的关注点而不包含以前的文本。这会导致存档时细节丢失。如果您没有明确更改现有要求，请在“已添加”下添加新要求。

正确编写修改的需求：
1) 在 `openspec/specs/<capability>/spec.md` 中找到现有需求。
2）复制整个需求块（来自`### Requirement: ...`通过其场景）。
3）粘贴到下面`## MODIFIED Requirements`并进行编辑以反映新的行为。
4) 确保标题文本完全匹配（空格不敏感）并至少保留一个“#### Scenario:”。

重命名示例：
``降价
## 重命名的要求
- 来自：`### 要求：登录`
- TO：`### 要求：用户身份验证`
````

## 故障排除

### 常见错误

**“更改必须至少有一个增量”**
- 检查`changes/[name]/specs/`与 .md 文件一起存在
- 验证文件是否具有操作前缀（## 添加要求）

**“要求必须至少有一种场景”**
- 检查场景使用`#### Scenario:`格式（4 个主题标签）
- 不要使用项目符号或粗体作为场景标题

**静默场景解析失败**
- 需要精确格式：`#### 场景：名称`
- 调试：`openspec show [change] --json --deltas-only`

### 验证提示

````bash
# 始终使用严格模式进行全面检查
openspec 验证 [更改] --strict --no-interactive

# 调试增量解析
openspec 显示 [更改] --json | jq '.deltas'

# 检查具体要求
openspec 显示 [规范] --json -r 1
````

## 快乐路径脚本

````bash
# 1) 探索当前状态
openspec 规范列表 --long
开放规范列表
# 可选的全文搜索：
# rg -n "要求:|场景:" openspec/specs
# rg -n "^#|要求：" openspec/changes

# 2) 选择更改 id 和脚手架
更改=添加双因素身份验证
mkdir -p openspec/changes/$CHANGE/{specs/auth}
printf "## 为什么\n...\n\n## 发生了什么变化\n- ...\n\n## 影响\n- ...\n" > openspec/changes/$CHANGE/proposal.md
printf "## 1. 实现\n- [ ] 1.1 ...\n" > openspec/changes/$CHANGE/tasks.md

# 3) 添加增量（示例）
猫 > openspec/changes/$CHANGE/specs/auth/spec.md << 'EOF'
## 添加的要求
### 要求：双因素身份验证
用户必须在登录期间提供第二个因素。

#### 场景：需要 OTP
- **何时** 提供有效凭证
- **那么** 需要 OTP 质询
EOF

# 4) 验证
openspec 验证 $CHANGE --strict --no-interactive
````

## 多功能示例

````
openspec/更改/add-2fa-notify/
├── 提案.md
├── 任务.md
└── 规格/
    ├── 授权/
    │ └── spec.md # 新增：双因素认证
    └── 通知/
        └── spec.md # 添加：OTP 电子邮件通知
````

授权/规范.md
``降价
## 添加的要求
### 要求：双因素身份验证
...
````

通知/spec.md
``降价
## 添加的要求
### 要求：OTP 电子邮件通知
...
````

## 最佳实践

### 简单第一
- 默认为 <100 行新代码
- 单文件实现，直到被证明不足为止
- 避免没有明确理由的框架
- 选择无聊、经过验证的模式

### 复杂性触发器
仅通过以下方式增加复杂性：
- 性能数据显示当前解决方案太慢
- 具体规模要求（>1000个用户，>100MB数据）
- 需要抽象的多个经过验证的用例

### 清晰的参考文献
- 使用`file.ts:42`代码位置的格式
- 参考规范为“specs/auth/spec.md”
- 链接相关变更和 PR

### 能力命名
- 使用动词名词：`user-auth`、` payment-capture`
- 每项能力单一目的
- 10分钟理解规则
- 如果描述需要“AND”则拆分

### 更改 ID 命名
- 使用短横线大小写，简短且具有描述性：`add-two-factor-auth`
- 更喜欢动词主导的前缀：`add-`、`update-`、`remove-`、`refactor-`
- 确保唯一性；如果采用，请附加“-2”、“-3”等。

## 工具选择指南

|任务|工具|为什么 |
|------|------|-----|
|按模式查找文件 |全球|快速模式匹配 |
|搜索码内容 |查询 |优化的正则表达式搜索 |
|读取特定文件 |阅读 |直接文件访问 |
|探索未知范围 |任务|多步调查|

## 错误恢复

### 改变冲突
1. 跑步`openspec list`查看活跃的变化
2. 检查重叠规格
3. 与变更负责人协调
4. 考虑合并提案

### 验证失败
1. 运行`--strict`旗帜
2. 检查 JSON 输出以获取详细信息
3. 验证spec文件格式
4. 确保场景格式正确

### 缺少上下文
1.先阅读project.md
2.检查相关规格
3.查看最近的档案
4. 要求澄清

## 快速参考

### 阶段指标
-`changes/`- 已提议，尚未建成
-`specs/`- 构建并部署
-`archive/`- 已完成的更改

### 文件用途
-`proposal.md`- 为什么以及什么
-`tasks.md`- 实施步骤
-`design.md`- 技术决策
-`spec.md`- 要求和行为

### CLI 要点
````bash
openspec list # 正在进行什么？
openspec show [item] # 查看详情
openspec validate --strict --no-interactive # 正确吗？
openspec archive <change-id> [--yes|-y] # 标记完成（添加 --yes 以实现自动化）
````

请记住：规格就是事实。更改是建议。让它们保持同步。