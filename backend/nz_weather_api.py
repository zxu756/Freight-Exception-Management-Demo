"""
Visual Crossing Weather API Integration for New Zealand Locations
获取新西兰各地的历史和实时天气数据
"""
import requests
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional

class NZWeatherAPI:
    """
    新西兰天气数据API客户端
    支持奥克兰、惠灵顿、基督城、陶朗加等主要城市
    """

    def __init__(self, api_key: str):
        """
        初始化API客户端

        Args:
            api_key: Visual Crossing API密钥
                    免费账户: 1000次请求/天
                    获取地址: https://www.visualcrossing.com/weather-api
        """
        self.api_key = api_key
        self.base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

        # 新西兰主要物流城市坐标
        self.nz_locations = {
            "Auckland": "-36.8485,174.7633",
            "Wellington": "-41.2865,174.7762",
            "Christchurch": "-43.5321,172.6362",
            "Hamilton": "-37.7870,175.2793",
            "Tauranga": "-37.6878,176.1651",
            "Dunedin": "-45.8788,170.5028",
            "Palmerston North": "-40.3523,175.6082",
            "Napier": "-39.4928,176.9120",

            # 重要海域（用于海运路线）
            "Cook Strait": "-41.2,174.5",  # 库克海峡
            "Hauraki Gulf": "-36.7,175.2",  # 豪拉基湾（奥克兰港外）
            "Tasman Sea": "-40.0,170.0",   # 塔斯曼海
        }

    def get_current_weather(self, location: str) -> Dict:
        """
        获取当前天气

        Args:
            location: 城市名称（如 "Auckland"）或坐标

        Returns:
            当前天气数据字典
        """
        # 转换为坐标（如果是城市名）
        coords = self.nz_locations.get(location, location)

        url = f"{self.base_url}/{coords}/today"
        params = {
            'key': self.api_key,
            'unitGroup': 'metric',  # 使用公制单位
            'include': 'current',
            'elements': 'datetime,temp,feelslike,humidity,precip,precipprob,windspeed,winddir,pressure,cloudcover,visibility,conditions'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        return self._parse_current_weather(data, location)

    def get_historical_weather(self, location: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取历史天气数据

        Args:
            location: 城市名称或坐标
            start_date: 开始日期 "YYYY-MM-DD"
            end_date: 结束日期 "YYYY-MM-DD"

        Returns:
            历史天气数据DataFrame

        Example:
            >>> api = NZWeatherAPI("your_api_key")
            >>> df = api.get_historical_weather("Auckland", "2024-01-01", "2024-12-31")
            >>> print(df.head())
        """
        coords = self.nz_locations.get(location, location)

        url = f"{self.base_url}/{coords}/{start_date}/{end_date}"
        params = {
            'key': self.api_key,
            'unitGroup': 'metric',
            'elements': 'datetime,tempmax,tempmin,temp,feelslike,humidity,precip,precipprob,preciptype,snow,windspeed,windgust,winddir,pressure,cloudcover,visibility,conditions,description'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # 转换为DataFrame
        df = pd.DataFrame(data['days'])
        df['location'] = location
        df['latitude'] = data['latitude']
        df['longitude'] = data['longitude']

        return df

    def get_forecast(self, location: str, days: int = 7) -> pd.DataFrame:
        """
        获取未来天气预报

        Args:
            location: 城市名称
            days: 预报天数（1-15天）

        Returns:
            天气预报DataFrame
        """
        coords = self.nz_locations.get(location, location)

        # 计算日期范围
        today = datetime.now()
        end_date = today + timedelta(days=days)

        url = f"{self.base_url}/{coords}/{today.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        params = {
            'key': self.api_key,
            'unitGroup': 'metric',
            'include': 'days,hours',
            'elements': 'datetime,tempmax,tempmin,precipprob,windspeed,windgust,conditions'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data['days'])
        df['location'] = location

        return df

    def check_severe_weather(self, location: str) -> Dict:
        """
        检查是否有恶劣天气（用于运输异常检测）

        Returns:
            {
                'has_severe_weather': bool,
                'severity': 'none' | 'moderate' | 'severe' | 'extreme',
                'conditions': str,
                'wind_speed': float,
                'precipitation': float,
                'alerts': List[str]
            }
        """
        weather = self.get_current_weather(location)
        alerts = []
        severity = 'none'

        # 检查风速（影响海运和陆运）
        if weather['windspeed'] > 80:  # 80+ km/h
            alerts.append(f"极强风速: {weather['windspeed']} km/h")
            severity = 'extreme'
        elif weather['windspeed'] > 60:
            alerts.append(f"强风: {weather['windspeed']} km/h")
            severity = 'severe' if severity != 'extreme' else severity
        elif weather['windspeed'] > 40:
            alerts.append(f"中度大风: {weather['windspeed']} km/h")
            severity = 'moderate' if severity == 'none' else severity

        # 检查降雨（影响陆运）
        if weather['precip'] > 50:  # 50+ mm
            alerts.append(f"暴雨: {weather['precip']} mm")
            severity = 'severe' if severity != 'extreme' else severity
        elif weather['precip'] > 20:
            alerts.append(f"大雨: {weather['precip']} mm")
            severity = 'moderate' if severity == 'none' else severity

        # 检查能见度（影响海运和空运）
        if weather['visibility'] < 1:  # < 1 km
            alerts.append(f"极低能见度: {weather['visibility']} km")
            severity = 'severe' if severity not in ['severe', 'extreme'] else severity
        elif weather['visibility'] < 5:
            alerts.append(f"低能见度: {weather['visibility']} km")
            severity = 'moderate' if severity == 'none' else severity

        return {
            'has_severe_weather': len(alerts) > 0,
            'severity': severity,
            'conditions': weather['conditions'],
            'wind_speed': weather['windspeed'],
            'precipitation': weather['precip'],
            'visibility': weather['visibility'],
            'alerts': alerts,
            'timestamp': weather['datetime']
        }

    def get_shipping_route_weather(self, origin: str, destination: str) -> List[Dict]:
        """
        获取运输路线沿途的天气情况

        Args:
            origin: 起点城市
            destination: 终点城市

        Returns:
            沿途关键点的天气列表
        """
        # 定义主要运输路线的中间点
        route_waypoints = {
            ('Auckland', 'Wellington'): ['Auckland', 'Hamilton', 'Taupo', 'Palmerston North', 'Wellington'],
            ('Auckland', 'Christchurch'): ['Auckland', 'Hamilton', 'Taupo', 'Wellington', 'Christchurch'],
            ('Wellington', 'Christchurch'): ['Wellington', 'Cook Strait', 'Christchurch'],
            ('Auckland', 'Tauranga'): ['Auckland', 'Tauranga'],
        }

        # 获取路线的关键点
        route_key = (origin, destination)
        waypoints = route_waypoints.get(route_key, [origin, destination])

        # 获取每个点的天气
        route_weather = []
        for location in waypoints:
            try:
                weather = self.get_current_weather(location)
                severe_check = self.check_severe_weather(location)

                route_weather.append({
                    'location': location,
                    'weather': weather,
                    'severe_weather': severe_check
                })
            except Exception as e:
                print(f"Error getting weather for {location}: {e}")

        return route_weather

    def _parse_current_weather(self, data: Dict, location: str) -> Dict:
        """解析当前天气数据"""
        current = data.get('currentConditions', data.get('days', [{}])[0])

        return {
            'location': location,
            'datetime': current.get('datetime'),
            'temp': current.get('temp'),
            'feelslike': current.get('feelslike'),
            'humidity': current.get('humidity'),
            'precip': current.get('precip', 0),
            'precipprob': current.get('precipprob', 0),
            'windspeed': current.get('windspeed'),
            'winddir': current.get('winddir'),
            'pressure': current.get('pressure'),
            'cloudcover': current.get('cloudcover'),
            'visibility': current.get('visibility'),
            'conditions': current.get('conditions', 'Unknown')
        }

    def generate_historical_weather_dataset(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        生成所有新西兰物流城市的历史天气数据集
        用于AI模型训练

        Args:
            start_date: "YYYY-MM-DD"
            end_date: "YYYY-MM-DD"

        Returns:
            完整的历史天气数据集
        """
        all_weather = []

        for location in self.nz_locations.keys():
            print(f"Fetching weather data for {location}...")
            try:
                df = self.get_historical_weather(location, start_date, end_date)
                all_weather.append(df)
            except Exception as e:
                print(f"Error fetching data for {location}: {e}")

        # 合并所有数据
        combined_df = pd.concat(all_weather, ignore_index=True)

        # 添加派生特征
        combined_df['is_winter'] = pd.to_datetime(combined_df['datetime']).dt.month.isin([6, 7, 8])
        combined_df['is_severe_wind'] = combined_df['windspeed'] > 60
        combined_df['is_heavy_rain'] = combined_df['precip'] > 20
        combined_df['is_poor_visibility'] = combined_df['visibility'] < 5

        return combined_df


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化API（需要你的API密钥）
    API_KEY = "YOUR_API_KEY_HERE"  # 从 https://www.visualcrossing.com/ 获取
    weather = NZWeatherAPI(API_KEY)

    # 示例1: 获取奥克兰当前天气
    print("\n=== 奥克兰当前天气 ===")
    current = weather.get_current_weather("Auckland")
    print(f"温度: {current['temp']}°C")
    print(f"风速: {current['windspeed']} km/h")
    print(f"降雨: {current['precip']} mm")
    print(f"状况: {current['conditions']}")

    # 示例2: 检查恶劣天气（用于异常检测）
    print("\n=== 库克海峡恶劣天气检查 ===")
    severe = weather.check_severe_weather("Cook Strait")
    print(f"有恶劣天气: {severe['has_severe_weather']}")
    print(f"严重程度: {severe['severity']}")
    print(f"警报: {severe['alerts']}")

    # 示例3: 获取运输路线天气
    print("\n=== 奥克兰→惠灵顿路线天气 ===")
    route_weather = weather.get_shipping_route_weather("Auckland", "Wellington")
    for point in route_weather:
        print(f"\n{point['location']}:")
        print(f"  温度: {point['weather']['temp']}°C")
        print(f"  风速: {point['weather']['windspeed']} km/h")
        if point['severe_weather']['has_severe_weather']:
            print(f"  ⚠️ 警报: {point['severe_weather']['alerts']}")

    # 示例4: 生成历史数据集（用于AI训练）
    print("\n=== 生成2024年历史天气数据 ===")
    df_weather = weather.generate_historical_weather_dataset(
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(f"总记录数: {len(df_weather)}")
    print(f"城市数: {df_weather['location'].nunique()}")
    print(f"恶劣天气天数: {df_weather['is_severe_wind'].sum()}")

    # 保存到CSV
    df_weather.to_csv('nz_weather_2024.csv', index=False)
    print("数据已保存到 nz_weather_2024.csv")
