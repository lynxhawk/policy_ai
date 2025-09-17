"""
政策预审系统核心逻辑模块
基于严格规则预审，返回0或1的预审结果
支持复杂的逻辑运算（AND、OR、NOT）
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re
from data_processor_enterprise import DataProcessor

# 配置日志
logger = logging.getLogger(__name__)


class PolicyAuditEngine:
    """政策预审引擎核心类"""
    
    def __init__(self):
        """初始化预审引擎"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_processor = DataProcessor()
    
    def audit_policy(self, enterprise_data: Dict, policy_data: Dict) -> int:
        """
        单个企业与单个政策预审
        
        Args:
            enterprise_data: 企业数据字典
            policy_data: 政策数据字典
            
        Returns:
            预审结果: 1-通过, 0-不通过
        """
        try:
            enterprise_id = enterprise_data.get("企业ID", "Unknown")
            policy_id = policy_data.get("政策编号", "Unknown")
            
            self.logger.info(f"开始预审: 企业={enterprise_id}, 政策={policy_id}")
            
            # 获取条件规则
            condition_root = policy_data.get("条件", {})
            
            if not condition_root:
                self.logger.warning(f"政策 {policy_id} 没有条件规则，默认预审通过")
                return 1
            
            # 使用 data_processor 中的方法评估规则
            result = self.data_processor.evaluate_rule_node(condition_root, enterprise_data)
            audit_result = 1 if result else 0
            
            self.logger.info(f"预审结果: 企业={enterprise_id}, 政策={policy_id}, 结果={audit_result}")
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"预审异常: 企业={enterprise_data.get('企业ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0  # 出错时默认不通过
    
    def multi_enterprise_audit_policy(self, enterprises_data: List[Dict], policy_data: Dict) -> List[int]:
        """
        多个企业与单个政策预审
        
        Args:
            enterprises_data: 企业数据列表
            policy_data: 政策数据字典
            
        Returns:
            预审结果列表 (每个元素为0或1)
        """
        results = []
        policy_id = policy_data.get("政策编号", "Unknown")
        
        self.logger.info(f"开始多企业预审: 企业数量={len(enterprises_data)}, 政策={policy_id}")
        
        for i, enterprise_data in enumerate(enterprises_data):
            try:
                result = self.audit_policy(enterprise_data, policy_data)
                results.append(result)
                
            except Exception as e:
                enterprise_id = enterprise_data.get("企业ID", f"Enterprise_{i}")
                self.logger.error(f"预审企业 {enterprise_id} 失败: {e}")
                results.append(0)  # 出错时默认不通过
        
        passed_count = sum(results)
        self.logger.info(f"多企业预审完成: 政策={policy_id}, 通过预审={passed_count}/{len(enterprises_data)}")
        
        return results
    
    def get_audit_summary(self, enterprises_data: List[Dict], policy_data: Dict, 
                         audit_results: List[int]) -> Dict[str, Any]:
        """
        生成预审统计摘要
        
        Args:
            enterprises_data: 企业数据列表
            policy_data: 政策数据字典
            audit_results: 预审结果列表
            
        Returns:
            统计摘要字典
        """
        try:
            passed_count = sum(audit_results)
            total_enterprises = len(enterprises_data)
            pass_rate = round(passed_count / total_enterprises, 3) if total_enterprises > 0 else 0.0
            
            summary = {
                "政策编号": policy_data.get("政策编号", "Unknown"),
                "政策名称": policy_data.get("政策名称", ""),
                "总企业数": total_enterprises,
                "预审通过数": passed_count,
                "通过率": pass_rate,
                "企业预审详情": []
            }
            
            # 统计每个企业的预审情况
            for i, enterprise_data in enumerate(enterprises_data):
                enterprise_id = enterprise_data.get("企业ID", f"Enterprise_{i}")
                enterprise_result = audit_results[i] if i < len(audit_results) else 0
                
                summary["企业预审详情"].append({
                    "企业ID": enterprise_id,
                    "预审结果": enterprise_result,
                    "预审状态": "通过" if enterprise_result == 1 else "不通过"
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成预审摘要异常: {e}")
            return {"错误": str(e)}