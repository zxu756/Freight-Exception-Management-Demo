"""
PortConnect API Integration for New Zealand Ports
新西兰港口数据平台API集成

Official API: https://developer.portconnect.io/

Supported Ports:
- Auckland Port
- Port of Tauranga
- Port Timaru
- Lyttelton Port (Christchurch)
"""
import requests
from datetime import datetime
from typing import Dict, List, Optional
import json


class PortConnectAPI:
    """
    PortConnect API客户端
    用于获取新西兰港口的船舶和集装箱信息
    """

    def __init__(self, api_key: str):
        """
        初始化PortConnect API客户端

        Args:
            api_key: PortConnect API密钥
                    获取地址: https://developer.portconnect.io/
        """
        self.api_key = api_key
        self.base_url = "https://api.portconnect.io/v1"  # 假设的API基础URL
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # 新西兰主要港口代码
        self.nz_ports = {
            "NZAKL": {"name": "Auckland Port", "city": "Auckland"},
            "NZTRG": {"name": "Port of Tauranga", "city": "Tauranga"},
            "NZTIU": {"name": "Port Timaru", "city": "Timaru"},
            "NZLYT": {"name": "Lyttelton Port", "city": "Christchurch"},
        }

    def get_vessel_schedule(self, port_code: str, days_ahead: int = 7) -> List[Dict]:
        """
        获取港口的船舶时刻表

        Args:
            port_code: 港口代码 (如 "NZAKL")
            days_ahead: 获取未来多少天的船期

        Returns:
            船舶时刻表列表
        """
        endpoint = f"{self.base_url}/ports/{port_code}/vessels"
        params = {
            'days_ahead': days_ahead
        }

        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching vessel schedule: {e}")
            return []

    def get_container_status(self, container_number: str) -> Dict:
        """
        获取集装箱状态

        Args:
            container_number: 集装箱号 (如 "MSCU1234567")

        Returns:
            集装箱状态信息
        """
        endpoint = f"{self.base_url}/containers/{container_number}"

        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            return {
                'container_number': container_number,
                'status': data.get('status'),  # 'at_port', 'discharged', 'available', 'collected'
                'current_location': data.get('location'),
                'port_code': data.get('port_code'),
                'vessel_name': data.get('vessel_name'),
                'arrival_time': data.get('arrival_time'),
                'discharge_time': data.get('discharge_time'),
                'available_from': data.get('available_from'),
                'customs_cleared': data.get('customs_cleared', False),
                'last_updated': data.get('last_updated')
            }
        except requests.exceptions.RequestException as e:
            print(f"Error fetching container status: {e}")
            return None

    def get_container_events(self, container_number: str) -> List[Dict]:
        """
        获取集装箱的完整事件历史

        Args:
            container_number: 集装箱号

        Returns:
            事件列表（按时间排序）
        """
        endpoint = f"{self.base_url}/containers/{container_number}/events"

        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json().get('events', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching container events: {e}")
            return []

    def subscribe_container(self, container_number: str, webhook_url: str) -> bool:
        """
        订阅集装箱事件（通过webhook接收实时更新）

        Args:
            container_number: 集装箱号
            webhook_url: 你的webhook接收地址

        Returns:
            订阅是否成功
        """
        endpoint = f"{self.base_url}/subscriptions"

        payload = {
            'container_number': container_number,
            'webhook_url': webhook_url,
            'event_types': [
                'vessel_arrived',
                'container_discharged',
                'container_available',
                'customs_cleared',
                'container_collected',
                'vessel_delayed'
            ]
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            print(f"✅ Successfully subscribed to container {container_number}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error subscribing to container: {e}")
            return False

    def check_vessel_delays(self, port_code: str) -> List[Dict]:
        """
        检查港口的船舶延误情况

        Args:
            port_code: 港口代码

        Returns:
            延误船舶列表
        """
        schedule = self.get_vessel_schedule(port_code)
        delays = []

        for vessel in schedule:
            if vessel.get('status') == 'delayed':
                delay_info = {
                    'vessel_name': vessel.get('vessel_name'),
                    'voyage_number': vessel.get('voyage_number'),
                    'original_eta': vessel.get('original_eta'),
                    'revised_eta': vessel.get('revised_eta'),
                    'delay_hours': self._calculate_delay_hours(
                        vessel.get('original_eta'),
                        vessel.get('revised_eta')
                    ),
                    'reason': vessel.get('delay_reason'),
                    'affected_containers': vessel.get('container_count', 0)
                }
                delays.append(delay_info)

        return delays

    def get_port_congestion_status(self, port_code: str) -> Dict:
        """
        获取港口拥堵状态

        Args:
            port_code: 港口代码

        Returns:
            港口状态信息
        """
        endpoint = f"{self.base_url}/ports/{port_code}/status"

        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            return {
                'port_code': port_code,
                'port_name': self.nz_ports[port_code]['name'],
                'operational_status': data.get('status'),  # 'normal', 'congested', 'closed'
                'berth_occupancy': data.get('berth_occupancy_percent'),
                'avg_waiting_time_hours': data.get('avg_waiting_time'),
                'vessels_waiting': data.get('vessels_waiting'),
                'containers_pending_collection': data.get('containers_pending'),
                'updated_at': data.get('updated_at')
            }
        except requests.exceptions.RequestException as e:
            print(f"Error fetching port status: {e}")
            return None

    def detect_exceptions_for_container(self, container_number: str, expected_eta: datetime) -> List[Dict]:
        """
        检测集装箱的异常情况

        Args:
            container_number: 集装箱号
            expected_eta: 预期到达时间

        Returns:
            检测到的异常列表
        """
        exceptions = []

        # 获取集装箱当前状态
        status = self.get_container_status(container_number)

        if not status:
            exceptions.append({
                'type': 'container_not_found',
                'severity': 'high',
                'message': f"Container {container_number} not found in PortConnect system"
            })
            return exceptions

        # 检查延误
        if status['status'] == 'at_sea':
            vessel_info = self._get_vessel_info(status['vessel_name'])
            if vessel_info and vessel_info.get('status') == 'delayed':
                exceptions.append({
                    'type': 'vessel_delay',
                    'severity': 'medium',
                    'message': f"Vessel {status['vessel_name']} delayed",
                    'delay_hours': vessel_info.get('delay_hours'),
                    'reason': vessel_info.get('delay_reason')
                })

        # 检查集装箱是否逾期未到
        if status['arrival_time']:
            arrival = datetime.fromisoformat(status['arrival_time'])
            if arrival > expected_eta:
                delay = (arrival - expected_eta).total_seconds() / 3600
                exceptions.append({
                    'type': 'late_arrival',
                    'severity': 'high' if delay > 24 else 'medium',
                    'message': f"Container arrived {delay:.1f} hours late",
                    'expected': expected_eta.isoformat(),
                    'actual': arrival.isoformat()
                })

        # 检查清关问题
        if status['status'] == 'at_port' and not status['customs_cleared']:
            exceptions.append({
                'type': 'customs_delay',
                'severity': 'high',
                'message': "Container at port but customs not cleared",
                'location': status['current_location']
            })

        # 检查货物不可提取
        if status['status'] == 'hold':
            exceptions.append({
                'type': 'container_hold',
                'severity': 'critical',
                'message': "Container on hold - cannot be collected",
                'reason': status.get('hold_reason', 'Unknown')
            })

        return exceptions

    def _calculate_delay_hours(self, original_eta: str, revised_eta: str) -> float:
        """计算延误小时数"""
        try:
            original = datetime.fromisoformat(original_eta)
            revised = datetime.fromisoformat(revised_eta)
            return (revised - original).total_seconds() / 3600
        except:
            return 0

    def _get_vessel_info(self, vessel_name: str) -> Optional[Dict]:
        """获取船舶信息（简化版）"""
        # 在实际应用中，这里会调用vessel API
        return None


# ==================== Webhook处理器 ====================

class PortConnectWebhookHandler:
    """
    处理来自PortConnect的webhook事件
    """

    def __init__(self):
        self.event_handlers = {
            'vessel_arrived': self.handle_vessel_arrival,
            'vessel_delayed': self.handle_vessel_delay,
            'container_discharged': self.handle_container_discharged,
            'container_available': self.handle_container_available,
            'customs_cleared': self.handle_customs_cleared,
            'container_hold': self.handle_container_hold,
        }

    def process_webhook(self, event_data: Dict) -> Dict:
        """
        处理webhook事件

        Args:
            event_data: PortConnect发送的事件数据

        Returns:
            处理结果
        """
        event_type = event_data.get('event_type')
        handler = self.event_handlers.get(event_type)

        if handler:
            return handler(event_data)
        else:
            print(f"Unknown event type: {event_type}")
            return {'status': 'unknown_event'}

    def handle_vessel_delay(self, event: Dict) -> Dict:
        """处理船舶延误事件"""
        print(f"⚠️ Vessel Delay Detected:")
        print(f"  Vessel: {event['vessel_name']}")
        print(f"  Original ETA: {event['original_eta']}")
        print(f"  Revised ETA: {event['revised_eta']}")
        print(f"  Delay: {event['delay_hours']} hours")
        print(f"  Reason: {event['delay_reason']}")

        # 触发你的异常管理系统
        from models import Exception as ExceptionModel
        # 创建异常记录...

        return {'status': 'processed', 'action': 'exception_created'}

    def handle_container_discharged(self, event: Dict) -> Dict:
        """处理集装箱卸货事件"""
        print(f"📦 Container Discharged:")
        print(f"  Container: {event['container_number']}")
        print(f"  Port: {event['port_code']}")
        print(f"  Time: {event['discharge_time']}")

        return {'status': 'processed'}

    def handle_container_available(self, event: Dict) -> Dict:
        """处理集装箱可提取事件"""
        print(f"✅ Container Available for Collection:")
        print(f"  Container: {event['container_number']}")
        print(f"  Available from: {event['available_from']}")

        # 通知运输团队
        return {'status': 'processed', 'action': 'notify_transport_team'}

    def handle_customs_cleared(self, event: Dict) -> Dict:
        """处理清关完成事件"""
        print(f"🛂 Customs Cleared:")
        print(f"  Container: {event['container_number']}")

        return {'status': 'processed'}

    def handle_container_hold(self, event: Dict) -> Dict:
        """处理集装箱扣留事件"""
        print(f"🚨 Container Hold:")
        print(f"  Container: {event['container_number']}")
        print(f"  Reason: {event['hold_reason']}")

        # 创建高优先级异常
        return {'status': 'processed', 'action': 'create_critical_exception'}

    def handle_vessel_arrival(self, event: Dict) -> Dict:
        """处理船舶到港事件"""
        print(f"🚢 Vessel Arrived:")
        print(f"  Vessel: {event['vessel_name']}")
        print(f"  Port: {event['port_code']}")
        print(f"  Arrival Time: {event['arrival_time']}")

        return {'status': 'processed'}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 注意：这是示例代码，实际API端点和响应格式需要参考PortConnect官方文档
    # 目前PortConnect API可能需要申请账户才能访问

    print("\n" + "="*60)
    print("🚢 PortConnect API 集成示例")
    print("新西兰港口数据平台")
    print("="*60)

    # 初始化API客户端（需要实际的API密钥）
    # api = PortConnectAPI(api_key="YOUR_PORTCONNECT_API_KEY")

    print("\n示例1: 检查奥克兰港船舶延误")
    print("-" * 60)
    # delays = api.check_vessel_delays("NZAKL")
    # for delay in delays:
    #     print(f"船舶: {delay['vessel_name']}")
    #     print(f"延误: {delay['delay_hours']} 小时")
    #     print(f"原因: {delay['reason']}")

    print("\n示例2: 获取集装箱状态")
    print("-" * 60)
    # status = api.get_container_status("MSCU1234567")
    # print(f"集装箱: {status['container_number']}")
    # print(f"状态: {status['status']}")
    # print(f"位置: {status['current_location']}")
    # print(f"清关: {status['customs_cleared']}")

    print("\n示例3: 订阅集装箱事件")
    print("-" * 60)
    # success = api.subscribe_container(
    #     container_number="MSCU1234567",
    #     webhook_url="https://your-server.com/webhooks/portconnect"
    # )

    print("\n示例4: 检测异常")
    print("-" * 60)
    # exceptions = api.detect_exceptions_for_container(
    #     container_number="MSCU1234567",
    #     expected_eta=datetime(2026, 8, 15, 14, 0)
    # )
    # for exc in exceptions:
    #     print(f"异常类型: {exc['type']}")
    #     print(f"严重程度: {exc['severity']}")
    #     print(f"信息: {exc['message']}")

    print("\n" + "="*60)
    print("注意事项:")
    print("1. 需要在 https://developer.portconnect.io/ 注册账户")
    print("2. 申请API密钥")
    print("3. 实际API端点和数据格式需参考官方文档")
    print("4. Webhook需要公网可访问的URL")
    print("="*60)
