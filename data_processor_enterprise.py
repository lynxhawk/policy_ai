"""
企业数据处理工具类
提供企业数据转换、规范化、验证等通用功能
增加了条件检查和规则评估功能，支持预审验证
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from fastapi import Request


class DataProcessor:
    """企业数据处理工具类"""

    def __init__(self):
        """初始化数据处理器"""
        self.logger = logging.getLogger(self.__class__.__name__)

        # 企业相关字段
        self.enterprise_boolean_fields = [
            '高新技术企业', '是否上市', '国有企业', '民营企业', '外资企业', '科技型企业', '制造业企业', '服务业企业']

        # 企业规模映射表
        self.enterprise_scale_mapping = {
            "大型": "大型",
            "中型": "中型",
            "小型": "小型",
            "微型": "微型",
            "large": "大型",
            "medium": "中型",
            "small": "小型",
            "micro": "微型"
        }

        # 企业性质映射表
        self.enterprise_nature_mapping = {
            "国有企业": "国有企业",
            "民营企业": "民营企业",
            "外资企业": "外资企业",
            "合资企业": "合资企业",
            "集体企业": "集体企业",
            "state": "国有企业",
            "private": "民营企业",
            "foreign": "外资企业",
            "joint": "合资企业",
            "collective": "集体企业"
        }

        # 布尔值映射表
        self.yes_values = ["是", "yes", "true", "1", "有", "对", "是的", "对的"]
        self.no_values = ["否", "no", "false", "0", "无", "不是", "没有", "不对"]

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
        简单的数字提取方法，支持带单位的字符串如"100万元"、"500人"等

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

            # 处理单位换算
            multiplier = 1
            if '万' in str_value:
                multiplier = 10000
                str_value = str_value.replace('万', '')
            elif '千' in str_value:
                multiplier = 1000
                str_value = str_value.replace('千', '')
            elif '亿' in str_value:
                multiplier = 100000000
                str_value = str_value.replace('亿', '')

            # 提取数字部分
            numbers = re.findall(r'-?\d+\.?\d*', str_value)

            if numbers:
                return float(numbers[0]) * multiplier

            return None

        except (ValueError, TypeError) as e:
            self.logger.warning(f"数字提取失败: {value}, 错误: {e}")
            return None

    def normalize_enterprise_scale(self, value: Any) -> str:
        """
        规范化企业规模

        Args:
            value: 原始企业规模值

        Returns:
            规范化后的企业规模
        """
        try:
            if value is None:
                return None

            # 处理枚举或对象
            if hasattr(value, 'value'):
                value = value.value

            # 转换为字符串并查找映射
            value_str = str(value).strip()
            return self.enterprise_scale_mapping.get(value_str, str(value))

        except Exception as e:
            self.logger.warning(f"规范化企业规模失败: {value}, 错误: {e}")
            return str(value) if value is not None else None

    def normalize_enterprise_nature(self, value: Any) -> str:
        """
        规范化企业性质

        Args:
            value: 原始企业性质值

        Returns:
            规范化后的企业性质
        """
        try:
            if value is None:
                return None

            # 处理枚举或对象
            if hasattr(value, 'value'):
                value = value.value

            # 转换为字符串并查找映射
            value_str = str(value).strip()
            return self.enterprise_nature_mapping.get(value_str, str(value))

        except Exception as e:
            self.logger.warning(f"规范化企业性质失败: {value}, 错误: {e}")
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
                num_val = float(value)
                if min_val is not None and max_val is not None:
                    if min_val <= num_val <= max_val:
                        return num_val
                    else:
                        return value
                return num_val

            # 字符串处理 - 提取数字
            extracted_num = self.extract_numeric_value_simple(value)
            if extracted_num is not None:
                if min_val is not None and max_val is not None:
                    if min_val <= extracted_num <= max_val:
                        return extracted_num
                    else:
                        return value
                return extracted_num
            else:
                return value

        except Exception as e:
            self.logger.warning(f"提取数字失败: {value}, 错误: {e}")
            return value

    def normalize_enterprise_data(self, enterprise_dict: Dict) -> Dict:
        """
        规范化企业数据

        Args:
            enterprise_dict: 原始企业数据字典

        Returns:
            规范化后的企业数据字典
        """
        normalized = {}

        for key, value in enterprise_dict.items():
            try:
                # 企业规模字段
                if key == '企业规模':
                    normalized[key] = self.normalize_enterprise_scale(value)

                # 企业性质字段
                elif key == '企业性质':
                    normalized[key] = self.normalize_enterprise_nature(value)

                # 企业布尔字段
                elif key in self.enterprise_boolean_fields:
                    normalized[key] = self.normalize_boolean_field(value)

                # 成立时间字段
                elif key == '成立时间':
                    normalized[key] = self.extract_numeric_value(
                        value, 1900, 2030)

                # 注册资本字段（提取数字，支持万元、千万等单位）
                elif key == '注册资本':
                    normalized[key] = self.extract_numeric_value_simple(value)

                # 员工数量字段
                elif key == '员工数量':
                    normalized[key] = self.extract_numeric_value(
                        value, 0, 1000000)

                # 年营业额字段
                elif key == '年营业额':
                    normalized[key] = self.extract_numeric_value_simple(value)

                # 纳税额字段
                elif key == '年纳税额':
                    normalized[key] = self.extract_numeric_value_simple(value)

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

    def process_enterprise_data(self, raw_enterprise_data: Any) -> Dict:
        """
        处理企业数据的完整流程

        Args:
            raw_enterprise_data: 原始企业数据

        Returns:
            处理后的企业数据字典
        """
        try:
            # 转换为字典
            enterprise_dict = self.safe_convert_to_dict(raw_enterprise_data)

            if not enterprise_dict:
                return {}

            # 规范化数据
            normalized_dict = self.normalize_enterprise_data(enterprise_dict)

            return normalized_dict

        except Exception as e:
            self.logger.error(f"处理企业数据失败: {e}")
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

    def validate_match_input(self, enterprise_data: Dict, policy_data: Dict) -> bool:
        """
        验证匹配输入数据的有效性
        
        Args:
            enterprise_data: 企业数据
            policy_data: 政策数据
            
        Returns:
            是否有效
        """
        try:
            # 检查企业数据
            if not isinstance(enterprise_data, dict) or not enterprise_data:
                self.logger.debug("企业数据无效或为空")
                return False
            
            # 检查政策数据
            if not isinstance(policy_data, dict) or not policy_data:
                self.logger.debug("政策数据无效或为空")
                return False
            
            # 添加政策类型验证
            policy_type = policy_data.get("适用对象", "") or policy_data.get("类型", "")
            if policy_type and policy_type != "企业":
                self.logger.debug(f"政策类型不匹配: {policy_type}, 需要: 企业")
                return False

            return True
            
        except Exception as e:
            self.logger.warning(f"验证输入数据失败: {e}")
            return False


    def validate_audit_input(self, enterprise_data: Dict, policy_data: Dict) -> bool:
        """
        验证预审输入数据的有效性

        Args:
            enterprise_data: 企业数据
            policy_data: 政策数据

        Returns:
            是否有效
        """
        try:
            # 检查企业数据
            if not isinstance(enterprise_data, dict) or not enterprise_data:
                self.logger.debug("预审：企业数据无效或为空")
                return False

            # 检查政策数据
            if not isinstance(policy_data, dict) or not policy_data:
                self.logger.debug("预审：政策数据无效或为空")
                return False

            # 预审可能需要额外的验证逻辑
            # 例如：检查是否包含必要的预审字段
            if "条件" not in policy_data:
                self.logger.debug("预审：政策数据缺少条件字段")
                return False

            # 检查企业是否有基本的识别信息
            if "企业ID" not in enterprise_data and "企业名称" not in enterprise_data:
                self.logger.debug("预审：企业数据缺少基本识别信息")
                return False

            # 添加政策类型验证
            policy_type = policy_data.get("适用对象", "") or policy_data.get("类型", "")
            if policy_type and policy_type != "企业":
                self.logger.debug(f"预审：政策类型不匹配: {policy_type}, 需要: 企业")
                return False

            return True

        except Exception as e:
            self.logger.warning(f"验证预审输入数据失败: {e}")
            return False

    def create_match_summary(self, results: List[int], policies_data: List[Dict],
                             enterprise_data: Dict = None) -> Dict:
        """
        创建匹配结果摘要

        Args:
            results: 匹配结果列表
            policies_data: 政策数据列表
            enterprise_data: 企业数据（可选）

        Returns:
            匹配摘要字典
        """
        try:
            total_policies = len(policies_data)
            matched_policies = sum(results)
            match_rate = round(matched_policies / total_policies,
                               3) if total_policies > 0 else 0.0

            summary = {
                "total_policies": total_policies,
                "matched_policies": matched_policies,
                "match_rate": match_rate,
                "results": results
            }

            # 如果提供了企业数据，添加企业ID
            if enterprise_data and isinstance(enterprise_data, dict):
                enterprise_id = enterprise_data.get("企业ID")
                if enterprise_id:
                    summary["enterprise_id"] = str(enterprise_id)

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

    # ============= 新增的条件检查和规则评估功能 =============

    def check_condition(self, enterprise_value: Any, operator: str, condition_value: Any) -> bool:
        """
        检查单个条件是否匹配，增强类型安全性

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
                    enterprise_val = self.extract_numeric_value_simple(
                        enterprise_value)
                    min_val = self.extract_numeric_value_simple(
                        condition_value[0])
                    max_val = self.extract_numeric_value_simple(
                        condition_value[1])

                    if enterprise_val is None or min_val is None or max_val is None:
                        self.logger.warning(
                            f"between操作符类型转换失败: enterprise={enterprise_value}, range={condition_value}")
                        return False

                    return min_val <= enterprise_val <= max_val
                else:
                    self.logger.warning(
                        f"between操作符条件值格式错误: {condition_value}")
                    return False

            # 数字比较操作符
            elif operator in ['>', '<', '>=', '<=']:
                enterprise_val = self.extract_numeric_value_simple(
                    enterprise_value)
                condition_val = self.extract_numeric_value_simple(
                    condition_value)

                if enterprise_val is None or condition_val is None:
                    self.logger.warning(
                        f"数字比较类型转换失败: enterprise={enterprise_value}, condition={condition_value}")
                    return False

                if operator == '>':
                    return enterprise_val > condition_val
                elif operator == '<':
                    return enterprise_val < condition_val
                elif operator == '>=':
                    return enterprise_val >= condition_val
                elif operator == '<=':
                    return enterprise_val <= condition_val

            # 字符串比较
            elif operator == '=':
                # 安全的字符串转换
                enterprise_str = self.safe_type_conversion(
                    enterprise_value, "str")
                condition_str = self.safe_type_conversion(
                    condition_value, "str")

                if enterprise_str is None or condition_str is None:
                    self.logger.warning(
                        f"字符串比较转换失败: enterprise={enterprise_value}, condition={condition_value}")
                    return False

                return enterprise_str == condition_str

            elif operator == '!=':
                # 安全的字符串转换
                enterprise_str = self.safe_type_conversion(
                    enterprise_value, "str")
                condition_str = self.safe_type_conversion(
                    condition_value, "str")

                if enterprise_str is None or condition_str is None:
                    self.logger.warning(
                        f"字符串比较转换失败: enterprise={enterprise_value}, condition={condition_value}")
                    return False

                return enterprise_str != condition_str

            # in 操作符（包含）
            elif operator == 'in':
                enterprise_str = self.safe_type_conversion(
                    enterprise_value, "str")
                condition_str = self.safe_type_conversion(
                    condition_value, "str")

                if enterprise_str is None or condition_str is None:
                    return False

                return enterprise_str in condition_str

            # contains 操作符（包含）
            elif operator == 'contains':
                enterprise_str = self.safe_type_conversion(
                    enterprise_value, "str")
                condition_str = self.safe_type_conversion(
                    condition_value, "str")

                if enterprise_str is None or condition_str is None:
                    return False

                return condition_str in enterprise_str

            else:
                self.logger.warning(f"不支持的操作符: {operator}")
                return False

        except Exception as e:
            self.logger.error(
                f"条件检查异常: enterprise={enterprise_value}, operator={operator}, condition={condition_value}, 错误: {e}")
            return False

    def evaluate_rule_node(self, rule_node: Dict, enterprise_data: Dict) -> bool:
        """
        递归评估规则节点，支持复杂的逻辑运算

        Args:
            rule_node: 规则节点
            enterprise_data: 企业数据

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

                if field not in enterprise_data:
                    self.logger.debug(f"企业数据中缺少字段: {field}")
                    return False

                enterprise_value = enterprise_data[field]
                result = self.check_condition(
                    enterprise_value, operator, value)

                self.logger.info(
                    f"条件评估: {field}({enterprise_value}) {operator} {value} = {result}")
                return result

            # 如果是容器节点，处理逻辑运算
            elif "规则" in rule_node:
                rules = rule_node["规则"]
                logic_operator = rule_node.get(
                    "逻辑", "and").lower()  # 默认为and，并转换为小写

                self.logger.info(
                    f"逻辑运算节点: {logic_operator}, 规则数量: {len(rules) if isinstance(rules, list) else 0}")

                if not isinstance(rules, list) or len(rules) == 0:
                    self.logger.warning(f"规则列表为空或格式错误: {rules}")
                    return False

                # 递归评估所有子规则
                results = []
                for i, sub_rule in enumerate(rules):
                    sub_result = self.evaluate_rule_node(
                        sub_rule, enterprise_data)
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

                self.logger.info(
                    f"逻辑运算 {logic_operator.upper()}: {results} = {final_result}")
                return final_result

            else:
                self.logger.warning(f"规则节点格式错误，既不是条件节点也不是逻辑节点: {rule_node}")
                return False

        except Exception as e:
            self.logger.error(f"评估规则节点异常: {rule_node}, 错误: {e}")
            return False
