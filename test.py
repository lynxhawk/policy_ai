from fastapi_policy import UserData, PolicyData
import json

def test_pydantic_conversion():
    """测试Pydantic模型转换对数据的影响"""
    
    # 原始JSON数据
    json_data = {
        "user": {
            "用户ID": "U0004",
            "毕业时间": 2,          # JSON中的数字
            "就业类型": "灵活就业",
            "养老保险": "否"
        },
        "policies": [
            {
                "政策编号": "POL0001",
                "标题": "测试政策",
                "条件": {
                    "逻辑": "AND",
                    "规则": [
                        {"字段": "毕业时间", "操作符": "<=", "值": "2"}
                    ]
                }
            }
        ]
    }
    
    print("🔍 Pydantic转换测试")
    print("-" * 40)
    
    # 模拟FastAPI的转换过程
    user_model = UserData(**json_data["user"])
    policy_model = PolicyData(**json_data["policies"][0])
    
    # 转换为字典
    user_dict = user_model.model_dump(exclude_none=False)
    policy_dict = policy_model.model_dump()
    
    print("📥 转换前:")
    print(f"  毕业时间: {json_data['user']['毕业时间']} (类型: {type(json_data['user']['毕业时间'])})")
    
    print("📤 转换后:")
    print(f"  毕业时间: {user_dict['毕业时间']} (类型: {type(user_dict['毕业时间'])})")
    
    print("\n🔍 政策条件值:")
    rules = policy_dict['条件']['规则']
    for rule in rules:
        if rule['字段'] == '毕业时间':
            print(f"  政策值: {rule['值']} (类型: {type(rule['值'])})")

if __name__ == "__main__":
    test_pydantic_conversion()