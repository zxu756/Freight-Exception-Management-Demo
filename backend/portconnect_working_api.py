"""
PortConnect API客户端 - 可用版本
使用正确的v1端点

Base URL: https://api.portconnect.io/v1/
API验证成功: 2026-08-13
"""
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional

PRIMARY_KEY = "56e067a235704e00b246de774f557d01"
API_BASE = "https://api.portconnect.io/v1"


class PortConnectAPI:
    """PortConnect官方API客户端（已验证可用）"""

    def __init__(self, api_key: str = PRIMARY_KEY):
        self.api_key = api_key
        self.base_url = API_BASE
        self.headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Content-Type': 'application/json'
        }

    def get_about(self) -> Dict:
        """获取API版本信息"""
        url = f"{self.base_url}/about"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def discover_endpoints(self) -> Dict:
        """
        尝试发现所有可用端点
        基于常见的RESTful模式
        """
        print("\n" + "="*60)
        print("🔍 发现可用API端点")
        print("="*60)

        # 常见的资源端点
        test_endpoints = [
            # Container相关
            "/containers",
            "/container",
            "/containervisit",
            "/containervisits",

            # Vessel相关
            "/vessels",
            "/vessel",
            "/vesselschedule",
            "/vesselvisit",

            # Port相关
            "/ports",
            "/port",

            # Event相关
            "/events",
            "/subscriptions",

            # 其他
            "/about",
            "/version",
            "/health"
        ]

        found_endpoints = {}

        for endpoint in test_endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                response = requests.get(url, headers=self.headers, timeout=5)

                if response.status_code == 200:
                    print(f"✅ {endpoint} - 200 OK")
                    found_endpoints[endpoint] = {
                        'status': 'available',
                        'method': 'GET',
                        'sample_response': response.text[:100]
                    }
                elif response.status_code == 400:
                    print(f"⚠️  {endpoint} - 400 (需要参数)")
                    found_endpoints[endpoint] = {
                        'status': 'needs_parameters',
                        'method': 'GET'
                    }
                elif response.status_code == 404:
                    print(f"❌ {endpoint} - 404 (不存在)")
                elif response.status_code == 405:
                    print(f"⚠️  {endpoint} - 405 (方法不允许，可能是POST)")
                    found_endpoints[endpoint] = {
                        'status': 'different_method',
                        'method': 'POST/PUT'
                    }
                else:
                    print(f"   {endpoint} - {response.status_code}")

            except Exception as e:
                pass

        return found_endpoints

    def test_container_endpoint(self, container_number: str = "TEST1234567"):
        """测试集装箱端点的各种可能路径"""
        print(f"\n" + "="*60)
        print(f"测试集装箱端点: {container_number}")
        print("="*60)

        patterns = [
            f"/containervisit/{container_number}",
            f"/container/{container_number}",
            f"/containers/{container_number}",
            f"/containervisit?containerNumber={container_number}",
            f"/container?number={container_number}"
        ]

        for pattern in patterns:
            url = f"{self.base_url}{pattern}"
            try:
                print(f"\n尝试: {pattern}")
                response = requests.get(url, headers=self.headers, timeout=5)
                print(f"状态码: {response.status_code}")

                if response.status_code == 200:
                    print("✅ 成功!")
                    print(f"响应: {response.text[:300]}")
                    return response.json()
                elif response.status_code == 404:
                    print("❌ 404 - 集装箱未找到或端点不存在")
                elif response.status_code == 400:
                    print("⚠️  400 - 参数格式可能不对")
                    print(f"响应: {response.text[:200]}")

            except Exception as e:
                print(f"错误: {e}")

        return None

    def test_vessel_endpoint(self, port_code: str = "NZAKL"):
        """测试船舶端点"""
        print(f"\n" + "="*60)
        print(f"测试船舶端点: {port_code}")
        print("="*60)

        patterns = [
            f"/vesselschedule?portCode={port_code}",
            f"/vessels?port={port_code}",
            f"/vesselvisit?portCode={port_code}",
            f"/ports/{port_code}/vessels"
        ]

        for pattern in patterns:
            url = f"{self.base_url}{pattern}"
            try:
                print(f"\n尝试: {pattern}")
                response = requests.get(url, headers=self.headers, timeout=5)
                print(f"状态码: {response.status_code}")

                if response.status_code == 200:
                    print("✅ 成功!")
                    data = response.json()
                    if isinstance(data, list):
                        print(f"返回 {len(data)} 条记录")
                        if len(data) > 0:
                            print(f"示例数据: {json.dumps(data[0], indent=2)[:300]}")
                    else:
                        print(f"响应: {json.dumps(data, indent=2)[:300]}")
                    return data
                elif response.status_code == 400:
                    print("⚠️  400 - 检查参数")
                    print(f"响应: {response.text[:200]}")

            except Exception as e:
                print(f"错误: {e}")

        return None


def full_api_exploration():
    """完整的API探索"""
    print("\n" + "="*60)
    print("🚢 PortConnect API 完整探索")
    print("Base URL: https://api.portconnect.io/v1")
    print("="*60)

    api = PortConnectAPI()

    # 1. 验证连接
    print("\n1️⃣ 验证API连接")
    print("-"*60)
    try:
        about = api.get_about()
        print(f"✅ API连接成功!")
        print(f"API Build: {about.get('build')}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    # 2. 发现端点
    print("\n2️⃣ 发现可用端点")
    found = api.discover_endpoints()

    if found:
        print(f"\n找到 {len(found)} 个可用端点:")
        for endpoint, info in found.items():
            print(f"  • {endpoint} - {info['status']}")

    # 3. 测试集装箱端点
    print("\n3️⃣ 测试集装箱查询")
    api.test_container_endpoint("MSCU1234567")

    # 4. 测试船舶端点
    print("\n4️⃣ 测试船舶时刻表")
    api.test_vessel_endpoint("NZAKL")

    # 总结
    print("\n" + "="*60)
    print("📊 探索总结")
    print("="*60)
    print("\n✅ 已确认:")
    print("  • API密钥有效")
    print("  • 基础URL正确: https://api.portconnect.io/v1")
    print("  • About端点可用")

    print("\n📝 下一步:")
    print("  1. 根据发现的端点编写完整客户端")
    print("  2. 获取真实的集装箱号/船舶信息进行测试")
    print("  3. 联系PortConnect获取完整API文档")
    print("  4. 或使用模拟API继续开发")


if __name__ == "__main__":
    full_api_exploration()
