"""
政策用户匹配系统核心逻辑模块
包含用户数据与政策条件的匹配计算功能
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re

# 配置日志
logger = logging.getLogger(__name__)


class PolicyUserMatcher:
    """政策用户匹配核心类"""
    
    def __init__(self):
        """初始化匹配器"""
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
            
            else:
                self.logger.warning(f"不支持的操作符: {operator}")
                return False
                
        except Exception as e:
            self.logger.error(f"条件检查异常: user={user_value}, operator={operator}, condition={condition_value}, 错误: {e}")
            return False
    
    def extract_all_conditions(self, condition_node: Dict) -> List[Dict]:
        """递归提取所有条件规则，忽略逻辑关系"""
        conditions = []
        
        try:
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
                    
        except Exception as e:
            self.logger.error(f"提取条件规则异常: {condition_node}, 错误: {e}")
        
        return conditions
    
    def calculate_match_score(self, user_data: Dict, policy_data: Dict) -> float:
        """
        计算用户与政策的匹配分数，返回0-1之间的匹配率
        增强类型安全性，类型不匹配时返回0
        
        Args:
            user_data: 用户数据字典
            policy_data: 政策数据字典
            
        Returns:
            匹配分数 (0.0-1.0)，出错时返回0.0
        """
        try:
            matched_conditions = 0
            total_conditions = 0
            
            # 处理嵌套条件结构
            condition_root = policy_data.get("条件", {})
            
            # 提取所有条件规则（忽略逻辑关系）
            all_conditions = self.extract_all_conditions(condition_root)
            #print(all_conditions)
            total_conditions = len(all_conditions)
            
            if total_conditions == 0:
                self.logger.warning(f"政策 {policy_data.get('政策编号', 'Unknown')} 没有条件规则")
                return 0.0
            
            
            for condition in all_conditions:
                try:
                    field = condition.get("字段")
                    operator = condition.get("操作符")
                    value = condition.get("值")
                    
                    if not field or not operator:
                        self.logger.warning(f"条件缺少必要字段: {condition}")
                        continue
                    
                    if field in user_data:
                        user_value = user_data[field]
                        
                        if self.check_condition(user_value, operator, value):
                            matched_conditions += 1
                    else:
                        self.logger.debug(f"用户数据中缺少字段: {field}")
                        
                except Exception as e:
                    self.logger.error(f"处理单个条件异常: {condition}, 错误: {e}")
                    continue
            
            # 返回匹配率（0-1之间的浮点数）
            score = matched_conditions / total_conditions
            # 判断是否能整除
            if matched_conditions % total_conditions == 0:
                return float(matched_conditions // total_conditions)
            else:
                return round(matched_conditions / total_conditions, 2)
            
        except Exception as e:
            self.logger.error(f"计算匹配分数异常: 用户={user_data.get('用户ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0.0
    
    def batch_calculate_match_scores(self, user_data: Dict, policies_data: List[Dict]) -> List[float]:
        """
        批量计算用户与多个政策的匹配分数
        
        Args:
            user_data: 用户数据字典
            policies_data: 政策数据列表
            
        Returns:
            匹配分数列表
        """
        scores = []
        user_id = user_data.get("用户ID", "Unknown")
        
        self.logger.info(f"开始为用户 {user_id} 计算 {len(policies_data)} 个政策的匹配分数")
        
        for i, policy_data in enumerate(policies_data):
            try:
                score = self.calculate_match_score(user_data, policy_data)
                scores.append(score)
                
                self.logger.debug(f"政策 {policy_data.get('政策编号', f'Policy_{i}')} 匹配分数: {score}")
                
            except Exception as e:
                self.logger.error(f"计算第 {i+1} 个政策匹配分数失败: {e}")
                scores.append(0.0)  # 出错时默认返回0分
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        self.logger.info(f"用户 {user_id} 匹配计算完成，平均分数: {avg_score:.2f}")
        
        return scores
    
    def multi_user_batch_calculate(self, users_data: List[Dict], policies_data: List[Dict]) -> List[float]:
        """
        多用户批量匹配计算
        
        Args:
            users_data: 用户数据列表
            policies_data: 政策数据列表
            
        Returns:
            所有用户所有政策的匹配分数列表（展平后）
        """
        all_scores = []
        
        self.logger.info(f"开始批量推荐：{len(users_data)} 个用户，{len(policies_data)} 个政策")
        
        for user_idx, user_data in enumerate(users_data):
            try:
                user_id = user_data.get("用户ID", f"User_{user_idx}")
                
                # 计算该用户与所有政策的匹配分数
                user_scores = self.batch_calculate_match_scores(user_data, policies_data)
                all_scores.extend(user_scores)
                        
            except Exception as e:
                self.logger.error(f"处理第 {user_idx} 个用户失败: {e}")
                # 为该用户的所有政策添加0分
                all_scores.extend([0.0] * len(policies_data))
        
        self.logger.info(f"批量推荐完成，生成 {len(all_scores)} 个分数")
        
        return all_scores


class PolicyRecommendationEngine:
    """政策推荐引擎（兼容性包装器）"""
    
    def __init__(self):
        """初始化推荐引擎"""
        self.matcher = PolicyUserMatcher()
        
    @staticmethod
    def safe_type_conversion(value: Any, target_type: str = "auto") -> Any:
        """静态方法包装器，保持向后兼容"""
        matcher = PolicyUserMatcher()
        return matcher.safe_type_conversion(value, target_type)
    
    @staticmethod
    def extract_numeric_value(value: Any) -> Optional[float]:
        """静态方法包装器，保持向后兼容"""
        matcher = PolicyUserMatcher()
        return matcher.extract_numeric_value(value)
    
    @staticmethod
    def check_condition(user_value: Any, operator: str, condition_value: Any) -> bool:
        """静态方法包装器，保持向后兼容"""
        matcher = PolicyUserMatcher()
        return matcher.check_condition(user_value, operator, condition_value)
    
    @staticmethod
    def extract_all_conditions(condition_node: Dict) -> List[Dict]:
        """静态方法包装器，保持向后兼容"""
        matcher = PolicyUserMatcher()
        return matcher.extract_all_conditions(condition_node)
    
    @staticmethod
    def calculate_match_score(user_data: Dict, policy_data: Dict) -> float:
        """静态方法包装器，保持向后兼容"""
        matcher = PolicyUserMatcher()
        return matcher.calculate_match_score(user_data, policy_data)


# 为了保持原代码的兼容性，提供RecommendationEngine别名
RecommendationEngine = PolicyRecommendationEngine