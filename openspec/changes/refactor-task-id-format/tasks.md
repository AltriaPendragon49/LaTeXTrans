# 任务 ID 发行机制变更工作任务明细

1. **核心发号器修改**
   - 目标文件: `backend/app/services/task_manager.py`
   - 工作内容: 将 `create_task` 方法内原本单薄的 `str(uuid.uuid4())` 改写为包含 arxiv 标识及当前日期的结构：`{safe_arxiv_id}-{MMDD}-{HHmm}-{uuid.uuid4()}`。

2. **移除非法的字符串切割 (配置拦截器)**
   - 目标文件: `backend/app/services/config_capture.py`
   - 工作内容: 舍弃原始组装逻辑 `f"{safe_arxiv_id}-{task_id[:6]}-{task_date}-{task_time}.json"`，变更为最安全可靠的 `f"{task_id}.json"`。消除 "读作 arxiv 的 id 前几位" 核心 Bug。

3. **同步结果脚本的 UUID 脱敏**
   - 目标文件: `scripts/sync_results.py`
   - 工作内容: 取消此前强行切割 `task_id[:8]` 读取前 8 位字符串的做作代码。如果需要短标识，必须以 `-` 切割并向后找寻真正的 UUID 进行展示或对应逻辑处理。

4. **确认现有测试是否正常**
   - 验证：运行 `pytest` 观察系统各节点对于新的长度更长的 `task_id` 有无异常行为并相应完善。
