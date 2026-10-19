# -*- coding: utf-8 -*-
"""
test_dra_local_service_binding_contract.py — 文档脱敏助手本地服务绑定安全契约

回归锁定 task 6 修复：run_local_service 默认拒绝非回环绑定（服务无认证），
除非显式设置 DRA_ALLOW_NON_LOOPBACK=1。防止 `--host 0.0.0.0` 暴露无认证
文件处理/任务控制接口到局域网/公网。

纯契约测试：mock 掉 ThreadingHTTPServer，不真实绑定端口、不启动服务。
"""

import os
import unittest
from unittest import mock


class DraLocalServiceBindingContractTest(unittest.TestCase):
    """run_local_service 非回环绑定拒绝契约。"""

    def tearDown(self):
        os.environ.pop("DRA_ALLOW_NON_LOOPBACK", None)

    def _call(self, host, allow=None):
        if allow is None:
            os.environ.pop("DRA_ALLOW_NON_LOOPBACK", None)
        else:
            os.environ["DRA_ALLOW_NON_LOOPBACK"] = allow
        from redaction_assistant import local_service

        with mock.patch.object(local_service, "ThreadingHTTPServer"):
            return local_service.run_local_service(host=host, port=0)

    def test_loopback_accepted_by_default(self):
        for host in ("127.0.0.1", "localhost", "::1"):
            # 应通过绑定校验进入 server 创建（被 mock 拦截后正常返回/继续）
            self._call(host, allow=None)

    def test_non_loopback_rejected_by_default(self):
        for host in ("0.0.0.0", "192.168.1.5", "10.0.0.1"):
            with self.assertRaises(ValueError) as ctx:
                self._call(host, allow=None)
            self.assertIn("non-loopback", str(ctx.exception))

    def test_non_loopback_allowed_when_explicitly_authorized(self):
        for host in ("0.0.0.0", "192.168.1.5"):
            self._call(host, allow="1")

    def test_non_loopback_allowed_when_explicit_truthy(self):
        for allow in ("true", "yes", "on"):
            self._call("0.0.0.0", allow=allow)


if __name__ == "__main__":
    unittest.main()