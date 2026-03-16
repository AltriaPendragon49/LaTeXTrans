校验模式：cd frontend && npm run i18n:check
同步缺失 key 为待翻译：cd frontend && npm run i18n:sync
直接 CLI：node ./scripts/i18n/check.mjs --write-missing --fail-on-pending --report-path ./.i18n-cache/i18n-usage-report.json
产物报告默认输出到 frontend/.i18n-cache/i18n-usage-report.json，包含完整 key 列表、引用位置、warnings、errors。