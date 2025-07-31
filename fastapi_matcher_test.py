import requests
import json

# API服务地址
BASE_URL = "http://localhost:8000"

def test_single_recommendation():
    """测试单个推荐接口"""
    print("🧪 测试单个政策推荐...")
    
    # 示例用户数据
    user_data = {
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
    }
    
    # 示例政策数据
    policy_data = {
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
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommend-single",
            json={"user": user_data, "policy": policy_data}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 推荐成功:")
            print(f"   政策: {result['政策标题']}")
            print(f"   匹配分数: {result['匹配分数']}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

def test_multiple_policies_recommendation():
    """测试多政策推荐接口"""
    print("\n🧪 测试多政策推荐...")
    
    # 示例用户数据
    user_data = {
        "用户ID": "U0001",
        "最高学历": "本科",
        "毕业时间": 1,
        "就业类型": "未就业",
        "养老保险": "是",
        "年龄": 22
    }
    
    # 多个政策数据
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
    
    # 构建请求数据
    request_data = {
        "user": user_data,
        "policies": policies_data
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommend",
            json=request_data
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
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

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
            json={"users": users_data, "policies": policies_data}
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
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

def test_health_check():
    """测试健康检查接口"""
    print("\n🩺 测试健康检查...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 服务健康: {result['status']}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务: {e}")

if __name__ == "__main__":
    print("🚀 政策推荐API测试客户端")
    print("=" * 50)
    
    # 测试健康检查
    test_health_check()
    
    # 测试单个推荐
    test_single_recommendation()
    
    # 测试多政策推荐
    test_multiple_policies_recommendation()
    
    # 测试批量推荐
    test_batch_recommendation()
    
    print(f"\n📚 更多API文档请访问: {BASE_URL}/docs")