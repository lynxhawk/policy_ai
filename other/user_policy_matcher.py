import os
import json
from typing import Dict, List, Tuple, Any

class PolicyRecommendationSystem:
    def __init__(self, policy_dir: str = "policy_new", user_dir: str = "user_dataset"):
        """
        初始化政策推荐系统
        
        Args:
            policy_dir: 政策文件夹路径
            user_dir: 用户数据文件夹路径
        """
        self.policy_dir = policy_dir
        self.user_dir = user_dir
        self.policies = {}
        self.users = {}
        
    def load_policies(self) -> Dict[str, Dict]:
        """加载所有政策数据"""
        self.policies = {}
        
        if not os.path.exists(self.policy_dir):
            print(f"错误: 政策目录 '{self.policy_dir}' 不存在")
            return self.policies
            
        for filename in os.listdir(self.policy_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.policy_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        policy_data = json.load(f)
                        policy_id = policy_data.get("政策编号", filename.replace('.json', ''))
                        self.policies[policy_id] = policy_data
                except Exception as e:
                    print(f"加载政策文件 {filename} 出错: {e}")
                    
        print(f"成功加载 {len(self.policies)} 个政策")
        return self.policies
    
    def load_users(self) -> Dict[str, Dict]:
        """加载所有用户数据"""
        self.users = {}
        
        if not os.path.exists(self.user_dir):
            print(f"错误: 用户目录 '{self.user_dir}' 不存在")
            return self.users
            
        for filename in os.listdir(self.user_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.user_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        user_data = json.load(f)
                        user_id = user_data.get("用户ID", filename.replace('.json', ''))
                        self.users[user_id] = user_data
                except Exception as e:
                    print(f"加载用户文件 {filename} 出错: {e}")
                    
        print(f"成功加载 {len(self.users)} 个用户")
        return self.users
    
    def check_condition(self, user_value: Any, operator: str, condition_value: Any) -> bool:
        """
        检查单个条件是否匹配
        
        Args:
            user_value: 用户字段值
            operator: 操作符 (=, >, <, >=, <=, !=, between)
            condition_value: 政策条件值
            
        Returns:
            bool: 是否匹配
        """
        if user_value is None:
            return False
            
        try:
            # between 操作符处理
            if operator == 'between':
                if isinstance(condition_value, list) and len(condition_value) == 2:
                    user_val = float(user_value)
                    min_val = float(condition_value[0])
                    max_val = float(condition_value[1])
                    return min_val <= user_val <= max_val
                return False
                
            # 如果是数字比较
            elif operator in ['>', '<', '>=', '<=']:
                user_val = float(user_value)
                # 处理可能包含单位的字符串，如 "2年"
                condition_str = str(condition_value)
                condition_val = float(''.join(filter(str.isdigit, condition_str))) if condition_str else 0
                
                if operator == '>':
                    return user_val > condition_val
                elif operator == '<':
                    return user_val < condition_val
                elif operator == '>=':
                    return user_val >= condition_val
                elif operator == '<=':
                    return user_val <= condition_val
                    
            # 字符串比较
            elif operator == '=':
                return str(user_value) == str(condition_value)
            elif operator == '!=':
                return str(user_value) != str(condition_value)
                
        except (ValueError, TypeError):
            # 如果转换失败，按字符串处理
            if operator == '=':
                return str(user_value) == str(condition_value)
            elif operator == '!=':
                return str(user_value) != str(condition_value)
                
        return False
    
    def extract_all_conditions(self, condition_node: Dict) -> List[Dict]:
        """
        递归提取所有条件规则，忽略逻辑关系
        
        Args:
            condition_node: 条件节点（可能包含嵌套结构）
            
        Returns:
            List[Dict]: 所有条件规则的扁平列表
        """
        conditions = []
        
        # 如果有 "规则" 字段，说明是容器节点
        if "规则" in condition_node:
            rules = condition_node["规则"]
            if isinstance(rules, list):
                for rule in rules:
                    # 递归处理每个规则
                    conditions.extend(self.extract_all_conditions(rule))
        else:
            # 如果包含字段、操作符、值，说明是叶子节点（实际条件）
            if all(key in condition_node for key in ["字段", "操作符", "值"]):
                conditions.append(condition_node)
        
        return conditions
    
    def calculate_match_score(self, user_data: Dict, policy_data: Dict) -> Tuple[int, List[str]]:
        """
        计算用户与政策的匹配分数
        
        Args:
            user_data: 用户数据
            policy_data: 政策数据
            
        Returns:
            Tuple[int, List[str]]: (匹配分数, 匹配的条件描述列表)
        """
        score = 0
        matched_conditions = []
        
        # 处理新的嵌套条件结构
        condition_root = policy_data.get("条件", {})
        
        # 提取所有条件规则（忽略逻辑关系）
        all_conditions = self.extract_all_conditions(condition_root)
        
        for condition in all_conditions:
            field = condition.get("字段")
            operator = condition.get("操作符")
            value = condition.get("值")
            description = condition.get("描述", f"{field} {operator} {value}")
            
            if field in user_data:
                user_value = user_data[field]
                
                if self.check_condition(user_value, operator, value):
                    score += 1
                    matched_conditions.append(description)
                    
        return score, matched_conditions
    
    def recommend_policies_for_user(self, user_id: str) -> List[Dict]:
        """
        为指定用户推荐政策
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 推荐政策列表，按分数降序，政策编号升序排列
        """
        if user_id not in self.users:
            print(f"用户 {user_id} 不存在")
            return []
            
        user_data = self.users[user_id]
        recommendations = []
        
        for policy_id, policy_data in self.policies.items():
            score, matched_conditions = self.calculate_match_score(user_data, policy_data)
            
            recommendations.append({
                "政策编号": policy_id,
                "政策标题": policy_data.get("标题", ""),
                "政策类型": policy_data.get("类型", ""),
                "匹配分数": score,
                "总条件数": len(policy_data.get("条件", [])),
                "匹配条件": matched_conditions,
                "匹配率": f"{score}/{len(policy_data.get('条件', []))}"
            })
        
        # 排序：先按分数降序，再按政策编号升序
        recommendations.sort(key=lambda x: (-x["匹配分数"], x["政策编号"]))
        
        return recommendations
    
    def recommend_policies_for_all_users(self) -> Dict[str, List[Dict]]:
        """
        为所有用户推荐政策
        
        Returns:
            Dict[str, List[Dict]]: 所有用户的推荐结果
        """
        all_recommendations = {}
        
        for user_id in self.users:
            all_recommendations[user_id] = self.recommend_policies_for_user(user_id)
            
        return all_recommendations
    
    def print_recommendations(self, user_id: str, limit: int = 10):
        """
        打印用户的政策推荐结果
        
        Args:
            user_id: 用户ID
            limit: 显示的推荐数量限制
        """
        recommendations = self.recommend_policies_for_user(user_id)
        
        if not recommendations:
            print(f"用户 {user_id} 没有找到匹配的政策")
            return
            
        print(f"\n用户 {user_id} 的政策推荐结果:")
        print("=" * 80)
        
        for i, rec in enumerate(recommendations[:limit], 1):
            print(f"{i}. 政策编号: {rec['政策编号']}")
            print(f"   政策标题: {rec['政策标题']}")
            print(f"   政策类型: {rec['政策类型']}")
            print(f"   匹配分数: {rec['匹配分数']} 分")
            print(f"   匹配率: {rec['匹配率']}")
            
            if rec['匹配条件']:
                print(f"   匹配条件: {', '.join(rec['匹配条件'])}")
            else:
                print("   匹配条件: 无")
            print("-" * 60)

def main():
    """主函数 - 生成所有用户的政策推荐结果并保存到文件"""
    # 创建推荐系统实例
    recommender = PolicyRecommendationSystem()
    
    # 加载数据
    print("正在加载政策和用户数据...")
    recommender.load_policies()
    recommender.load_users()
    
    if not recommender.policies:
        print("未找到政策数据，请检查 policy_new 目录")
        return []
        
    if not recommender.users:
        print("未找到用户数据，请检查 user_dataset 目录")
        return []
    
    # 创建结果输出目录
    output_dir = "recommendation_results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 为所有用户生成推荐并保存结果
    print("\n开始为所有用户生成推荐结果...")
    all_recommendations = recommender.recommend_policies_for_all_users()
    
    # 用于存储最终返回的政策ID数组
    all_policy_ids = []
    
    for user_id, recommendations in all_recommendations.items():
        # 创建每个用户的结果文件
        result_file = os.path.join(output_dir, f"{user_id}_recommendations.json")
        
        # 准备保存的数据
        user_result = {
            "用户ID": user_id,
            "推荐时间": "2025-07-31",  # 可以使用 datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            "推荐政策数量": len(recommendations),
            "推荐列表": recommendations,
            "推荐政策ID顺序": [rec["政策编号"] for rec in recommendations]
        }
        
        # 保存到JSON文件
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(user_result, f, ensure_ascii=False, indent=2)
            print(f"✓ 已保存用户 {user_id} 的推荐结果到 {result_file}")
        except Exception as e:
            print(f"✗ 保存用户 {user_id} 结果时出错: {e}")
        
        # 收集该用户的政策ID
        user_policy_ids = [rec["政策编号"] for rec in recommendations]
        all_policy_ids.extend(user_policy_ids)
    
    # 生成汇总报告
    summary_file = os.path.join(output_dir, "summary_report.json")
    summary_data = {
        "生成时间": "2025-07-31",
        "总用户数": len(all_recommendations),
        "总政策数": len(recommender.policies),
        "用户推荐统计": {}
    }
    
    # 统计每个用户的推荐情况
    for user_id, recommendations in all_recommendations.items():
        matches_count = sum(1 for rec in recommendations if rec['匹配分数'] > 0)
        best_score = recommendations[0]['匹配分数'] if recommendations else 0
        
        summary_data["用户推荐统计"][user_id] = {
            "推荐政策总数": len(recommendations),
            "有匹配分数的政策数": matches_count,
            "最高匹配分数": best_score,
            "推荐政策ID列表": [rec["政策编号"] for rec in recommendations]
        }
    
    # 保存汇总报告
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存汇总报告到 {summary_file}")
    except Exception as e:
        print(f"✗ 保存汇总报告时出错: {e}")
    
    # 去重并按政策编号排序的所有政策ID
    unique_policy_ids = sorted(list(set(all_policy_ids)))
    
    print(f"\n处理完成!")
    print(f"- 处理用户数: {len(all_recommendations)}")
    print(f"- 输出目录: {output_dir}")
    print(f"- 涉及政策数: {len(unique_policy_ids)}")
    print(f"- 推荐政策ID列表: {unique_policy_ids}")
    
    # 返回按推荐顺序的政策ID数组（去重后的）
    return unique_policy_ids

if __name__ == "__main__":
    main()