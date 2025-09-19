"""
政策预审系统核心逻辑模块
基于严格规则审核，返回0或1的审核结果以及不符合的条件详情
支持复杂的逻辑运算（AND、OR、NOT）
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re
from data_processor_user import DataProcessor

# 配置日志
logger = logging.getLogger(__name__)


class PolicyPreAuditEngine:
    """政策预审引擎核心类"""
    
    def __init__(self):
        """初始化预审引擎"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_processor = DataProcessor()
    
    def _collect_failed_conditions(self, rule_node: Dict, user_data: Dict, failed_conditions: List[str], condition_path: str = "") -> bool:
        """
        递归遍历规则树，收集所有不符合的条件字段名
        
        Args:
            rule_node: 规则节点
            user_data: 用户数据
            failed_conditions: 用于收集失败条件的列表
            condition_path: 当前条件路径（用于标识嵌套条件）
            
        Returns:
            当前节点的评估结果
        """
        try:
            if not isinstance(rule_node, dict):
                return True
            
            # 处理逻辑操作符
            if "AND" in rule_node or "逻辑" in rule_node and rule_node.get("逻辑") == "and":
                # 处理新旧格式的AND条件
                and_conditions = rule_node.get("AND") or rule_node.get("规则", [])
                if not isinstance(and_conditions, list):
                    return True
                
                all_results = []
                for i, condition in enumerate(and_conditions):
                    result = self._collect_failed_conditions(condition, user_data, failed_conditions, condition_path)
                    all_results.append(result)
                
                return all(all_results)
            
            elif "OR" in rule_node or "逻辑" in rule_node and rule_node.get("逻辑") == "or":
                # 处理新旧格式的OR条件
                or_conditions = rule_node.get("OR") or rule_node.get("规则", [])
                if not isinstance(or_conditions, list):
                    return True
                
                any_results = []
                temp_failed = []  # 临时存储OR条件中的失败项
                
                for i, condition in enumerate(or_conditions):
                    temp_failed_for_this_condition = []
                    result = self._collect_failed_conditions(condition, user_data, temp_failed_for_this_condition, condition_path)
                    any_results.append(result)
                    if not result:
                        temp_failed.extend(temp_failed_for_this_condition)
                
                # 如果OR条件全部失败，则添加失败条件
                if not any(any_results):
                    failed_conditions.extend(temp_failed)
                
                return any(any_results)
            
            elif "NOT" in rule_node:
                not_condition = rule_node["NOT"]
                temp_failed = []
                result = self._collect_failed_conditions(not_condition, user_data, temp_failed, condition_path)
                
                # NOT条件的逻辑：如果内部条件成功，则NOT失败
                if result:
                    # 对于NOT条件，我们添加被否定的字段名
                    field_name = self._extract_field_name(not_condition)
                    if field_name:
                        failed_conditions.append(f"{field_name}(NOT条件)")
                
                return not result
            
            # 处理具体的条件规则
            else:
                result = self.data_processor.evaluate_rule_node(rule_node, user_data)
                if not result:
                    # 只提取字段名
                    field_name = self._extract_field_name(rule_node)
                    if field_name and field_name not in failed_conditions:
                        failed_conditions.append(field_name)
                
                return result
        
        except Exception as e:
            self.logger.error(f"收集失败条件时出错: {e}")
            return False
    
    def _extract_field_name(self, rule_node: Dict) -> str:
        """
        从规则节点中提取字段名
        
        Args:
            rule_node: 规则节点
            
        Returns:
            字段名或空字符串
        """
        try:
            if not isinstance(rule_node, dict):
                return ""
            
            # 尝试从不同的字段名中提取
            field_name = (rule_node.get('字段') or 
                         rule_node.get('field') or 
                         rule_node.get('attribute') or 
                         rule_node.get('属性') or "")
            
            return str(field_name) if field_name else ""
                
        except Exception as e:
            self.logger.error(f"提取字段名时出错: {e}")
            return ""
    
    def audit_policy(self, user_data: Dict, policy_data: Dict) -> Dict:
        """
        单个用户与单个政策预审
        
        Args:
            user_data: 用户数据字典
            policy_data: 政策数据字典
            
        Returns:
            预审结果字典，包含审核结果和不符合条件列表
        """
        try:
            # 使用数据处理器处理输入数据
            processed_user_data = self.data_processor.process_user_data(user_data)
            processed_policy_data = self.data_processor.process_policy_data(policy_data)
            
            # 验证输入数据
            if not self.data_processor.validate_match_input(processed_user_data, processed_policy_data):
                self.logger.warning("输入数据验证失败")
                return {
                    "result": 0,
                    "failed_conditions": ["输入数据验证失败"],
                    "message": "输入数据格式不正确或缺少必要字段"
                }
            
            user_id = processed_user_data.get("用户ID", "Unknown")
            policy_id = processed_policy_data.get("政策编号", "Unknown")
            
            self.logger.info(f"开始预审: 用户={user_id}, 政策={policy_id}")
            
            # 获取条件规则
            condition_root = processed_policy_data.get("条件", {})
            
            if not condition_root:
                self.logger.warning(f"政策 {policy_id} 没有条件规则，默认审核通过")
                return {
                    "result": 1,
                    "failed_conditions": [],
                    "message": "政策无条件限制，审核通过"
                }
            
            # 收集所有不符合的条件
            failed_conditions = []
            result = self._collect_failed_conditions(condition_root, processed_user_data, failed_conditions)
            audit_result = 1 if result else 0
            
            self.logger.info(f"预审结果: 用户={user_id}, 政策={policy_id}, 结果={audit_result}, 失败条件数={len(failed_conditions)}")
            
            return {
                "result": audit_result,
                "failed_conditions": failed_conditions,
                "message": "审核通过" if audit_result == 1 else f"审核未通过，存在{len(failed_conditions)}个不符合条件"
            }
            
        except Exception as e:
            error_msg = f"预审异常: 用户={user_data.get('用户ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}"
            self.logger.error(error_msg)
            return {
                "result": 0,
                "failed_conditions": [f"系统异常: {str(e)}"],
                "message": "预审过程中发生异常"
            }
    
    def multi_user_audit_policy(self, users_data: List[Dict], policy_data: Dict) -> List[Dict]:
        """
        多个用户与单个政策预审
        
        Args:
            users_data: 用户数据列表
            policy_data: 政策数据字典
            
        Returns:
            预审结果列表 (每个元素包含审核结果和失败条件)
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
                results.append({
                    "result": 0,
                    "failed_conditions": [f"用户处理异常: {str(e)}"],
                    "message": "用户数据处理异常"
                })
        
        passed_count = sum(1 for r in results if r.get("result", 0) == 1)
        self.logger.info(f"多用户预审完成: 政策={policy_id}, 审核通过={passed_count}/{len(users_data)}")
        
        return results
    
    def get_audit_summary(self, users_data: List[Dict], policy_data: Dict, 
                         audit_results: List[Dict]) -> Dict[str, Any]:
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
            
            passed_count = sum(1 for r in audit_results if r.get("result", 0) == 1)
            total_users = len(users_data)
            pass_rate = round(passed_count / total_users, 3) if total_users > 0 else 0.0
            
            # 统计所有失败条件
            all_failed_conditions = []
            for result in audit_results:
                if result.get("result", 0) == 0:
                    all_failed_conditions.extend(result.get("failed_conditions", []))
            
            # 统计失败条件频次
            condition_counts = {}
            for condition in all_failed_conditions:
                condition_counts[condition] = condition_counts.get(condition, 0) + 1
            
            summary = {
                "政策编号": processed_policy_data.get("政策编号", "Unknown"),
                "政策名称": processed_policy_data.get("政策名称", ""),
                "总用户数": total_users,
                "审核通过数": passed_count,
                "通过率": pass_rate,
                "常见失败条件": dict(sorted(condition_counts.items(), key=lambda x: x[1], reverse=True)[:10]),  # 前10个最常见的失败条件
                "用户审核详情": []
            }
            
            # 统计每个用户的预审情况
            for i, user_data in enumerate(users_data):
                processed_user_data = self.data_processor.process_user_data(user_data)
                user_id = processed_user_data.get("用户ID", f"User_{i}")
                user_result = audit_results[i] if i < len(audit_results) else {"result": 0, "failed_conditions": [], "message": ""}
                
                summary["用户审核详情"].append({
                    "用户ID": user_id,
                    "审核结果": user_result.get("result", 0),
                    "审核状态": "通过" if user_result.get("result", 0) == 1 else "不通过",
                    "失败条件": user_result.get("failed_conditions", []),
                    "消息": user_result.get("message", "")
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成预审摘要异常: {e}")
            return {"错误": str(e)}