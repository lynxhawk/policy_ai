"""
政策预审系统核心逻辑模块
基于严格规则审核，返回0或1的审核结果
支持复杂的逻辑运算（AND、OR、NOT）
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re

# 配置日志
logger = logging.getLogger(__name__)


class PolicyPreAuditEngine:
    """政策预审引擎核心类"""
    
    def __init__(self):
        """初始化预审引擎"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def safe_type_conversion(self, value: Any, target_type: str = "auto") -> Any:
        """
        安全的类型转换，失败时返回None
        
        Args:
            value: 需要转换的值
            target_type: 目标类型 ("int", "float", "str", "auto")
            
        Returns:
            转换后的值，失败时返回None
        """
        if value is None:
            return None
            
        try:
            if target_type == "int":
                return int(float(str(value)))
            elif target_type == "float":
                return float(str(value))
            elif target_type == "str":
                return str(value)
            else:  # auto
                # 尝试自动推断类型
                str_value = str(value).strip()
                
                # 尝试转换为数字
                if str_value.replace('.', '').replace('-', '').isdigit():
                    if '.' in str_value:
                        return float(str_value)
                    else:
                        return int(str_value)
                
                return str_value
                
        except (ValueError, TypeError, OverflowError) as e:
            self.logger.warning(f"类型转换失败: {value} -> {target_type}, 错误: {e}")
            return None
    
    def extract_numeric_value(self, value: Any) -> Optional[float]:
        """
        从值中提取数字，支持带单位的字符串如"2年"、"25岁"等
        
        Args:
            value: 输入值
            
        Returns:
            提取的数字，失败时返回None
        """
        if value is None:
            return None
            
        try:
            # 如果已经是数字类型
            if isinstance(value, (int, float)):
                return float(value)
                
            # 字符串处理
            str_value = str(value).strip()
            
            # 提取数字部分
            numbers = re.findall(r'-?\d+\.?\d*', str_value)
            
            if numbers:
                return float(numbers[0])
            
            return None
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"数字提取失败: {value}, 错误: {e}")
            return None
    
    def check_condition(self, user_value: Any, operator: str, condition_value: Any) -> bool:
        """
        检查单个条件是否匹配，增强类型安全性
        
        Args:
            user_value: 用户数据值
            operator: 操作符
            condition_value: 条件值
            
        Returns:
            是否匹配，类型不匹配时返回False
        """
        # 如果用户值为None或空，直接返回False
        if user_value is None or user_value == "":
            self.logger.debug(f"用户值为空: {user_value}")
            return False
            
        try:
            # between 操作符处理
            if operator == 'between':
                if isinstance(condition_value, list) and len(condition_value) == 2:
                    user_val = self.extract_numeric_value(user_value)
                    min_val = self.extract_numeric_value(condition_value[0])
                    max_val = self.extract_numeric_value(condition_value[1])
                    
                    if user_val is None or min_val is None or max_val is None:
                        self.logger.warning(f"between操作符类型转换失败: user={user_value}, range={condition_value}")
                        return False
                        
                    return min_val <= user_val <= max_val
                else:
                    self.logger.warning(f"between操作符条件值格式错误: {condition_value}")
                    return False
                    
            # 数字比较操作符
            elif operator in ['>', '<', '>=', '<=']:
                user_val = self.extract_numeric_value(user_value)
                condition_val = self.extract_numeric_value(condition_value)
                
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
                user_str = self.safe_type_conversion(user_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    self.logger.warning(f"字符串比较转换失败: user={user_value}, condition={condition_value}")
                    return False
                    
                return user_str == condition_str
                
            elif operator == '!=':
                # 安全的字符串转换
                user_str = self.safe_type_conversion(user_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    self.logger.warning(f"字符串比较转换失败: user={user_value}, condition={condition_value}")
                    return False
                    
                return user_str != condition_str
                
            # in 操作符（包含）
            elif operator == 'in':
                user_str = self.safe_type_conversion(user_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    return False
                    
                return user_str in condition_str
                
            # contains 操作符（包含）
            elif operator == 'contains':
                user_str = self.safe_type_conversion(user_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
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
    
    def pre_audit_policy(self, user_data: Dict, policy_data: Dict) -> int:
        """
        对用户进行政策预审，严格按照规则逻辑审核
        
        Args:
            user_data: 用户数据字典
            policy_data: 政策数据字典
            
        Returns:
            审核结果: 1-通过, 0-不通过
        """
        try:
            user_id = user_data.get("用户ID", "Unknown")
            policy_id = policy_data.get("政策编号", "Unknown")
            
            self.logger.info(f"开始预审: 用户={user_id}, 政策={policy_id}")
            
            # 获取条件规则
            condition_root = policy_data.get("条件", {})
            
            if not condition_root:
                self.logger.warning(f"政策 {policy_id} 没有条件规则，默认审核通过")
                return 1
            
            # 评估规则
            result = self.evaluate_rule_node(condition_root, user_data)
            audit_result = 1 if result else 0
            
            self.logger.info(f"预审结果: 用户={user_id}, 政策={policy_id}, 结果={audit_result}")
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"预审异常: 用户={user_data.get('用户ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0  # 出错时默认不通过
    
    def batch_pre_audit(self, user_data: Dict, policies_data: List[Dict]) -> List[int]:
        """
        批量预审用户与多个政策
        
        Args:
            user_data: 用户数据字典
            policies_data: 政策数据列表
            
        Returns:
            审核结果列表 (每个元素为0或1)
        """
        results = []
        user_id = user_data.get("用户ID", "Unknown")
        
        self.logger.info(f"开始批量预审: 用户={user_id}, 政策数量={len(policies_data)}")
        
        for i, policy_data in enumerate(policies_data):
            try:
                result = self.pre_audit_policy(user_data, policy_data)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"预审第 {i+1} 个政策失败: {e}")
                results.append(0)  # 出错时默认不通过
        
        passed_count = sum(results)
        self.logger.info(f"批量预审完成: 用户={user_id}, 通过={passed_count}/{len(policies_data)}")
        
        return results
    
    def multi_user_batch_pre_audit(self, users_data: List[Dict], policies_data: List[Dict]) -> List[List[int]]:
        """
        多用户批量预审
        
        Args:
            users_data: 用户数据列表
            policies_data: 政策数据列表
            
        Returns:
            二维结果列表: [用户][政策] = 0或1
        """
        all_results = []
        
        self.logger.info(f"开始多用户批量预审: 用户数量={len(users_data)}, 政策数量={len(policies_data)}")
        
        for user_idx, user_data in enumerate(users_data):
            try:
                user_results = self.batch_pre_audit(user_data, policies_data)
                all_results.append(user_results)
                        
            except Exception as e:
                self.logger.error(f"处理第 {user_idx+1} 个用户失败: {e}")
                # 为该用户的所有政策添加0（不通过）
                all_results.append([0] * len(policies_data))
        
        total_audits = len(users_data) * len(policies_data)
        total_passed = sum(sum(user_results) for user_results in all_results)
        
        self.logger.info(f"多用户批量预审完成: 总审核={total_audits}, 总通过={total_passed}")
        
        return all_results
    
    def get_audit_summary(self, users_data: List[Dict], policies_data: List[Dict], 
                         audit_results: List[List[int]]) -> Dict[str, Any]:
        """
        生成预审统计摘要
        
        Args:
            users_data: 用户数据列表
            policies_data: 政策数据列表
            audit_results: 预审结果二维列表
            
        Returns:
            统计摘要字典
        """
        try:
            summary = {
                "总用户数": len(users_data),
                "总政策数": len(policies_data),
                "总审核数": len(users_data) * len(policies_data),
                "总通过数": sum(sum(user_results) for user_results in audit_results),
                "总通过率": 0.0,
                "用户通过统计": [],
                "政策通过统计": []
            }
            
            # 计算总通过率
            if summary["总审核数"] > 0:
                summary["总通过率"] = round(summary["总通过数"] / summary["总审核数"], 3)
            
            # 统计每个用户的通过情况
            for i, user_data in enumerate(users_data):
                user_id = user_data.get("用户ID", f"User_{i}")
                user_passed = sum(audit_results[i]) if i < len(audit_results) else 0
                user_pass_rate = round(user_passed / len(policies_data), 3) if len(policies_data) > 0 else 0.0
                
                summary["用户通过统计"].append({
                    "用户ID": user_id,
                    "通过数": user_passed,
                    "通过率": user_pass_rate
                })
            
            # 统计每个政策的通过情况
            for j, policy_data in enumerate(policies_data):
                policy_id = policy_data.get("政策编号", f"Policy_{j}")
                policy_passed = sum(audit_results[i][j] for i in range(len(audit_results)) if j < len(audit_results[i]))
                policy_pass_rate = round(policy_passed / len(users_data), 3) if len(users_data) > 0 else 0.0
                
                summary["政策通过统计"].append({
                    "政策编号": policy_id,
                    "政策名称": policy_data.get("政策名称", ""),
                    "通过数": policy_passed,
                    "通过率": policy_pass_rate
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成审核摘要异常: {e}")
            return {"错误": str(e)}