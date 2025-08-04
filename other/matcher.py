import os
import json
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import jieba

@dataclass
class PolicyRule:
    """政策规则"""
    field: str          # 字段名
    operator: str       # 操作符
    value: Any         # 规则值
    description: str   # 描述
    confidence: float  # 置信度

@dataclass
class PolicyBenefit:
    """政策福利"""
    benefit_type: str   # 福利类型
    amount: str        # 金额
    duration: str      # 期限
    description: str   # 描述

@dataclass
class MatchResult:
    """匹配结果"""
    policy_id: str
    policy_title: str
    match_score: float
    is_eligible: bool
    matched_rules: List[Dict]
    unmatched_rules: List[Dict]
    benefits: List[PolicyBenefit]
    recommendations: List[str]

class PolicyDatasetMatcher:
    """政策数据集匹配系统"""
    
    def __init__(self, policy_dir="policy_dataset", user_dir="user_dataset"):
        self.policy_dir = policy_dir
        self.user_dir = user_dir
        self._init_jieba()
        self._init_patterns()
        
    def _init_jieba(self):
        """初始化jieba分词"""
        custom_words = [
            '高校毕业生', '就业困难人员', '灵活就业', '创业担保贷款',
            '社保补贴', '人才码', '被征地人员', '职业培训', '见习补贴',
            '平湖市', '嘉兴市', '法定退休年龄', '小微企业'
        ]
        for word in custom_words:
            jieba.add_word(word, 10)
    
    def _init_patterns(self):
        """初始化提取模式"""
        # 规则提取模式
        self.rule_patterns = {
            'age': [
                (r'(\d+)周岁以上', 'age', '>='),
                (r'(\d+)岁以上', 'age', '>='),
                (r'年满(\d+)周岁', 'age', '>='),
                (r'距离法定退休年龄不足(\d+)年', 'retirement_years_left', '<')
            ],
            'education': [
                ('博士', 'education', '>='), ('硕士', 'education', '>='),
                ('本科', 'education', '>='), ('专科', 'education', '>='),
                ('高中', 'education', '>='), ('初中', 'education', '>=')
            ],
            'work_experience': [
                (r'工作年限(\d+)年以上', 'work_years', '>='),
                (r'从业(\d+)年以上', 'work_years', '>='),
                (r'正常经营满(\d+)个月', 'work_months', '>='),
                (r'缴费(\d+)年以上', 'insurance_years', '>=')
            ],
            'graduation': [
                (r'毕业(\d+)年[以内下]', 'graduation_years', '<='),
                ('毕业学年', 'graduation_status', '=='),
                ('应届毕业生', 'graduation_status', '==')
            ],
            'talent_code': [
                (r'([A-G])类.*?人才码', 'talent_code', '>='),
                (r'人才码.*?([A-G])类', 'talent_code', '>=')
            ],
            'employment_status': [
                ('就业困难人员', 'employment_status', '=='),
                ('灵活就业', 'employment_type', '=='),
                ('失业人员', 'employment_status', '=='),
                ('登记失业', 'employment_status', '=='),
                ('初次创业', 'employment_type', '==')
            ],
            'location': [
                ('平湖市', 'location', 'in'),
                ('本市', 'location', 'in'),
                ('市域内', 'location', 'in'),
                ('嘉兴市', 'location', 'in')
            ],
            'company_type': [
                ('小微企业', 'company_type', '=='),
                ('中小微企业', 'company_type', '=='),
                ('事业单位', 'company_type', '=='),
                ('民办非企业', 'company_type', '==')
            ],
            'social_insurance': [
                ('依法缴纳社会保险', 'social_insurance', '=='),
                ('缴纳社会保险费', 'social_insurance', '=='),
                ('参加社会保险', 'social_insurance', '=='),
                ('首次缴纳社保', 'social_insurance', '==')
            ]
        }
        
        # 福利提取模式
        self.benefit_patterns = {
            'amount': [
                r'每人每月(\d+)元',
                r'每年(\d+)元',
                r'一次性.*?(\d+)元',
                r'不超过(\d+)元',
                r'最高(\d+)万?元',
                r'(\d+)%.*?补贴'
            ],
            'duration': [
                r'不超过(\d+)年',
                r'期限.*?(\d+)年',
                r'(\d+)个月',
                r'至退休',
                r'一次性'
            ]
        }
        
        # 学历等级
        self.education_levels = {
            '小学': 1, '初中': 2, '高中': 3, '中专': 3,
            '专科': 4, '本科': 5, '硕士': 6, '博士': 7
        }
        
        # 人才码等级
        self.talent_code_levels = {
            'G': 1, 'F': 2, 'E': 3, 'D': 4, 'C': 5, 'B': 6, 'A': 7
        }
    
    def load_policies(self) -> List[Dict]:
        """加载所有政策数据"""
        policies = []
        if not os.path.exists(self.policy_dir):
            print(f"❌ 政策目录不存在: {self.policy_dir}")
            return policies
        
        json_files = [f for f in os.listdir(self.policy_dir) if f.endswith('.json')]
        print(f"📁 找到 {len(json_files)} 个政策文件")
        
        for filename in sorted(json_files):
            file_path = os.path.join(self.policy_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    policy_data = json.load(f)
                    policies.append(policy_data)
                    print(f"✅ 加载政策: {policy_data.get('政策编号', filename)}")
            except Exception as e:
                print(f"❌ 加载失败 {filename}: {e}")
        
        return policies
    
    def load_users(self) -> List[Dict]:
        """加载所有用户数据"""
        users = []
        if not os.path.exists(self.user_dir):
            print(f"❌ 用户目录不存在: {self.user_dir}")
            return users
        
        json_files = [f for f in os.listdir(self.user_dir) if f.endswith('.json')]
        print(f"📁 找到 {len(json_files)} 个用户文件")
        
        for filename in sorted(json_files):
            file_path = os.path.join(self.user_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    
                    # 检查数据格式
                    if isinstance(user_data, dict):
                        users.append(user_data)
                        print(f"✅ 加载用户: {user_data.get('用户ID', filename)}")
                    elif isinstance(user_data, list):
                        # 如果是数组，跳过或处理
                        print(f"⚠️ 跳过数组格式文件: {filename}")
                        continue
                    else:
                        print(f"⚠️ 跳过未知格式文件: {filename}")
                        continue
                        
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败 {filename}: {e}")
            except Exception as e:
                print(f"❌ 加载失败 {filename}: {e}")
        
        return users
    
    def extract_policy_rules(self, policy_content) -> List[PolicyRule]:
        """提取政策规则（支持字符串和数组格式）"""
        
        # 处理不同格式的内容
        if isinstance(policy_content, list):
            # 数组格式，合并为字符串进行规则提取
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            # 字符串格式，直接使用
            content_text = policy_content
        else:
            print(f"⚠️ 未知的内容格式: {type(policy_content)}")
            return []
        
        rules = []
        
        for category, patterns in self.rule_patterns.items():
            for pattern_info in patterns:
                if len(pattern_info) == 3:
                    pattern, field, operator = pattern_info
                    
                    # 处理正则表达式模式
                    if isinstance(pattern, str) and pattern.startswith('r\'') and pattern.endswith('\''):
                        # 正则表达式字符串
                        regex_pattern = pattern[2:-1]  # 去掉 r' 和 '
                        matches = re.finditer(regex_pattern, content_text)
                        for match in matches:
                            try:
                                if field == 'retirement_years_left':
                                    value = int(match.group(1))
                                elif field in ['age', 'work_years', 'work_months', 'insurance_years', 'graduation_years']:
                                    value = int(match.group(1))
                                elif field == 'talent_code':
                                    value = match.group(1)
                                else:
                                    value = match.group(1)
                                
                                rule = PolicyRule(
                                    field=field,
                                    operator=operator,
                                    value=value,
                                    description=self._generate_rule_description(field, operator, value),
                                    confidence=0.9
                                )
                                rules.append(rule)
                            except (ValueError, IndexError):
                                continue
                    
                    elif pattern.startswith('r'):
                        # 处理正则表达式（去掉r前缀）
                        regex_pattern = pattern[1:]
                        try:
                            matches = re.finditer(regex_pattern, content_text)
                            for match in matches:
                                try:
                                    if field == 'retirement_years_left':
                                        value = int(match.group(1))
                                    elif field in ['age', 'work_years', 'work_months', 'insurance_years', 'graduation_years']:
                                        value = int(match.group(1))
                                    elif field == 'talent_code':
                                        value = match.group(1)
                                    else:
                                        value = match.group(1)
                                    
                                    rule = PolicyRule(
                                        field=field,
                                        operator=operator,
                                        value=value,
                                        description=self._generate_rule_description(field, operator, value),
                                        confidence=0.9
                                    )
                                    rules.append(rule)
                                except (ValueError, IndexError):
                                    continue
                        except re.error:
                            # 如果正则表达式有问题，按关键词处理
                            if pattern in content_text:
                                rule = PolicyRule(
                                    field=field,
                                    operator=operator,
                                    value=pattern,
                                    description=self._generate_rule_description(field, operator, pattern),
                                    confidence=0.7
                                )
                                rules.append(rule)
                    else:
                        # 关键词匹配
                        if pattern in content_text:
                            if field == 'education':
                                value = pattern
                            elif field == 'graduation_status':
                                value = '应届'
                            elif field == 'employment_status':
                                if pattern == '就业困难人员':
                                    value = '就业困难'
                                elif pattern in ['失业人员', '登记失业']:
                                    value = '失业'
                                else:
                                    value = pattern
                            elif field == 'employment_type':
                                if pattern == '灵活就业':
                                    value = '灵活就业'
                                elif pattern == '初次创业':
                                    value = '初次创业'
                                else:
                                    value = pattern
                            elif field in ['location', 'company_type']:
                                value = pattern
                            elif field == 'social_insurance':
                                value = 'required'
                            else:
                                value = pattern
                            
                            rule = PolicyRule(
                                field=field,
                                operator=operator,
                                value=value,
                                description=self._generate_rule_description(field, operator, value),
                                confidence=0.8
                            )
                            rules.append(rule)
        
        return rules
    
    def extract_policy_benefits(self, policy_content) -> List[PolicyBenefit]:
        """提取政策福利（支持字符串和数组格式）"""
        
        # 处理不同格式的内容
        if isinstance(policy_content, list):
            # 数组格式，合并为字符串进行福利提取
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            # 字符串格式，直接使用
            content_text = policy_content
        else:
            print(f"⚠️ 未知的内容格式: {type(policy_content)}")
            return []
        
        benefits = []
        
        # 确定福利类型
        benefit_type = '补贴'
        if '社保' in content_text:
            benefit_type = '社保补贴'
        elif '培训' in content_text:
            benefit_type = '培训补贴'
        elif '就业' in content_text:
            benefit_type = '就业补贴'
        elif '创业' in content_text:
            benefit_type = '创业补贴'
        elif '租房' in content_text or '住房' in content_text:
            benefit_type = '租房补贴'
        elif '贷款' in content_text:
            benefit_type = '创业贷款'
        elif '生活' in content_text:
            benefit_type = '生活补助'
        
        # 提取金额
        amount = '详见政策'
        for pattern in self.benefit_patterns['amount']:
            match = re.search(pattern, content_text)
            if match:
                amount = match.group(1)
                if '万' in match.group(0):
                    amount += '万元'
                elif '%' in match.group(0):
                    amount += '%'
                else:
                    amount += '元'
                break
        
        # 提取期限
        duration = '详见政策'
        for pattern in self.benefit_patterns['duration']:
            match = re.search(pattern, content_text)
            if match:
                duration = match.group(0)
                break
        
        if amount != '详见政策' or duration != '详见政策' or benefit_type != '补贴':
            benefit = PolicyBenefit(
                benefit_type=benefit_type,
                amount=amount,
                duration=duration,
                description=f"{benefit_type}: {amount}, {duration}"
            )
            benefits.append(benefit)
        
        return benefits
    
    def match_user_to_policy(self, user_info: Dict, policy_data: Dict) -> MatchResult:
        """匹配用户与单个政策（支持数组格式内容）"""
        policy_content = policy_data.get('内容', '')
        
        # 提取政策规则和福利
        rules = self.extract_policy_rules(policy_content)
        benefits = self.extract_policy_benefits(policy_content)
        
        # 匹配规则
        matched_rules = []
        unmatched_rules = []
        recommendations = []
        
        for rule in rules:
            is_match, person_value, gap = self._check_rule(user_info, rule)
            
            if is_match:
                matched_rules.append({
                    'rule': asdict(rule),
                    'person_value': person_value,
                    'status': '满足'
                })
            else:
                unmatched_rules.append({
                    'rule': asdict(rule),
                    'person_value': person_value,
                    'status': '不满足',
                    'gap': gap
                })
                
                # 生成建议
                recommendation = self._generate_recommendation(rule, gap)
                if recommendation:
                    recommendations.append(recommendation)
        
        # 计算匹配分数
        total_rules = len(rules)
        match_score = len(matched_rules) / total_rules if total_rules > 0 else 0.8
        is_eligible = match_score >= 0.8
        
        return MatchResult(
            policy_id=policy_data.get('政策编号', ''),
            policy_title=policy_data.get('标题', ''),
            match_score=match_score,
            is_eligible=is_eligible,
            matched_rules=matched_rules,
            unmatched_rules=unmatched_rules,
            benefits=benefits,
            recommendations=recommendations
        )
    
    def match_user_to_all_policies(self, user_info: Dict, policies: List[Dict]) -> List[MatchResult]:
        """匹配用户与所有政策"""
        results = []
        
        for policy_data in policies:
            result = self.match_user_to_policy(user_info, policy_data)
            results.append(result)
        
        # 按匹配度排序
        results.sort(key=lambda x: x.match_score, reverse=True)
        
        return results
    
    def _check_rule(self, user_info: Dict, rule: PolicyRule) -> Tuple[bool, Any, str]:
        """检查单个规则"""
        field = rule.field
        operator = rule.operator
        rule_value = rule.value
        
        try:
            person_value = self._get_user_field_value(user_info, field)
            
            if person_value is None:
                return False, "未提供", f"缺少{field}信息"
            
            is_match = self._compare_values(person_value, operator, rule_value, field)
            
            if is_match:
                return True, person_value, None
            else:
                gap = self._calculate_gap(person_value, operator, rule_value, field)
                return False, person_value, gap
                
        except Exception as e:
            return False, "检查失败", str(e)
    
    def _get_user_field_value(self, user_info: Dict, field: str):
        """获取用户字段值"""
        field_mapping = {
            'age': '年龄',
            'education': '最高学历',
            'work_years': '工作年限',
            'talent_code': '人才码等级',
            'location': '籍贯',
            'employment_status': '就业状态',
            'graduation_years': '毕业年份',
            'company_type': '企业类型'
        }
        
        if field == 'retirement_years_left':
            age = user_info.get('年龄')
            if age:
                return max(0, 60 - age)  # 假设60岁退休
            return None
        
        if field == 'graduation_years':
            grad_year = user_info.get('毕业年份')
            if grad_year:
                from datetime import datetime
                return datetime.now().year - grad_year
            return None
        
        chinese_field = field_mapping.get(field, field)
        return user_info.get(chinese_field)
    
    def _compare_values(self, person_value, operator: str, rule_value, field: str) -> bool:
        """比较值"""
        try:
            if field == 'education':
                return self._compare_education(person_value, rule_value, operator)
            elif field == 'talent_code':
                return self._compare_talent_code(person_value, rule_value, operator)
            elif field == 'location':
                return rule_value in str(person_value)
            elif operator == '>=':
                return person_value >= rule_value
            elif operator == '<=':
                return person_value <= rule_value
            elif operator == '<':
                return person_value < rule_value
            elif operator == '>':
                return person_value > rule_value
            elif operator == '==':
                return str(person_value) == str(rule_value)
            elif operator == 'in':
                return rule_value in str(person_value)
            
            return False
        except:
            return False
    
    def _compare_education(self, person_edu: str, required_edu: str, operator: str) -> bool:
        """比较学历"""
        person_level = self.education_levels.get(person_edu, 0)
        required_level = self.education_levels.get(required_edu, 0)
        
        if operator == '>=':
            return person_level >= required_level
        elif operator == '==':
            return person_level == required_level
        return False
    
    def _compare_talent_code(self, person_code: str, required_code: str, operator: str) -> bool:
        """比较人才码"""
        person_level = self.talent_code_levels.get(person_code, 0)
        required_level = self.talent_code_levels.get(required_code, 0)
        
        if operator == '>=':
            return person_level >= required_level
        elif operator == '==':
            return person_level == required_level
        return False
    
    def _calculate_gap(self, person_value, operator: str, rule_value, field: str) -> str:
        """计算差距"""
        if field == 'age':
            if operator == '>=' and person_value < rule_value:
                return f"需要{rule_value}岁以上，当前{person_value}岁"
        elif field == 'work_years':
            if operator == '>=' and person_value < rule_value:
                return f"需要{rule_value}年工作经验，当前{person_value}年"
        elif field == 'education':
            return f"需要{rule_value}及以上学历，当前{person_value}"
        elif field == 'talent_code':
            return f"需要{rule_value}类及以上人才码，当前{person_value}类"
        
        return f"不满足条件：{rule_value}"
    
    def _generate_rule_description(self, field: str, operator: str, value: Any) -> str:
        """生成规则描述"""
        field_names = {
            'age': '年龄',
            'education': '学历',
            'work_years': '工作年限',
            'graduation_years': '毕业年限',
            'talent_code': '人才码',
            'location': '地域',
            'employment_status': '就业状态',
            'retirement_years_left': '距离退休年限'
        }
        
        operator_names = {
            '>=': '不少于',
            '<=': '不超过',
            '==': '为',
            'in': '包含',
            '<': '少于'
        }
        
        field_name = field_names.get(field, field)
        operator_name = operator_names.get(operator, operator)
        
        return f"{field_name}{operator_name}{value}"
    
    def _generate_recommendation(self, rule: PolicyRule, gap: str) -> str:
        """生成改进建议"""
        field = rule.field
        
        if field == 'education':
            return f"建议提升学历至{rule.value}及以上"
        elif field == 'work_years':
            return f"建议积累工作经验至{rule.value}年以上"
        elif field == 'talent_code':
            return f"建议申请{rule.value}类及以上人才码认定"
        elif field == 'age':
            return "等待满足年龄要求"
        elif field == 'location':
            return f"该政策仅适用于{rule.value}地区"
        
        return f"请满足条件：{rule.description}"
    
    def generate_user_match_report(self, user_info: Dict, match_results: List[MatchResult]) -> str:
        """生成用户匹配报告（精简版）"""
        report = []
        user_id = user_info.get('用户ID', '未知')
        
        report.append(f"用户ID: {user_id}")
        report.append(f"学历: {user_info.get('最高学历', '未知')}")
        report.append(f"工作年限: {user_info.get('工作年限', '未知')}年")
        report.append(f"籍贯: {user_info.get('籍贯', '未知')}")
        report.append("-" * 50)
        
        # 匹配统计
        total_policies = len(match_results)
        eligible_policies = len([r for r in match_results if r.is_eligible])
        
        report.append(f"总政策数: {total_policies}")
        report.append(f"符合条件: {eligible_policies}")
        report.append(f"符合率: {eligible_policies/total_policies:.1%}")
        report.append("-" * 50)
        
        # 匹配结果
        for i, result in enumerate(match_results, 1):
            status = "✅" if result.is_eligible else "❌"
            report.append(f"{i}. {status} {result.policy_id} | 匹配度: {result.match_score:.1%}")
            report.append(f"   标题: {result.policy_title}")
            
            # 福利信息
            if result.benefits:
                benefit_info = " | ".join([f"{b.benefit_type}:{b.amount}" for b in result.benefits])
                report.append(f"   福利: {benefit_info}")
            
            # 满足条件数量
            matched_count = len(result.matched_rules)
            unmatched_count = len(result.unmatched_rules)
            report.append(f"   满足条件: {matched_count}项 | 不满足: {unmatched_count}项")
            
            # 关键不满足条件
            if result.unmatched_rules and not result.is_eligible:
                key_issues = [unmatch['gap'] for unmatch in result.unmatched_rules[:2]]
                report.append(f"   主要问题: {' | '.join(key_issues)}")
            
            report.append("")
        
        return "\n".join(report)

    def generate_policy_match_report(self, policy_data: Dict, all_users: List[Dict]) -> str:
        """生成政策匹配报告（针对所有用户）"""
        policy_id = policy_data.get('政策编号', '未知')
        policy_title = policy_data.get('标题', '未知')
        
        report = []
        report.append(f"政策编号: {policy_id}")
        report.append(f"政策标题: {policy_title}")
        report.append("-" * 50)
        
        # 提取政策规则和福利
        rules = self.extract_policy_rules(policy_data.get('内容', ''))
        benefits = self.extract_policy_benefits(policy_data.get('内容', ''))
        
        # 政策信息
        if rules:
            report.append("政策条件:")
            for rule in rules:
                report.append(f"  - {rule.description}")
        
        if benefits:
            report.append("政策福利:")
            for benefit in benefits:
                report.append(f"  - {benefit.description}")
        
        report.append("-" * 50)
        
        # 匹配统计
        user_results = []
        eligible_users = 0
        total_users = len(all_users)
        
        for user_info in all_users:
            result = self.match_user_to_policy(user_info, policy_data)
            user_results.append((user_info, result))
            if result.is_eligible:
                eligible_users += 1
        
        report.append(f"总用户数: {total_users}")
        report.append(f"符合条件用户: {eligible_users}")
        report.append(f"政策适用率: {eligible_users/total_users:.1%}")
        report.append("-" * 50)
        
        # 用户匹配详情
        report.append("用户匹配详情:")
        
        # 按匹配度排序
        user_results.sort(key=lambda x: x[1].match_score, reverse=True)
        
        for user_info, result in user_results:
            user_id = user_info.get('用户ID', '未知')
            status = "✅" if result.is_eligible else "❌"
            
            report.append(f"{status} {user_id} | 匹配度: {result.match_score:.1%}")
            
            # 用户基本信息
            user_details = []
            if '最高学历' in user_info:
                user_details.append(f"学历:{user_info['最高学历']}")
            if '工作年限' in user_info:
                user_details.append(f"工作年限:{user_info['工作年限']}年")
            if '籍贯' in user_info:
                user_details.append(f"籍贯:{user_info['籍贯']}")
            if '年龄' in user_info:
                user_details.append(f"年龄:{user_info['年龄']}岁")
            
            if user_details:
                report.append(f"   用户信息: {' | '.join(user_details)}")
            
            # 匹配情况
            matched_count = len(result.matched_rules)
            unmatched_count = len(result.unmatched_rules)
            report.append(f"   匹配情况: 满足{matched_count}项 | 不满足{unmatched_count}项")
            
            # 不满足的关键条件
            if result.unmatched_rules:
                key_issues = [unmatch['gap'] for unmatch in result.unmatched_rules[:2]]
                report.append(f"   主要问题: {' | '.join(key_issues)}")
            
            report.append("")
        
        return "\n".join(report)

    def save_all_reports(self, users: List[Dict], policies: List[Dict], output_dir: str = "match_reports"):
        """保存所有匹配报告"""
        import os
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        user_reports_dir = os.path.join(output_dir, "user_reports")
        policy_reports_dir = os.path.join(output_dir, "policy_reports")
        
        if not os.path.exists(user_reports_dir):
            os.makedirs(user_reports_dir)
        if not os.path.exists(policy_reports_dir):
            os.makedirs(policy_reports_dir)
        
        print(f"\n📁 创建报告目录: {output_dir}")
        
        # 生成用户匹配报告
        print("\n📝 生成用户匹配报告...")
        for user_info in users:
            user_id = user_info.get('用户ID', 'Unknown')
            print(f"  处理用户: {user_id}")
            
            # 匹配所有政策
            match_results = self.match_user_to_all_policies(user_info, policies)
            
            # 生成报告
            report = self.generate_user_match_report(user_info, match_results)
            
            # 保存文件
            filename = os.path.join(user_reports_dir, f"user_{user_id}_matches.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
        
        print(f"✅ 用户报告保存完成: {len(users)}个文件")
        
        # 生成政策匹配报告
        print("\n📝 生成政策匹配报告...")
        for policy_data in policies:
            policy_id = policy_data.get('政策编号', 'Unknown')
            print(f"  处理政策: {policy_id}")
            
            # 生成报告
            report = self.generate_policy_match_report(policy_data, users)
            
            # 保存文件
            filename = os.path.join(policy_reports_dir, f"policy_{policy_id}_matches.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
        
        print(f"✅ 政策报告保存完成: {len(policies)}个文件")
        
        # 生成汇总报告
        self._generate_summary_report(users, policies, output_dir)
    
    def _generate_summary_report(self, users: List[Dict], policies: List[Dict], output_dir: str):
        """生成汇总报告"""
        print("\n📊 生成汇总报告...")
        
        summary = []
        summary.append("政策匹配系统汇总报告")
        summary.append("=" * 60)
        summary.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"用户数量: {len(users)}")
        summary.append(f"政策数量: {len(policies)}")
        summary.append("")
        
        # 用户匹配统计
        summary.append("用户匹配统计:")
        summary.append("-" * 30)
        
        user_stats = []
        for user_info in users:
            user_id = user_info.get('用户ID', 'Unknown')
            match_results = self.match_user_to_all_policies(user_info, policies)
            eligible_count = len([r for r in match_results if r.is_eligible])
            match_rate = eligible_count / len(policies) if policies else 0
            
            user_stats.append({
                'user_id': user_id,
                'eligible_policies': eligible_count,
                'match_rate': match_rate
            })
            
            summary.append(f"{user_id}: 符合{eligible_count}个政策 (匹配率: {match_rate:.1%})")
        
        summary.append("")
        
        # 政策匹配统计
        summary.append("政策匹配统计:")
        summary.append("-" * 30)
        
        for policy_data in policies:
            policy_id = policy_data.get('政策编号', 'Unknown')
            eligible_users = 0
            
            for user_info in users:
                result = self.match_user_to_policy(user_info, policy_data)
                if result.is_eligible:
                    eligible_users += 1
            
            coverage_rate = eligible_users / len(users) if users else 0
            summary.append(f"{policy_id}: 适用于{eligible_users}个用户 (覆盖率: {coverage_rate:.1%})")
        
        summary.append("")
        
        # 整体统计
        total_matches = sum(len([r for r in self.match_user_to_all_policies(u, policies) if r.is_eligible]) for u in users)
        total_possible = len(users) * len(policies)
        overall_match_rate = total_matches / total_possible if total_possible > 0 else 0
        
        summary.append("整体统计:")
        summary.append("-" * 30)
        summary.append(f"总匹配数: {total_matches}")
        summary.append(f"总可能匹配数: {total_possible}")
        summary.append(f"整体匹配率: {overall_match_rate:.1%}")
        
        # 保存汇总报告
        summary_file = os.path.join(output_dir, "summary_report.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary))
        
        print(f"✅ 汇总报告保存完成: {summary_file}")

def main():
    """主函数"""
    from datetime import datetime
    
    print("🚀 政策数据集匹配系统启动")
    print("=" * 60)
    
    # 初始化匹配器
    matcher = PolicyDatasetMatcher()
    
    # 加载数据
    print("\n📁 加载数据...")
    policies = matcher.load_policies()
    users = matcher.load_users()
    
    if not policies:
        print("❌ 没有加载到政策数据")
        return
    
    if not users:
        print("❌ 没有加载到用户数据")
        return
    
    print(f"\n✅ 数据加载完成：{len(policies)}个政策，{len(users)}个用户")
    
    # 生成所有报告
    matcher.save_all_reports(users, policies)
    
    print("\n🎉 所有报告生成完成！")
    print("\n📂 报告文件结构：")
    print("match_reports/")
    print("├── user_reports/")
    print("│   ├── user_U001_matches.txt")
    print("│   ├── user_U002_matches.txt")
    print("│   └── ...")
    print("├── policy_reports/")
    print("│   ├── policy_POL0001_matches.txt")
    print("│   ├── policy_POL0002_matches.txt")
    print("│   └── ...")
    print("└── summary_report.txt")

def quick_test():
    """快速测试"""
    print("🧪 快速测试模式")
    print("=" * 40)
    
    matcher = PolicyDatasetMatcher()
    
    # 测试数据
    test_policies = [
        {
            "政策编号": "POL0001",
            "标题": "关于调整平湖市灵活就业人员社会保险补贴标准的通知",
            "内容": "就业困难人员实现灵活就业并依法缴纳社会保险费的，按当年最低社会保险缴费基数缴费额的50%给予社保补贴，期限不超过3年，其中对初次核定享受补贴政策时距离法定退休年龄不足5年的人员，延长至退休。"
        }
    ]
    
    test_users = [
        {
            "用户ID": "U001",
            "最高学历": "本科",
            "工作年限": 5,
            "籍贯": "平湖市",
            "年龄": 58,
            "就业状态": "就业困难"
        },
        {
            "用户ID": "U002", 
            "最高学历": "专科",
            "工作年限": 3,
            "籍贯": "北京市",
            "年龄": 25
        }
    ]
    
    # 生成测试报告
    matcher.save_all_reports(test_users, test_policies, "test_reports")
    
    print("\n✅ 测试报告生成完成，请查看 test_reports 目录")

if __name__ == "__main__":
    # 检查数据目录是否存在
    if os.path.exists("policy_dataset") and os.path.exists("user_dataset"):
        main()
    else:
        print("⚠️  数据目录不存在，运行测试模式")
        quick_test()

def test_single_match():
    """测试单个匹配"""
    print("🧪 单个匹配测试")
    print("=" * 40)
    
    matcher = PolicyDatasetMatcher()
    
    # 测试数据
    policy = {
        "政策编号": "POL0001",
        "标题": "关于调整平湖市灵活就业人员社会保险补贴标准的通知",
        "内容": "就业困难人员实现灵活就业并依法缴纳社会保险费的，按当年最低社会保险缴费基数缴费额（基本养老、基本医疗保险）的50%给予社保补贴，期限不超过3年，其中对初次核定享受补贴政策时距离法定退休年龄不足5年的人员，延长至退休。"
    }
    
    user = {
        "用户ID": "U001",
        "最高学历": "本科",
        "工作年限": 5,
        "籍贯": "平湖市",
        "年龄": 58,
        "就业状态": "就业困难"
    }
    
    result = matcher.match_user_to_policy(user, policy)
    
    print(f"政策：{result.policy_title}")
    print(f"匹配度：{result.match_score:.1%}")
    print(f"是否符合：{'是' if result.is_eligible else '否'}")
    
    if result.matched_rules:
        print("\n✅ 满足的条件：")
        for match in result.matched_rules:
            rule = match['rule']
            person_value = match['person_value']
            print(f"  ✓ {rule['description']} (当前值: {person_value})")
    
    if result.unmatched_rules:
        print("\n❌ 不满足的条件：")
        for unmatch in result.unmatched_rules:
            rule = unmatch['rule']
            gap = unmatch['gap']
            print(f"  ✗ {rule['description']} (差距: {gap})")

if __name__ == "__main__":
    # 检查数据目录是否存在
    if os.path.exists("policy_dataset") and os.path.exists("user_dataset"):
        main()
    else:
        print("⚠️  数据目录不存在，运行测试模式")
        test_single_match()
