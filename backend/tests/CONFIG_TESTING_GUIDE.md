
# 初始化测试环境
cd backend
python tests/test_config_interceptor.py

# 应用拦截代码 (自动备份)  
python tests/apply_interceptor_patch.py

# 启动后端,进行翻译测试...

# 验证配置是否生效
python tests/config_validator.py tests/captured_configs/config_*.json

# 测试完成后撤销
python tests/apply_interceptor_patch.py undo