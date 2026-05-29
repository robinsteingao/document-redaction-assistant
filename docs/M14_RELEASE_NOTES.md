# M14 发布说明：安装器外壳与客户验收包

## 核心判断

M14 不绑定 MSI/EXE 编译器，而是先交付可执行安装器外壳、图形化安装向导、客户验收清单和真实环境试装记录模板。这样可以先支撑客户试装和试点验收，再进入签名安装器。

## 新增能力

- 新增 `installer_assets.py`，生成安装器外壳和验收材料。
- 安装包新增 `setup.bat`。
- 安装包新增 `uninstall.bat`。
- 安装包新增 `installer_wizard\index.html`。
- 安装包新增 `customer_acceptance\ACCEPTANCE_CHECKLIST.md`。
- 安装包新增 `customer_acceptance\PILOT_SIGNOFF.md`。
- 安装包新增 `install_records\INSTALL_RECORD_TEMPLATE.md`。
- 安装包新增 `installer_manifest.json`。

## 当前边界

- 当前是脚本式便携安装器外壳，不是 MSI/EXE 安装器。
- 当前不写入 Windows 注册表。
- 卸载方式为备份本地输出后删除安装目录。

## 验收口径

- M14 安装器与验收包专项测试 `1/1 OK`。
- 产品全量自动化测试覆盖 M1-M14 与端到端闭环，当前 `33/33 OK`。
- 后端沙箱导入 API 含报告摘要测试 `4/4 OK`。
- M14 目录包执行 `setup.bat` 输出 `INSTALLER_SHELL_OK`。
- M14 目录包执行 `app\run_sample_self_test.bat` 输出 `SAMPLE_SELF_TEST_OK`。
- M14 目录包执行 `app\build_report_delivery_demo.bat` 可生成报告交付材料。
- M14 zip 解压后重复执行安装器外壳、样例自检和报告交付演示，均通过。
