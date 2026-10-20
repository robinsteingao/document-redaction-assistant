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

## 二进制内部组件：尚需补充核对

- 对上述 cryptography 42.0.8 Windows wheel 的运行查询返回 `OpenSSL 3.2.2 4 Jun 2024`。OpenSSL 3.2.2 上游 `LICENSE.txt` 使用 Apache-2.0；其官方文本位于 https://github.com/openssl/openssl/blob/openssl-3.2.2/LICENSE.txt 。
- 仅核对 wheel 的 METADATA 与顶层许可文件，不能证明其全部内嵌 OpenSSL、Rust、C 库组件及所需 attribution 均已核对完整。此项仍是实际二进制公开分发门槛，不能写成“第三方声明全部通过”。
- 正式分发前，发布负责人应补齐适用的内嵌组件许可与版权材料，记录具体 wheel 哈希，并让接收者能在分发包内取得所需完整文本。不得只留一个网络链接来代替必须随包提供的文本。

## 可选组件（不属于上述核心 wheelhouse）

Office 外发校验使用 `lxml`、`python-docx`、`openpyxl`，测试还可能使用 `pytest`、`Pillow`；本项目的 Python wheel 不内嵌这些库。安装者应保留实际安装版本携带的许可文件。

OCR 引擎、模型权重、Python 运行时、PDFium、LibreOffice 不包含在上述基础候选中。如将来加入离线包，必须逐版本、逐模型核对并随包提供相应许可与声明；不得从本清单推导其已获分发批准。

## 分发责任

- 源码和本项目 wheel/便携包须包含 `LICENSE`、`NOTICE`、本文件；核心依赖 wheel 保留其自身原始许可材料。
- 本文件描述的是已核对范围与尚缺事项，不是许可证兼容性的法律保证，不授予本来无权授予的权利。
- 发布仍须满足工程复核、实际平台运行验收、真实反馈门槛和独立推送/tag/Release 授权；本地许可落盘不等于公开发布。
