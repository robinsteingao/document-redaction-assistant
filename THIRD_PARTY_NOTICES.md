# 第三方组件与分发声明

本项目原创部分适用 Apache-2.0。第三方软件不因此改为本项目的许可证；再分发时须保留各组件的版权、许可与适用声明。本清单不替代组件原始许可文本，不构成“全部依赖已无风险”的结论。

## 已核对的 0.27.0 核心 wheelhouse

以下为本轮本地待发布候选所用的具体版本。源码依赖约束并不锁定这些版本；后续构建必须按实际 wheelhouse 复核，不可直接复用本清单作为新二进制的许可证明。

| 组件 | 版本 | 上游许可声明 | 原始文本在 wheel 内的位置 |
| --- | --- | --- | --- |
| cryptography | 42.0.8 | Apache-2.0 OR BSD-3-Clause | `cryptography-42.0.8.dist-info/LICENSE`、`LICENSE.APACHE`、`LICENSE.BSD` |
| cffi | 1.17.1 | MIT | `cffi-1.17.1.dist-info/LICENSE` |
| pycparser | 2.22 | BSD-3-Clause | `pycparser-2.22.dist-info/LICENSE` |
| pypdf | 6.21.1 | BSD-3-Clause | `pypdf-6.21.1.dist-info/licenses/LICENSE` |
| defusedxml | 0.7.1 | Python Software Foundation License | `defusedxml-0.7.1.dist-info/LICENSE` |

cffi 分别提供 CPython 3.10、3.11、3.12、3.13 的 Windows x64 wheel；其余为 ABI 兼容或纯 Python wheel。wheel 文件存在不表示相应 Python 版本已完成运行验收。原始上游 wheel 不做修改，其内部版权与许可文本必须随 wheel 保留。

上游项目来源：[cryptography](https://github.com/pyca/cryptography)、[cffi](https://cffi.readthedocs.io/)、[pycparser](https://github.com/eliben/pycparser)、[pypdf](https://github.com/py-pdf/pypdf)、[defusedxml](https://github.com/tiran/defusedxml)。

## 已核对的内嵌与离线组件

以下只覆盖 2026-10-20 的 Windows x64 / CPython 3.11 离线候选。完整文本随对应 wheel、运行时或 LibreOffice 目录分发，不因写入本文件而改变其许可证。文件哈希见本地 `sources-manifest.json`；公开仓库不入库这些二进制。

| 组件 | 版本 | 许可声明 | 随包文本 |
| --- | --- | --- | --- |
| CPython | 3.11.9 | PSF License | `app/runtime/python/LICENSE.txt` |
| OpenSSL（cryptography 静态链接查询结果） | 3.2.2，4 Jun 2024 | Apache-2.0 | 上游 `openssl-3.2.2/LICENSE.txt`；wheel 未单列 OpenSSL NOTICE 文件 |
| cryptography 编译产物 | 42.0.8 | Apache-2.0 OR BSD-3-Clause | wheel 内 `LICENSE`、`LICENSE.APACHE`、`LICENSE.BSD` |
| rapidocr-onnxruntime | 1.4.4 | METADATA 声明 Apache-2.0 | wheel 随包；未另附独立模型许可文件 |
| 随 RapidOCR 分发的模型 | `ch_PP-OCRv4_det_infer.onnx`、`ch_PP-OCRv4_rec_infer.onnx`、`ch_ppocr_mobile_v2.0_cls_infer.onnx` | 由上述 wheel 一并分发 | 位于 `rapidocr_onnxruntime/models/` |
| onnxruntime | 1.31.0 | MIT | wheel 内 `onnxruntime/LICENSE`、`ThirdPartyNotices.txt` |
| pypdfium2 / PDFium | 5.14.0 | BSD-3-Clause、Apache-2.0 及依赖许可 | wheel 自带许可文件 |
| opencv-python | 4.11.0.86 | Apache-2.0 | wheel 内 `LICENSE.txt`、`LICENSE-3RD-PARTY.txt` |
| numpy | 1.26.4 | BSD-3-Clause，并声明其捆绑库 | wheel 内 `LICENSE.txt` |
| LibreOffice | 26.2.6 Windows x64 | MPL-2.0 及第三方附加条款 | `app/office_runtime/license.txt`、`NOTICE`、`LICENSE.html` |

其余离线安装 wheel（cffi、pycparser、pypdf、defusedxml、lxml、python-docx、openpyxl、Pillow、protobuf、pyclipper、shapely、PyYAML、six、tqdm、packaging、colorama、flatbuffers、typing-extensions、et-xmlfile）均未修改。其 METADATA 或 wheel 内许可文件随 wheel 保留；et_xmlfile 与 flatbuffers 的声明位于 METADATA，未另见独立许可文件。

OpenSSL 3.2.2 版权归 OpenSSL 项目贡献者。cryptography 的 Rust 绑定是该项目自身双许可编译产物，本包不另分发 Rust 工具链。LibreOffice 对应源码位于 https://download.documentfoundation.org/libreoffice/src/26.2.6/ ；MSI SHA256 为 `f9877032fd908beb9c0ddf06df4af5c2e85f419c42e14876c4cce5aae5fb2660`。

此核对是文件级与运行查询证据，不是法律意见，也不表示可以省略真实反馈或发布授权。

## 分发责任

- 源码和本项目 wheel/便携包须包含 `LICENSE`、`NOTICE`、本文件；核心依赖 wheel 保留其自身原始许可材料。
- 本文件描述的是已核对范围与尚缺事项，不是许可证兼容性的法律保证，不授予本来无权授予的权利。
- 发布仍须满足工程复核、实际平台运行验收、真实反馈门槛和独立推送/tag/Release 授权；本地许可落盘不等于公开发布。
