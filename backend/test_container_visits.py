"""
测试 PortConnect Container Visits API
查询集装箱访问记录和状态
"""
import requests
import json
from datetime import datetime, timedelta

PRIMARY_KEY = "56e067a235704e00b246de774f557d01"
API_BASE = "https://api.portconnect.io/v1"


def test_container_visits_search():
    """测试集装箱搜索API"""
    print("="*60)
    print("📦 测试 Container Visits API - 搜索")
    print("="*60)

    url = f"{API_BASE}/container-visits"
    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    # 测试1: 搜索特定集装箱号
    print("\n📍 测试1: 搜索集装箱 (需要真实集装箱号)")
    print("-"*60)

    # 尝试几个可能的集装箱号
    test_containers = [
        "MSCU1234567",
        "MAEU1234567",
        "CMAU1234567",
        "TEST1234567"
    ]

    for container_num in test_containers:
        try:
            params = {'containerNumber': container_num}
            response = requests.get(url, headers=headers, params=params, timeout=10)

            print(f"\n尝试: {container_num}")
            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功! 找到 {len(data)} 条记录")

                if data:
                    print(f"\n集装箱信息:")
                    print(json.dumps(data[0], indent=2))

                    # 保存数据
                    with open(f'container_visit_{container_num}.json', 'w') as f:
                        json.dump(data, f, indent=2)

                    return data
                else:
                    print("返回空列表 - 集装箱可能不在系统中")
            elif response.status_code == 404:
                print("❌ 404 - 未找到")
            elif response.status_code == 400:
                print(f"⚠️  400 - 参数错误")
                print(f"响应: {response.text[:200]}")
            else:
                print(f"响应: {response.text[:200]}")

        except Exception as e:
            print(f"异常: {e}")

    # 测试2: 按港口和日期范围搜索
    print("\n📍 测试2: 按港口和日期搜索")
    print("-"*60)

    try:
        # 搜索过去7天奥克兰港的集装箱
        today = datetime.now()
        week_ago = today - timedelta(days=7)

        params = {
            'portCode': 'NZAKL',
            'arrivalDateFrom': week_ago.strftime('%Y-%m-%d'),
            'arrivalDateTo': today.strftime('%Y-%m-%d')
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"搜索参数: {params}")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 找到 {len(data)} 个集装箱访问记录")

            if data:
                print(f"\n前3个集装箱:")
                for i, container in enumerate(data[:3], 1):
                    print(f"\n{i}. 集装箱号: {container.get('containerNumber')}")
                    print(f"   状态: {container.get('containerStatus')}")
                    print(f"   船名: {container.get('inboundVesselName')}")
                    print(f"   到达: {container.get('inboundArrivalDatetime')}")

                # 保存数据
                with open('container_visits_akl.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n✅ 数据已保存到 container_visits_akl.json")

                return data
        else:
            print(f"响应: {response.text[:300]}")

    except Exception as e:
        print(f"异常: {e}")

    return None


def test_container_visit_by_id():
    """测试通过ID获取集装箱详情"""
    print("\n" + "="*60)
    print("📦 测试 Container Visit - 按ID查询")
    print("="*60)

    # 这个需要真实的containerVisitId
    # 我们先尝试从搜索结果中获取
    try:
        with open('container_visits_akl.json', 'r') as f:
            containers = json.load(f)

        if containers and len(containers) > 0:
            container_id = containers[0].get('containerVisitId')

            if container_id:
                url = f"{API_BASE}/container-visits/{container_id}"
                headers = {
                    'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
                    'Content-Type': 'application/json'
                }

                response = requests.get(url, headers=headers, timeout=10)
                print(f"查询ID: {container_id}")
                print(f"状态码: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 成功获取详细信息!")
                    print(json.dumps(data, indent=2)[:500])
                    return data
                else:
                    print(f"响应: {response.text[:200]}")
            else:
                print("⚠️  没有找到containerVisitId")
        else:
            print("⚠️  需要先运行搜索获取数据")

    except FileNotFoundError:
        print("⚠️  请先运行搜索测试")
    except Exception as e:
        print(f"异常: {e}")

    return None


def test_available_parameters():
    """测试所有可用的查询参数"""
    print("\n" + "="*60)
    print("🔍 测试不同的查询参数组合")
    print("="*60)

    url = f"{API_BASE}/container-visits"
    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    # 根据文档，可能的参数
    param_combinations = [
        {'portCode': 'NZAKL'},
        {'portCode': 'NZTRG'},
        {'vesselName': 'MAERSK'},
        {'containerSize': '40'},
        {'containerType': 'GP'},
    ]

    results = {}

    for params in param_combinations:
        try:
            print(f"\n尝试参数: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=5)
            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 'N/A'
                print(f"✅ 成功! 返回 {count} 条记录")
                results[str(params)] = count
            elif response.status_code == 400:
                print(f"⚠️  400 - 参数可能不支持")
            else:
                print(f"状态: {response.status_code}")

        except Exception as e:
            print(f"异常: {e}")

    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚢 PortConnect Container Visits API 测试")
    print("="*60)

    # 测试1: 搜索集装箱
    containers = test_container_visits_search()

    # 测试2: 按ID查询
    if containers:
        test_container_visit_by_id()

    # 测试3: 测试不同参数
    test_available_parameters()

    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)

    print("\n💡 关于 Container Visits API:")
    print("  • 这个API需要真实的集装箱号或访问ID")
    print("  • 如果返回空结果，说明:")
    print("    - 集装箱号不在PortConnect系统中")
    print("    - 或者集装箱已经完成访问（很久以前）")
    print("  • 建议:")
    print("    1. 从 scheduled-vessels 获取真实船舶信息")
    print("    2. 联系PortConnect获取测试用的集装箱号")
    print("    3. 或使用webhook订阅实时接收新的集装箱数据")

    print("\n📝 可用的查询字段（基于API文档）:")
    fields = [
        "containerNumber", "containerVisitId", "portCode",
        "arrivalDateFrom", "arrivalDateTo", "vesselName",
        "bookingReference", "containerSize", "containerType"
    ]
    for i, field in enumerate(fields, 1):
        print(f"  {i}. {field}")
