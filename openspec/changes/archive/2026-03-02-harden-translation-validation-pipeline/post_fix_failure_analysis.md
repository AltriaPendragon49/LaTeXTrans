# Post-Fix 失败任务根因分析报告

> **日期:** 2026-02-25  
> **上下文:** `harden-translation-validation-pipeline` 全部 Task 完成后，三篇论文重试仍失败

---

## 总览

| 任务 ID | 论文 | 验证错误 | 编译错误 | 根因 |
|---------|------|---------|---------|------|
| `61308a1a` | 2601.00025 | 51 | `Undefined control sequence` | **修复能力不足** — `repair_math_delimiters` 只修1个 |
| `0dce92cc` | 2602.18680 | 51 | `\begin{document} ended by \end{list}` | **解析器 Bug** — `\newenvironment` 正则遗漏 end-code |
| `77864a3f` | 2602.18654 | **0** | `Extra }, or forgotten $` | **验证器盲区** — 严重翻译损坏未检测 |

---

## Bug #1：`\newenvironment` 解析正则缺陷（2602.18680）

### 调用链

```
parser.parse() → remove_comments() → _extract_newcommands() → get_newcommand_pattern()
```

### 根因

[get_newcommand_pattern()](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/utils.py#L1458-L1462) 用同一个正则匹配 `\newcommand` 和 `\newenvironment`：

```python
# utils.py:1460
newcommand = rf'\\(?:newcommand\*?|def|renewcommand|newenvironment|renewenvironment)
    {spaces}(?:\{{\\([a-zA-Z]+)\}}|\\([a-zA-Z]+)){spaces}
    (?:\[(\d)\])?{spaces}
    ({get_pattern_brace(4)})'   # ← 只有一个 {...} 参数组！
```

`\newcommand` 只有一个 `{body}` 参数，但 `\newenvironment` 有 **两个**：`{begin-code}{end-code}`。正则只匹配了 `{begin-code}`，**`{end-code}` 被遗漏**。

### 损坏过程

**原始文件 (68-75行)：**
```latex
\newenvironment{entry}
  {\begin{list}{}%          ← % 注释符保持行的连续性
        {\renewcommand{\makelabel}{\entrylabel}%
         \setlength{\labelwidth}{70pt}%
         \setlength{\leftmargin}{\labelwidth+\labelsep}%
        }%
  }%
  {\end{list}}              ← end-code，应该被包含在 placeholder 里
```

1. `remove_comments()` 剥除所有 `%` 注释符
2. `_extract_newcommands()` 使用正则匹配 — 只匹配到 `{\begin{list}{}...}` (begin-code)
3. `{\end{list}}` 没有被包含在 `<PLACEHOLDER_NEWCOMMAND_N>` 中
4. 游离的 `{\end{list}}` 变成输出文件第75行的 `\end{list}}`
5. 编译器报错：`\begin{document} ended by \end{list}`

**同一文件的 `\newenvironment{bsmallmatrix}` 也被损坏：**
```diff
  # 原始（正确 — 两行）
    {\left [\begin{smallmatrix}}
    {\end{smallmatrix}\right ] }
  # 翻译后（损坏 — end-code 丢失）
    {\left [\begin{smallmatrix}
  \end{smallmatrix}\right ] }
```

---

## Bug #2：验证器漏检严重翻译损坏（2602.18654）

### 损坏现象

翻译后第49行：
```latex
记$G_\infty$为$G$在$\Aut(X^*)$中的闭包。鞅方法表明，当$\mu$为紧群$G_\infty$上的
Haar概率测度时，有$})\\} = 0$g$固定$X^*$G_\infty$。定理1.5的证明...
```

LLM 翻译时严重损坏了复杂的集合构造器表达式 `$\mu(\{g\in G_\infty : g \text{ fixes } ...\}) = 0$`，**混入了英文残留碎片、丢失 `\{`/`\}` 配对、提前关闭 `$`**。

### 验证器失败原因

[_validate_math_delimiters()](file:///d:/future/antigravity/LaTexTrans/backend/app/services/agents/validator_agent.py#L259-L306) 只检查：
1. `$` 总数是否 `translation >= original` — ✅ 凑巧通过
2. bare math token 是否在 `$` 外 — ✅ 损坏处恰好在 `$` 区域内

[_validate_command()](file:///d:/future/antigravity/LaTexTrans/backend/app/services/agents/validator_agent.py#L176-L195) 只统计命令总数 — ✅ 凑巧通过

**缺失的检查：**
- 不检测翻译中的英文残留（如 `fixes at least one end of`）
- 不验证 `$...$` 内容的结构合法性（如 `$})\\}$` 明显非法）

---

## Bug #3：`repair_math_delimiters` 修复能力不足（2601.00025）

### 根因

[repair_math_delimiters()](file:///d:/future/antigravity/LaTexTrans/backend/app/services/agents/validator_agent.py#L308-L378) 第373行：

```python
            break  # Only fix first occurrence per call to be safe
```

每次调用只修复 **一个** bare math token 就退出。面对51个错误无能为力。

且缺少对以下情况的修复：
- LLM 删除的 `\begin{lemma}...\end{lemma}` 环境标签
- 丢失的 `<PLACEHOLDER_ENV_N>` 占位符
