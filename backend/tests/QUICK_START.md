# 快速使用指南

## ✅ 当前状态

配置拦截代码已成功添加到 `translate.py` (第 154-171 行)!

## 🚀 下一步操作

### 1. 启动后端服务
```bash
# 确保在 backend 目录下
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 进行翻译测试

使用不同的高级配置进行翻译:

**测试场景**:
- [ ] 测试 1: 默认配置 (所有选项默认)
- [ ] 测试 2: 摘要模式 (`translation_mode = "abstract"`)
- [ ] 测试 3: XeLaTeX (`compile_strategy = "xelatex"`)
- [ ] 测试 4: 关闭验证 (`enable_verification = false`)
- [ ] 测试 5: 双语输出 (`bilingual_output = true`)
- [ ] 测试 6: 不同模型 (`translation_model = "gpt-4.1-mini"`)

### 3. 查看捕获的配置

每次翻译后,检查:
```bash
ls tests/captured_configs/
```

你会看到类似的文件:
```
config_a1b2c3d4_20260204_163045.json
config_e5f6g7h8_20260204_163512.json
...
```

### 4. 运行配置验证

```bash
python tests/config_validator.py tests/captured_configs/config_*.json
```

这会输出:
- ✅ 哪些配置生效了
- ⚠️ 哪些配置未生效
- 📊 多个配置的差异对比

### 5. 完成测试后撤销补丁

```bash
python tests/apply_interceptor_patch.py undo
```

## 📁 重要文件

- **拦截器位置**: `backend/app/api/routes/translate.py` (第 154-171 行)
- **配置输出**: `backend/tests/captured_configs/config_*.json`
- **验证器**: `backend/tests/config_validator.py`
- **测试样例**: `backend/tests/captured_configs/samples/`

## 🔍 验证示例

运行验证器后,你会看到类似输出:

```
================================================================================
配置验证报告: config_a1b2c3d4_20260204_163045.json
================================================================================

📊 总计: 7 项配置
   ✅ 生效: 7 项
   ⚠️  未生效: 0 项

配置项                   原始值              Agent值             状态      备注
----------------------------------------------------------------------------------------------------
translation_mode         abstract            1                   ✅        配置已生效
compile_strategy         xelatex             xelatex             ✅        配置已生效
enable_verification      False               False               ✅        配置已生效
bilingual_output         True                True                ✅        配置已生效
```

## ✅ 验收标准

完成以下测试后,可将 tasks.md 中的任务标记为完成:

- [ ] 所有 6 个测试场景都已运行
- [ ] 每个场景都生成了配置文件
- [ ] 验证器确认所有配置项都生效
- [ ] 没有未生效的配置项 (⚠️ = 0)

---

**开始测试吧!** 🎉
