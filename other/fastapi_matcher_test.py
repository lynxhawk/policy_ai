import requests
import json
import time

# API服务地址 - 使用实际工作的端口8081
BASE_URL = "http://127.0.0.1:8081"

def check_service_status():
    """检查服务是否可用"""
    print("🔍 检查服务状态...")
    print(f"   目标地址: {BASE_URL}")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ 服务运行正常: {response.json()}")
            return True
        else:
            print(f"⚠️ 服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 无法连接到服务 {BASE_URL}")
        print(f"   详细错误: {e}")
        print("请确保FastAPI服务已启动，并检查端口号是否正确")
        return False
    except Exception as e:
        print(f"❌ 连接出错: {e}")
        return False

def test_single_recommendation():
    """测试单个推荐接口"""
    print("\n🧪 测试单个政策推荐...")
    
    # 示例数据
    request_data = {
        "user": {
            "用户ID": "U0001",
            "最高学历": "本科",
            "毕业时间": 5,
            "籍贯": "浙江省平湖市",
            "专业": "计算机科学与技术",
            "技能等级": "高级专业技术职务",
            "征地人员": "否",
            "缴纳社保": "是",
            "养老保险": "是",
            "困难人员": "否",
            "就业类型": "受雇就业",
            "年龄": 25
        },
        "policy": {
            "政策编号": "POL0001",
            "标题": "高校毕业生社保补贴（灵活就业）",
            "条件": {
                "逻辑": "AND",
                "规则": [
                    {
                        "字段": "毕业时间",
                        "操作符": "<=",
                        "值": "2",
                        "描述": "2年以内"
                    },
                    {
                        "字段": "就业类型",
                        "操作符": "=",
                        "值": "灵活就业",
                        "描述": "灵活就业"
                    },
                    {
                        "字段": "养老保险",
                        "操作符": "=",
                        "值": "是",
                        "描述": "养老保险"
                    }
                ]
            },
            "类型": "个人"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommend-single",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 推荐成功:")
            print(f"   政策: {result['政策标题']}")
            print(f"   匹配分数: {result['匹配分数']}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

def test_multiple_policies_recommendation():
    """测试多政策推荐接口"""
    print("\n🧪 测试多政策推荐...")
    
    # 构建请求数据
    request_data = {
        "user": {
            "用户ID": "U0001",
            "最高学历": "本科",
            "毕业时间": 1,
            "就业类型": "未就业",
            "养老保险": "是",
            "年龄": 22
        },
        "policies": [
            {
                "政策编号": "POL0001",
                "标题": "高校毕业生社保补贴（灵活就业）",
                "条件": {
                    "逻辑": "AND",
                    "规则": [
                        {"字段": "毕业时间", "操作符": "<=", "值": "2", "描述": "2年以内"},
                        {"字段": "就业类型", "操作符": "=", "值": "灵活就业", "描述": "灵活就业"},
                        {"字段": "养老保险", "操作符": "=", "值": "是", "描述": "养老保险"}
                    ]
                },
                "类型": "个人"
            },
            {
                "政策编号": "POL0008",
                "标题": "就业见习补贴",
                "条件": {
                    "逻辑": "OR",
                    "规则": [
                        {
                            "逻辑": "AND",
                            "规则": [
                                {"字段": "毕业时间", "操作符": "<=", "值": "2年", "描述": "毕业2年以内"},
                                {"字段": "就业类型", "操作符": "=", "值": "未就业", "描述": "尚未就业"}
                            ]
                        },
                        {
                            "逻辑": "AND", 
                            "规则": [
                                {"字段": "年龄", "操作符": "between", "值": [16, 24], "描述": "16-24岁"},
                                {"字段": "就业类型", "操作符": "=", "值": "未就业", "描述": "失业青年"}
                            ]
                        }
                    ]
                },
                "类型": "个人"
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommend",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 推荐成功:")
            print(f"   用户ID: {result['user_id']}")
            print(f"   总政策数: {result['total_policies']}")
            print(f"   推荐结果:")
            
            for policy_title, score in result['recommendations'].items():
                print(f"     - {policy_title}: {score} 分")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

def test_health_check():
    """测试健康检查接口"""
    print("\n🩺 测试健康检查...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 服务健康: {result['status']}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 健康检查超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务: {e}")
        return False

def test_batch_recommendation():
    """测试批量推荐接口"""
    print("\n🧪 测试批量用户推荐...")
    
    # 多个用户数据
    users_data = [
        {
            "用户ID": "U0001",
            "毕业时间": 1,
            "就业类型": "未就业",
            "养老保险": "是",
            "年龄": 22
        },
        {
            "用户ID": "U0002", 
            "毕业时间": 3,
            "就业类型": "灵活就业",
            "养老保险": "是",
            "年龄": 26
        }
    ]
    
    # 政策数据
    policies_data = [
        {
            "政策编号": "POL0001",
            "标题": "高校毕业生社保补贴（灵活就业）",
            "条件": {
                "逻辑": "AND",
                "规则": [
                    {"字段": "毕业时间", "操作符": "<=", "值": "2", "描述": "2年以内"},
                    {"字段": "就业类型", "操作符": "=", "值": "灵活就业", "描述": "灵活就业"},
                    {"字段": "养老保险", "操作符": "=", "值": "是", "描述": "养老保险"}
                ]
            },
            "类型": "个人"
        }
    ]
    
    try:
        response = requests.post(
            f"{BASE_URL}/batch-recommend",
            json={"users": users_data, "policies": policies_data},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 批量推荐成功:")
            print(f"   处理用户数: {result['处理用户数']}")
            print(f"   政策数: {result['政策数']}")
            print(f"   推荐结果:")
            
            for user_id, recommendations in result['批量推荐结果'].items():
                print(f"     {user_id}:")
                for policy_title, score in recommendations.items():
                    print(f"       - {policy_title}: {score} 分")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

if __name__ == "__main__":
    print("🚀 政策推荐API测试客户端")
    print("=" * 50)
    
    # 首先检查服务状态
    if not check_service_status():
        print("\n💡 解决建议:")
        print("1. 确认FastAPI服务已启动")
        print("2. 检查端口号是否正确（当前设置: 8001）")
        print("3. 如果使用其他端口，请修改 BASE_URL")
        print("4. 确认防火墙没有阻止连接")
        exit(1)
    
    # 等待一下确保服务完全启动
    print("\n⏳ 等待服务完全启动...")
    time.sleep(2)
    
    # 测试健康检查
    if not test_health_check():
        print("❌ 健康检查失败，停止测试")
        exit(1)
    
    # 测试推荐功能
    test_single_recommendation()
    test_multiple_policies_recommendation()
    test_batch_recommendation()
    
    print(f"\n📚 更多API文档请访问: {BASE_URL}/docs")