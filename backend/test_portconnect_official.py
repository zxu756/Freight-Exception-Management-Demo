"""
PortConnect API 测试脚本 (更新版)
使用官方API文档中的正确端点

Official Documentation: https://portconnect.atlassian.net/wiki/spaces/PUG/pages/2631237633/API+Documentation
API Base URL: https://api.portconnect.io/v1 和 https://api.portconnect.io/v2
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 你的API密钥
PRIMARY_KEY = "56e067a235704e00b246de774f557d01"
SECONDARY_KEY = "e9ccd94f3240496cae5988ceb8314000"

# 正确的API配置
API_BASE_V1 = "https://api.portconnect.io/v1"
API_BASE_V2 = "https://api.portconnect.io/v2"


class PortConnectAPI:
    """PortConnect官方API客户端"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Content-Type': 'application/json'
        }

    def test_container_visit(self, container_number: str):
        """
        测试 Container Visit API
        获取集装箱访问信息（类似Track & Trace）
        """
        print(f"\n{'='*60}")
        print(f"测试: Container Visit API - {container_number}")
        print(f"{'='*60}")

        url = f"{API_BASE_V1}/containervisit/{container_number}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            print(f"请求URL: {url}")
            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ 成功获取集装箱信息!")
                print(f"\n响应数据:")
                print(json.dumps(data, indent=2))
                return data
            elif response.status_code == 404:
                print(f"⚠️  集装箱未找到 - 可能不在PortConnect系统中")
                print(f"响应: {response.text}")
            elif response.status_code == 401:
                print(f"❌ 认证失败 - API密钥无效")
            elif response.status_code == 403:
                print(f"❌ 访问被拒绝 - 可能需要订阅此API")
            else:
                print(f"响应: {response.text}")

            return None

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None

    def test_vessel_schedule(self, port_code: str = "NZAKL"):
        """
        测试 Vessel Schedule API
        获取船舶时刻表
        """
        print(f"\n{'='*60}")
        print(f"测试: Vessel Schedule API - {port_code}")
        print(f"{'='*60}")

        url = f"{API_BASE_V1}/vesselschedule"
        params = {'portCode': port_code}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            print(f"请求URL: {url}")
            print(f"参数: {params}")
            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ 成功获取船舶时刻表!")

                if isinstance(data, list) and len(data) > 0:
                    print(f"船舶数量: {len(data)}")
                    print(f"\n前3个船舶:")
                    for vessel in data[:3]:
                        print(f"\n船名: {vessel.get('vesselName', 'N/A')}")
                        print(f"  航次: {vessel.get('voyageNumber', 'N/A')}")
                        print(f"  ETA: {vessel.get('eta', 'N/A')}")
                        print(f"  ETD: {vessel.get('etd', 'N/A')}")
                else:
                    print(f"响应数据: {json.dumps(data, indent=2)[:500]}")

                return data
            elif response.status_code == 404:
                print(f"⚠️  未找到数据")
                print(f"响应: {response.text}")
            else:
                print(f"响应: {response.text}")

            return None

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None

    def test_container_events_subscription(self, container_number: str):
        """
        测试 Container Visit Event API (v2)
        订阅集装箱事件
        """
        print(f"\n{'='*60}")
        print(f"测试: Container Event Subscriptions API v2")
        print(f"{'='*60}")

        url = f"{API_BASE_V2}/subscriptions"

        # 订阅请求体
        subscription_data = {
            "containerNumber": container_number,
            "eventTypes": [
                "Vessel Arrived",
                "Container Discharged",
                "Container Available for Collection",
                "Container Departed Terminal"
            ],
            "webhookUrl": "https://your-server.com/webhook"  # 需要替换为真实URL
        }

        try:
            response = requests.post(url, headers=self.headers, json=subscription_data, timeout=10)

            print(f"请求URL: {url}")
            print(f"订阅集装箱: {container_number}")
            print(f"状态码: {response.status_code}")

            if response.status_code in [200, 201]:
                data = response.json()
                print(f"\n✅ 成功创建订阅!")
                print(f"响应: {json.dumps(data, indent=2)}")
                return data
            elif response.status_code == 400:
                print(f"⚠️  请求参数错误")
                print(f"响应: {response.text}")
            elif response.status_code == 403:
                print(f"⚠️  需要有效的webhook URL或订阅权限")
                print(f"响应: {response.text}")
            else:
                print(f"响应: {response.text}")

            return None

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None

    def get_available_event_types(self):
        """
        获取可用的事件类型
        """
        print(f"\n{'='*60}")
        print(f"可用的集装箱事件类型")
        print(f"{'='*60}")

        event_types = [
            "Vessel Arrived",
            "Container Discharged",
            "Container Available for Collection",
            "Container Departed Terminal",
            "Container Gate In",
            "Container Gate Out",
            "Container Loaded on Vessel",
            "Vessel Departed",
            "Customs Released",
            "Biosecurity Released"
        ]

        for i, event_type in enumerate(event_types, 1):
            print(f"{i}. {event_type}")

        return event_types


def test_real_container_numbers():
    """
    使用一些可能存在的集装箱号格式进行测试
    """
    print(f"\n{'='*60}")
    print(f"测试常见集装箱号格式")
    print(f"{'='*60}")

    # ISO 6346标准集装箱号格式: 4字母+7数字
    # 常见的集装箱运营商代码
    test_containers = [
        "MSCU1234567",  # MSC (Mediterranean Shipping Company)
        "MAEU1234567",  # Maersk
        "CMAU1234567",  # CMA CGM
        "CSLU1234567",  # COSCO
    ]

    print("\n注意: 这些是测试用的集装箱号格式")
    print("实际测试需要使用真实的、当前在新西兰港口的集装箱号")
    print("\n你可以从以下途径获取真实集装箱号:")
    print("1. PortConnect Track & Trace: https://www.portconnect.io/")
    print("2. 你公司的实际货运订单")
    print("3. 联系PortConnect support获取测试数据")

    return test_containers


def show_api_info():
    """显示API信息和资源"""
    print(f"\n{'='*60}")
    print(f"📚 PortConnect API 资源")
    print(f"{'='*60}")

    print("\n官方文档:")
    print("- API文档: https://portconnect.atlassian.net/wiki/spaces/PUG/pages/2631237633/")
    print("- 开发者门户: https://developer.portconnect.io/")
    print("- 测试环境: https://developertest.portconnect.io/")

    print("\n可用的API:")
    print("1. Container Visit API - 查询集装箱信息")
    print("2. Vessel Schedule API - 查询船舶时刻表")
    print("3. Container Event Subscription API - 订阅实时事件")
    print("4. Vessel Event Subscription API - 订阅船舶事件")
    print("5. Export Pre-Advice API - 发送出口预告")

    print("\n覆盖的港口:")
    ports = [
        "NZAKL - Port of Auckland (奥克兰港)",
        "NZTRG - Port of Tauranga (陶朗加港)",
        "NZTIU - Timaru Container Terminal (蒂马鲁港)",
        "NZLYT - Lyttelton Port Company (利特尔顿港)",
        "NZWLG - CentrePort Wellington (惠灵顿港 - 仅船舶时刻表)"
    ]
    for port in ports:
        print(f"  • {port}")

    print("\n支持与帮助:")
    print("  📧 Email: info@portconnect.co.nz")
    print("  📞 需要帮助时提供你的API密钥名称: 'testing'")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚢 PortConnect API 完整测试")
    print("新西兰港口数据平台 - 官方端点")
    print("="*60)

    # 显示API信息
    show_api_info()

    # 初始化API客户端
    api = PortConnectAPI(PRIMARY_KEY)

    print("\n\n" + "="*60)
    print("开始API测试")
    print("="*60)

    # 测试1: 船舶时刻表 (最可能成功的API)
    print("\n" + "="*60)
    print("🚢 测试 1: 获取奥克兰港船舶时刻表")
    print("="*60)
    vessel_data = api.test_vessel_schedule("NZAKL")

    # 测试2: 测试其他港口
    for port_code in ["NZTRG", "NZTIU", "NZLYT"]:
        vessel_data = api.test_vessel_schedule(port_code)

    # 测试3: 集装箱查询
    print("\n" + "="*60)
    print("📦 测试 2: 集装箱查询")
    print("="*60)

    test_containers = test_real_container_numbers()

    print("\n尝试查询测试集装箱号:")
    for container in test_containers[:2]:  # 只测试前2个
        api.test_container_visit(container)

    # 测试4: 显示事件类型
    api.get_available_event_types()

    # 总结
    print("\n\n" + "="*60)
    print("📊 测试完成")
    print("="*60)

    print("\n✅ API密钥有效")
    print(f"主密钥: {PRIMARY_KEY[:10]}...{PRIMARY_KEY[-10:]}")

    print("\n📝 下一步:")
    print("1. 如果船舶时刻表API成功 - 说明基本连接没问题")
    print("2. 集装箱查询需要真实的集装箱号")
    print("3. 订阅API需要有效的webhook URL（公网可访问）")
    print("4. 联系 info@portconnect.co.nz 获取:")
    print("   - 测试用的真实集装箱号")
    print("   - 完整的API文档和示例代码")
    print("   - Webhook设置指南")

    print("\n🔗 有用的链接:")
    print("- Track & Trace: https://www.portconnect.io/")
    print("- API文档: https://portconnect.atlassian.net/wiki/spaces/PUG/")
    print("- 开发者门户: https://developer.portconnect.io/")
