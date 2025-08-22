"""
企业政策预审系统核心逻辑模块
基于严格规则审核，返回0或1的审核结果
支持复杂的逻辑运算（AND、OR、NOT）
专门针对企业数据和企业政策进行优化
"""

import logging
from typing import Dict, List, Any, Optional, Union
import re
from datetime import datetime, date

# 配置日志
logger = logging.getLogger(__name__)


class EnterprisePreAuditEngine:
    """企业政策预审引擎核心类"""
    
    def __init__(self):
        """初始化企业预审引擎"""
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
        检查企业单个条件是否匹配，针对企业特有字段进行严格验证
        
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
                    
            # 精确字符串匹配
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
            
            # 在列表中匹配（用于多选字段）
            elif operator == 'in':
                if isinstance(condition_value, list):
                    enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                    condition_strs = [self.safe_type_conversion(v, "str") for v in condition_value]
                    return enterprise_str in condition_strs
                else:
                    # 单值处理
                    enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                    condition_str = self.safe_type_conversion(condition_value, "str")
                    return enterprise_str == condition_str
            
            elif operator == 'not_in':
                if isinstance(condition_value, list):
                    enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                    condition_strs = [self.safe_type_conversion(v, "str") for v in condition_value]
                    return enterprise_str not in condition_strs
                else:
                    # 单值处理
                    enterprise_str = self.safe_type_conversion(enterprise_value, "str")
                    condition_str = self.safe_type_conversion(condition_value, "str")
                    return enterprise_str != condition_str
            
            # 地址区域匹配（特殊逻辑）
            elif operator == 'location_in':
                enterprise_location = self.safe_type_conversion(enterprise_value, "str")
                if not enterprise_location:
                    return False
                    
                # 解析地址信息
                location_info = self.extract_location_info(enterprise_location)
                
                # 检查是否在指定区域内
                if isinstance(condition_value, list):
                    for region in condition_value:
                        region_str = self.safe_type_conversion(region, "str")
                        if (region_str in enterprise_location or 
                            region_str == location_info["省"] or 
                            region_str == location_info["市"] or 
                            region_str == location_info["区"]):
                            return True
                    return False
                else:
                    region_str = self.safe_type_conversion(condition_value, "str")
                    return (region_str in enterprise_location or 
                           region_str == location_info["省"] or 
                           region_str == location_info["市"] or 
                           region_str == location_info["区"])
            
            else:
                self.logger.warning(f"不支持的操作符: {operator}")
                return False
                
        except Exception as e:
            self.logger.error(f"企业条件检查异常: enterprise={enterprise_value}, operator={operator}, condition={condition_value}, 错误: {e}")
            return False
    
    def evaluate_enterprise_rule_node(self, rule_node: Dict, enterprise_data: Dict) -> bool:
        """
        递归评估企业规则节点，支持复杂的逻辑运算
        
        Args:
            rule_node: 规则节点
            enterprise_data: 企业数据
            
        Returns:
            规则评估结果 (True/False)
        """
        try:
            self.logger.debug(f"评估企业规则节点: {rule_node}")
            
            # 如果是叶子节点（包含字段、操作符、值），直接评估条件
            if all(key in rule_node for key in ["字段", "操作符", "值"]):
                field = rule_node["字段"]
                operator = rule_node["操作符"]
                value = rule_node["值"]
                
                if field not in enterprise_data:
                    self.logger.debug(f"企业数据中缺少字段: {field}")
                    return False
                    
                enterprise_value = enterprise_data[field]
                result = self.check_enterprise_condition(enterprise_value, operator, value)
                
                self.logger.info(f"企业条件评估: {field}({enterprise_value}) {operator} {value} = {result}")
                return result
            
            # 如果是容器节点，处理逻辑运算
            elif "规则" in rule_node:
                rules = rule_node["规则"]
                # 支持多种逻辑字段名
                logic_operator = (rule_node.get("逻辑", "") or 
                                rule_node.get("逻辑关系", "") or 
                                "and").lower()  # 默认为and
                
                self.logger.info(f"企业逻辑运算节点: {logic_operator}, 规则数量: {len(rules) if isinstance(rules, list) else 0}")
                
                if not isinstance(rules, list) or len(rules) == 0:
                    self.logger.warning(f"规则列表为空或格式错误: {rules}")
                    return False
                
                # 递归评估所有子规则
                results = []
                for i, sub_rule in enumerate(rules):
                    sub_result = self.evaluate_enterprise_rule_node(sub_rule, enterprise_data)
                    results.append(sub_result)
                    self.logger.debug(f"企业子规则{i+1}结果: {sub_result}")
                    
                    # 短路评估优化
                    if logic_operator == "and" and not sub_result:
                        self.logger.debug(f"企业AND逻辑短路: 发现False，直接返回False")
                        return False
                    elif logic_operator == "or" and sub_result:
                        self.logger.debug(f"企业OR逻辑短路: 发现True，直接返回True")
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
                
                self.logger.info(f"企业逻辑运算 {logic_operator.upper()}: {results} = {final_result}")
                return final_result
            
            else:
                self.logger.warning(f"企业规则节点格式错误，既不是条件节点也不是逻辑节点: {rule_node}")
                return False
                
        except Exception as e:
            self.logger.error(f"评估企业规则节点异常: {rule_node}, 错误: {e}")
            return False
    
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
                processed_data["注册资本"] = processed_data["注册资本（万元）"]
            elif "注册资本" in processed_data:
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
    
    def pre_audit_enterprise_policy(self, enterprise_data: Dict, policy_data: Dict) -> int:
        """
        对企业进行政策预审，严格按照规则逻辑审核
        
        Args:
            enterprise_data: 企业数据字典
            policy_data: 政策数据字典
            
        Returns:
            审核结果: 1-通过, 0-不通过
        """
        try:
            enterprise_id = enterprise_data.get("企业ID", "Unknown")
            policy_id = policy_data.get("政策编号", "Unknown")
            
            self.logger.info(f"开始企业预审: 企业={enterprise_id}, 政策={policy_id}")
            
            # 检查是否为企业政策
            if not self.is_enterprise_policy(policy_data):
                self.logger.info(f"政策 {policy_id} 不是企业政策，预审不通过")
                return 0
            
            # 预处理企业数据
            processed_enterprise_data = self.preprocess_enterprise_data(enterprise_data)
            
            # 获取条件规则
            condition_root = policy_data.get("条件", {})
            
            if not condition_root:
                self.logger.warning(f"企业政策 {policy_id} 没有条件规则，默认审核通过")
                return 1
            
            # 评估规则
            result = self.evaluate_enterprise_rule_node(condition_root, processed_enterprise_data)
            audit_result = 1 if result else 0
            
            self.logger.info(f"企业预审结果: 企业={enterprise_id}, 政策={policy_id}, 结果={audit_result}")
            
            return audit_result
            
        except Exception as e:
            self.logger.error(f"企业预审异常: 企业={enterprise_data.get('企业ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0  # 出错时默认不通过
    
    def batch_pre_audit_enterprise(self, enterprise_data: Dict, policies_data: List[Dict]) -> List[int]:
        """
        批量预审企业与多个政策
        
        Args:
            enterprise_data: 企业数据字典
            policies_data: 政策数据列表
            
        Returns:
            审核结果列表 (每个元素为0或1)
        """
        results = []
        enterprise_id = enterprise_data.get("企业ID", "Unknown")
        
        # 过滤出企业政策
        enterprise_policies = [policy for policy in policies_data if self.is_enterprise_policy(policy)]
        
        self.logger.info(f"开始批量企业预审: 企业={enterprise_id}, 企业政策数量={len(enterprise_policies)}")
        
        for i, policy_data in enumerate(enterprise_policies):
            try:
                result = self.pre_audit_enterprise_policy(enterprise_data, policy_data)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"预审第 {i+1} 个企业政策失败: {e}")
                results.append(0)  # 出错时默认不通过
        
        passed_count = sum(results)
        self.logger.info(f"批量企业预审完成: 企业={enterprise_id}, 通过={passed_count}/{len(enterprise_policies)}")
        
        return results
    
    def multi_enterprise_batch_pre_audit(self, enterprises_data: List[Dict], policies_data: List[Dict]) -> List[List[int]]:
        """
        多企业批量预审
        
        Args:
            enterprises_data: 企业数据列表
            policies_data: 政策数据列表
            
        Returns:
            二维结果列表: [企业][政策] = 0或1
        """
        all_results = []
        
        # 预先过滤出企业政策
        enterprise_policies = [policy for policy in policies_data if self.is_enterprise_policy(policy)]
        
        self.logger.info(f"开始多企业批量预审: 企业数量={len(enterprises_data)}, 企业政策数量={len(enterprise_policies)}")
        
        for enterprise_idx, enterprise_data in enumerate(enterprises_data):
            try:
                enterprise_results = self.batch_pre_audit_enterprise(enterprise_data, enterprise_policies)
                all_results.append(enterprise_results)
                        
            except Exception as e:
                self.logger.error(f"处理第 {enterprise_idx+1} 个企业失败: {e}")
                # 为该企业的所有政策添加0（不通过）
                all_results.append([0] * len(enterprise_policies))
        
        total_audits = len(enterprises_data) * len(enterprise_policies)
        total_passed = sum(sum(enterprise_results) for enterprise_results in all_results)
        
        self.logger.info(f"多企业批量预审完成: 总审核={total_audits}, 总通过={total_passed}")
        
        return all_results
    
    def get_enterprise_audit_summary(self, enterprises_data: List[Dict], policies_data: List[Dict], 
                                   audit_results: List[List[int]]) -> Dict[str, Any]:
        """
        生成企业预审统计摘要
        
        Args:
            enterprises_data: 企业数据列表
            policies_data: 政策数据列表
            audit_results: 预审结果二维列表
            
        Returns:
            统计摘要字典
        """
        try:
            # 过滤出企业政策
            enterprise_policies = [policy for policy in policies_data if self.is_enterprise_policy(policy)]
            
            summary = {
                "总企业数": len(enterprises_data),
                "总政策数": len(policies_data),
                "企业政策数": len(enterprise_policies),
                "总审核数": len(enterprises_data) * len(enterprise_policies),
                "总通过数": sum(sum(enterprise_results) for enterprise_results in audit_results),
                "总通过率": 0.0,
                "企业通过统计": [],
                "政策通过统计": []
            }
            
            # 计算总通过率
            if summary["总审核数"] > 0:
                summary["总通过率"] = round(summary["总通过数"] / summary["总审核数"], 3)
            
            # 统计每个企业的通过情况
            for i, enterprise_data in enumerate(enterprises_data):
                enterprise_id = enterprise_data.get("企业ID", f"Enterprise_{i}")
                enterprise_passed = sum(audit_results[i]) if i < len(audit_results) else 0
                enterprise_pass_rate = round(enterprise_passed / len(enterprise_policies), 3) if len(enterprise_policies) > 0 else 0.0
                
                summary["企业通过统计"].append({
                    "企业ID": enterprise_id,
                    "企业名称": enterprise_data.get("企业名称", ""),
                    "注册地": enterprise_data.get("注册地", ""),
                    "行业": enterprise_data.get("行业", ""),
                    "通过数": enterprise_passed,
                    "通过率": enterprise_pass_rate
                })
            
            # 统计每个企业政策的通过情况
            for j, policy_data in enumerate(enterprise_policies):
                policy_id = policy_data.get("政策编号", f"Policy_{j}")
                policy_passed = sum(audit_results[i][j] for i in range(len(audit_results)) if j < len(audit_results[i]))
                policy_pass_rate = round(policy_passed / len(enterprises_data), 3) if len(enterprises_data) > 0 else 0.0
                
                summary["政策通过统计"].append({
                    "政策编号": policy_id,
                    "政策名称": policy_data.get("政策名称", policy_data.get("标题", "")),
                    "政策类型": policy_data.get("政策类型", policy_data.get("类型", "")),
                    "适用对象": policy_data.get("适用对象", ""),
                    "通过数": policy_passed,
                    "通过率": policy_pass_rate
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成企业审核摘要异常: {e}")
            return {"错误": str(e)}


# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建企业预审引擎
    audit_engine = EnterprisePreAuditEngine()