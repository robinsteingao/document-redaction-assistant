# M6 发布说明：OCR 与产品组件接入

## 核心判断

M6 不追求一次性做成完整安装包，而是先把“本地运行产品”的关键组件边界打通：OCR 适配器、本地服务、桌面壳和脱敏包生成接口。

## 新增能力

- OCR 适配器支持注入本地 OCR 引擎，统一输出 `status / engine / text / confidence`。
- 未配置 OCR 引擎时返回 `unavailable`，不影响 DOCX、XLSX、文本型 PDF 和 TXT 处理。
- 本地服务提供 `GET /ocr-status` 和 `POST /build-package`。
- 桌面壳支持绑定 `service_url`，从静态壳升级为可连接本地服务的产品入口。
- CLI 增加 `serve-local` 和 `ocr-extract`，便于试点环境验证。

## 当前边界

- 当前仓库不内置真实 OCR 模型或 OCR 运行时。
- 扫描 PDF 的正式识别质量仍取决于后续选型的轻量 OCR 引擎。
- 本地服务当前定位为单机试点组件，不作为多用户后台服务暴露到局域网。

## 验收口径

- M6 专项测试 `3/3 OK`。
- 产品全量自动化测试覆盖 M1-M6 与端到端闭环，当前 `17/17 OK`。
- 后端沙箱导入 API 当前 `2/2 OK`。
- 本地 HTTP 服务 `/ocr-status`、`/build-package` 和 CORS 预检冒烟通过。
