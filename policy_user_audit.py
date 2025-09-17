"""
政策预审系统核心逻辑模块
基于严格规则审核，返回0或1的审核结果
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
            
            # 使用 data_processor 中的方法评估规则
            result = self.data_processor.evaluate_rule_node(condition_root, processed_user_data)
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