"""
政策匹配系统核心逻辑模块
基于严格规则匹配，返回0或1的匹配结果
支持复杂的逻辑运算（AND、OR、NOT）
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re
from data_processor import DataProcessor

# 配置日志
logger = logging.getLogger(__name__)


class PolicyMatchEngine:
    """政策匹配引擎核心类"""
    
    def __init__(self):
        """初始化匹配引擎"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_processor = DataProcessor()
    
    def match_policy(self, user_data: Dict, policy_data: Dict) -> int:
        """
        单个用户与单个政策匹配
        
        Args:
            user_data: 用户数据字典
            policy_data: 政策数据字典
            
        Returns:
            匹配结果: 1-匹配, 0-不匹配
        """
        try:
            user_id = user_data.get("用户ID", "Unknown")
            policy_id = policy_data.get("政策编号", "Unknown")
            
            self.logger.info(f"开始匹配: 用户={user_id}, 政策={policy_id}")
            
            # 获取条件规则
            condition_root = policy_data.get("条件", {})
            
            if not condition_root:
                self.logger.warning(f"政策 {policy_id} 没有条件规则，默认匹配成功")
                return 1
            
            # 使用 data_processor 中的方法评估规则
            result = self.data_processor.evaluate_rule_node(condition_root, user_data)
            match_result = 1 if result else 0
            
            self.logger.info(f"匹配结果: 用户={user_id}, 政策={policy_id}, 结果={match_result}")
            
            return match_result
            
        except Exception as e:
            self.logger.error(f"匹配异常: 用户={user_data.get('用户ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0  # 出错时默认不匹配
    
    def multi_user_match_policy(self, users_data: List[Dict], policy_data: Dict) -> List[int]:
        """
        多个用户与单个政策匹配
        
        Args:
            users_data: 用户数据列表
            policy_data: 政策数据字典
            
        Returns:
            匹配结果列表 (每个元素为0或1)
        """
        results = []
        policy_id = policy_data.get("政策编号", "Unknown")
        
        self.logger.info(f"开始多用户匹配: 用户数量={len(users_data)}, 政策={policy_id}")
        
        for i, user_data in enumerate(users_data):
            try:
                result = self.match_policy(user_data, policy_data)
                results.append(result)
                
            except Exception as e:
                user_id = user_data.get("用户ID", f"User_{i}")
                self.logger.error(f"匹配用户 {user_id} 失败: {e}")
                results.append(0)  # 出错时默认不匹配
        
        matched_count = sum(results)
        self.logger.info(f"多用户匹配完成: 政策={policy_id}, 匹配成功={matched_count}/{len(users_data)}")
        
        return results
    
    def get_match_summary(self, users_data: List[Dict], policy_data: Dict, 
                         match_results: List[int]) -> Dict[str, Any]:
        """
        生成匹配统计摘要
        
        Args:
            users_data: 用户数据列表
            policy_data: 政策数据字典
            match_results: 匹配结果列表
            
        Returns:
            统计摘要字典
        """
        try:
            matched_count = sum(match_results)
            total_users = len(users_data)
            match_rate = round(matched_count / total_users, 3) if total_users > 0 else 0.0
            
            summary = {
                "政策编号": policy_data.get("政策编号", "Unknown"),
                "政策名称": policy_data.get("政策名称", ""),
                "总用户数": total_users,
                "匹配成功数": matched_count,
                "匹配率": match_rate,
                "用户匹配详情": []
            }
            
            # 统计每个用户的匹配情况
            for i, user_data in enumerate(users_data):
                user_id = user_data.get("用户ID", f"User_{i}")
                user_result = match_results[i] if i < len(match_results) else 0
                
                summary["用户匹配详情"].append({
                    "用户ID": user_id,
                    "匹配结果": user_result,
                    "匹配状态": "匹配" if user_result == 1 else "不匹配"
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成匹配摘要异常: {e}")
            return {"错误": str(e)}