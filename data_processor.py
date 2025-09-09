"""
数据处理工具类
提供数据转换、规范化、验证等通用功能
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from fastapi import Request


class DataProcessor:
    """数据处理工具类"""
    
    def __init__(self):
        """初始化数据处理器"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 就业类型映射表
        self.employment_mapping = {
            "受雇就业": "受雇就业",
            "灵活就业": "灵活就业", 
            "自主创业": "自主创业",
            "未就业": "未就业",
            "employed": "受雇就业",
            "flexible": "灵活就业",
            "entrepreneur": "自主创业",
            "unemployed": "未就业"
        }
        
        # 布尔值映射表
        self.yes_values = ["是", "yes", "true", "1", "有", "对", "是的", "对的"]
        self.no_values = ["否", "no", "false", "0", "无", "不是", "没有", "不对"]
        
        # 需要布尔规范化的字段
        self.boolean_fields = ['征地人员', '缴纳社保', '养老保险', '困难人员']
    
    def safe_convert_to_dict(self, data: Any, default_value: Dict = None) -> Dict:
        """
        安全地将数据转换为字典
        
        Args:
            data: 需要转换的数据
            default_value: 默认值
            
        Returns:
            转换后的字典
        """
        if default_value is None:
            default_value = {}
        
        try:
            if isinstance(data, dict):
                return data
            elif hasattr(data, 'model_dump'):
                return data.model_dump()
            elif hasattr(data, 'dict'):
                return data.dict()
            elif hasattr(data, '__dict__'):
                return data.__dict__
            else:
                self.logger.warning(f"无法转换为字典: {type(data)}")
                return default_value
        except Exception as e:
            self.logger.warning(f"转换字典失败: {e}")
            return default_value
    
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
    
    def extract_numeric_value_simple(self, value: Any) -> Optional[float]:
        """
        简单的数字提取方法，支持带单位的字符串如"2年"、"25岁"等
        
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
    
    def normalize_employment_type(self, value: Any) -> str:
        """
        规范化就业类型
        
        Args:
            value: 原始就业类型值
            
        Returns:
            规范化后的就业类型
        """
        try:
            if value is None:
                return None
                
            # 处理枚举或对象
            if hasattr(value, 'value'):
                value = value.value
            
            # 转换为字符串并查找映射
            value_str = str(value).strip()
            return self.employment_mapping.get(value_str, str(value))
            
        except Exception as e:
            self.logger.warning(f"规范化就业类型失败: {value}, 错误: {e}")
            return str(value) if value is not None else None
    
    def normalize_boolean_field(self, value: Any) -> Optional[str]:
        """
        规范化布尔字段为"是"或"否"
        
        Args:
            value: 原始值
            
        Returns:
            "是"、"否"或原始值
        """
        try:
            if value is None:
                return None
                
            v_str = str(value).strip().lower()
            
            # 检查是否匹配"是"的值
            if any(v_str == y.lower() for y in self.yes_values):
                return "是"
            # 检查是否匹配"否"的值
            elif any(v_str == n.lower() for n in self.no_values):
                return "否"
            else:
                # 无法识别，保持原值
                return value
                
        except Exception as e:
            self.logger.warning(f"规范化布尔字段失败: {value}, 错误: {e}")
            return value
    
    def extract_numeric_value(self, value: Any, min_val: int = None, max_val: int = None) -> Any:
        """
        从值中提取数字（带范围验证）
        
        Args:
            value: 原始值
            min_val: 最小值限制
            max_val: 最大值限制
            
        Returns:
            提取的数字或原始值
        """
        try:
            if value is None:
                return None
                
            # 如果已经是数字类型
            if isinstance(value, (int, float)):
                num_val = int(value)
                if min_val is not None and max_val is not None:
                    if min_val <= num_val <= max_val:
                        return num_val
                    else:
                        return value
                return num_val
            
            # 字符串处理 - 提取数字
            numbers = re.findall(r'\d+', str(value))
            if numbers:
                num_val = int(numbers[0])
                if min_val is not None and max_val is not None:
                    if min_val <= num_val <= max_val:
                        return num_val
                    else:
                        return value
                return num_val
            else:
                return value
                
        except Exception as e:
            self.logger.warning(f"提取数字失败: {value}, 错误: {e}")
            return value
    
    def normalize_user_data(self, user_dict: Dict) -> Dict:
        """
        规范化用户数据
        
        Args:
            user_dict: 原始用户数据字典
            
        Returns:
            规范化后的用户数据字典
        """
        normalized = {}
        
        for key, value in user_dict.items():
            try:
                # 就业类型字段
                if key == '就业类型':
                    normalized[key] = self.normalize_employment_type(value)
                
                # 布尔字段
                elif key in self.boolean_fields:
                    normalized[key] = self.normalize_boolean_field(value)
                
                # 年龄字段
                elif key == '年龄':
                    normalized[key] = self.extract_numeric_value(value, 0, 120)
                
                # 毕业时间字段
                elif key == '毕业时间':
                    normalized[key] = self.extract_numeric_value(value)
                
                # 其他字段保持原样
                else:
                    normalized[key] = value
                    
            except Exception as e:
                self.logger.warning(f"处理字段 {key} 时出错: {e}，保持原值")
                normalized[key] = value
        
        return normalized
    
    def convert_logic_to_lowercase(self, data: Any) -> Any:
        """
        递归地将逻辑操作符转换为小写
        
        Args:
            data: 需要转换的数据
            
        Returns:
            转换后的数据
        """
        try:
            if isinstance(data, dict):
                result = {}
                for key, value in data.items():
                    if key == "逻辑" and isinstance(value, str):
                        result[key] = value.lower()
                    elif isinstance(value, (dict, list)):
                        result[key] = self.convert_logic_to_lowercase(value)
                    else:
                        result[key] = value
                return result
            elif isinstance(data, list):
                return [self.convert_logic_to_lowercase(item) for item in data]
            else:
                return data
        except Exception as e:
            self.logger.warning(f"转换逻辑操作符失败: {e}")
            return data
    
    async def parse_request_safely(self, request: Request) -> Dict:
        """
        安全地解析请求体
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            解析后的字典数据
        """
        try:
            body = await request.body()
            if not body:
                return {}
            
            # 尝试解析JSON
            try:
                return json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.logger.warning("请求体不是有效的JSON格式")
                return {}
                
        except Exception as e:
            self.logger.warning(f"解析请求体失败: {e}")
            return {}
    
    def process_user_data(self, raw_user_data: Any) -> Dict:
        """
        处理用户数据的完整流程
        
        Args:
            raw_user_data: 原始用户数据
            
        Returns:
            处理后的用户数据字典
        """
        try:
            # 转换为字典
            user_dict = self.safe_convert_to_dict(raw_user_data)
            
            if not user_dict:
                return {}
            
            # 规范化数据
            normalized_dict = self.normalize_user_data(user_dict)
            
            return normalized_dict
            
        except Exception as e:
            self.logger.error(f"处理用户数据失败: {e}")
            return {}
    
    def process_policy_data(self, raw_policy_data: Any) -> Dict:
        """
        处理政策数据的完整流程
        
        Args:
            raw_policy_data: 原始政策数据
            
        Returns:
            处理后的政策数据字典
        """
        try:
            # 转换为字典
            policy_dict = self.safe_convert_to_dict(raw_policy_data)
            
            if not policy_dict:
                return {}
            
            # 转换逻辑操作符
            processed_dict = self.convert_logic_to_lowercase(policy_dict)
            
            return processed_dict
            
        except Exception as e:
            self.logger.error(f"处理政策数据失败: {e}")
            return {}
    
    def validate_match_input(self, user_data: Dict, policy_data: Dict) -> bool:
        """
        验证匹配输入数据的有效性
        
        Args:
            user_data: 用户数据
            policy_data: 政策数据
            
        Returns:
            是否有效
        """
        try:
            # 检查用户数据
            if not isinstance(user_data, dict) or not user_data:
                self.logger.debug("用户数据无效或为空")
                return False
            
            # 检查政策数据
            if not isinstance(policy_data, dict) or not policy_data:
                self.logger.debug("政策数据无效或为空")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"验证输入数据失败: {e}")
            return False
    
    def create_match_summary(self, results: List[int], policies_data: List[Dict], 
                           user_data: Dict = None) -> Dict:
        """
        创建匹配结果摘要
        
        Args:
            results: 匹配结果列表
            policies_data: 政策数据列表
            user_data: 用户数据（可选）
            
        Returns:
            匹配摘要字典
        """
        try:
            total_policies = len(policies_data)
            matched_policies = sum(results)
            match_rate = round(matched_policies / total_policies, 3) if total_policies > 0 else 0.0
            
            summary = {
                "total_policies": total_policies,
                "matched_policies": matched_policies,
                "match_rate": match_rate,
                "results": results
            }
            
            # 如果提供了用户数据，添加用户ID
            if user_data and isinstance(user_data, dict):
                user_id = user_data.get("用户ID")
                if user_id:
                    summary["user_id"] = str(user_id)
            
            # 添加政策详情
            policy_details = []
            for i, (policy_data, result) in enumerate(zip(policies_data, results)):
                policy_dict = self.safe_convert_to_dict(policy_data)
                policy_details.append({
                    "policy_id": str(policy_dict.get('政策编号', f'Policy_{i+1}')),
                    "policy_name": str(policy_dict.get('政策名称', policy_dict.get('标题', f'政策{i+1}'))),
                    "match_result": result,
                    "match_status": "匹配" if result == 1 else "不匹配"
                })
            
            summary["policy_details"] = policy_details
            
            return summary
            
        except Exception as e:
            self.logger.error(f"创建匹配摘要失败: {e}")
            return {
                "total_policies": 0,
                "matched_policies": 0,
                "match_rate": 0.0,
                "results": [],
                "error": str(e)
            }