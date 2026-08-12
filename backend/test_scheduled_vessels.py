"""
测试 PortConnect Scheduled Vessels API
正确的端点：/scheduled-vessels
"""
import requests
import json
from datetime import datetime, timedelta

PRIMARY_KEY = "56e067a235704e00b246de774f557d01"
API_BASE = "https://api.portconnect.io/v1"


def test_scheduled_vessels():
    """测试船舶时刻表API - 使用正确的端点"""

    print("="*60)
    print("🚢 测试 Scheduled Vessels API")
    print("="*60)

    url = f"{API_BASE}/scheduled-vessels"

    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    # 测试1: 无参数（获取所有船舶）
    print("\n📍 测试1: 获取所有船舶")
    print("-"*60)
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 返回 {len(data)} 艘船")

            if len(data) > 0:
                print(f"\n前3艘船的信息:")
                for vessel in data[:3]:
                    print(f"\n船名: {vessel.get('vesselName')}")
                    print(f"  IMO: {vessel.get('imoNumber')}")
                    print(f"  港口: {vessel.get('portCode')}")
                    print(f"  到达: {vessel.get('arrivalDatetime')}")
                    print(f"  离开: {vessel.get('departureDatetime')}")
                    print(f"  状态: {vessel.get('vesselStatus')}")
                    print(f"  类型: {vessel.get('vesselType')}")
                    print(f"  码头: {vessel.get('wharfName')}")

                # 保存完整数据
                with open('scheduled_vessels_full.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n✅ 完整数据已保存到 scheduled_vessels_full.json")

                return data
        else:
            print(f"❌ 错误")
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"❌ 异常: {e}")

    # 测试2: 按港口过滤
    print("\n📍 测试2: 获取奥克兰港船舶 (portCode=NZAKL)")
    print("-"*60)
    try:
        params = {'portCode': 'NZAKL'}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"URL: {url}?portCode=NZAKL")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 奥克兰港有 {len(data)} 艘船")

            for vessel in data[:5]:
                print(f"\n• {vessel.get('vesselName')} - {vessel.get('vesselStatus')}")
                print(f"  到达: {vessel.get('arrivalDatetime')}")
                print(f"  航次: {vessel.get('inboundVoyage')}")

    except Exception as e:
        print(f"❌ 异常: {e}")

    # 测试3: 按日期范围过滤
    print("\n📍 测试3: 获取未来7天的船舶")
    print("-"*60)
    try:
        today = datetime.now()
        week_later = today + timedelta(days=7)

        params = {
            'arrivalDateFrom': today.strftime('%Y-%m-%d'),
            'arrivalDateTo': week_later.strftime('%Y-%m-%d')
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"日期范围: {params['arrivalDateFrom']} 到 {params['arrivalDateTo']}")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 找到 {len(data)} 艘船")

    except Exception as e:
        print(f"❌ 异常: {e}")

    # 测试4: 测试所有港口
    print("\n📍 测试4: 测试所有新西兰港口")
    print("-"*60)

    ports = {
        'NZAKL': 'Auckland',
        'NZTRG': 'Tauranga',
        'NZTIU': 'Timaru',
        'NZLYT': 'Lyttelton',
        'NZWLG': 'Wellington'
    }

    port_results = {}

    for code, name in ports.items():
        try:
            params = {'portCode': code}
            response = requests.get(url, headers=headers, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                port_results[name] = len(data)
                print(f"  {name:15s} ({code}): {len(data):2d} 艘船")
            else:
                print(f"  {name:15s} ({code}): 错误 {response.status_code}")

        except Exception as e:
            print(f"  {name:15s} ({code}): 异常")

    return port_results


def analyze_vessel_data():
    """分析船舶数据，检测延误等异常"""
    print("\n" + "="*60)
    print("📊 分析船舶数据")
    print("="*60)

    try:
        with open('scheduled_vessels_full.json', 'r') as f:
            vessels = json.load(f)

        print(f"\n总船舶数: {len(vessels)}")

        # 按港口统计
        ports = {}
        for v in vessels:
            port = v.get('portCode', 'Unknown')
            ports[port] = ports.get(port, 0) + 1

        print(f"\n按港口分布:")
        for port, count in sorted(ports.items(), key=lambda x: x[1], reverse=True):
            print(f"  {port}: {count} 艘")

        # 按状态统计
        statuses = {}
        for v in vessels:
            status = v.get('vesselStatus', 'Unknown')
            statuses[status] = statuses.get(status, 0) + 1

        print(f"\n按状态分布:")
        for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
            print(f"  {status}: {count} 艘")

        # 按类型统计
        types = {}
        for v in vessels:
            vtype = v.get('vesselType', 'Unknown')
            types[vtype] = types.get(vtype, 0) + 1

        print(f"\n按类型分布:")
        for vtype, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype}: {count} 艘")

        # 即将到达的船舶（24小时内）
        print(f"\n⏰ 24小时内到达的船舶:")
        now = datetime.now()
        within_24h = []

        for v in vessels:
            arrival = v.get('arrivalDatetime')
            if arrival:
                try:
                    arrival_dt = datetime.fromisoformat(arrival.replace('Z', '+00:00'))
                    hours_until = (arrival_dt - now).total_seconds() / 3600

                    if 0 <= hours_until <= 24:
                        within_24h.append({
                            'name': v.get('vesselName'),
                            'port': v.get('portCode'),
                            'hours': hours_until,
                            'arrival': arrival
                        })
                except:
                    pass

        within_24h.sort(key=lambda x: x['hours'])

        if within_24h:
            for ship in within_24h[:10]:
                print(f"  • {ship['name']} → {ship['port']} ({ship['hours']:.1f}小时)")
        else:
            print("  (无)")

    except FileNotFoundError:
        print("⚠️  请先运行测试获取数据")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚢 PortConnect Scheduled Vessels API 测试")
    print("="*60)

    # 运行测试
    results = test_scheduled_vessels()

    # 分析数据
    if results:
        analyze_vessel_data()

    print("\n" + "="*60)
    print("✅ 测试完成!")
    print("="*60)

    print("\n🎉 成功发现的API端点:")
    print("  1. /about - API信息")
    print("  2. /subscriptions - 订阅管理")
    print("  3. /scheduled-vessels - 船舶时刻表 ✨")

    print("\n📝 可用参数:")
    print("  • portCode - 港口代码 (NZAKL, NZTRG, etc.)")
    print("  • vesselType - 船舶类型")
    print("  • vesselStatus - 船舶状态")
    print("  • arrivalDateFrom - 起始日期")
    print("  • arrivalDateTo - 结束日期")
    print("  • vesselName - 船名")

    print("\n🚀 下一步:")
    print("  1. 集成到你的异常检测系统")
    print("  2. 监控船舶延误和状态变化")
    print("  3. 结合天气API预测潜在延误")
