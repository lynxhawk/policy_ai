"""
政策预审系统核心逻辑模块
基于严格规则审核，返回0或1的审核结果
支持复杂的逻辑运算（AND、OR、NOT）
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re
from data_processor import DataProcessor

# 配置日志
logger = logging.getLogger(__name__)


class PolicyPreAuditEngine:
    """政策预审引擎核心类"""
    
    def __init__(self):
        """初始化预审引擎"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_processor = DataProcessor()
        
    def check_condition(self, user_value: Any, operator: str, condition_value: Any) -> bool:
        """
        检查单个条件是否满足，增强类型安全性
        
        Args:
            user_value: 用户数据值
            operator: 操作符
            condition_value: 条件值
            
        Returns:
            是否满足条件，类型不匹配时返回False
        """
        # 如果用户值为None或空，直接返回False
        if user_value is None or user_value == "":
            self.logger.debug(f"用户值为空: {user_value}")
            return False
            
        try:
            # between 操作符处理
            if operator == 'between':
                if isinstance(condition_value, list) and len(condition_value) == 2:
                    user_val = self.data_processor.extract_numeric_value_simple(user_value)
                    min_val = self.data_processor.extract_numeric_value_simple(condition_value[0])
                    max_val = self.data_processor.extract_numeric_value_simple(condition_value[1])
                    
                    if user_val is None or min_val is None or max_val is None:
                        self.logger.warning(f"between操作符类型转换失败: user={user_value}, range={condition_value}")
                        return False
                        
                    return min_val <= user_val <= max_val
                else:
                    self.logger.warning(f"between操作符条件值格式错误: {condition_value}")
                    return False
                    
            # 数字比较操作符
            elif operator in ['>', '<', '>=', '<=']:
                user_val = self.data_processor.extract_numeric_value_simple(user_value)
                condition_val = self.data_processor.extract_numeric_value_simple(condition_value)
                
                if user_val is None or condition_val is None:
                    self.logger.warning(f"数字比较类型转换失败: user={user_value}, condition={condition_value}")
                    return False
                
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
                # 安全的字符串转换
                user_str = self.data_processor.safe_type_conversion(user_value, "str")
                condition_str = self.data_processor.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    self.logger.warning(f"字符串比较转换失败: user={user_value}, condition={condition_value}")
                    return False
                    
                return user_str == condition_str
                
            elif operator == '!=':
                # 安全的字符串转换
                user_str = self.data_processor.safe_type_conversion(user_value, "str")
                condition_str = self.data_processor.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    self.logger.warning(f"字符串比较转换失败: user={user_value}, condition={condition_value}")
                    return False
                    
                return user_str != condition_str
                
            # in 操作符（包含）
            elif operator == 'in':
                user_str = self.data_processor.safe_type_conversion(user_value, "str")
                condition_str = self.data_processor.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    return False
                    
                return user_str in condition_str
                
            # contains 操作符（包含）
            elif operator == 'contains':
                user_str = self.data_processor.safe_type_conversion(user_value, "str")
                condition_str = self.data_processor.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    return False
                    
                return condition_str in user_str
            
            else:
                self.logger.warning(f"不支持的操作符: {operator}")
                return False
                
        except Exception as e:
            self.logger.error(f"条件检查异常: user={user_value}, operator={operator}, condition={condition_value}, 错误: {e}")
            return False
    
    def evaluate_rule_node(self, rule_node: Dict, user_data: Dict) -> bool:
        """
        递归评估规则节点，支持复杂的逻辑运算
        
        Args:
            rule_node: 规则节点
            user_data: 用户数据
            
        Returns:
            规则评估结果 (True/False)
        """
        try:
            self.logger.debug(f"评估规则节点: {rule_node}")
            
            # 如果是叶子节点（包含字段、操作符、值），直接评估条件
            if all(key in rule_node for key in ["字段", "操作符", "值"]):
                field = rule_node["字段"]
                operator = rule_node["操作符"]
                value = rule_node["值"]
                
                if field not in user_data:
                    self.logger.debug(f"用户数据中缺少字段: {field}")
                    return False
                    
                user_value = user_data[field]
                result = self.check_condition(user_value, operator, value)
                
                self.logger.info(f"条件评估: {field}({user_value}) {operator} {value} = {result}")
                return result
            
            # 如果是容器节点，处理逻辑运算
            elif "规则" in rule_node:
                rules = rule_node["规则"]
                logic_operator = rule_node.get("逻辑", "and").lower()  # 默认为and，并转换为小写
                
                self.logger.info(f"逻辑运算节点: {logic_operator}, 规则数量: {len(rules) if isinstance(rules, list) else 0}")
                
                if not isinstance(rules, list) or len(rules) == 0:
                    self.logger.warning(f"规则列表为空或格式错误: {rules}")
                    return False
                
                # 递归评估所有子规则
                results = []
                for i, sub_rule in enumerate(rules):
                    sub_result = self.evaluate_rule_node(sub_rule, user_data)
                    results.append(sub_result)
                    self.logger.debug(f"子规则{i+1}结果: {sub_result}")
                    
                    # 短路评估优化
                    if logic_operator == "and" and not sub_result:
                        self.logger.debug(f"AND逻辑短路: 发现False，直接返回False")
                        return False
                    elif logic_operator == "or" and sub_result:
                        self.logger.debug(f"OR逻辑短路: 发现True，直接返回True")
                        return True
                
                # 根据逻辑操作符计算最终结果
                if logic_operator == "and":
                    final_result = all(results)
                elif logic_operator == "or":
                    final_result = any(results)
                elif logic_operator == "not":
                    # NOT逻辑：对第一个规则取反
                    final_result = not results[0] if results else False
                else:
                    self.logger.warning(f"不支持的逻辑操作符: {logic_operator}")
                    return False
                
                self.logger.info(f"逻辑运算 {logic_operator.upper()}: {results} = {final_result}")
                return final_result
            
            else:
                self.logger.warning(f"规则节点格式错误，既不是条件节点也不是逻辑节点: {rule_node}")
                return False
                
        except Exception as e:
            self.logger.error(f"评估规则节点异常: {rule_node}, 错误: {e}")
            return False
    
    def audit_policy(self, user_data: Dict, policy_data: Dict) -> int:
        """
        单个用户与单个政策预审
        
        Args:
            user_data: 用户数据字典
            policy_data: 政策数据字典
            
        Returns:
            预审结果: 1-通过, 0-不通过
        """
        try:
            # 使用数据处理器处理输入数据
            processed_user_data = self.data_processor.process_user_data(user_data)
            processed_policy_data = self.data_processor.process_policy_data(policy_data)
            
            # 验证输入数据
            if not self.data_processor.validate_match_input(processed_user_data, processed_policy_data):
                self.logger.warning("输入数据验证失败")
                return 0
            
            user_id = processed_user_data.get("用户ID", "Unknown")
            policy_id = processed_policy_data.get("政策编号", "Unknown")
            
            self.logger.info(f"开始预审: 用户={user_id}, 政策={policy_id}")
            
            # 获取条件规则
            condition_root = processed_policy_data.get("条件", {})
            
            if not condition_root:
                self.logger.warning(f"政策 {policy_id} 没有条件规则，默认审核通过")
                return 1
            
            # 评估规则
            result = self.evaluate_rule_node(condition_root, processed_user_data)
            audit_result = 1 if result else 0
            
            self.logger.info(f"预审结果: 用户={user_id}, 政策={policy_id}, 结果={audit_result}")
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"预审异常: 用户={user_data.get('用户ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0  # 出错时默认不通过
    
    def multi_user_audit_policy(self, users_data: List[Dict], policy_data: Dict) -> List[int]:
        """
        多个用户与单个政策预审
        
        Args:
            users_data: 用户数据列表
            policy_data: 政策数据字典
            
        Returns:
            预审结果列表 (每个元素为0或1)
        """
        results = []
        # 处理政策数据
        processed_policy_data = self.data_processor.process_policy_data(policy_data)
        policy_id = processed_policy_data.get("政策编号", "Unknown")
        
        self.logger.info(f"开始多用户预审: 用户数量={len(users_data)}, 政策={policy_id}")
        
        for i, user_data in enumerate(users_data):
            try:
                result = self.audit_policy(user_data, policy_data)
                results.append(result)
                
            except Exception as e:
                user_id = user_data.get("用户ID", f"User_{i}")
                self.logger.error(f"预审用户 {user_id} 失败: {e}")
                results.append(0)  # 出错时默认不通过
        
        passed_count = sum(results)
        self.logger.info(f"多用户预审完成: 政策={policy_id}, 审核通过={passed_count}/{len(users_data)}")
        
        return results
    
    def get_audit_summary(self, users_data: List[Dict], policy_data: Dict, 
                         audit_results: List[int]) -> Dict[str, Any]:
        """
        生成预审统计摘要
        
        Args:
            users_data: 用户数据列表
            policy_data: 政策数据字典
            audit_results: 预审结果列表
            
        Returns:
            统计摘要字典
        """
        try:
            # 处理政策数据
            processed_policy_data = self.data_processor.process_policy_data(policy_data)
            
            passed_count = sum(audit_results)
            total_users = len(users_data)
            pass_rate = round(passed_count / total_users, 3) if total_users > 0 else 0.0
            
            summary = {
                "政策编号": processed_policy_data.get("政策编号", "Unknown"),
                "政策名称": processed_policy_data.get("政策名称", ""),
                "总用户数": total_users,
                "审核通过数": passed_count,
                "通过率": pass_rate,
                "用户审核详情": []
            }
            
            # 统计每个用户的预审情况
            for i, user_data in enumerate(users_data):
                processed_user_data = self.data_processor.process_user_data(user_data)
                user_id = processed_user_data.get("用户ID", f"User_{i}")
                user_result = audit_results[i] if i < len(audit_results) else 0
                
                summary["用户审核详情"].append({
                    "用户ID": user_id,
                    "审核结果": user_result,
                    "审核状态": "通过" if user_result == 1 else "不通过"
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成预审摘要异常: {e}")
            return {"错误": str(e)}