"""
PortConnect 模拟数据生成器
Mock Data Generator for PortConnect API

用于开发和测试，模拟真实的港口和集装箱数据
等真实API配置完成后，可以无缝切换
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List
import json


class PortConnectMockAPI:
    """
    PortConnect模拟API
    生成真实感的港口和集装箱数据
    """

    def __init__(self):
        """初始化模拟数据"""
        self.vessels = self._generate_vessels()
        self.containers = self._generate_containers()

    def _generate_vessels(self) -> List[Dict]:
        """生成模拟船舶数据"""
        vessel_names = [
            "Southern Star", "Pacific Navigator", "Kiwi Express",
            "Tasman Trader", "ANL Whangarei", "Maersk Eindhoven",
            "MSC Amsterdam", "CMA CGM Libra", "COSCO Wellington"
        ]

        ports = ["NZAKL", "NZTRG", "NZTIU", "NZLYT", "NZWLG"]

        vessels = []
        for i, name in enumerate(vessel_names):
            now = datetime.now()

            # 随机生成到达和离开时间
            eta = now + timedelta(days=random.randint(-2, 5), hours=random.randint(0, 23))
            etd = eta + timedelta(days=random.randint(1, 3))

            vessel = {
                "vesselName": name,
                "voyageNumber": f"V{2024000 + i}",
                "imo": f"IMO{9000000 + i}",
                "portCode": random.choice(ports),
                "eta": eta.isoformat(),
                "etd": etd.isoformat(),
                "status": random.choice(["Expected", "Arrived", "Berthed", "Departed"]),
                "berthLocation": f"Berth {random.randint(1, 12)}",
                "containerCount": random.randint(50, 500)
            }

            # 有15%概率是延误状态
            if random.random() < 0.15:
                original_eta = eta - timedelta(hours=random.randint(6, 48))
                vessel["status"] = "Delayed"
                vessel["originalEta"] = original_eta.isoformat()
                vessel["delayReason"] = random.choice([
                    "Weather - High winds in Cook Strait",
                    "Port congestion",
                    "Mechanical issue",
                    "Berthing delay"
                ])
                vessel["delayHours"] = (eta - original_eta).total_seconds() / 3600

            vessels.append(vessel)

        return vessels

    def _generate_containers(self) -> List[Dict]:
        """生成模拟集装箱数据"""
        operators = ["MSCU", "MAEU", "CMAU", "CSLU", "HLCU"]
        statuses = [
            "On Vessel",
            "Discharged",
            "Available for Collection",
            "Collected",
            "Customs Hold",
            "Gate Out"
        ]

        containers = []
        for _ in range(50):  # 生成50个集装箱
            operator = random.choice(operators)
            number = f"{operator}{random.randint(1000000, 9999999)}"

            vessel = random.choice(self.vessels)

            container = {
                "containerNumber": number,
                "status": random.choice(statuses),
                "vesselName": vessel["vesselName"],
                "voyageNumber": vessel["voyageNumber"],
                "portCode": vessel["portCode"],
                "size": random.choice(["20FT", "40FT", "40HC"]),
                "type": random.choice(["GP", "RF", "OT", "FR"]),
                "weight": random.randint(5000, 28000),
                "arrivalDate": vessel["eta"],
                "dischargeDate": None,
                "availableDate": None,
                "collectionDate": None,
                "customsCleared": random.choice([True, False]),
                "biosecurityCleared": random.choice([True, False])
            }

            # 根据状态设置日期
            if container["status"] in ["Discharged", "Available for Collection", "Collected"]:
                arrival = datetime.fromisoformat(vessel["eta"])
                container["dischargeDate"] = (arrival + timedelta(hours=random.randint(2, 24))).isoformat()

            if container["status"] in ["Available for Collection", "Collected"]:
                discharge = datetime.fromisoformat(container["dischargeDate"])
                container["availableDate"] = (discharge + timedelta(hours=random.randint(1, 48))).isoformat()

            if container["status"] == "Collected":
                available = datetime.fromisoformat(container["availableDate"])
                container["collectionDate"] = (available + timedelta(hours=random.randint(1, 72))).isoformat()

            containers.append(container)

        return containers

    def get_vessel_schedule(self, port_code: str = "NZAKL") -> List[Dict]:
        """
        模拟获取船舶时刻表

        Args:
            port_code: 港口代码

        Returns:
            船舶列表
        """
        return [v for v in self.vessels if v["portCode"] == port_code]

    def get_container_status(self, container_number: str) -> Dict:
        """
        模拟获取集装箱状态

        Args:
            container_number: 集装箱号

        Returns:
            集装箱信息
        """
        # 查找已有的集装箱
        for container in self.containers:
            if container["containerNumber"] == container_number:
                return container

        # 如果找不到，生成一个新的
        return self._generate_new_container(container_number)

    def _generate_new_container(self, container_number: str) -> Dict:
        """为未知集装箱号生成新数据"""
        vessel = random.choice(self.vessels)

        return {
            "containerNumber": container_number,
            "status": "On Vessel",
            "vesselName": vessel["vesselName"],
            "voyageNumber": vessel["voyageNumber"],
            "portCode": vessel["portCode"],
            "size": "40FT",
            "type": "GP",
            "weight": 18000,
            "arrivalDate": vessel["eta"],
            "customsCleared": False,
            "biosecurityCleared": False
        }

    def check_vessel_delays(self, port_code: str = None) -> List[Dict]:
        """
        检查船舶延误

        Args:
            port_code: 港口代码（可选）

        Returns:
            延误船舶列表
        """
        delays = []
        vessels = self.vessels if not port_code else [v for v in self.vessels if v["portCode"] == port_code]

        for vessel in vessels:
            if vessel.get("status") == "Delayed":
                delays.append({
                    "vesselName": vessel["vesselName"],
                    "voyageNumber": vessel["voyageNumber"],
                    "portCode": vessel["portCode"],
                    "originalEta": vessel.get("originalEta"),
                    "revisedEta": vessel["eta"],
                    "delayHours": vessel.get("delayHours", 0),
                    "reason": vessel.get("delayReason"),
                    "affectedContainers": vessel.get("containerCount", 0)
                })

        return delays

    def simulate_container_event(self, container_number: str, event_type: str) -> Dict:
        """
        模拟集装箱事件

        Args:
            container_number: 集装箱号
            event_type: 事件类型

        Returns:
            事件数据
        """
        event = {
            "eventId": f"EVT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "containerNumber": container_number,
            "eventType": event_type,
            "timestamp": datetime.now().isoformat(),
            "location": random.choice(["NZAKL", "NZTRG", "NZTIU", "NZLYT"])
        }

        event_details = {
            "Vessel Arrived": {
                "vesselName": "Southern Star",
                "berthLocation": "Berth 5"
            },
            "Container Discharged": {
                "stackLocation": f"Stack A{random.randint(1, 20)}"
            },
            "Container Available for Collection": {
                "availableFrom": datetime.now().isoformat(),
                "note": "All clearances complete"
            },
            "Customs Hold": {
                "holdReason": "Documentation required",
                "contactEmail": "customs@mpi.govt.nz"
            }
        }

        if event_type in event_details:
            event.update(event_details[event_type])

        return event


# ==================== 使用示例 ====================

def demo_mock_api():
    """演示模拟API的使用"""
    print("="*60)
    print("🚢 PortConnect 模拟API演示")
    print("="*60)

    # 初始化模拟API
    mock_api = PortConnectMockAPI()

    # 示例1: 获取奥克兰港船舶时刻表
    print("\n📍 示例1: 奥克兰港船舶时刻表")
    print("-"*60)
    vessels = mock_api.get_vessel_schedule("NZAKL")
    print(f"找到 {len(vessels)} 艘船")
    for vessel in vessels[:3]:
        print(f"\n船名: {vessel['vesselName']}")
        print(f"  航次: {vessel['voyageNumber']}")
        print(f"  状态: {vessel['status']}")
        print(f"  ETA: {vessel['eta']}")
        if vessel['status'] == 'Delayed':
            print(f"  ⚠️ 延误: {vessel.get('delayHours', 0):.1f} 小时")
            print(f"  原因: {vessel.get('delayReason')}")

    # 示例2: 检查延误
    print("\n⚠️  示例2: 检查所有港口的船舶延误")
    print("-"*60)
    delays = mock_api.check_vessel_delays()
    if delays:
        print(f"发现 {len(delays)} 艘船舶延误:")
        for delay in delays:
            print(f"\n• {delay['vesselName']} ({delay['portCode']})")
            print(f"  延误: {delay['delayHours']:.1f} 小时")
            print(f"  原因: {delay['reason']}")
            print(f"  受影响集装箱: {delay['affectedContainers']}")
    else:
        print("✅ 没有船舶延误")

    # 示例3: 查询集装箱
    print("\n📦 示例3: 查询集装箱状态")
    print("-"*60)
    test_container = mock_api.containers[0]["containerNumber"]
    container = mock_api.get_container_status(test_container)
    print(f"集装箱: {container['containerNumber']}")
    print(f"状态: {container['status']}")
    print(f"船名: {container['vesselName']}")
    print(f"港口: {container['portCode']}")
    print(f"清关: {'✅' if container['customsCleared'] else '❌'}")

    # 示例4: 模拟事件
    print("\n🔔 示例4: 模拟实时事件")
    print("-"*60)
    event = mock_api.simulate_container_event(test_container, "Container Discharged")
    print(json.dumps(event, indent=2))

    print("\n" + "="*60)
    print("💡 提示:")
    print("  这些是模拟数据，用于开发和测试")
    print("  真实API配置完成后，只需替换数据源")
    print("  模拟数据的行为和格式与真实API一致")
    print("="*60)


if __name__ == "__main__":
    demo_mock_api()

    # 保存示例数据到JSON文件
    mock_api = PortConnectMockAPI()

    with open('mock_vessels.json', 'w') as f:
        json.dump(mock_api.vessels, f, indent=2)
    print("\n✅ 船舶数据已保存到 mock_vessels.json")

    with open('mock_containers.json', 'w') as f:
        json.dump(mock_api.containers, f, indent=2)
    print("✅ 集装箱数据已保存到 mock_containers.json")
