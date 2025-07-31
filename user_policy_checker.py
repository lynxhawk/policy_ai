import os
import json
from typing import Dict, List, Any, Union

class PolicyPrecheckSystem:
    def __init__(self, policy_dir: str = "policy_new", user_dir: str = "user_dataset"):
        """
        初始化政策预审系统
        
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
    
    def check_single_condition(self, user_value: Any, operator: str, condition_value: Any) -> bool:
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
    
    def evaluate_condition_node(self, user_data: Dict, condition_node: Dict) -> bool:
        """
        递归评估条件节点，严格按照逻辑规则
        
        Args:
            user_data: 用户数据
            condition_node: 条件节点
            
        Returns:
            bool: 条件是否满足
        """
        # 如果是叶子节点（包含字段、操作符、值）
        if all(key in condition_node for key in ["字段", "操作符", "值"]):
            field = condition_node["字段"]
            operator = condition_node["操作符"]
            value = condition_node["值"]
            
            if field not in user_data:
                return False
                
            return self.check_single_condition(user_data[field], operator, value)
        
        # 如果是容器节点（包含逻辑和规则）
        elif "逻辑" in condition_node and "规则" in condition_node:
            logic = condition_node["逻辑"]
            rules = condition_node["规则"]
            
            if not isinstance(rules, list):
                return False
            
            if logic == "AND":
                # 所有子规则都必须满足
                return all(self.evaluate_condition_node(user_data, rule) for rule in rules)
            elif logic == "OR":
                # 至少一个子规则满足
                return any(self.evaluate_condition_node(user_data, rule) for rule in rules)
        
        # 如果结构不符合预期，返回False
        return False
    
    def check_user_policy_match(self, user_data: Dict, policy_data: Dict) -> bool:
        """
        检查用户是否符合政策条件
        
        Args:
            user_data: 用户数据
            policy_data: 政策数据
            
        Returns:
            bool: True(1) - 符合条件, False(0) - 不符合条件
        """
        condition_root = policy_data.get("条件", {})
        
        if not condition_root:
            # 如果没有条件，默认符合
            return True
            
        return self.evaluate_condition_node(user_data, condition_root)
    
    def precheck_all_users_policies(self) -> Dict[str, Dict[str, int]]:
        """
        为所有用户预审所有政策
        
        Returns:
            Dict[str, Dict[str, int]]: {用户ID: {政策ID: 0或1}}
        """
        results = {}
        
        for user_id, user_data in self.users.items():
            user_results = {}
            
            for policy_id, policy_data in self.policies.items():
                match_result = self.check_user_policy_match(user_data, policy_data)
                user_results[policy_id] = 1 if match_result else 0
                
            results[user_id] = user_results
            
        return results
    
    def generate_precheck_report(self, results: Dict[str, Dict[str, int]]) -> Dict:
        """
        生成预审统计报告
        
        Args:
            results: 预审结果
            
        Returns:
            Dict: 统计报告
        """
        total_users = len(results)
        total_policies = len(self.policies) if self.policies else 0
        
        # 统计每个政策的通过率
        policy_stats = {}
        for policy_id in self.policies:
            passed_users = sum(1 for user_results in results.values() 
                             if user_results.get(policy_id, 0) == 1)
            policy_stats[policy_id] = {
                "通过用户数": passed_users,
                "总用户数": total_users,
                "通过率": f"{passed_users/total_users*100:.1f}%" if total_users > 0 else "0%"
            }
        
        # 统计每个用户的通过政策数
        user_stats = {}
        for user_id, user_results in results.items():
            passed_policies = sum(user_results.values())
            user_stats[user_id] = {
                "通过政策数": passed_policies,
                "总政策数": total_policies,
                "通过率": f"{passed_policies/total_policies*100:.1f}%" if total_policies > 0 else "0%"
            }
        
        return {
            "统计时间": "2025-07-31",
            "总体统计": {
                "总用户数": total_users,
                "总政策数": total_policies,
                "总匹配数": sum(sum(user_results.values()) for user_results in results.values())
            },
            "政策统计": policy_stats,
            "用户统计": user_stats
        }

def main():
    """主函数 - 执行预审并保存结果"""
    # 创建预审系统实例
    precheck_system = PolicyPrecheckSystem()
    
    # 加载数据
    print("正在加载政策和用户数据...")
    precheck_system.load_policies()
    precheck_system.load_users()
    
    if not precheck_system.policies:
        print("未找到政策数据，请检查 policy_new 目录")
        return {}
        
    if not precheck_system.users:
        print("未找到用户数据，请检查 user_dataset 目录")
        return {}
    
    # 创建结果输出目录
    output_dir = "precheck_results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 执行预审
    print("\n开始执行政策预审...")
    results = precheck_system.precheck_all_users_policies()
    
    # 保存详细结果
    detailed_results_file = os.path.join(output_dir, "detailed_precheck_results.json")
    try:
        with open(detailed_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存详细预审结果到 {detailed_results_file}")
    except Exception as e:
        print(f"✗ 保存详细结果时出错: {e}")
    
    # 生成并保存统计报告
    report = precheck_system.generate_precheck_report(results)
    report_file = os.path.join(output_dir, "precheck_statistical_report.json")
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存统计报告到 {report_file}")
    except Exception as e:
        print(f"✗ 保存统计报告时出错: {e}")
    
    # 生成矩阵格式结果（用户-政策矩阵）
    matrix_file = os.path.join(output_dir, "user_policy_matrix.json")
    matrix_data = {
        "说明": "用户-政策匹配矩阵，1表示符合条件，0表示不符合条件",
        "用户列表": list(results.keys()),
        "政策列表": list(precheck_system.policies.keys()),
        "匹配矩阵": results
    }
    
    try:
        with open(matrix_file, 'w', encoding='utf-8') as f:
            json.dump(matrix_data, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存用户-政策矩阵到 {matrix_file}")
    except Exception as e:
        print(f"✗ 保存矩阵文件时出错: {e}")
    
    # 打印简要统计
    total_matches = sum(sum(user_results.values()) for user_results in results.values())
    total_combinations = len(results) * len(precheck_system.policies)
    
    print(f"\n预审完成!")
    print(f"- 处理用户数: {len(results)}")
    print(f"- 处理政策数: {len(precheck_system.policies)}")
    print(f"- 总匹配组合: {total_matches}/{total_combinations}")
    print(f"- 整体通过率: {total_matches/total_combinations*100:.1f}%" if total_combinations > 0 else "0%")
    print(f"- 输出目录: {output_dir}")
    
    # 显示每个用户的匹配情况
    print(f"\n各用户匹配情况:")
    for user_id, user_results in results.items():
        passed_count = sum(user_results.values())
        print(f"  {user_id}: {passed_count}/{len(precheck_system.policies)} 个政策通过")
    
    return results

if __name__ == "__main__":
    precheck_results = main()