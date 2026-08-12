"""
测试PortConnect About端点
直接测试API的About操作
"""
import requests
import json

PRIMARY_KEY = "56e067a235704e00b246de774f557d01"

def test_about_endpoint():
    """测试About端点（通常返回API版本和基本信息）"""

    print("="*60)
    print("测试 PortConnect About 端点")
    print("="*60)

    # 可能的About端点URL
    possible_urls = [
        "https://api.portconnect.io/about",
        "https://api.portconnect.io/v1/about",
        "https://api.portconnect.io/v2/about",
        "https://api.portconnect.io/api/about",
    ]

    headers = {
        'Ocp-Apim-Subscription-Key': PRIMARY_KEY,
        'Content-Type': 'application/json'
    }

    for url in possible_urls:
        print(f"\n尝试: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                print("✅ 成功!")
                try:
                    data = response.json()
                    print("\n响应数据:")
                    print(json.dumps(data, indent=2))
                except:
                    print(f"响应 (文本): {response.text}")
                return True
            elif response.status_code == 404:
                print("❌ 404 - 端点不存在")
            elif response.status_code == 401:
                print("❌ 401 - 认证失败")
            elif response.status_code == 403:
                print("❌ 403 - 访问被拒绝")
            else:
                print(f"响应: {response.text[:200]}")

        except Exception as e:
            print(f"错误: {e}")

    return False

if __name__ == "__main__":
    test_about_endpoint()

    print("\n" + "="*60)
    print("建议:")
    print("="*60)
    print("\n由于API端点信息不完整，建议采取以下步骤:")
    print("\n1. 联系PortConnect支持")
    print("   Email: info@portconnect.co.nz")
    print("   说明: 需要完整的API文档和端点列表")
    print("\n2. 请求Postman Collection")
    print("   这会包含所有可用端点的示例")
    print("\n3. 使用模拟数据继续开发")
    print("   我们已经创建了 portconnect_mock_api.py")
    print("   可以完整模拟PortConnect的功能")
    print("\n4. 访问开发者门户")
    print("   https://developer.portconnect.io/")
    print("   登录后查看完整API文档")
