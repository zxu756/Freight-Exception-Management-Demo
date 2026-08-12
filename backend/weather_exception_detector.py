"""
集成天气API到异常检测系统
Weather-Enhanced Exception Detection System
"""
from nz_weather_api import NZWeatherAPI
from datetime import datetime, timedelta
import random

class WeatherEnhancedExceptionDetector:
    """
    增强版异常检测器 - 集成实时天气数据
    """

    def __init__(self, weather_api_key: str):
        self.weather_api = NZWeatherAPI(weather_api_key)

    def detect_weather_related_exceptions(self, active_shipments: list) -> list:
        """
        检测所有进行中货运的天气相关风险

        Returns:
            检测到的异常列表
        """
        exceptions = []

        for shipment in active_shipments:
            # 获取路线天气
            route_weather = self.weather_api.get_shipping_route_weather(
                shipment['origin'],
                shipment['destination']
            )

            # 检查每个路段
            for segment in route_weather:
                severe = segment['severe_weather']

                if severe['has_severe_weather']:
                    # 计算预计延误
                    expected_delay = self._estimate_delay(
                        severe['severity'],
                        shipment['transport_mode'],
                        segment['location']
                    )

                    # 创建异常
                    exception = {
                        'shipment_id': shipment['shipment_id'],
                        'exception_type': 'weather_delay',
                        'location': segment['location'],
                        'severity': severe['severity'],
                        'weather_conditions': severe['conditions'],
                        'alerts': severe['alerts'],
                        'expected_delay_hours': expected_delay,
                        'detected_at': datetime.now(),
                        'weather_data': {
                            'wind_speed': severe['wind_speed'],
                            'precipitation': severe['precipitation'],
                            'visibility': severe['visibility']
                        }
                    }

                    exceptions.append(exception)

                    # 触发AI诊断
                    self._trigger_ai_diagnosis(exception, shipment)

        return exceptions

    def _estimate_delay(self, severity: str, transport_mode: str, location: str) -> float:
        """
        根据天气严重程度估算延误时长

        Args:
            severity: 'moderate', 'severe', 'extreme'
            transport_mode: 'road', 'sea', 'air'
            location: 受影响地点

        Returns:
            预计延误小时数
        """
        # 基础延误（小时）
        base_delays = {
            'moderate': 2,
            'severe': 6,
            'extreme': 24
        }

        base_delay = base_delays.get(severity, 0)

        # 运输模式影响系数
        mode_multipliers = {
            'sea': 1.5,      # 海运对天气更敏感
            'air': 2.0,      # 空运对天气极度敏感
            'road': 0.8      # 陆运相对灵活
        }

        multiplier = mode_multipliers.get(transport_mode, 1.0)

        # 特殊位置系数（如库克海峡）
        if 'Strait' in location or 'Sea' in location:
            multiplier *= 1.3

        return base_delay * multiplier

    def _trigger_ai_diagnosis(self, exception: dict, shipment: dict):
        """
        触发AI诊断，生成根因分析和解决方案
        """
        # 调用你现有的决策引擎
        from decision_engine import decision_engine
        from risk_calculator import calculate_risk_score, categorize_risk

        # 计算风险分数
        risk_score = calculate_risk_score(
            cargo_value=shipment['cargo_value'],
            customer_tier=shipment['customer_tier'],
            sla_breach_hours=exception['expected_delay_hours'],
            exception_type='weather_delay'
        )

        risk_level = categorize_risk(risk_score)

        # 生成AI诊断
        diagnosis = f"""
        天气异常检测报告

        货运: {shipment['shipment_id']}
        客户: {shipment['customer_name']} ({shipment['customer_tier']})

        天气状况:
        - 位置: {exception['location']}
        - 严重程度: {exception['severity']}
        - 条件: {exception['weather_conditions']}
        - 警报: {', '.join(exception['alerts'])}

        影响评估:
        - 预计延误: {exception['expected_delay_hours']:.1f} 小时
        - 风险等级: {risk_level}
        - 风险分数: {risk_score}/100

        实时数据:
        - 风速: {exception['weather_data']['wind_speed']} km/h
        - 降雨: {exception['weather_data']['precipitation']} mm
        - 能见度: {exception['weather_data']['visibility']} km
        """

        print(diagnosis)

        # 生成解决方案
        solutions = decision_engine.generate_solutions(
            exception_type='weather_delay',
            shipment=shipment,
            exception_data={
                'delayed_eta': datetime.now() + timedelta(hours=exception['expected_delay_hours']),
                'delay_hours': exception['expected_delay_hours'],
                'weather_severity': exception['severity']
            }
        )

        return {
            'diagnosis': diagnosis,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'solutions': solutions
        }

    def predict_weather_exceptions(self, scheduled_shipments: list, days_ahead: int = 3) -> list:
        """
        预测性异常检测 - 基于未来天气预报
        提前24-72小时预警可能的延误

        Args:
            scheduled_shipments: 计划中的货运列表
            days_ahead: 预测天数（1-7天）

        Returns:
            预测的异常列表
        """
        predictions = []

        for shipment in scheduled_shipments:
            # 获取未来天气预报
            origin_forecast = self.weather_api.get_forecast(
                shipment['origin'],
                days=days_ahead
            )
            dest_forecast = self.weather_api.get_forecast(
                shipment['destination'],
                days=days_ahead
            )

            # 检查预定日期的天气
            pickup_date = shipment['scheduled_pickup'].date()

            for forecast in origin_forecast.itertuples():
                forecast_date = datetime.strptime(forecast.datetime, '%Y-%m-%d').date()

                if forecast_date == pickup_date:
                    # 检查是否有恶劣天气预报
                    if forecast.windspeed > 60 or forecast.precipprob > 80:
                        prediction = {
                            'shipment_id': shipment['shipment_id'],
                            'alert_type': 'proactive_weather_warning',
                            'forecast_date': forecast_date,
                            'location': shipment['origin'],
                            'wind_speed': forecast.windspeed,
                            'precip_probability': forecast.precipprob,
                            'conditions': forecast.conditions,
                            'recommended_action': self._recommend_proactive_action(
                                forecast, shipment
                            ),
                            'predicted_at': datetime.now()
                        }

                        predictions.append(prediction)

        return predictions

    def _recommend_proactive_action(self, forecast, shipment) -> str:
        """
        基于预报推荐主动措施
        """
        if forecast.windspeed > 80:
            return "建议提前24小时改期或选择替代路线"
        elif forecast.windspeed > 60:
            return "建议提前通知客户可能延误，准备应急方案"
        elif forecast.precipprob > 80:
            return "建议增加运输时间缓冲，通知司机注意路况"
        else:
            return "正常监控，暂无需特殊措施"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化增强检测器
    detector = WeatherEnhancedExceptionDetector(
        weather_api_key="YOUR_API_KEY"
    )

    # 模拟进行中的货运
    active_shipments = [
        {
            'shipment_id': 'SF-2024-09002',
            'customer_name': 'Countdown Supermarkets',
            'customer_tier': 'high',
            'cargo_value': 28000,
            'origin': 'Wellington',
            'destination': 'Christchurch',
            'transport_mode': 'sea',
            'scheduled_pickup': datetime.now() - timedelta(hours=2),
            'scheduled_delivery': datetime.now() + timedelta(hours=14)
        }
    ]

    # 实时异常检测
    print("\n=== 实时天气异常检测 ===")
    exceptions = detector.detect_weather_related_exceptions(active_shipments)

    if exceptions:
        print(f"检测到 {len(exceptions)} 个天气相关异常:")
        for exc in exceptions:
            print(f"\n货运: {exc['shipment_id']}")
            print(f"位置: {exc['location']}")
            print(f"严重程度: {exc['severity']}")
            print(f"预计延误: {exc['expected_delay_hours']:.1f} 小时")
            print(f"警报: {exc['alerts']}")
    else:
        print("未检测到天气异常")

    # 预测性检测
    print("\n=== 未来3天天气风险预测 ===")
    scheduled_shipments = [
        {
            'shipment_id': 'SF-2024-09010',
            'customer_name': 'Fisher & Paykel',
            'customer_tier': 'VIP',
            'origin': 'Auckland',
            'destination': 'Wellington',
            'transport_mode': 'sea',
            'scheduled_pickup': datetime.now() + timedelta(days=2)
        }
    ]

    predictions = detector.predict_weather_exceptions(scheduled_shipments, days_ahead=3)

    if predictions:
        print(f"发现 {len(predictions)} 个潜在天气风险:")
        for pred in predictions:
            print(f"\n货运: {pred['shipment_id']}")
            print(f"预报日期: {pred['forecast_date']}")
            print(f"风速: {pred['wind_speed']} km/h")
            print(f"降雨概率: {pred['precip_probability']}%")
            print(f"推荐措施: {pred['recommended_action']}")
    else:
        print("未来3天天气状况良好")
