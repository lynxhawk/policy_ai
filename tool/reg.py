import re
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import jieba
import jieba.posseg as pseg

@dataclass
class PolicyRule:
    """政策规则数据类"""
    rule_type: str      # 规则类型：条件、福利、限制等
    field: str          # 字段名：年龄、学历、工作年限等
    operator: str       # 操作符：>=、<=、==、in等
    value: Any         # 规则值
    description: str   # 规则描述
    confidence: float  # 提取置信度
    original_text: str # 原文片段

@dataclass
class PolicyBenefit:
    """政策福利数据类"""
    benefit_type: str   # 福利类型
    amount: str        # 金额
    duration: str      # 期限
    description: str   # 描述

@dataclass
class PolicyInfo:
    """完整政策信息"""
    policy_id: str
    title: str
    content: str
    rules: List[PolicyRule]
    benefits: List[PolicyBenefit]
    target_groups: List[str]
    policy_category: str
    effective_date: str

class SmartPolicyExtractor:
    """智能政策规则提取器"""
    
    def __init__(self):
        self._init_rule_patterns()
        self._init_jieba_dict()
        
    def _init_jieba_dict(self):
        """初始化jieba自定义词典"""
        custom_words = [
            ('高校毕业生', 10), ('就业困难人员', 10), ('灵活就业', 10),
            ('创业担保贷款', 10), ('社保补贴', 10), ('人才码', 10),
            ('被征地人员', 10), ('职业培训', 10), ('见习补贴', 10),
            ('平湖市', 10), ('嘉兴市', 10), ('法定退休年龄', 10)
        ]
        
        for word, freq in custom_words:
            jieba.add_word(word, freq)
    
    def _init_rule_patterns(self):
        """初始化规则提取模式"""
        self.rule_patterns = {
            # 年龄相关规则
            'age': {
                'patterns': [
                    r'(\d+)周岁以上',
                    r'(\d+)岁以上', 
                    r'年满(\d+)周岁',
                    r'距离法定退休年龄不足(\d+)年'
                ],
                'extractors': [
                    ('age', '>=', lambda m: int(m.group(1))),
                    ('age', '>=', lambda m: int(m.group(1))),
                    ('age', '>=', lambda m: int(m.group(1))),
                    ('retirement_years_left', '<', lambda m: int(m.group(1)))
                ]
            },
            
            # 学历相关规则
            'education': {
                'keywords': ['博士', '硕士', '本科', '专科', '高中', '初中'],
                'extractor': ('education', '>=', lambda text: self._extract_education_level(text))
            },
            
            # 毕业时间规则
            'graduation': {
                'patterns': [
                    r'毕业(\d+)年[以内下]',
                    r'毕业学年',
                    r'应届.*?毕业生'
                ],
                'extractors': [
                    ('graduation_years', '<=', lambda m: int(m.group(1))),
                    ('graduation_status', '==', lambda m: '应届'),
                    ('graduation_status', '==', lambda m: '应届')
                ]
            },
            
            # 工作年限规则
            'work_experience': {
                'patterns': [
                    r'工作年限(\d+)年以上',
                    r'从业(\d+)年以上',
                    r'正常经营满(\d+)个月',
                    r'缴费(\d+)年以上'
                ],
                'extractors': [
                    ('work_years', '>=', lambda m: int(m.group(1))),
                    ('work_years', '>=', lambda m: int(m.group(1))),
                    ('work_months', '>=', lambda m: int(m.group(1))),
                    ('insurance_years', '>=', lambda m: int(m.group(1)))
                ]
            },
            
            # 人才码规则
            'talent_code': {
                'patterns': [r'([A-G])类.*?人才码', r'人才码.*?([A-G])类'],
                'extractors': [
                    ('talent_code', '>=', lambda m: m.group(1)),
                    ('talent_code', '>=', lambda m: m.group(1))
                ]
            },
            
            # 地域规则
            'location': {
                'keywords': ['平湖市', '本市', '市域内', '嘉兴市'],
                'extractor': ('location', 'in', lambda text: text)
            },
            
            # 就业状态规则
            'employment_status': {
                'keywords': ['就业困难人员', '灵活就业', '失业人员', '登记失业', '初次创业'],
                'mapping': {
                    '就业困难人员': ('employment_status', '==', '就业困难'),
                    '灵活就业': ('employment_type', '==', '灵活就业'),
                    '失业人员': ('employment_status', '==', '失业'),
                    '登记失业': ('employment_status', '==', '登记失业'),
                    '初次创业': ('employment_type', '==', '初次创业')
                }
            },
            
            # 企业类型规则
            'company_type': {
                'keywords': ['小微企业', '中小微企业', '事业单位', '民办非企业'],
                'extractor': ('company_type', '==', lambda text: text)
            },
            
            # 社保缴纳规则
            'social_insurance': {
                'keywords': ['依法缴纳社会保险', '缴纳社会保险费', '参加社会保险', '首次缴纳社保'],
                'extractor': ('social_insurance', '==', lambda text: 'required')
            }
        }
        
        # 福利提取模式
        self.benefit_patterns = {
            'subsidy_amount': [
                r'每人每月(\d+)元',
                r'每年(\d+)元',
                r'一次性.*?(\d+)元',
                r'不超过(\d+)元',
                r'最高(\d+)万?元'
            ],
            'subsidy_percentage': [
                r'按.*?(\d+)%.*?给予',
                r'给予.*?(\d+)%'
            ],
            'duration': [
                r'不超过(\d+)年',
                r'期限.*?(\d+)年',
                r'(\d+)个月',
                r'至退休',
                r'一次性'
            ]
        }
    
    def extract_policy_rules(self, policy_data: Dict) -> PolicyInfo:
        """提取政策规则"""
        content = policy_data.get('内容', '')
        title = policy_data.get('标题', '')
        
        # 使用jieba分词
        words = list(jieba.cut(content))
        pos_tags = list(pseg.cut(content))
        
        # 提取规则
        rules = self._extract_all_rules(content, words, pos_tags)
        
        # 提取福利
        benefits = self._extract_benefits(content)
        
        # 提取目标人群
        target_groups = self._extract_target_groups(content, words)
        
        # 分类政策类型
        policy_category = self._classify_policy(title, content, words)
        
        # 提取生效日期
        effective_date = self._extract_effective_date(content)
        
        return PolicyInfo(
            policy_id=policy_data.get('政策编号', ''),
            title=title,
            content=content,
            rules=rules,
            benefits=benefits,
            target_groups=target_groups,
            policy_category=policy_category,
            effective_date=effective_date
        )
    
    def _extract_all_rules(self, content: str, words: List[str], pos_tags: List) -> List[PolicyRule]:
        """提取所有规则"""
        rules = []
        
        for rule_category, rule_config in self.rule_patterns.items():
            category_rules = self._extract_category_rules(content, rule_category, rule_config)
            rules.extend(category_rules)
        
        return rules
    
    def _extract_category_rules(self, content: str, category: str, config: Dict) -> List[PolicyRule]:
        """提取特定类别的规则"""
        rules = []
        
        if 'patterns' in config and 'extractors' in config:
            # 基于正则模式提取
            patterns = config['patterns']
            extractors = config['extractors']
            
            for pattern, extractor in zip(patterns, extractors):
                matches = re.finditer(pattern, content)
                for match in matches:
                    field, operator, value_func = extractor
                    try:
                        value = value_func(match)
                        rule = PolicyRule(
                            rule_type='condition',
                            field=field,
                            operator=operator,
                            value=value,
                            description=self._generate_rule_description(field, operator, value),
                            confidence=0.9,
                            original_text=match.group(0)
                        )
                        rules.append(rule)
                    except Exception as e:
                        continue
        
        elif 'pattern' in config and 'extractor' in config:
            # 单个模式提取
            pattern = config['pattern']
            extractor = config['extractor']
            field, operator, value_func = extractor
            
            matches = re.finditer(pattern, content)
            for match in matches:
                try:
                    value = value_func(match.group(0))
                    rule = PolicyRule(
                        rule_type='condition',
                        field=field,
                        operator=operator,
                        value=value,
                        description=self._generate_rule_description(field, operator, value),
                        confidence=0.85,
                        original_text=match.group(0)
                    )
                    rules.append(rule)
                except Exception as e:
                    continue
        
        elif 'keywords' in config:
            # 基于关键词提取
            keywords = config['keywords']
            
            if 'mapping' in config:
                # 有映射关系的关键词
                mapping = config['mapping']
                for keyword in keywords:
                    if keyword in content:
                        field, operator, value = mapping[keyword]
                        rule = PolicyRule(
                            rule_type='condition',
                            field=field,
                            operator=operator,
                            value=value,
                            description=f"{field}: {keyword}",
                            confidence=0.8,
                            original_text=keyword
                        )
                        rules.append(rule)
                        break  # 避免重复
            elif 'extractor' in config:
                # 简单关键词提取
                extractor = config['extractor']
                field, operator, value_func = extractor
                for keyword in keywords:
                    if keyword in content:
                        try:
                            value = value_func(keyword)
                            rule = PolicyRule(
                                rule_type='condition',
                                field=field,
                                operator=operator,
                                value=value,
                                description=f"{field}: {keyword}",
                                confidence=0.8,
                                original_text=keyword
                            )
                            rules.append(rule)
                            break  # 避免重复
                        except Exception as e:
                            continue
        
        return rules
    
    def _extract_education_level(self, text: str) -> str:
        """提取学历等级"""
        education_map = {
            '博士': '博士', '硕士': '硕士', '本科': '本科', 
            '专科': '专科', '高中': '高中', '初中': '初中'
        }
        
        for edu in education_map:
            if edu in text:
                return education_map[edu]
        return '未知'
    
    def _extract_benefits(self, content: str) -> List[PolicyBenefit]:
        """提取政策福利"""
        benefits = []
        
        # 社保补贴
        if '社保补贴' in content or '社会保险补贴' in content:
            benefit = self._extract_specific_benefit(content, '社保补贴')
            if benefit:
                benefits.append(benefit)
        
        # 培训补贴
        if '培训补贴' in content:
            benefit = self._extract_specific_benefit(content, '培训补贴')
            if benefit:
                benefits.append(benefit)
        
        # 就业补贴
        if '就业补贴' in content:
            benefit = self._extract_specific_benefit(content, '就业补贴')
            if benefit:
                benefits.append(benefit)
        
        # 创业补贴
        if '创业补贴' in content:
            benefit = self._extract_specific_benefit(content, '创业补贴')
            if benefit:
                benefits.append(benefit)
        
        # 租房补贴
        if '租房补贴' in content or '住房补贴' in content:
            benefit = self._extract_specific_benefit(content, '租房补贴')
            if benefit:
                benefits.append(benefit)
        
        # 创业担保贷款
        if '创业担保贷款' in content:
            benefit = self._extract_specific_benefit(content, '创业担保贷款')
            if benefit:
                benefits.append(benefit)
        
        # 生活保障
        if '生活保障' in content or '生活补助' in content:
            benefit = self._extract_specific_benefit(content, '生活保障')
            if benefit:
                benefits.append(benefit)
        
        return benefits
    
    def _extract_specific_benefit(self, content: str, benefit_type: str) -> Optional[PolicyBenefit]:
        """提取特定类型的福利"""
        # 找到包含福利关键词的句子
        sentences = re.split(r'[。；]', content)
        relevant_sentences = [s for s in sentences if benefit_type in s or any(keyword in s for keyword in ['补贴', '补助', '贷款'])]
        
        if not relevant_sentences:
            return None
        
        context = ''.join(relevant_sentences)
        
        # 提取金额
        amount = self._extract_amount(context)
        
        # 提取期限
        duration = self._extract_duration(context)
        
        return PolicyBenefit(
            benefit_type=benefit_type,
            amount=amount,
            duration=duration,
            description=context
        )
    
    def _extract_amount(self, text: str) -> str:
        """提取金额"""
        amount_patterns = [
            r'(\d+)万元', r'(\d+)元', r'(\d+)%',
            r'每人每月(\d+)元', r'每年(\d+)元',
            r'不超过(\d+)元', r'最高(\d+)元'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text)
            if match:
                if '万' in pattern:
                    return match.group(1) + '万元'
                elif '%' in pattern:
                    return match.group(1) + '%'
                else:
                    return match.group(1) + '元'
        
        return '详见政策'
    
    def _extract_duration(self, text: str) -> str:
        """提取期限"""
        duration_patterns = [
            r'不超过(\d+)年', r'期限.*?(\d+)年',
            r'(\d+)个月', r'至退休', r'一次性'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return '详见政策'
    
    def _extract_target_groups(self, content: str, words: List[str]) -> List[str]:
        """提取目标人群"""
        target_groups = []
        
        group_keywords = {
            '高校毕业生': ['高校毕业生', '大学生', '毕业生'],
            '就业困难人员': ['就业困难人员', '失业人员'],
            '灵活就业人员': ['灵活就业人员', '灵活就业'],
            '创业人员': ['创业人员', '创业者'],
            '被征地人员': ['被征地人员', '被征地农民'],
            '人才': ['人才', '高层次人才'],
            '企业职工': ['企业职工', '职工'],
            '退役军人': ['退役军人'],
            '残疾人': ['残疾人']
        }
        
        for group, keywords in group_keywords.items():
            if any(keyword in content for keyword in keywords):
                target_groups.append(group)
        
        return target_groups
    
    def _classify_policy(self, title: str, content: str, words: List[str]) -> str:
        """分类政策类型"""
        policy_categories = {
            '就业促进': ['就业', '稳岗', '失业'],
            '创业扶持': ['创业', '创业补贴', '创业担保'],
            '人才政策': ['人才', '人才公寓', '人才码'],
            '培训补贴': ['培训', '职业培训', '技能'],
            '社会保障': ['社保', '社会保险', '生活保障'],
            '住房保障': ['公寓', '租房', '住房']
        }
        
        text = title + content
        for category, keywords in policy_categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return '其他'
    
    def _extract_effective_date(self, content: str) -> str:
        """提取生效日期"""
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日.*?[起施行生效]',
            r'自(\d{4})年(\d{1,2})月(\d{1,2})日'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
        
        return '未明确'
    
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

class PersonPolicyMatcher:
    """人员政策匹配器"""
    
    def __init__(self):
        self.extractor = SmartPolicyExtractor()
        
        # 学历等级映射
        self.education_levels = {
            '小学': 1, '初中': 2, '高中': 3, '中专': 3,
            '专科': 4, '本科': 5, '硕士': 6, '博士': 7
        }
        
        # 人才码等级映射
        self.talent_code_levels = {
            'G': 1, 'F': 2, 'E': 3, 'D': 4, 'C': 5, 'B': 6, 'A': 7
        }
    
    def match_policy(self, person_info: Dict, policy_data: Dict) -> Dict:
        """匹配单个政策"""
        # 提取政策规则
        policy_info = self.extractor.extract_policy_rules(policy_data)
        
        # 计算匹配度
        match_result = self._calculate_match_score(person_info, policy_info)
        
        return {
            'policy_info': asdict(policy_info),
            'match_score': match_result['match_score'],
            'matched_rules': match_result['matched_rules'],
            'unmatched_rules': match_result['unmatched_rules'],
            'recommendations': match_result['recommendations'],
            'is_eligible': match_result['is_eligible']
        }
    
    def match_multiple_policies(self, person_info: Dict, policies_data: List[Dict]) -> List[Dict]:
        """匹配多个政策"""
        results = []
        
        for policy_data in policies_data:
            match_result = self.match_policy(person_info, policy_data)
            results.append(match_result)
        
        # 按匹配度排序
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return results
    
    def _calculate_match_score(self, person_info: Dict, policy_info: PolicyInfo) -> Dict:
        """计算匹配度"""
        rules = policy_info.rules
        
        if not rules:
            return {
                'match_score': 0.8,
                'matched_rules': [],
                'unmatched_rules': [],
                'recommendations': ['该政策无特殊条件限制'],
                'is_eligible': True
            }
        
        matched_rules = []
        unmatched_rules = []
        recommendations = []
        
        for rule in rules:
            is_match, person_value, gap = self._check_rule(person_info, rule)
            
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
        matched_count = len(matched_rules)
        match_score = matched_count / total_rules if total_rules > 0 else 1.0
        
        # 判断是否符合条件（80%以上匹配）
        is_eligible = match_score >= 0.8
        
        return {
            'match_score': match_score,
            'matched_rules': matched_rules,
            'unmatched_rules': unmatched_rules,
            'recommendations': recommendations,
            'is_eligible': is_eligible
        }
    
    def _check_rule(self, person_info: Dict, rule: PolicyRule) -> tuple:
        """检查单个规则"""
        field = rule.field
        operator = rule.operator
        rule_value = rule.value
        
        try:
            # 获取个人对应字段的值
            person_value = self._get_person_field_value(person_info, field)
            
            if person_value is None:
                return False, "未提供", f"缺少{field}信息"
            
            # 执行比较
            is_match = self._compare_values(person_value, operator, rule_value, field)
            
            if is_match:
                return True, person_value, None
            else:
                gap = self._calculate_gap(person_value, operator, rule_value, field)
                return False, person_value, gap
                
        except Exception as e:
            return False, "检查失败", str(e)
    
    def _get_person_field_value(self, person_info: Dict, field: str):
        """获取个人字段值"""
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
            age = person_info.get('年龄')
            if age:
                return max(0, 60 - age)  # 假设60岁退休
            return None
        
        if field == 'graduation_years':
            grad_year = person_info.get('毕业年份')
            if grad_year:
                return datetime.now().year - grad_year
            return None
        
        chinese_field = field_mapping.get(field, field)
        return person_info.get(chinese_field)
    
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
                return person_value == rule_value
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

# 使用示例
def main():
    # 初始化匹配器
    matcher = PersonPolicyMatcher()
    
    # 示例政策数据
    policies = [
        {
            "政策编号": "POL0001",
            "标题": "关于调整平湖市灵活就业人员社会保险补贴标准的通知",
            "内容": "就业困难人员实现灵活就业并依法缴纳社会保险费的，按当年最低社会保险缴费基数缴费额（基本养老、基本医疗保险）的50%给予社保补贴，期限不超过3年，其中对初次核定享受补贴政策时距离法定退休年龄不足5年的人员，延长至退休。补贴政策自2018年1月1日起实施。"
        },
        {
            "政策编号": "POL0002",
            "标题": "关于《平湖市人才公寓管理暂行办法》政策解读",
            "内容": "申请资金补助对象应同时符合以下条件：（一）2021年10月1日后，在我市首次缴纳社保、公积金、个人所得税其中之一。（二）申请时未取得房产网签备案或不动产权证。（三）拥有G类及以上的人才码（归属管理权限在平湖市内）,其中在事业单位工作的拥有F类及以上人才码。人才码E类及以上人才，每月每人不超过2000元。人才码F类人才，每月每人不超过1200元。人才码G类人才，每月每人不超过600元。"
        },
        {
            "政策编号": "POL0003",
            "标题": "关于进一步加强和完善职业培训补贴管理工作的通知",
            "内容": "毕业年度高校毕业生（含技工院校高级工班、预备技师班、技师班和特殊教育院校职业教育类毕业生）参加就业技能培训的，培训后取得符合规定证书的，给予职业培训补贴。企业新录用的六类人员，与企业签订1年以上期限劳动合同，并于签订劳动合同之日起1年内参加培训，培训后取得证书的给予职业培训补贴。"
        },
        {
            "政策编号": "POL0004",
            "标题": "平湖市创业担保贷款政策",
            "内容": "符合条件的创业人员，可申请最高50万元的创业担保贷款。对在校大学生和毕业5年以内高校毕业生、登记失业半年以上人员、就业困难人员申请的个人创业担保贷款按规定给予全额贴息。小微企业招用重点人群的，可按规定申请最高300万元的创业担保贷款。"
        }
    ]
    
    # 示例人员信息
    person_info = {
        "用户ID": "U001",
        "姓名": "张三",
        "年龄": 28,
        "最高学历": "本科",
        "专业": "计算机科学与技术",
        "工作年限": 3,
        "籍贯": "平湖市",
        "人才码等级": "G",  
        "就业状态": "就业困难",
        "毕业年份": 2019,
        "企业类型": "小微企业",
        "工作经历": [
            {
                "公司名称": "平湖某科技有限公司",
                "职位": "软件开发工程师",
                "工作时间": "2020.03-2022.08"
            }
        ]
    }
    
    print("🚀 智能政策规则提取与匹配系统")
    print("=" * 60)
    
    # 匹配所有政策
    match_results = matcher.match_multiple_policies(person_info, policies)
    
    print(f"\n👤 个人信息：")
    print(f"   姓名：{person_info['姓名']}")
    print(f"   年龄：{person_info['年龄']}岁")
    print(f"   学历：{person_info['最高学历']}")
    print(f"   工作年限：{person_info['工作年限']}年")
    print(f"   籍贯：{person_info['籍贯']}")
    print(f"   人才码：{person_info['人才码等级']}类")
    print(f"   就业状态：{person_info['就业状态']}")
    
    print(f"\n📋 政策匹配结果：")
    print("=" * 60)
    
    for i, result in enumerate(match_results, 1):
        policy_info = result['policy_info']
        match_score = result['match_score']
        is_eligible = result['is_eligible']
        
        print(f"\n{i}. 📄 {policy_info['title']}")
        print(f"   政策编号：{policy_info['policy_id']}")
        print(f"   政策类型：{policy_info['policy_category']}")
        print(f"   匹配度：{match_score:.1%} {'✅' if is_eligible else '❌'}")
        print(f"   生效日期：{policy_info['effective_date']}")
        
        # 显示目标人群
        if policy_info['target_groups']:
            print(f"   🎯 目标人群：{', '.join(policy_info['target_groups'])}")
        
        # 显示提取的规则
        print(f"   📝 提取的政策规则：")
        for rule in policy_info['rules']:
            confidence_icon = "🔥" if rule['confidence'] >= 0.9 else "⚡" if rule['confidence'] >= 0.8 else "💡"
            print(f"      {confidence_icon} {rule['description']} (置信度: {rule['confidence']:.1%})")
        
        # 显示福利
        if policy_info['benefits']:
            print(f"   🎁 政策福利：")
            for benefit in policy_info['benefits']:
                print(f"      - {benefit['benefit_type']}: {benefit['amount']} ({benefit['duration']})")
        
        # 显示匹配详情
        if result['matched_rules']:
            print(f"   ✅ 满足的条件 ({len(result['matched_rules'])}项)：")
            for matched in result['matched_rules']:
                rule = matched['rule']
                person_value = matched['person_value']
                print(f"      ✓ {rule['description']} (当前值: {person_value})")
        
        if result['unmatched_rules']:
            print(f"   ❌ 不满足的条件 ({len(result['unmatched_rules'])}项)：")
            for unmatched in result['unmatched_rules']:
                rule = unmatched['rule']
                gap = unmatched['gap']
                print(f"      ✗ {rule['description']} (差距: {gap})")
        
        # 显示建议
        if result['recommendations']:
            print(f"   💡 改进建议：")
            for rec in result['recommendations']:
                print(f"      - {rec}")
        
        print("-" * 60)
    
    # 显示政策规则提取统计
    print(f"\n📊 政策规则提取统计：")
    print("=" * 60)
    
    total_rules = 0
    rule_types = {}
    confidence_stats = {'高': 0, '中': 0, '低': 0}
    
    for result in match_results:
        rules = result['policy_info']['rules']
        total_rules += len(rules)
        
        for rule in rules:
            rule_type = rule['field']
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
            
            # 统计置信度
            confidence = rule['confidence']
            if confidence >= 0.9:
                confidence_stats['高'] += 1
            elif confidence >= 0.8:
                confidence_stats['中'] += 1
            else:
                confidence_stats['低'] += 1
    
    print(f"总规则数：{total_rules}")
    print(f"规则类型分布：{dict(rule_types)}")
    print(f"置信度分布：{dict(confidence_stats)}")
    
    # 推荐最匹配的政策
    if match_results:
        best_match = match_results[0]
        if best_match['is_eligible']:
            print(f"\n🏆 最推荐的政策：")
            print(f"   {best_match['policy_info']['title']}")
            print(f"   匹配度：{best_match['match_score']:.1%}")
            print(f"   建议：立即申请该政策!")
        else:
            print(f"\n⚠️  当前没有完全符合条件的政策")
            print(f"   最接近的政策：{best_match['policy_info']['title']}")
            print(f"   匹配度：{best_match['match_score']:.1%}")
            print(f"   建议：根据改进建议提升条件后申请")

def test_single_policy():
    """测试单个政策提取"""
    matcher = PersonPolicyMatcher()
    
    # 测试政策
    policy = {
        "政策编号": "TEST001",
        "标题": "测试政策",
        "内容": "25周岁以上本科毕业生，工作年限3年以上，拥有F类及以上人才码，在平湖市工作的，给予每月1500元租房补贴，期限不超过2年。"
    }
    
    person = {
        "年龄": 27,
        "最高学历": "本科",
        "工作年限": 4,
        "人才码等级": "F",
        "籍贯": "平湖市"
    }
    
    print("\n🧪 单政策测试：")
    print("=" * 40)
    
    result = matcher.match_policy(person, policy)
    
    print(f"政策：{policy['标题']}")
    print(f"匹配度：{result['match_score']:.1%}")
    print(f"是否符合：{'是' if result['is_eligible'] else '否'}")
    
    print("\n提取的规则：")
    for rule in result['policy_info']['rules']:
        print(f"  - {rule['description']} (置信度: {rule['confidence']:.1%})")

if __name__ == "__main__":
    main()
    test_single_policy()