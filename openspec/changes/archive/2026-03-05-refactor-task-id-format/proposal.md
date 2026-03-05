# Change: Refactoring task_id Format

## Why
目前系统中 `task_id` 仅使用 `uuid.uuid4()` 生成 36 位随机字符串。这导致在分析、日志以及配置拦截等场景下：
- 无法直接通过 `task_id` 得知对应的论文 `arxiv_id` 以及创建时间。
- 配置拦截脚本 `config_capture.py` 需要随时自行解析并拼凑文件名 `f"{safe_arxiv_id}-{task_id[:6]}-{task_date}-{task_time}.json"`。如果修改 `task_id` 原有的生成方式，这种固化写死的截取前6位（`task_id[:6]`）的逻辑极易引发致命错误（例如将 `1901.06081` 截取为 `1901.0` 作为独立 ID），导致误读并破坏后续脚本对 ID 的检索。

## What Changes
将全站的 `task_id` 生成逻辑彻底更正变更为：
`arxiv_id-MMDD-HHmm-full_uuid`（对于无 arxiv_id 的本地上传任务使用 `upload-MMDD-HHmm-full_uuid`）。
## Impact
通过该变更：
1. 任何环节都可以轻松从 `task_id` 获取所有必要的定位信息（时间点，来源论文）。
2. 配置拦截逻辑 `config_capture.py` 将直接采纳并保存为 `f"{task_id}.json"`，彻底消除硬编码的字符串分割带来的一系列连锁读取失败。
3. 同步脚本 `sync_results.py` 将通过严谨的分隔符提取 UUID，不再由于截短前缀造成数据错误覆盖。
