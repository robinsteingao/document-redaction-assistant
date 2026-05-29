# M13 发布说明：报告交付与本地还原

## 核心判断

M13 打通客户侧闭环的最后一段：线上只返回脱敏评估报告，客户使用本地映射表生成还原预览。这样报告下载和本地还原演示不需要原始文件离开客户电脑。

## 新增能力

- 新增 `report_delivery.py`，生成脱敏评估报告、交付清单和本地还原预览。
- 新增 `build-report-delivery` 命令。
- 安装包新增 `app\build_report_delivery_demo.bat`。
- 后端沙箱导入结果新增 `report_summary`。
- 支持读取 Windows 常见 UTF-8 BOM JSON 评估结果和本地映射文件。

## 当前边界

- 报告交付包不包含本地映射表。
- 报告交付包不包含原始文件。
- 本地还原预览只在客户侧生成。

## 验收口径

- M13 报告交付专项测试 `2/2 OK`。
- 后端沙箱导入 API 含报告摘要测试 `4/4 OK`。
- 产品全量自动化测试覆盖 M1-M13 与端到端闭环，当前 `32/32 OK`。
- M13 目录包执行 `app\install_local.bat` 输出 `INSTALL_READINESS_OK`。
- M13 目录包执行 `app\run_sample_self_test.bat` 输出 `SAMPLE_SELF_TEST_OK`。
- M13 目录包执行 `app\build_report_delivery_demo.bat` 可生成 `redacted_evaluation_report.md`、`local_restored_report_preview.md` 和 `report_delivery_manifest.json`。
- M13 zip 解压后重复执行安装预检、样例自检和报告交付演示，均通过。
