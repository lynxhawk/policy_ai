"""
企业政策匹配系统核心逻辑模块
专门处理企业数据与企业政策条件的匹配计算功能
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re
from datetime import datetime, date

# 配置日志
logger = logging.getLogger(__name__)


class EnterprisePolicyMatcher:
    """企业政策匹配核心类"""
    
    def __init__(self):
        """初始化企业匹配器"""
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
        从值中提取数字，支持带单位的字符串如"500万元"、"7年"等
        
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
    
    def extract_location_info(self, location: str) -> Dict[str, str]:
        """
        从注册地址中提取省、市、区信息
        
        Args:
            location: 注册地址字符串
            
        Returns:
            包含省市区信息的字典
        """
        location_info = {"省": "", "市": "", "区": ""}
        
        try:
            if not location:
                return location_info
                
            location = str(location).strip()
            
            # 提取省份
            province_match = re.search(r'(.*?省)', location)
            if province_match:
                location_info["省"] = province_match.group(1)
            
            # 提取市
            city_match = re.search(r'(.*?市)', location)
            if city_match:
                location_info["市"] = city_match.group(1)
            
            # 提取区/县
            district_match = re.search(r'(.*?[区县])', location)
            if district_match:
                location_info["区"] = district_match.group(1)
                
        except Exception as e:
            self.logger.warning(f"地址解析失败: {location}, 错误: {e}")
            
        return location_info
    
    def calculate_work_experience(self, graduation_time: str) -> Optional[int]:
        """
        根据法人毕业时间计算毕业年限
        
        Args:
            graduation_time: 毕业时间字符串
            
        Returns:
            毕业年限，失败时返回None
        """
        try:
            if not graduation_time:
                return None
                
            # 尝试解析毕业日期格式
            graduation_date = None
            
            # 支持多种日期格式
            date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y-%m", "%Y年%m月", "%Y"]
            
            for fmt in date_formats:
                try:
                    graduation_date = datetime.strptime(str(graduation_time), fmt).date()
                    break
                except ValueError:
                    continue
            
            # 如果无法解析为日期，尝试提取年份
            if not graduation_date:
                graduation_year = self.extract_numeric_value(graduation_time)
                if graduation_year and 1950 <= graduation_year <= 2030:  # 合理性检查
                    graduation_date = date(int(graduation_year), 6, 30)  # 默认6月30日毕业
            
            if graduation_date:
                today = date.today()
                work_years = today.year - graduation_date.year
                
                # 如果还没到毕业月份，毕业年限减1
                if today.month < graduation_date.month or (today.month == graduation_date.month and today.day < graduation_date.day):
                    work_years -= 1
                
                # 毕业年限不能为负数，最小为0
                return max(0, work_years)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"毕业年限计算失败: {graduation_time}, 错误: {e}")
            return None
    
    def calculate_operation_years(self, register_time: str) -> Optional[int]:
        """
        根据注册时间计算经营年限
        
        Args:
            register_time: 注册时间字符串
            
        Returns:
            经营年限，失败时返回None
        """
        try:
            if not register_time:
                return None
                
            # 尝试解析日期格式
            register_date = None
            
            # 支持多种日期格式
            date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y-%m", "%Y年%m月"]
            
            for fmt in date_formats:
                try:
                    register_date = datetime.strptime(str(register_time), fmt).date()
                    break
                except ValueError:
                    continue
            
            if register_date:
                today = date.today()
                years = today.year - register_date.year
                # 如果还没到注册月份，年数减1
                if today.month < register_date.month or (today.month == register_date.month and today.day < register_date.day):
                    years -= 1
                return max(0, years)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"经营年限计算失败: {register_time}, 错误: {e}")
            return None
    
    def check_enterprise_condition(self, enterprise_value: Any, operator: str, condition_value: Any) -> bool:
        """
        检查企业单个条件是否匹配，针对企业特有字段进行优化
        
        Args:
            enterprise_value: 企业数据值
            operator: 操作符
            condition_value: 条件值
            
        Returns:
            是否匹配，类型不匹配时返回False
        """
        # 如果企业值为None或空，直接返回False
        if enterprise_value is None or enterprise_value == "":
            self.logger.debug(f"企业值为空: {enterprise_value}")
            return False
            
        try:
            # between 操作符处理
            if operator == 'between':
                if isinstance(condition_value, list) and len(condition_value) == 2:
                    enterprise_val = self.extract_numeric_value(enterprise_value)
                    min_val = self.extract_numeric_value(condition_value[0])
                    max_val = self.extract_numeric_value(condition_value[1])
                    
                    if enterprise_val is None or min_val is None or max_val is None:
                        self.logger.warning(f"between操作符类型转换失败: enterprise={enterprise_value}, range={condition_value}")
                        return False
                        
                    return min_val <= enterprise_val <= max_val
                else:
                    self.logger.warning(f"between操作符条件值格式错误: {condition_value}")
                    return False
                    
            # 数字比较操作符
            elif operator in ['>', '<', '>=', '<=']:
                enterprise_val = self.extract_numeric_value(enterprise_value)
                condition_val = self.extract_numeric_value(condition_value)
                
                if enterprise_val is None or condition_val is None:
                    self.logger.warning(f"数字比较类型转换失败: enterprise={enterprise_value}, condition={condition_value}")
                    return False
                
                if operator == '>':
                    return enterprise_val > condition_val
                elif operator == '<':
                    return enterprise_val < condition_val
                elif operator == '>=':
                    return enterprise_val >= condition_val
                elif operator == '<=':
                    return enterprise_val <= condition_val
                    
            # 字符串比较（支持地址匹配）
            elif operator == '=':
                enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if enterprise_str is None or condition_str is None:
                    self.logger.warning(f"字符串比较转换失败: enterprise={enterprise_value}, condition={condition_value}")
                    return False
                    
                return enterprise_str == condition_str
                
            elif operator == '!=':
                enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if enterprise_str is None or condition_str is None:
                    self.logger.warning(f"字符串比较转换失败: enterprise={enterprise_value}, condition={condition_value}")
                    return False
                    
                return enterprise_str != condition_str
            
            # 包含匹配（用于地址、行业等字段）
            elif operator == 'contains':
                enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if enterprise_str is None or condition_str is None:
                    return False
                    
                return condition_str in enterprise_str
            
            # 不包含匹配
            elif operator == 'not_contains':
                enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                condition_str = self.safe_type_conversion(condition_value, "str")
                
                if enterprise_str is None or condition_str is None:
                    return False
                    
                return condition_str not in enterprise_str
            
            # 列表匹配（用于多选字段）
            elif operator == 'in':
                if isinstance(condition_value, list):
                    enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                    return enterprise_str in [self.safe_type_conversion(v, "str") for v in condition_value]
                else:
                    return False
            
            elif operator == 'not_in':
                if isinstance(condition_value, list):
                    enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                    return enterprise_str not in [self.safe_type_conversion(v, "str") for v in condition_value]
                else:
                    return False
            
            else:
                self.logger.warning(f"不支持的操作符: {operator}")
                return False
                
        except Exception as e:
            self.logger.error(f"企业条件检查异常: enterprise={enterprise_value}, operator={operator}, condition={condition_value}, 错误: {e}")
            return False
    
    def extract_all_conditions(self, condition_node: Dict) -> List[Dict]:
        """递归提取所有条件规则，支持多种格式"""
        conditions = []
        
        try:
            # 支持 "规则" 或 "rules" 字段
            rules_key = "规则" if "规则" in condition_node else "rules"
            
            # 如果有规则字段，说明是容器节点
            if rules_key in condition_node:
                rules = condition_node[rules_key]
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
    
    def preprocess_enterprise_data(self, enterprise_data: Dict) -> Dict:
        """
        预处理企业数据，添加计算字段和标准化字段
        
        Args:
            enterprise_data: 原始企业数据
            
        Returns:
            处理后的企业数据
        """
        processed_data = enterprise_data.copy()
        
        try:
            # 计算法人毕业年限（如果有法人毕业时间）
            if "法人毕业时间" in processed_data:
                work_years = self.calculate_work_experience(processed_data["法人毕业时间"])
                if work_years is not None:
                    processed_data["法人毕业年限"] = work_years
            
            # 计算实际经营年限（如果没有提供）
            if "经营时间" not in processed_data and "注册时间" in processed_data:
                operation_years = self.calculate_operation_years(processed_data["注册时间"])
                if operation_years is not None:
                    processed_data["经营时间"] = operation_years
            
            # 解析注册地址
            if "注册地" in processed_data:
                location_info = self.extract_location_info(processed_data["注册地"])
                processed_data.update({
                    "注册省份": location_info["省"],
                    "注册城市": location_info["市"],
                    "注册区域": location_info["区"]
                })
            
            # 处理贷款情况字段
            if "贷款情况" in processed_data:
                loan_status = str(processed_data["贷款情况"]).strip()
                if loan_status in ["未结清", "有贷款", "存在贷款"]:
                    processed_data["有贷款"] = "是"
                else:
                    processed_data["有贷款"] = "否"
            
            # 标准化注册资本字段（支持多种单位）
            if "注册资本（万元）" in processed_data:
                # 如果政策条件中用的是"注册资本"，添加别名
                processed_data["注册资本"] = processed_data["注册资本（万元）"]
            elif "注册资本" in processed_data:
                # 如果企业数据中是"注册资本"，也添加带单位的别名
                processed_data["注册资本（万元）"] = processed_data["注册资本"]
                    
        except Exception as e:
            self.logger.error(f"企业数据预处理异常: {e}")
        
        return processed_data
    
    def is_enterprise_policy(self, policy_data: Dict) -> bool:
        """
        判断政策是否为企业类型政策
        
        Args:
            policy_data: 政策数据
            
        Returns:
            是否为企业政策
        """
        # 支持多种字段名
        policy_type = (policy_data.get("政策类型", "") or 
                      policy_data.get("类型", "")).strip()
        target_audience = policy_data.get("适用对象", "").strip()
        
        # 检查政策类型和适用对象
        enterprise_keywords = ["企业", "公司", "法人", "商户", "经营者"]
        
        return (policy_type == "企业" or 
                any(keyword in target_audience for keyword in enterprise_keywords))
    
    def calculate_enterprise_match_score(self, enterprise_data: Dict, policy_data: Dict) -> int:
        """
        计算企业与政策的匹配结果，返回0或1（二值化结果）
        只有所有条件都匹配才返回1，否则返回0
        
        Args:
            enterprise_data: 企业数据字典
            policy_data: 政策数据字典
            
        Returns:
            匹配结果 (0或1)，出错时返回0
        """
        try:
            # 检查是否为企业政策
            if not self.is_enterprise_policy(policy_data):
                self.logger.debug(f"政策 {policy_data.get('政策编号', 'Unknown')} 不是企业政策")
                return 0
            
            # 预处理企业数据
            processed_enterprise_data = self.preprocess_enterprise_data(enterprise_data)
            
            # 处理嵌套条件结构
            condition_root = policy_data.get("条件", {})
            
            # 提取所有条件规则（忽略逻辑关系）
            all_conditions = self.extract_all_conditions(condition_root)
            total_conditions = len(all_conditions)
            
            if total_conditions == 0:
                self.logger.warning(f"企业政策 {policy_data.get('政策编号', 'Unknown')} 没有条件规则")
                return 0
            
            # 检查每个条件，有任何一个不匹配就返回0
            for condition in all_conditions:
                try:
                    field = condition.get("字段")
                    operator = condition.get("操作符")
                    value = condition.get("值")
                    
                    if not field or not operator:
                        self.logger.warning(f"条件缺少必要字段: {condition}")
                        return 0  # 缺少必要字段视为不匹配
                    
                    if field in processed_enterprise_data:
                        enterprise_value = processed_enterprise_data[field]
                        
                        if not self.check_enterprise_condition(enterprise_value, operator, value):
                            self.logger.debug(f"条件匹配失败: {field} {operator} {value}, 企业值: {enterprise_value}")
                            return 0  # 有任何条件不匹配，立即返回0
                        else:
                            self.logger.debug(f"条件匹配成功: {field} {operator} {value}, 企业值: {enterprise_value}")
                    else:
                        self.logger.debug(f"企业数据中缺少字段: {field}")
                        return 0  # 缺少字段视为不匹配
                        
                except Exception as e:
                    self.logger.error(f"处理单个条件异常: {condition}, 错误: {e}")
                    return 0  # 出现异常视为不匹配
            
            # 所有条件都匹配才返回1
            self.logger.info(f"企业 {enterprise_data.get('企业ID', 'Unknown')} 与政策 {policy_data.get('政策编号', 'Unknown')} 完全匹配 (1)")
            return 1
            
        except Exception as e:
            self.logger.error(f"计算企业匹配结果异常: 企业={enterprise_data.get('企业ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0
    
    def batch_calculate_enterprise_match_scores(self, enterprise_data: Dict, policies_data: List[Dict]) -> List[Dict]:
        """
        批量计算企业与多个政策的匹配结果
        
        Args:
            enterprise_data: 企业数据字典
            policies_data: 政策数据列表
            
        Returns:
            包含政策信息和匹配结果的列表，完全匹配的政策排在前面
        """
        results = []
        enterprise_id = enterprise_data.get("企业ID", "Unknown")
        
        # 过滤出企业类型政策
        enterprise_policies = [policy for policy in policies_data if self.is_enterprise_policy(policy)]
        
        self.logger.info(f"开始为企业 {enterprise_id} 计算 {len(enterprise_policies)} 个企业政策的匹配结果")
        
        for i, policy_data in enumerate(enterprise_policies):
            try:
                match_result = self.calculate_enterprise_match_score(enterprise_data, policy_data)
                
                result = {
                    "政策编号": policy_data.get("政策编号", f"Policy_{i}"),
                    "政策名称": policy_data.get("政策名称", ""),
                    "政策类型": policy_data.get("政策类型", ""),
                    "匹配结果": match_result,  # 0或1
                    "匹配状态": "完全匹配" if match_result == 1 else "不匹配",
                    "适用对象": policy_data.get("适用对象", ""),
                    "政策描述": policy_data.get("政策描述", "")
                }
                
                results.append(result)
                
                self.logger.debug(f"政策 {result['政策编号']} 匹配结果: {match_result}")
                
            except Exception as e:
                self.logger.error(f"计算第 {i+1} 个政策匹配结果失败: {e}")
                continue
        
        # 按匹配结果排序：完全匹配的(1)排在前面
        results.sort(key=lambda x: x["匹配结果"], reverse=True)
        
        matched_count = sum(1 for r in results if r["匹配结果"] == 1)
        self.logger.info(f"企业 {enterprise_id} 匹配计算完成，完全匹配 {matched_count} 个政策，共处理 {len(results)} 个企业政策")
        
        return results
    
    def multi_enterprise_batch_calculate(self, enterprises_data: List[Dict], policies_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        多企业批量匹配计算
        
        Args:
            enterprises_data: 企业数据列表
            policies_data: 政策数据列表
            
        Returns:
            企业ID为键，匹配结果列表为值的字典
        """
        all_results = {}
        
        # 预先过滤出企业政策
        enterprise_policies = [policy for policy in policies_data if self.is_enterprise_policy(policy)]
        
        self.logger.info(f"开始批量企业政策匹配：{len(enterprises_data)} 个企业，{len(enterprise_policies)} 个企业政策")
        
        for enterprise_idx, enterprise_data in enumerate(enterprises_data):
            try:
                enterprise_id = enterprise_data.get("企业ID", f"Enterprise_{enterprise_idx}")
                
                # 计算该企业与所有企业政策的匹配结果
                enterprise_results = self.batch_calculate_enterprise_match_scores(enterprise_data, enterprise_policies)
                all_results[enterprise_id] = enterprise_results
                        
            except Exception as e:
                self.logger.error(f"处理第 {enterprise_idx} 个企业失败: {e}")
                # 为该企业添加空结果
                enterprise_id = enterprise_data.get("企业ID", f"Enterprise_{enterprise_idx}")
                all_results[enterprise_id] = []
        
        self.logger.info(f"批量企业政策匹配完成，处理了 {len(all_results)} 个企业")
        
        return all_results


class EnterprisePolicyRecommendationEngine:
    """企业政策推荐引擎（兼容性包装器）"""
    
    def __init__(self):
        """初始化企业推荐引擎"""
        self.matcher = EnterprisePolicyMatcher()
        
    def recommend_policies_for_enterprise(self, enterprise_data: Dict, policies_data: List[Dict], 
                                        top_n: int = 10, only_matched: bool = True) -> List[Dict]:
        """
        为单个企业推荐政策
        
        Args:
            enterprise_data: 企业数据
            policies_data: 政策数据列表
            top_n: 返回前N个推荐结果
            only_matched: 是否只返回完全匹配的政策
            
        Returns:
            推荐政策列表
        """
        results = self.matcher.batch_calculate_enterprise_match_scores(enterprise_data, policies_data)
        
        # 过滤结果
        if only_matched:
            filtered_results = [r for r in results if r["匹配结果"] == 1]
        else:
            filtered_results = results
        
        # 返回前N个结果
        return filtered_results[:top_n]
    
    @staticmethod
    def calculate_enterprise_match_score(enterprise_data: Dict, policy_data: Dict) -> int:
        """静态方法包装器，保持向后兼容（现在返回0或1）"""
        matcher = EnterprisePolicyMatcher()
        return matcher.calculate_enterprise_match_score(enterprise_data, policy_data)