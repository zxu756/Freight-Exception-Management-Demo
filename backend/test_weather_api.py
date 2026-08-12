"""
Visual Crossing Weather API 测试脚本
Test script for New Zealand weather data
"""
import requests
import json
from datetime import datetime, timedelta

# 你的API密钥
API_KEY = "37Y5H59434B8AYDHSRRFSBBFH"

def test_auckland_current_weather():
    """测试获取奥克兰当前天气"""
    print("\n" + "="*60)
    print("测试 1: 获取奥克兰当前天气")
    print("="*60)

    location = "Auckland,New Zealand"
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/today"

    params = {
        'key': API_KEY,
        'unitGroup': 'metric',
        'include': 'current'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        current = data.get('currentConditions', {})

        print(f"\n📍 位置: {data.get('resolvedAddress')}")
        print(f"⏰ 时间: {current.get('datetime')}")
        print(f"🌡️  温度: {current.get('temp')}°C (体感 {current.get('feelslike')}°C)")
        print(f"💧 湿度: {current.get('humidity')}%")
        print(f"🌧️  降雨: {current.get('precip', 0)} mm")
        print(f"💨 风速: {current.get('windspeed')} km/h")
        print(f"🧭 风向: {current.get('winddir')}°")
        print(f"☁️  云量: {current.get('cloudcover')}%")
        print(f"👁️  能见度: {current.get('visibility')} km")
        print(f"📊 气压: {current.get('pressure')} mb")
        print(f"🌤️  状况: {current.get('conditions')}")

        return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_cook_strait_weather():
    """测试获取库克海峡天气（重要海运路线）"""
    print("\n" + "="*60)
    print("测试 2: 获取库克海峡天气（Wellington-Picton ferry route）")
    print("="*60)

    # 库克海峡坐标
    location = "-41.2,174.5"
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/today"

    params = {
        'key': API_KEY,
        'unitGroup': 'metric',
        'include': 'current'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        current = data.get('currentConditions', {})

        print(f"\n📍 位置: Cook Strait (库克海峡)")
        print(f"🌡️  温度: {current.get('temp')}°C")
        print(f"💨 风速: {current.get('windspeed')} km/h")
        print(f"🌊 阵风: {current.get('windgust', 'N/A')} km/h")
        print(f"🌧️  降雨: {current.get('precip', 0)} mm")
        print(f"👁️  能见度: {current.get('visibility')} km")

        # 检查是否适合渡轮运行
        windspeed = current.get('windspeed', 0)
        if windspeed > 60:
            print("\n⚠️  警告: 风速过高，渡轮可能延误或取消！")
        elif windspeed > 40:
            print("\n⚠️  注意: 中度大风，可能影响渡轮准点")
        else:
            print("\n✅ 天气良好，适合渡轮运行")

        return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_historical_data():
    """测试获取历史天气数据"""
    print("\n" + "="*60)
    print("测试 3: 获取惠灵顿过去7天历史天气")
    print("="*60)

    location = "Wellington,New Zealand"

    # 获取过去7天
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"

    params = {
        'key': API_KEY,
        'unitGroup': 'metric'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        print(f"\n📍 位置: {data.get('resolvedAddress')}")
        print(f"\n过去7天天气概况:")
        print("-" * 60)

        for day in data.get('days', []):
            date = day.get('datetime')
            temp_max = day.get('tempmax')
            temp_min = day.get('tempmin')
            precip = day.get('precip', 0)
            windspeed = day.get('windspeed')
            conditions = day.get('conditions')

            print(f"{date} | {temp_min}°C - {temp_max}°C | 降雨:{precip}mm | 风速:{windspeed}km/h | {conditions}")

        return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_multiple_cities():
    """测试获取多个新西兰城市的天气"""
    print("\n" + "="*60)
    print("测试 4: 获取新西兰主要物流城市当前天气")
    print("="*60)

    cities = [
        ("Auckland", "-36.8485,174.7633"),
        ("Wellington", "-41.2865,174.7762"),
        ("Christchurch", "-43.5321,172.6362"),
        ("Hamilton", "-37.7870,175.2793"),
        ("Tauranga", "-37.6878,176.1651")
    ]

    print(f"\n{'城市':<15} {'温度':<10} {'风速':<10} {'降雨':<10} {'状况':<20}")
    print("-" * 70)

    for city_name, coords in cities:
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{coords}/today"

        params = {
            'key': API_KEY,
            'unitGroup': 'metric',
            'include': 'current'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            current = data.get('currentConditions', {})
            temp = current.get('temp', 'N/A')
            wind = current.get('windspeed', 'N/A')
            precip = current.get('precip', 0)
            conditions = current.get('conditions', 'N/A')

            print(f"{city_name:<15} {temp}°C      {wind} km/h   {precip} mm     {conditions}")

        except Exception as e:
            print(f"{city_name:<15} ❌ 获取失败: {e}")

    return True


def test_forecast():
    """测试获取未来天气预报"""
    print("\n" + "="*60)
    print("测试 5: 获取奥克兰未来3天天气预报")
    print("="*60)

    location = "Auckland,New Zealand"
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}"

    params = {
        'key': API_KEY,
        'unitGroup': 'metric',
        'include': 'days',
        'elements': 'datetime,tempmax,tempmin,precipprob,windspeed,conditions'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        print(f"\n📍 位置: {data.get('resolvedAddress')}")
        print(f"\n未来天气预报:")
        print("-" * 70)

        for i, day in enumerate(data.get('days', [])[:3]):
            date = day.get('datetime')
            temp_max = day.get('tempmax')
            temp_min = day.get('tempmin')
            precip_prob = day.get('precipprob', 0)
            windspeed = day.get('windspeed')
            conditions = day.get('conditions')

            print(f"\n{date} ({'今天' if i == 0 else '明天' if i == 1 else '后天'}):")
            print(f"  温度: {temp_min}°C - {temp_max}°C")
            print(f"  降雨概率: {precip_prob}%")
            print(f"  风速: {windspeed} km/h")
            print(f"  状况: {conditions}")

        return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def check_api_quota():
    """检查API配额使用情况"""
    print("\n" + "="*60)
    print("API 配额信息")
    print("="*60)

    print("\n你的API密钥: " + API_KEY[:10] + "..." + API_KEY[-5:])
    print("计划: 免费账户")
    print("配额: 1,000 次请求/天")
    print("重置时间: 每天 UTC 00:00")
    print("\n提示: 如果遇到 'Too many requests' 错误，说明今日配额已用完")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌦️  Visual Crossing Weather API 测试")
    print("新西兰物流天气数据获取")
    print("="*60)

    # 检查配额信息
    check_api_quota()

    # 运行所有测试
    tests = [
        test_auckland_current_weather,
        test_cook_strait_weather,
        test_historical_data,
        test_multiple_cities,
        test_forecast
    ]

    results = []
    for test_func in tests:
        try:
            success = test_func()
            results.append(success)
        except Exception as e:
            print(f"\n测试失败: {e}")
            results.append(False)

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"✅ 成功: {sum(results)}/{len(results)}")
    print(f"❌ 失败: {len(results) - sum(results)}/{len(results)}")

    if all(results):
        print("\n🎉 所有测试通过！API密钥有效，可以正常使用。")
        print("\n下一步:")
        print("1. 将 nz_weather_api.py 中的 API_KEY 替换为你的密钥")
        print("2. 运行 weather_exception_detector.py 测试异常检测")
        print("3. 开始生成历史天气数据用于AI训练")
    else:
        print("\n⚠️  部分测试失败，请检查:")
        print("1. API密钥是否正确")
        print("2. 网络连接是否正常")
        print("3. 是否超出免费配额（1000次/天）")
