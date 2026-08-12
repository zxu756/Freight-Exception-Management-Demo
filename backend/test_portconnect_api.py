"""
PortConnect API 测试脚本
Test script for New Zealand Port Data

Official API: https://developer.portconnect.io/

测试你的API密钥并获取实时港口数据
"""
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional

# 你的API密钥
PRIMARY_KEY = "56e067a235704e00b246de774f557d01"
SECONDARY_KEY = "e9ccd94f3240496cae5988ceb8314000"

# API基础配置
BASE_URL = "https://api.portconnect.io"  # 实际URL需要确认
API_VERSION = "v1"


class PortConnectTester:
    """PortConnect API测试类"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = BASE_URL
        self.headers = {
            'Ocp-Apim-Subscription-Key': api_key,  # PortConnect使用Azure API Management
            'Content-Type': 'application/json'
        }

    def test_connection(self):
        """测试API连接"""
        print("\n" + "="*60)
        print("测试 1: API连接测试")
        print("="*60)

        # 尝试不同的可能端点
        test_endpoints = [
            f"{self.base_url}/about",
            f"{self.base_url}/api/about",
            f"{self.base_url}/api/{API_VERSION}/about",
            "https://portconnect-api.azure-api.net/about"
        ]

        for endpoint in test_endpoints:
            try:
                print(f"\n尝试连接: {endpoint}")
                response = requests.get(endpoint, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    print(f"✅ 成功连接!")
                    print(f"响应: {response.text[:200]}")
                    return True
                else:
                    print(f"状态码: {response.status_code}")
                    print(f"响应: {response.text[:200]}")
            except Exception as e:
                print(f"❌ 连接失败: {e}")

        return False

    def test_ports_list(self):
        """测试获取港口列表"""
        print("\n" + "="*60)
        print("测试 2: 获取新西兰港口列表")
        print("="*60)

        endpoints = [
            f"{self.base_url}/api/{API_VERSION}/ports",
            f"{self.base_url}/ports",
            "https://portconnect-api.azure-api.net/api/ports"
        ]

        for endpoint in endpoints:
            try:
                print(f"\n尝试: {endpoint}")
                response = requests.get(endpoint, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 成功获取港口列表!")
                    print(f"港口数量: {len(data) if isinstance(data, list) else 'N/A'}")
                    print(f"\n响应数据:")
                    print(json.dumps(data, indent=2)[:500])
                    return True
                elif response.status_code == 401:
                    print(f"❌ 认证失败 (401) - API密钥可能无效或已过期")
                elif response.status_code == 403:
                    print(f"❌ 访问被拒绝 (403) - 可能需要额外的权限")
                elif response.status_code == 404:
                    print(f"⚠️  端点不存在 (404) - 尝试下一个...")
                else:
                    print(f"状态码: {response.status_code}")
                    print(f"响应: {response.text[:200]}")
            except Exception as e:
                print(f"❌ 请求失败: {e}")

        return False

    def test_vessel_schedule(self):
        """测试获取船舶时刻表"""
        print("\n" + "="*60)
        print("测试 3: 获取奥克兰港船舶时刻表")
        print("="*60)

        port_codes = ["NZAKL", "Auckland", "AKL"]

        for port_code in port_codes:
            endpoints = [
                f"{self.base_url}/api/{API_VERSION}/ports/{port_code}/vessels",
                f"{self.base_url}/api/{API_VERSION}/vessels?port={port_code}",
                f"{self.base_url}/ports/{port_code}/schedule"
            ]

            for endpoint in endpoints:
                try:
                    print(f"\n尝试: {endpoint}")
                    response = requests.get(endpoint, headers=self.headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ 成功获取船舶数据!")
                        print(f"\n响应数据:")
                        print(json.dumps(data, indent=2)[:500])
                        return True
                    elif response.status_code == 404:
                        print(f"⚠️  端点或港口不存在 (404)")
                    else:
                        print(f"状态码: {response.status_code}")
                except Exception as e:
                    print(f"❌ 请求失败: {e}")

        return False

    def test_container_tracking(self):
        """测试集装箱追踪"""
        print("\n" + "="*60)
        print("测试 4: 测试集装箱追踪功能")
        print("="*60)

        # 使用常见的测试集装箱号
        test_containers = ["MSCU1234567", "TEST1234567", "DEMO1234567"]

        for container in test_containers:
            endpoints = [
                f"{self.base_url}/api/{API_VERSION}/containers/{container}",
                f"{self.base_url}/api/{API_VERSION}/tracking/{container}",
                f"{self.base_url}/containers/{container}/status"
            ]

            for endpoint in endpoints:
                try:
                    print(f"\n尝试追踪: {container}")
                    print(f"端点: {endpoint}")
                    response = requests.get(endpoint, headers=self.headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ 成功获取集装箱信息!")
                        print(f"\n响应数据:")
                        print(json.dumps(data, indent=2)[:500])
                        return True
                    elif response.status_code == 404:
                        print(f"⚠️  集装箱未找到 (404) - 可能需要真实的集装箱号")
                    else:
                        print(f"状态码: {response.status_code}")
                except Exception as e:
                    print(f"❌ 请求失败: {e}")

        return False

    def test_api_documentation(self):
        """测试API文档端点"""
        print("\n" + "="*60)
        print("测试 5: 查找API文档")
        print("="*60)

        doc_endpoints = [
            "https://developer.portconnect.io/api-details",
            "https://api.portconnect.io/swagger",
            "https://api.portconnect.io/docs",
            "https://portconnect-api.azure-api.net/api-docs"
        ]

        for endpoint in doc_endpoints:
            try:
                print(f"\n尝试: {endpoint}")
                response = requests.get(endpoint, timeout=10)

                if response.status_code == 200:
                    print(f"✅ 找到文档端点!")
                    print(f"内容类型: {response.headers.get('content-type')}")
                    if 'json' in response.headers.get('content-type', ''):
                        print(f"响应: {response.text[:300]}")
                    return True
                else:
                    print(f"状态码: {response.status_code}")
            except Exception as e:
                print(f"❌ 请求失败: {e}")

        return False


def check_api_key_info():
    """显示API密钥信息"""
    print("\n" + "="*60)
    print("🔑 PortConnect API 密钥信息")
    print("="*60)

    print(f"\nAPI名称: testing")
    print(f"创建日期: 08/10/2026")
    print(f"主密钥: {PRIMARY_KEY[:10]}...{PRIMARY_KEY[-10:]}")
    print(f"备用密钥: {SECONDARY_KEY[:10]}...{SECONDARY_KEY[-10:]}")
    print(f"\n注意: 这些密钥来自 Azure API Management")
    print(f"      需要使用正确的API端点URL")


def try_discover_api_structure():
    """尝试发现API结构"""
    print("\n" + "="*60)
    print("🔍 尝试发现API结构")
    print("="*60)

    # 常见的Azure API Management URL模式
    possible_bases = [
        "https://portconnect-api.azure-api.net",
        "https://api.portconnect.io",
        "https://portconnect.api.azure.com",
        "https://nz-portconnect.azure-api.net"
    ]

    headers = {'Ocp-Apim-Subscription-Key': PRIMARY_KEY}

    for base in possible_bases:
        print(f"\n测试基础URL: {base}")

        common_paths = [
            "/",
            "/api",
            "/about",
            "/health",
            "/status"
        ]

        for path in common_paths:
            try:
                url = base + path
                response = requests.get(url, headers=headers, timeout=5)

                if response.status_code in [200, 301, 302]:
                    print(f"  ✅ {path} - 响应 {response.status_code}")
                    if response.text:
                        print(f"     内容: {response.text[:100]}")
            except:
                pass


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚢 PortConnect API 测试")
    print("新西兰港口数据平台")
    print("="*60)

    # 显示API密钥信息
    check_api_key_info()

    # 尝试发现API结构
    try_discover_api_structure()

    # 使用主密钥进行测试
    print("\n" + "="*60)
    print("开始API功能测试（使用主密钥）")
    print("="*60)

    tester = PortConnectTester(PRIMARY_KEY)

    # 运行所有测试
    tests = [
        ("连接测试", tester.test_connection),
        ("港口列表", tester.test_ports_list),
        ("船舶时刻表", tester.test_vessel_schedule),
        ("集装箱追踪", tester.test_container_tracking),
        ("API文档", tester.test_api_documentation)
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 异常: {e}")
            results[test_name] = False

    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)

    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:20s} - {status}")

    success_count = sum(results.values())
    total_count = len(results)

    print(f"\n成功率: {success_count}/{total_count}")

    if success_count == 0:
        print("\n" + "="*60)
        print("⚠️  所有测试失败 - 可能的原因:")
        print("="*60)
        print("\n1. API端点URL不正确")
        print("   - PortConnect可能使用不同的域名")
        print("   - 建议联系PortConnect获取正确的API文档")
        print("\n2. API密钥权限不足")
        print("   - 密钥可能还未激活")
        print("   - 可能需要额外的访问权限配置")
        print("\n3. 需要额外的认证步骤")
        print("   - 某些API可能需要OAuth或其他认证方式")
        print("\n4. API可能在维护中")
        print("   - 检查 https://developer.portconnect.io/ 的状态公告")
        print("\n" + "="*60)
        print("📋 建议下一步:")
        print("="*60)
        print("\n1. 访问 https://developer.portconnect.io/")
        print("2. 查看API文档和快速开始指南")
        print("3. 查找示例代码或Postman集合")
        print("4. 联系PortConnect技术支持获取帮助")
        print("   - 提供你的API密钥名称: 'testing'")
        print("   - 询问正确的API基础URL和端点")
    else:
        print("\n🎉 部分测试成功！可以开始使用API了。")

    print("\n" + "="*60)
