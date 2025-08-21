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
            
            # 标准化布尔值字段
            boolean_fields = ["缴纳社保", "营业执照"]
            for field in boolean_fields:
                if field in processed_data:
                    value = str(processed_data[field]).strip()
                    if value in ["是", "存续", "True", "true", "1", "有"]:
                        processed_data[field] = "是"
                    else:
                        processed_data[field] = "否"
            
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
    
    def calculate_enterprise_match_score(self, enterprise_data: Dict, policy_data: Dict) -> float:
        """
        计算企业与政策的匹配分数，返回0-1之间的匹配率
        
        Args:
            enterprise_data: 企业数据字典
            policy_data: 政策数据字典
            
        Returns:
            匹配分数 (0.0-1.0)，出错时返回0.0
        """
        try:
            # 检查是否为企业政策
            if not self.is_enterprise_policy(policy_data):
                self.logger.debug(f"政策 {policy_data.get('政策编号', 'Unknown')} 不是企业政策")
                return 0.0
            
            # 预处理企业数据
            processed_enterprise_data = self.preprocess_enterprise_data(enterprise_data)
            
            matched_conditions = 0
            total_conditions = 0
            
            # 处理嵌套条件结构
            condition_root = policy_data.get("条件", {})
            
            # 提取所有条件规则（忽略逻辑关系）
            all_conditions = self.extract_all_conditions(condition_root)
            total_conditions = len(all_conditions)
            
            if total_conditions == 0:
                self.logger.warning(f"企业政策 {policy_data.get('政策编号', 'Unknown')} 没有条件规则")
                return 0.0
            
            for condition in all_conditions:
                try:
                    field = condition.get("字段")
                    operator = condition.get("操作符")
                    value = condition.get("值")
                    
                    if not field or not operator:
                        self.logger.warning(f"条件缺少必要字段: {condition}")
                        continue
                    
                    if field in processed_enterprise_data:
                        enterprise_value = processed_enterprise_data[field]
                        
                        if self.check_enterprise_condition(enterprise_value, operator, value):
                            matched_conditions += 1
                            self.logger.debug(f"条件匹配成功: {field} {operator} {value}, 企业值: {enterprise_value}")
                        else:
                            self.logger.debug(f"条件匹配失败: {field} {operator} {value}, 企业值: {enterprise_value}")
                    else:
                        self.logger.debug(f"企业数据中缺少字段: {field}")
                        
                except Exception as e:
                    self.logger.error(f"处理单个条件异常: {condition}, 错误: {e}")
                    continue
            
            # 返回匹配率（0-1之间的浮点数）
            score = matched_conditions / total_conditions
            self.logger.info(f"企业 {enterprise_data.get('企业ID', 'Unknown')} 与政策 {policy_data.get('政策编号', 'Unknown')} 匹配分数: {score:.2f} ({matched_conditions}/{total_conditions})")
            
            return round(score, 2)
            
        except Exception as e:
            self.logger.error(f"计算企业匹配分数异常: 企业={enterprise_data.get('企业ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0.0
    
    def batch_calculate_enterprise_match_scores(self, enterprise_data: Dict, policies_data: List[Dict]) -> List[Dict]:
        """
        批量计算企业与多个政策的匹配分数
        
        Args:
            enterprise_data: 企业数据字典
            policies_data: 政策数据列表
            
        Returns:
            包含政策信息和匹配分数的列表，按分数降序排列
        """
        results = []
        enterprise_id = enterprise_data.get("企业ID", "Unknown")
        
        # 过滤出企业类型政策
        enterprise_policies = [policy for policy in policies_data if self.is_enterprise_policy(policy)]
        
        self.logger.info(f"开始为企业 {enterprise_id} 计算 {len(enterprise_policies)} 个企业政策的匹配分数")
        
        for i, policy_data in enumerate(enterprise_policies):
            try:
                score = self.calculate_enterprise_match_score(enterprise_data, policy_data)
                
                result = {
                    "政策编号": policy_data.get("政策编号", f"Policy_{i}"),
                    "政策名称": policy_data.get("政策名称", ""),
                    "政策类型": policy_data.get("政策类型", ""),
                    "匹配分数": score,
                    "适用对象": policy_data.get("适用对象", ""),
                    "政策描述": policy_data.get("政策描述", "")
                }
                
                results.append(result)
                
                self.logger.debug(f"政策 {result['政策编号']} 匹配分数: {score}")
                
            except Exception as e:
                self.logger.error(f"计算第 {i+1} 个政策匹配分数失败: {e}")
                continue
        
        # 按匹配分数降序排列
        results.sort(key=lambda x: x["匹配分数"], reverse=True)
        
        avg_score = sum(r["匹配分数"] for r in results) / len(results) if results else 0.0
        self.logger.info(f"企业 {enterprise_id} 匹配计算完成，平均分数: {avg_score:.2f}, 共匹配 {len(results)} 个企业政策")
        
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
                
                # 计算该企业与所有企业政策的匹配分数
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
                                        top_n: int = 10, min_score: float = 0.0) -> List[Dict]:
        """
        为单个企业推荐政策
        
        Args:
            enterprise_data: 企业数据
            policies_data: 政策数据列表
            top_n: 返回前N个推荐结果
            min_score: 最低匹配分数阈值
            
        Returns:
            推荐政策列表
        """
        results = self.matcher.batch_calculate_enterprise_match_scores(enterprise_data, policies_data)
        
        # 过滤低分政策
        filtered_results = [r for r in results if r["匹配分数"] >= min_score]
        
        # 返回前N个结果
        return filtered_results[:top_n]
    
    @staticmethod
    def calculate_enterprise_match_score(enterprise_data: Dict, policy_data: Dict) -> float:
        """静态方法包装器，保持向后兼容"""
        matcher = EnterprisePolicyMatcher()
        return matcher.calculate_enterprise_match_score(enterprise_data, policy_data)


# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 示例企业数据
    enterprise_sample = {
        "企业ID": "ENT0001",
        "注册地": "浙江省平湖市",
        "注册时间": "2018-03-15",
        "行业": "养老服务",
        "注册资本（万元）": 500,
        "缴纳社保": "是",
        "贷款情况": "未结清",
        "法人姓名": "张明华",
        "营业执照": "存续",
        "法人年龄": 45,
        "法人毕业时间": "1998-06",
        "企业规模": "中型企业",
        "经营时间": 7
    }
    
    # 示例政策数据
    policy_sample = {
        "政策编号": "POL001",
        "政策名称": "中小企业发展扶持政策",
        "政策类型": "企业",
        "适用对象": "中小企业",
        "条件": {
            "逻辑关系": "AND",
            "规则": [
                {"字段": "注册资本（万元）", "操作符": "<=", "值": 1000},
                {"字段": "经营时间", "操作符": ">=", "值": 3},
                {"字段": "缴纳社保", "操作符": "=", "值": "是"}
            ]
        }
    }
    
    # 创建匹配器
    matcher = EnterprisePolicyMatcher()
    
    # 计算匹配分数
    score = matcher.calculate_enterprise_match_score(enterprise_sample, policy_sample)
    print(f"匹配分数: {score}")
    
    # 使用推荐引擎
    engine = EnterprisePolicyRecommendationEngine()
    recommendations = engine.recommend_policies_for_enterprise(enterprise_sample, [policy_sample])
    
    print("推荐结果:")
    for rec in recommendations:
        print(f"- {rec['政策名称']}: {rec['匹配分数']}")