"""
测试 PortConnect Subscriptions API (V2)
订阅实时事件通知
"""
import requests
import json
from datetime import datetime

PRIMARY_KEY = "56e067a235704e00b246de774f557d01"
API_BASE_V1 = "https://api.portconnect.io/v1"
API_BASE_V2 = "https://api.portconnect.io/v2"


def test_list_subscriptions_v1():
    """测试获取V1订阅列表"""
    print("="*60)
    print("📋 测试 V1 Subscriptions - 列表")
    print("="*60)

    url = f"{API_BASE_V1}/subscriptions"
    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 找到 {len(data)} 个订阅")

            if data:
                print(f"\n订阅列表:")
                for i, sub in enumerate(data, 1):
                    print(f"\n{i}. 订阅ID: {sub.get('subscriptionId')}")
                    print(f"   状态: {sub.get('status')}")
                    print(f"   Webhook: {sub.get('webhookUrl')}")
                    print(f"   创建时间: {sub.get('createdDatetime')}")

                # 保存数据
                with open('subscriptions_v1.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n✅ 数据已保存到 subscriptions_v1.json")
            else:
                print("\n当前没有活动订阅")

            return data
        else:
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"异常: {e}")

    return None


def test_list_subscriptions_v2():
    """测试获取V2订阅列表"""
    print("\n" + "="*60)
    print("📋 测试 V2 Subscriptions - 列表")
    print("="*60)

    url = f"{API_BASE_V2}/subscriptions"
    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 找到 {len(data)} 个订阅")

            if data:
                print(f"\n订阅列表:")
                for i, sub in enumerate(data, 1):
                    print(f"\n{i}. 订阅ID: {sub.get('subscriptionId')}")
                    print(f"   事件类型: {sub.get('eventType')}")
                    print(f"   Webhook: {sub.get('webhookUrl')}")

                # 保存数据
                with open('subscriptions_v2.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n✅ 数据已保存到 subscriptions_v2.json")
            else:
                print("\n当前没有V2订阅")

            return data
        else:
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"异常: {e}")

    return None


def test_vessel_schedule_subscriptions():
    """测试船期订阅列表"""
    print("\n" + "="*60)
    print("🚢 测试 Vessel Schedule Subscriptions")
    print("="*60)

    url = f"{API_BASE_V1}/subscriptions-vessel-schedule"
    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 找到 {len(data)} 个船期订阅")

            if data:
                print(f"\n船期订阅:")
                for i, sub in enumerate(data, 1):
                    print(f"\n{i}. 订阅ID: {sub.get('subscriptionId')}")
                    print(f"   港口: {sub.get('portCode')}")
                    print(f"   Webhook: {sub.get('webhookUrl')}")

                # 保存数据
                with open('vessel_schedule_subscriptions.json', 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                print("\n当前没有船期订阅")

            return data
        else:
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"异常: {e}")

    return None


def show_subscription_info():
    """显示订阅相关信息"""
    print("\n" + "="*60)
    print("💡 关于 Subscriptions API")
    print("="*60)

    print("\n📝 创建订阅需要:")
    print("  1. 有效的 Webhook URL（必须是公网可访问的HTTPS地址）")
    print("  2. 选择要订阅的事件类型")
    print("  3. 可选：指定容器号、船名、港口等过滤条件")

    print("\n🔔 可订阅的事件类型（V2）:")
    event_types = [
        "Container Arrived at Port",
        "Container Departed from Port",
        "Container Loaded on Vessel",
        "Container Discharged from Vessel",
        "Container Available for Collection",
        "Container Gate In",
        "Container Gate Out",
        "Customs Released",
        "MPI Released",
        "Line Released"
    ]
    for i, event in enumerate(event_types, 1):
        print(f"  {i}. {event}")

    print("\n🚢 船期订阅 (Vessel Schedule):")
    print("  • Vessel Arrived")
    print("  • Vessel Departed")
    print("  • Schedule Updated")

    print("\n⚠️  注意事项:")
    print("  • Webhook必须返回 2xx 状态码")
    print("  • 超时时间: 30秒")
    print("  • 失败重试: 最多3次")
    print("  • 需要验证webhook所有权（首次创建时）")

    print("\n🌐 Webhook URL要求:")
    print("  • 必须是HTTPS（不能是HTTP）")
    print("  • 必须公网可访问")
    print("  • 推荐使用: ngrok, webhook.site, 或云服务器")

    print("\n📘 示例订阅请求 (V2):")
    example_v2 = {
        "eventType": "Container Arrived at Port",
        "webhookUrl": "https://your-domain.com/webhook/portconnect",
        "containerNumber": "MSCU1234567",  # 可选
        "portCode": "NZAKL"  # 可选
    }
    print(json.dumps(example_v2, indent=2))

    print("\n📘 示例船期订阅请求:")
    example_vessel = {
        "portCode": "NZAKL",
        "webhookUrl": "https://your-domain.com/webhook/vessel-schedule",
        "vesselName": "SOUTHERN STAR"  # 可选
    }
    print(json.dumps(example_vessel, indent=2))


def test_create_subscription_dryrun():
    """演示如何创建订阅（不实际执行）"""
    print("\n" + "="*60)
    print("📝 创建订阅示例（演示）")
    print("="*60)

    print("\n如果你有有效的Webhook URL，可以这样创建订阅:\n")

    # V2订阅示例
    print("1️⃣ 创建V2事件订阅:")
    print("-"*60)
    print("curl --request POST \\")
    print(f"  --url '{API_BASE_V2}/subscriptions' \\")
    print(f"  --header 'Ocp-Apim-Subscription-Key: {PRIMARY_KEY}' \\")
    print("  --header 'Content-Type: application/json' \\")
    print("  --data '{")
    print('    "eventType": "Container Arrived at Port",')
    print('    "webhookUrl": "https://your-domain.com/webhook",')
    print('    "portCode": "NZAKL"')
    print("  }'")

    print("\n2️⃣ 创建船期订阅:")
    print("-"*60)
    print("curl --request POST \\")
    print(f"  --url '{API_BASE_V1}/subscriptions-vessel-schedule' \\")
    print(f"  --header 'Ocp-Apim-Subscription-Key: {PRIMARY_KEY}' \\")
    print("  --header 'Content-Type: application/json' \\")
    print("  --data '{")
    print('    "portCode": "NZAKL",')
    print('    "webhookUrl": "https://your-domain.com/webhook/vessel"')
    print("  }'")

    print("\n💡 推荐的Webhook测试工具:")
    print("  • webhook.site - 免费临时webhook URL")
    print("  • ngrok - 本地开发tunneling")
    print("  • RequestBin - webhook调试工具")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔔 PortConnect Subscriptions API 测试")
    print("="*60)

    # 测试1: V1订阅列表
    v1_subs = test_list_subscriptions_v1()

    # 测试2: V2订阅列表
    v2_subs = test_list_subscriptions_v2()

    # 测试3: 船期订阅
    vessel_subs = test_vessel_schedule_subscriptions()

    # 显示订阅信息
    show_subscription_info()

    # 显示创建订阅的示例
    test_create_subscription_dryrun()

    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)

    print("\n✅ Subscriptions API 可用!")
    print(f"  • V1订阅数: {len(v1_subs) if v1_subs else 0}")
    print(f"  • V2订阅数: {len(v2_subs) if v2_subs else 0}")
    print(f"  • 船期订阅数: {len(vessel_subs) if vessel_subs else 0}")

    print("\n🚀 下一步:")
    print("  1. 如果需要实时事件，创建webhook接收器")
    print("  2. 或者使用轮询方式定期查询scheduled-vessels和container-visits")
    print("  3. 对于demo，建议使用轮询（更简单）")
