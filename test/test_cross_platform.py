#!/usr/bin/env python3
"""
net-proxy-tool: Cross-Platform Automated Test Suite (v3.0)
Tests multi-gateway resolution, dynamic configuration API, worker node CRUD, and sandbox isolation.
Zero external dependencies. Works on Windows and Linux.
"""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest

TEST_DIR = Path(__file__).resolve().parent
TOOL_DIR = TEST_DIR.parent
sys.path.insert(0, str(TOOL_DIR))

from sdk.proxy_session import ProxySession, is_gateway_alive, PROXY_KEYS
from web.server import ThreadingHTTPServer, ProxyConsoleHandler


class TestNetProxyToolV3(unittest.TestCase):
    def setUp(self):
        for k in PROXY_KEYS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k in PROXY_KEYS:
            os.environ.pop(k, None)

    def test_01_gateway_probe(self):
        """测试网关连通性探测"""
        alive = is_gateway_alive(timeout=1.0)
        self.assertIsInstance(alive, bool)
        print(f"\n[Test 01] 默认网关连通性探测函数执行正常 (返回布尔值: {alive}): PASS")

    def test_02_proxy_session_lifecycle(self):
        """测试 Python SDK ProxySession 零残留生命周期"""
        self.assertIsNone(os.environ.get("http_proxy"))
        self.assertIsNone(os.environ.get("HTTP_PROXY"))

        with ProxySession(check=False) as proxy_url:
            self.assertEqual(os.environ.get("http_proxy"), proxy_url)
            self.assertEqual(os.environ.get("HTTP_PROXY"), proxy_url)
            self.assertIn("127.0.0.1", os.environ.get("no_proxy", ""))

        # 离开作用域必须 100% 销毁
        for k in PROXY_KEYS:
            self.assertIsNone(os.environ.get(k), f"环境变量 {k} 未被销毁！")
        print("\n[Test 02] ProxySession 离开代码块后环境变量零残留: PASS")

    def test_03_proxy_session_exception_safety(self):
        """测试抛出异常时 finally 强制销毁代理变量"""
        try:
            with ProxySession(check=False):
                raise RuntimeError("测试中断异常")
        except RuntimeError:
            pass

        for k in PROXY_KEYS:
            self.assertIsNone(os.environ.get(k), f"异常发生后环境变量 {k} 未被清理！")
        print("\n[Test 03] 抛出异常后 finally 强制注销保证: PASS")

    def test_04_cli_process_sandbox_isolation(self):
        """测试 with_proxy.py 子进程沙箱隔离性及自定义网关传参"""
        script = str(TOOL_DIR / "with_proxy.py")
        cmd = [
            sys.executable, script,
            "--gateway", "192.168.1.100:7890",
            "--no-check",
            sys.executable, "-c",
            "import os; print('CHILD_PROXY=' + str(os.environ.get('HTTP_PROXY')))"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 0, f"with_proxy 退出失败: {result.stderr}")
        self.assertIn("CHILD_PROXY=http://192.168.1.100:7890", result.stdout)

        # 验证父进程环境变量依然完全纯净
        self.assertIsNone(os.environ.get("HTTP_PROXY"))
        self.assertIsNone(os.environ.get("http_proxy"))
        print("\n[Test 04] 子进程代理注入且父进程严格保持纯净: PASS")

    def test_05_web_server_endpoints_and_crud(self):
        """测试原生微型 Web 控制台接口 (多网关、节点 CRUD 与动态配置 API)"""
        test_port = 18899
        httpd = ThreadingHTTPServer(("127.0.0.1", test_port), ProxyConsoleHandler)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.5)

        try:
            # 1. 测试 GET /api/config
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            conn.request("GET", "/api/config")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("gateways", data)
            self.assertGreaterEqual(len(data["gateways"]), 1)
            active_gw = data.get("active_gateway_id") or data["gateways"][0]["id"]
            first_node_id = data["clients"][0]["id"] if data.get("clients") else "node-test-auto"
            conn.close()

            # 2. 测试 POST /api/test-gateway (使用正在监听的测试服务器端口，保证 TCP 连通可测)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            test_body = json.dumps({"host": "127.0.0.1", "port": test_port})
            conn.request("POST", "/api/test-gateway", body=test_body, headers={"Content-Type": "application/json"})
            resp_test = conn.getresponse()
            self.assertEqual(resp_test.status, 200)
            test_res = json.loads(resp_test.read().decode("utf-8"))
            self.assertTrue(test_res["online"])
            print(f"\n[Test 05.1] 动态网关测试 API 验证通过, 延迟: {test_res['latency_ms']}ms")
            conn.close()

            # 3. 测试 POST /api/clients/add (添加新业务节点)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            new_client = {
                "id": "node-test-auto",
                "name": "自动化测试节点",
                "host": "192.168.1.250",
                "os_type": "linux",
                "bound_gateway_id": active_gw,
                "tags": ["测试", "自动构建"],
                "description": "单元测试临时节点"
            }
            conn.request("POST", "/api/clients/add", body=json.dumps(new_client), headers={"Content-Type": "application/json"})
            resp_add = conn.getresponse()
            self.assertEqual(resp_add.status, 200)
            add_res = json.loads(resp_add.read().decode("utf-8"))
            self.assertTrue(add_res["success"])
            print("\n[Test 05.2] 动态登记新业务节点 API 验证通过: PASS")
            conn.close()

            # 4. 测试 POST /api/clients/update (更新业务节点)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            update_data = {
                "id": "node-test-auto",
                "name": "自动化测试节点(已更新)",
                "description": "已更新的描述"
            }
            conn.request("POST", "/api/clients/update", body=json.dumps(update_data), headers={"Content-Type": "application/json"})
            resp_up = conn.getresponse()
            self.assertEqual(resp_up.status, 200)
            up_res = json.loads(resp_up.read().decode("utf-8"))
            self.assertTrue(up_res["success"])
            self.assertEqual(up_res["client"]["name"], "自动化测试节点(已更新)")
            print("\n[Test 05.3] 更新业务节点信息 API 验证通过: PASS")
            conn.close()

            # 5. 测试 POST /api/clients/delete (删除测试节点)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            del_data = {"id": "node-test-auto"}
            conn.request("POST", "/api/clients/delete", body=json.dumps(del_data), headers={"Content-Type": "application/json"})
            resp_del = conn.getresponse()
            self.assertEqual(resp_del.status, 200)
            del_res = json.loads(resp_del.read().decode("utf-8"))
            self.assertTrue(del_res["success"])
            print("\n[Test 05.4] 删除业务节点 API 验证通过: PASS")
            conn.close()

            # 6. 测试 GET /api/status (全景出海诊断)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=25.0)
            conn.request("GET", f"/api/status?gateway_id={active_gw}")
            resp_stat = conn.getresponse()
            self.assertEqual(resp_stat.status, 200)
            stat_data = json.loads(resp_stat.read().decode("utf-8"))
            self.assertIn("targets", stat_data)
            self.assertIn("gateway", stat_data)
            print(f"\n[Test 05.5] 全景出海连通性诊断通过, 目标数: {len(stat_data['targets'])}")
            conn.close()

            # 7. 测试 GET /proxy-on 和 GET /proxy-off (轻量端点注入源)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            conn.request("GET", "/proxy-on")
            resp_pon = conn.getresponse()
            self.assertEqual(resp_pon.status, 200)
            pon_script = resp_pon.read().decode("utf-8")
            self.assertIn("export HTTP_PROXY=", pon_script)
            self.assertIn("http://", pon_script)
            conn.close()

            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            conn.request("GET", "/proxy-off")
            resp_poff = conn.getresponse()
            self.assertEqual(resp_poff.status, 200)
            poff_script = resp_poff.read().decode("utf-8")
            self.assertIn("unset HTTP_PROXY", poff_script)
            print("\n[Test 05.6] Web 动态代理端点 /proxy-on 和 /proxy-off 验证通过: PASS")
            conn.close()

            # 8. 测试 POST /api/node-switch (节点开关功能)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            switch_payload = json.dumps({"node_id": first_node_id, "action": "on"})
            conn.request("POST", "/api/node-switch", body=switch_payload, headers={"Content-Type": "application/json"})
            resp_sw = conn.getresponse()
            self.assertEqual(resp_sw.status, 200)
            sw_data = json.loads(resp_sw.read().decode("utf-8"))
            self.assertTrue(sw_data["success"])
            self.assertEqual(sw_data["action"], "on")
            print("\n[Test 05.7] 节点代理开关切换 API (/api/node-switch) 验证通过: PASS")
            conn.close()

            # 9. 测试 POST /api/node-test (节点连通性实时复测)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=18.0)
            test_node_payload = json.dumps({"node_id": first_node_id})
            conn.request("POST", "/api/node-test", body=test_node_payload, headers={"Content-Type": "application/json"})
            resp_ntest = conn.getresponse()
            self.assertEqual(resp_ntest.status, 200)
            ntest_data = json.loads(resp_ntest.read().decode("utf-8"))
            self.assertTrue(ntest_data["success"])
            print(f"\n[Test 05.8] 节点出海连通性复测 API (/api/node-test) 验证通过: PASS (状态: {ntest_data.get('status_line')})")
            conn.close()

            # 10. 测试 POST /api/nodes/batch-switch (一键全局切断/恢复直连)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=12.0)
            batch_payload = json.dumps({"action": "off"})
            conn.request("POST", "/api/nodes/batch-switch", body=batch_payload, headers={"Content-Type": "application/json"})
            resp_batch = conn.getresponse()
            self.assertEqual(resp_batch.status, 200)
            batch_data = json.loads(resp_batch.read().decode("utf-8"))
            self.assertTrue(batch_data["success"])
            self.assertEqual(batch_data["action"], "off")
            print(f"\n[Test 05.9] 批量开关与全局断网恢复 API (/api/nodes/batch-switch) 验证通过: PASS (恢复直连节点数: {batch_data.get('success_count')})")
            conn.close()

            # 11. 测试 POST /api/test-node-preflight (三阶深度预检)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=10.0)
            preflight_payload = json.dumps({
                "host": "127.0.0.1",
                "port": test_port,
                "access_mode": "ssh"
            })
            conn.request("POST", "/api/test-node-preflight", body=preflight_payload, headers={"Content-Type": "application/json"})
            resp_pref = conn.getresponse()
            self.assertEqual(resp_pref.status, 200)
            pref_data = json.loads(resp_pref.read().decode("utf-8"))
            self.assertTrue(pref_data["tcp_ok"])
            print(f"\n[Test 05.10] 三阶深度预检 API (/api/test-node-preflight) 验证通过: PASS (TCP连通且延迟: {pref_data.get('latency_ms')}ms)")
            conn.close()

            # 12. 测试 GET /api/audit-logs (操作审计流水)
            conn = http.client.HTTPConnection("127.0.0.1", test_port, timeout=8.0)
            conn.request("GET", "/api/audit-logs")
            resp_audit = conn.getresponse()
            self.assertEqual(resp_audit.status, 200)
            audit_data = json.loads(resp_audit.read().decode("utf-8"))
            self.assertTrue(audit_data["success"])
            self.assertGreaterEqual(len(audit_data.get("logs", [])), 1)
            print(f"\n[Test 05.11] 操作审计流水 API (/api/audit-logs) 验证通过: PASS (流水记录数: {len(audit_data['logs'])})")
            conn.close()
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
