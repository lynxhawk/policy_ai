#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扣分制政策推荐系统
基于正则规则匹配和关键词相似度的扣分制评分算法
分数越高表示匹配度越高，扣分越少
"""

import os
import json
import re
import math
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import Counter
from datetime import datetime
import jieba
import jieba.analyse

@dataclass
class DeductionScore:
    """扣分详情"""
    base_score: float = 100.0          # 基础分数
    rule_deductions: List[Dict] = None  # 规则扣分详情
    similarity_deductions: List[Dict] = None  # 相似度扣分详情
    final_score: float = 0.0           # 最终分数
    deduction_reasons: List[str] = None # 扣分原因
    
    def __post_init__(self):
        if self.rule_deductions is None:
            self.rule_deductions = []
        if self.similarity_deductions is None:
            self.similarity_deductions = []
        if self.deduction_reasons is None:
            self.deduction_reasons = []

@dataclass
class PolicyRecommendation:
    """政策推荐结果"""
    policy_id: str
    policy_title: str
    final_score: float
    rank: int
    deduction_score: DeductionScore
    match_level: str  # 高度匹配/中度匹配/低度匹配/需改进
    recommendation_reason: str
    benefits: List[str]

class DeductionPolicyRecommender:
    """扣分制政策推荐系统"""
    
    def __init__(self, policy_dir="policy_dataset", user_dir="user_dataset"):
        self.policy_dir = policy_dir
        self.user_dir = user_dir
        self._init_jieba()
        self._init_deduction_config()
        self._init_patterns()
        
    def _init_jieba(self):
        """初始化jieba分词"""
        custom_words = [
            '高校毕业生', '就业困难人员', '灵活就业', '创业担保贷款',
            '社保补贴', '人才码', '被征地人员', '职业培训', '见习补贴',
            '平湖市', '嘉兴市', '法定退休年龄', '小微企业', '初次创业'
        ]
        for word in custom_words:
            jieba.add_word(word, 10)
    
    def _init_deduction_config(self):
        """初始化扣分配置"""
        # 扣分权重配置
        self.deduction_weights = {
            'rule_weight': 0.7,        # 规则匹配权重
            'similarity_weight': 0.3   # 相似度权重
        }
        
        # 规则扣分标准
        self.rule_deduction_standards = {
            # 严重不匹配 - 重度扣分
            'critical_mismatch': {
                'age_gap_major': 30,      # 年龄差距过大
                'education_level_gap': 25, # 学历等级差距大
                'location_mismatch': 35,   # 地域完全不匹配
                'employment_status_wrong': 30  # 就业状态错误
            },
            
            # 中度不匹配 - 中度扣分
            'moderate_mismatch': {
                'age_gap_minor': 15,      # 年龄稍有差距
                'work_experience_gap': 20, # 工作经验不足
                'talent_code_lower': 15,   # 人才码等级稍低
                'graduation_time_gap': 10  # 毕业时间差距
            },
            
            # 轻度不匹配 - 轻度扣分
            'minor_mismatch': {
                'partial_requirement': 8,  # 部分条件不满足
                'documentation_missing': 5, # 材料可能缺失
                'procedure_complexity': 3   # 申请流程复杂
            }
        }
        
        # 相似度扣分标准
        self.similarity_deduction_standards = {
            'keyword_mismatch': {
                'no_common_keywords': 25,    # 无共同关键词
                'low_similarity': 15,        # 相似度很低 (<0.2)
                'medium_similarity': 8,      # 相似度中等 (0.2-0.5)
                'field_mismatch': 12         # 专业领域不匹配
            },
            
            'semantic_gap': {
                'profession_unrelated': 20,  # 专业完全无关
                'industry_different': 10,    # 行业不同
                'skill_mismatch': 8          # 技能不匹配
            }
        }
        
        # 学历等级映射
        self.education_levels = {
            '小学': 1, '初中': 2, '高中': 3, '中专': 3,
            '专科': 4, '本科': 5, '硕士': 6, '博士': 7
        }
        
        # 人才码等级映射
        self.talent_code_levels = {
            'G': 1, 'F': 2, 'E': 3, 'D': 4, 'C': 5, 'B': 6, 'A': 7
        }
        
        # 匹配等级阈值
        self.match_level_thresholds = {
            'high': 85,     # 高度匹配
            'medium': 65,   # 中度匹配  
            'low': 40,      # 低度匹配
            'need_improve': 0  # 需改进
        }
    
    def _init_patterns(self):
        """初始化正则匹配模式"""
        self.rule_patterns = {
            'age': [
                (r'(\d+)周岁以上', 'age', '>=', 'age_requirement'),
                (r'(\d+)岁以上', 'age', '>=', 'age_requirement'),
                (r'年满(\d+)周岁', 'age', '>=', 'age_requirement'),
                (r'距离法定退休年龄不足(\d+)年', 'retirement_years_left', '<', 'retirement_requirement')
            ],
            'education': [
                ('博士', 'education', '>=', 'education_requirement'),
                ('硕士', 'education', '>=', 'education_requirement'),
                ('本科', 'education', '>=', 'education_requirement'),
                ('专科', 'education', '>=', 'education_requirement'),
                ('高中', 'education', '>=', 'education_requirement')
            ],
            'work_experience': [
                (r'工作年限(\d+)年以上', 'work_years', '>=', 'experience_requirement'),
                (r'从业(\d+)年以上', 'work_years', '>=', 'experience_requirement'),
                (r'正常经营满(\d+)个月', 'work_months', '>=', 'business_requirement'),
                (r'缴费(\d+)年以上', 'insurance_years', '>=', 'insurance_requirement')
            ],
            'graduation': [
                (r'毕业(\d+)年[以内下]', 'graduation_years', '<=', 'graduation_time'),
                ('毕业学年', 'graduation_status', '==', 'graduation_status'),
                ('应届毕业生', 'graduation_status', '==', 'graduation_status')
            ],
            'talent_code': [
                (r'([A-G])类.*?人才码', 'talent_code', '>=', 'talent_requirement'),
                (r'人才码.*?([A-G])类', 'talent_code', '>=', 'talent_requirement')
            ],
            'employment': [
                ('就业困难人员', 'employment_status', '==', 'employment_type'),
                ('灵活就业', 'employment_type', '==', 'employment_type'),
                ('失业人员', 'employment_status', '==', 'employment_type'),
                ('初次创业', 'employment_type', '==', 'employment_type')
            ],
            'location': [
                ('平湖市', 'location', 'in', 'location_requirement'),
                ('本市', 'location', 'in', 'location_requirement'),
                ('嘉兴市', 'location', 'in', 'location_requirement')
            ]
        }
    
    def extract_policy_requirements(self, policy_content) -> List[Dict]:
        """提取政策要求"""
        if isinstance(policy_content, list):
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            content_text = policy_content
        else:
            return []
        
        requirements = []
        
        for category, patterns in self.rule_patterns.items():
            for pattern_info in patterns:
                if len(pattern_info) >= 3:
                    pattern, field, operator = pattern_info[:3]
                    requirement_type = pattern_info[3] if len(pattern_info) > 3 else 'general'
                    
                    if pattern.startswith('r') or pattern.startswith('('):
                        # 正则表达式
                        try:
                            matches = re.finditer(pattern, content_text)
                            for match in matches:
                                value = match.group(1) if match.groups() else match.group(0)
                                try:
                                    if field in ['age', 'work_years', 'work_months', 'insurance_years', 'graduation_years', 'retirement_years_left']:
                                        value = int(value)
                                    
                                    requirements.append({
                                        'field': field,
                                        'operator': operator,
                                        'value': value,
                                        'type': requirement_type,
                                        'pattern': pattern,
                                        'description': self._generate_requirement_description(field, operator, value)
                                    })
                                except ValueError:
                                    continue
                        except re.error:
                            continue
                    else:
                        # 关键词匹配
                        if pattern in content_text:
                            requirements.append({
                                'field': field,
                                'operator': operator,
                                'value': pattern,
                                'type': requirement_type,
                                'pattern': pattern,
                                'description': self._generate_requirement_description(field, operator, pattern)
                            })
        
        return requirements
    
    def extract_user_keywords(self, user_info: Dict) -> List[str]:
        """提取用户关键词"""
        user_text = ""
        
        # 收集用户信息文本
        for key, value in user_info.items():
            if key not in ['用户ID', '工作经历']:
                user_text += str(value) + " "
        
        # 添加工作经历
        if '工作经历' in user_info:
            for work in user_info['工作经历']:
                user_text += str(work.get('公司名称', '')) + " "
                user_text += str(work.get('职位', '')) + " "
        
        # 提取关键词
        try:
            keywords = jieba.analyse.extract_tags(user_text, topK=20)
            return keywords
        except:
            return []
    
    def extract_policy_keywords(self, policy_content) -> List[str]:
        """提取政策关键词"""
        if isinstance(policy_content, list):
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            content_text = policy_content
        else:
            return []
        
        try:
            keywords = jieba.analyse.extract_tags(content_text, topK=30)
            return keywords
        except:
            return []
    
    def calculate_keyword_similarity(self, user_keywords: List[str], policy_keywords: List[str]) -> float:
        """计算关键词相似度（余弦相似度）"""
        if not user_keywords or not policy_keywords:
            return 0.0
        
        # 创建词汇表
        all_words = list(set(user_keywords + policy_keywords))
        
        # 创建向量
        user_vector = [user_keywords.count(word) for word in all_words]
        policy_vector = [policy_keywords.count(word) for word in all_words]
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(user_vector, policy_vector))
        magnitude1 = math.sqrt(sum(a * a for a in user_vector))
        magnitude2 = math.sqrt(sum(a * a for a in policy_vector))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def calculate_deduction_score(self, user_info: Dict, policy_data: Dict) -> DeductionScore:
        """计算扣分制分数"""
        deduction_score = DeductionScore()
        
        # 1. 提取政策要求和关键词
        requirements = self.extract_policy_requirements(policy_data.get('内容', ''))
        user_keywords = self.extract_user_keywords(user_info)
        policy_keywords = self.extract_policy_keywords(policy_data.get('内容', ''))
        
        # 2. 计算规则匹配扣分
        rule_deductions = self._calculate_rule_deductions(user_info, requirements)
        deduction_score.rule_deductions = rule_deductions
        
        # 3. 计算相似度扣分
        similarity = self.calculate_keyword_similarity(user_keywords, policy_keywords)
        similarity_deductions = self._calculate_similarity_deductions(
            similarity, user_keywords, policy_keywords, user_info
        )
        deduction_score.similarity_deductions = similarity_deductions
        
        # 4. 计算总扣分
        total_rule_deduction = sum(d['deduction'] for d in rule_deductions)
        total_similarity_deduction = sum(d['deduction'] for d in similarity_deductions)
        
        weighted_rule_deduction = total_rule_deduction * self.deduction_weights['rule_weight']
        weighted_similarity_deduction = total_similarity_deduction * self.deduction_weights['similarity_weight']
        
        total_deduction = weighted_rule_deduction + weighted_similarity_deduction
        
        # 5. 计算最终分数
        deduction_score.final_score = max(0, deduction_score.base_score - total_deduction)
        
        # 6. 生成扣分原因
        deduction_score.deduction_reasons = self._generate_deduction_reasons(
            rule_deductions, similarity_deductions
        )
        
        return deduction_score
    
    def _calculate_rule_deductions(self, user_info: Dict, requirements: List[Dict]) -> List[Dict]:
        """计算规则匹配扣分"""
        deductions = []
        
        for req in requirements:
            field = req['field']
            operator = req['operator']
            required_value = req['value']
            req_type = req['type']
            
            user_value = self._get_user_field_value(user_info, field)
            
            if user_value is None:
                # 缺少信息扣分
                deductions.append({
                    'reason': f"缺少{field}信息",
                    'deduction': self.rule_deduction_standards['minor_mismatch']['documentation_missing'],
                    'severity': 'minor',
                    'field': field,
                    'requirement': req['description']
                })
                continue
            
            # 检查是否满足要求
            is_match, gap_info = self._check_requirement_match(user_value, operator, required_value, field)
            
            if not is_match:
                deduction_amount, severity = self._calculate_rule_deduction_amount(
                    field, gap_info, req_type
                )
                
                deductions.append({
                    'reason': gap_info,
                    'deduction': deduction_amount,
                    'severity': severity,
                    'field': field,
                    'requirement': req['description'],
                    'user_value': user_value,
                    'required_value': required_value
                })
        
        return deductions
    
    def _calculate_similarity_deductions(self, similarity: float, user_keywords: List[str], 
                                       policy_keywords: List[str], user_info: Dict) -> List[Dict]:
        """计算相似度扣分"""
        deductions = []
        
        # 1. 整体相似度扣分
        if similarity == 0:
            deductions.append({
                'reason': '关键词完全不匹配',
                'deduction': self.similarity_deduction_standards['keyword_mismatch']['no_common_keywords'],
                'severity': 'critical',
                'field': 'keyword_similarity',
                'similarity_score': similarity
            })
        elif similarity < 0.2:
            deductions.append({
                'reason': '关键词相似度很低',
                'deduction': self.similarity_deduction_standards['keyword_mismatch']['low_similarity'],
                'severity': 'moderate',
                'field': 'keyword_similarity',
                'similarity_score': similarity
            })
        elif similarity < 0.5:
            deductions.append({
                'reason': '关键词相似度中等',
                'deduction': self.similarity_deduction_standards['keyword_mismatch']['medium_similarity'],
                'severity': 'minor',
                'field': 'keyword_similarity',
                'similarity_score': similarity
            })
        
        # 2. 专业领域匹配度扣分
        user_profession = user_info.get('专业', '')
        if user_profession:
            profession_match = any(
                user_profession in policy_kw or policy_kw in user_profession 
                for policy_kw in policy_keywords
            )
            
            if not profession_match:
                deductions.append({
                    'reason': '专业领域不相关',
                    'deduction': self.similarity_deduction_standards['semantic_gap']['profession_unrelated'],
                    'severity': 'moderate',
                    'field': 'profession_match',
                    'user_profession': user_profession
                })
        
        # 3. 查找共同关键词
        common_keywords = set(user_keywords) & set(policy_keywords)
        if len(common_keywords) == 0 and len(user_keywords) > 0 and len(policy_keywords) > 0:
            deductions.append({
                'reason': '无共同关键词',
                'deduction': self.similarity_deduction_standards['keyword_mismatch']['no_common_keywords'] * 0.5,
                'severity': 'moderate',
                'field': 'common_keywords',
                'common_count': 0
            })
        
        return deductions
    
    def _check_requirement_match(self, user_value, operator: str, required_value, field: str) -> Tuple[bool, str]:
        """检查要求匹配"""
        try:
            if field == 'education':
                return self._check_education_match(user_value, required_value, operator)
            elif field == 'talent_code':
                return self._check_talent_code_match(user_value, required_value, operator)
            elif field == 'location':
                is_match = required_value in str(user_value)
                gap = f"需要在{required_value}，当前在{user_value}" if not is_match else ""
                return is_match, gap
            elif operator == '>=':
                is_match = user_value >= required_value
                gap = f"需要≥{required_value}，当前{user_value}" if not is_match else ""
                return is_match, gap
            elif operator == '<=':
                is_match = user_value <= required_value
                gap = f"需要≤{required_value}，当前{user_value}" if not is_match else ""
                return is_match, gap
            elif operator == '==':
                is_match = str(user_value) == str(required_value)
                gap = f"需要{required_value}，当前{user_value}" if not is_match else ""
                return is_match, gap
            
            return False, "无法比较"
        except:
            return False, "比较失败"
    
    def _check_education_match(self, user_edu: str, required_edu: str, operator: str) -> Tuple[bool, str]:
        """检查学历匹配"""
        user_level = self.education_levels.get(user_edu, 0)
        required_level = self.education_levels.get(required_edu, 0)
        
        if operator == '>=':
            is_match = user_level >= required_level
            gap = f"需要{required_edu}及以上，当前{user_edu}" if not is_match else ""
        else:
            is_match = user_level == required_level
            gap = f"需要{required_edu}，当前{user_edu}" if not is_match else ""
        
        return is_match, gap
    
    def _check_talent_code_match(self, user_code: str, required_code: str, operator: str) -> Tuple[bool, str]:
        """检查人才码匹配"""
        user_level = self.talent_code_levels.get(user_code, 0)
        required_level = self.talent_code_levels.get(required_code, 0)
        
        if operator == '>=':
            is_match = user_level >= required_level
            gap = f"需要{required_code}类及以上人才码，当前{user_code}类" if not is_match else ""
        else:
            is_match = user_level == required_level
            gap = f"需要{required_code}类人才码，当前{user_code}类" if not is_match else ""
        
        return is_match, gap
    
    def _calculate_rule_deduction_amount(self, field: str, gap_info: str, req_type: str) -> Tuple[float, str]:
        """计算规则扣分数量"""
        # 根据字段类型和差距确定扣分等级
        if field == 'age':
            if '需要≥' in gap_info:
                try:
                    parts = gap_info.split('需要≥')[1].split('，当前')
                    required = int(parts[0])
                    current = int(parts[1])
                    gap = required - current
                    
                    if gap > 10:
                        return self.rule_deduction_standards['critical_mismatch']['age_gap_major'], 'critical'
                    elif gap > 5:
                        return self.rule_deduction_standards['moderate_mismatch']['age_gap_minor'], 'moderate'
                    else:
                        return self.rule_deduction_standards['minor_mismatch']['partial_requirement'], 'minor'
                except:
                    return self.rule_deduction_standards['moderate_mismatch']['age_gap_minor'], 'moderate'
        
        elif field == 'education':
            return self.rule_deduction_standards['critical_mismatch']['education_level_gap'], 'critical'
        
        elif field == 'location':
            return self.rule_deduction_standards['critical_mismatch']['location_mismatch'], 'critical'
        
        elif field == 'work_years':
            return self.rule_deduction_standards['moderate_mismatch']['work_experience_gap'], 'moderate'
        
        elif field == 'talent_code':
            return self.rule_deduction_standards['moderate_mismatch']['talent_code_lower'], 'moderate'
        
        elif field == 'employment_status' or field == 'employment_type':
            return self.rule_deduction_standards['critical_mismatch']['employment_status_wrong'], 'critical'
        
        else:
            return self.rule_deduction_standards['minor_mismatch']['partial_requirement'], 'minor'
    
    def _get_user_field_value(self, user_info: Dict, field: str):
        """获取用户字段值"""
        field_mapping = {
            'age': '年龄',
            'education': '最高学历',
            'work_years': '工作年限',
            'talent_code': '人才码等级',
            'location': '籍贯',
            'employment_status': '就业状态',
            'employment_type': '就业状态',
            'graduation_years': '毕业年份'
        }
        
        if field == 'retirement_years_left':
            age = user_info.get('年龄')
            return max(0, 60 - age) if age else None
        
        if field == 'graduation_years':
            grad_year = user_info.get('毕业年份')
            return datetime.now().year - grad_year if grad_year else None
        
        # 针对您的数据结构的特殊处理
        if field == 'age' and '年龄' not in user_info:
            # 如果没有年龄信息，根据工作年限估算（假设22岁毕业开始工作）
            work_years = user_info.get('工作年限', 0)
            if work_years > 0:
                return 22 + work_years
            return None
        
        if field == 'employment_status' and '就业状态' not in user_info:
            # 如果有工作经历，推断为就业状态
            if user_info.get('工作经历'):
                return '在职'
            return None
        
        chinese_field = field_mapping.get(field, field)
        return user_info.get(chinese_field)
    
    def _generate_requirement_description(self, field: str, operator: str, value: Any) -> str:
        """生成要求描述"""
        field_names = {
            'age': '年龄',
            'education': '学历',
            'work_years': '工作年限',
            'talent_code': '人才码',
            'location': '地域',
            'employment_status': '就业状态',
            'employment_type': '就业类型'
        }
        
        field_name = field_names.get(field, field)
        
        if operator == '>=':
            return f"{field_name}要求：{value}及以上"
        elif operator == '<=':
            return f"{field_name}要求：{value}及以下"
        elif operator == '==':
            return f"{field_name}要求：{value}"
        elif operator == 'in':
            return f"{field_name}要求：包含{value}"
        else:
            return f"{field_name}要求：{value}"
    
    def _generate_deduction_reasons(self, rule_deductions: List[Dict], 
                                  similarity_deductions: List[Dict]) -> List[str]:
        """生成扣分原因"""
        reasons = []
        
        # 规则扣分原因
        for deduction in rule_deductions:
            if deduction['severity'] == 'critical':
                reasons.append(f"❗ 关键条件不满足：{deduction['reason']} (扣{deduction['deduction']:.1f}分)")
            elif deduction['severity'] == 'moderate':
                reasons.append(f"⚠️ 重要条件不满足：{deduction['reason']} (扣{deduction['deduction']:.1f}分)")
            else:
                reasons.append(f"📝 次要条件不满足：{deduction['reason']} (扣{deduction['deduction']:.1f}分)")
        
        # 相似度扣分原因
        for deduction in similarity_deductions:
            if deduction['severity'] == 'critical':
                reasons.append(f"❗ 严重不匹配：{deduction['reason']} (扣{deduction['deduction']:.1f}分)")
            elif deduction['severity'] == 'moderate':
                reasons.append(f"⚠️ 中度不匹配：{deduction['reason']} (扣{deduction['deduction']:.1f}分)")
            else:
                reasons.append(f"📝 轻度不匹配：{deduction['reason']} (扣{deduction['deduction']:.1f}分)")
        
        return reasons
    
    def get_match_level(self, score: float) -> str:
        """获取匹配等级"""
        if score >= self.match_level_thresholds['high']:
            return '高度匹配'
        elif score >= self.match_level_thresholds['medium']:
            return '中度匹配'
        elif score >= self.match_level_thresholds['low']:
            return '低度匹配'
        else:
            return '需改进'
    
    def generate_recommendation_reason(self, score: float, deduction_score: DeductionScore) -> str:
        """生成推荐理由"""
        match_level = self.get_match_level(score)
        
        if match_level == '高度匹配':
            return f"强烈推荐！您的条件与该政策高度匹配（得分{score:.1f}），建议优先申请。"
        elif match_level == '中度匹配':
            return f"推荐申请。您的条件与该政策中度匹配（得分{score:.1f}），有较大申请成功可能。"
        elif match_level == '低度匹配':
            return f"可考虑申请。您的条件与该政策匹配度一般（得分{score:.1f}），需要完善部分条件。"
        else:
            main_issues = [reason for reason in deduction_score.deduction_reasons[:2]]
            issues_text = "、".join(main_issues) if main_issues else "多项条件不满足"
            return f"暂不推荐。您的条件与该政策匹配度较低（得分{score:.1f}），主要问题：{issues_text}。"
    
    def recommend_policies_for_user(self, user_info: Dict, policies: List[Dict]) -> List[PolicyRecommendation]:
        """为用户推荐所有政策（按扣分制排序）"""
        recommendations = []
        
        for policy_data in policies:
            # 计算扣分制分数
            deduction_score = self.calculate_deduction_score(user_info, policy_data)
            
            # 获取匹配等级
            match_level = self.get_match_level(deduction_score.final_score)
            
            # 生成推荐理由
            recommendation_reason = self.generate_recommendation_reason(
                deduction_score.final_score, deduction_score
            )
            
            # 提取政策福利
            benefits = self.extract_policy_benefits(policy_data.get('内容', ''))
            
            recommendation = PolicyRecommendation(
                policy_id=policy_data.get('政策编号', ''),
                policy_title=policy_data.get('标题', ''),
                final_score=deduction_score.final_score,
                rank=0,  # 稍后排序时设置
                deduction_score=deduction_score,
                match_level=match_level,
                recommendation_reason=recommendation_reason,
                benefits=benefits
            )
            
            recommendations.append(recommendation)
        
        # 按分数降序排序（分数越高，匹配度越高）
        recommendations.sort(key=lambda x: x.final_score, reverse=True)
        
        # 设置排名
        for i, rec in enumerate(recommendations, 1):
            rec.rank = i
        
        return recommendations
    
    def extract_policy_benefits(self, policy_content) -> List[str]:
        """提取政策福利"""
        if isinstance(policy_content, list):
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            content_text = policy_content
        else:
            return []
        
        benefits = []
        
        # 福利提取模式
        benefit_patterns = [
            r'每人每月(\d+)元',
            r'每年(\d+)元', 
            r'一次性.*?(\d+)元',
            r'不超过(\d+)元',
            r'最高(\d+)万?元',
            r'(\d+)%.*?补贴',
            r'补贴.*?(\d+)元',
            r'资助.*?(\d+)元'
        ]
        
        for pattern in benefit_patterns:
            matches = re.findall(pattern, content_text)
            for match in matches:
                benefits.append(f"补贴金额：{match}元")
        
        # 福利类型识别
        if '社保' in content_text:
            benefits.append("社保补贴")
        if '培训' in content_text:
            benefits.append("培训补贴") 
        if '就业' in content_text:
            benefits.append("就业补贴")
        if '创业' in content_text:
            benefits.append("创业扶持")
        if '租房' in content_text or '住房' in content_text:
            benefits.append("住房补贴")
        if '贷款' in content_text:
            benefits.append("贷款支持")
        
        return list(set(benefits)) if benefits else ["详见政策内容"]
    
    def generate_user_recommendation_report(self, user_info: Dict, 
                                          recommendations: List[PolicyRecommendation]) -> str:
        """生成用户政策推荐报告"""
        report = []
        user_id = user_info.get('用户ID', '未知')
        
        # 报告头部
        report.append("=" * 80)
        report.append(f"政策推荐报告（扣分制）- 用户ID: {user_id}")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"推荐算法: 扣分制评分（规则权重{self.deduction_weights['rule_weight']:.1%} + 相似度权重{self.deduction_weights['similarity_weight']:.1%}）")
        report.append("")
        
        # 用户基本信息
        report.append("👤 用户基本信息")
        report.append("-" * 40)
        basic_fields = ['最高学历', '专业', '工作年限', '籍贯', '技能等级']
        for field in basic_fields:
            value = user_info.get(field, '未提供')
            report.append(f"  {field}: {value}")
        
        # 工作经历
        if '工作经历' in user_info and user_info['工作经历']:
            report.append("  工作经历:")
            for i, work in enumerate(user_info['工作经历'], 1):
                company = work.get('公司名称', '未知')
                position = work.get('职位', '未知')
                time_period = work.get('工作时间', '未知')
                report.append(f"    {i}. {company} - {position} ({time_period})")
        
        # 推算信息
        estimated_age = self._get_user_field_value(user_info, 'age')
        if estimated_age:
            report.append(f"  推算年龄: {estimated_age}岁")
        
        report.append("")
        
        # 推荐统计
        total_policies = len(recommendations)
        high_match = len([r for r in recommendations if r.match_level == '高度匹配'])
        medium_match = len([r for r in recommendations if r.match_level == '中度匹配'])
        low_match = len([r for r in recommendations if r.match_level == '低度匹配'])
        need_improve = len([r for r in recommendations if r.match_level == '需改进'])
        
        report.append("📊 推荐统计")
        report.append("-" * 40)
        report.append(f"  总政策数: {total_policies}")
        report.append(f"  🟢 高度匹配: {high_match} ({high_match/total_policies:.1%})")
        report.append(f"  🟡 中度匹配: {medium_match} ({medium_match/total_policies:.1%})")
        report.append(f"  🟠 低度匹配: {low_match} ({low_match/total_policies:.1%})")
        report.append(f"  🔴 需改进: {need_improve} ({need_improve/total_policies:.1%})")
        
        if recommendations:
            avg_score = sum(r.final_score for r in recommendations) / len(recommendations)
            max_score = max(r.final_score for r in recommendations)
            min_score = min(r.final_score for r in recommendations)
            report.append(f"  平均得分: {avg_score:.1f}")
            report.append(f"  最高得分: {max_score:.1f}")
            report.append(f"  最低得分: {min_score:.1f}")
        
        report.append("")
        
        # 详细推荐结果
        report.append("🎯 详细推荐结果（按匹配度排序）")
        report.append("=" * 80)
        
        for rec in recommendations:
            # 匹配等级图标
            level_icon = {
                '高度匹配': '🟢',
                '中度匹配': '🟡', 
                '低度匹配': '🟠',
                '需改进': '🔴'
            }.get(rec.match_level, '⚪')
            
            report.append(f"#{rec.rank} {level_icon} {rec.policy_id} | 得分: {rec.final_score:.1f} | {rec.match_level}")
            report.append(f"   标题: {rec.policy_title}")
            report.append(f"   推荐理由: {rec.recommendation_reason}")
            
            # 福利信息
            if rec.benefits:
                benefits_str = " | ".join(rec.benefits[:3])  # 显示前3个福利
                report.append(f"   政策福利: {benefits_str}")
            
            # 扣分详情
            ds = rec.deduction_score
            total_rule_deduction = sum(d['deduction'] for d in ds.rule_deductions)
            total_similarity_deduction = sum(d['deduction'] for d in ds.similarity_deductions)
            
            report.append(f"   扣分详情: 规则扣分{total_rule_deduction:.1f} + 相似度扣分{total_similarity_deduction:.1f} = 总扣分{total_rule_deduction + total_similarity_deduction:.1f}")
            
            # 主要扣分原因
            if ds.deduction_reasons:
                main_reasons = ds.deduction_reasons[:2]  # 显示前2个主要原因
                for reason in main_reasons:
                    report.append(f"   {reason}")
            
            report.append("")
        
        # 改进建议
        report.append("💡 总体改进建议")
        report.append("=" * 40)
        
        # 统计最常见的扣分原因
        all_deduction_reasons = []
        for rec in recommendations:
            all_deduction_reasons.extend(rec.deduction_score.deduction_reasons)
        
        # 提取改进建议
        suggestions = self._generate_improvement_suggestions(recommendations, user_info)
        for suggestion in suggestions:
            report.append(f"  • {suggestion}")
        
        return "\n".join(report)
    
    def _generate_improvement_suggestions(self, recommendations: List[PolicyRecommendation], 
                                        user_info: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 统计扣分字段
        field_deductions = {}
        for rec in recommendations:
            for deduction in rec.deduction_score.rule_deductions:
                field = deduction['field']
                if field not in field_deductions:
                    field_deductions[field] = []
                field_deductions[field].append(deduction)
        
        # 根据高频扣分字段生成建议
        for field, deductions in field_deductions.items():
            if len(deductions) >= len(recommendations) * 0.3:  # 超过30%的政策都在此字段扣分
                if field == 'education':
                    suggestions.append("考虑提升学历水平，更多政策对学历有较高要求")
                elif field == 'age':
                    suggestions.append("部分政策有年龄限制，建议关注适合当前年龄段的政策")
                elif field == 'work_years':
                    suggestions.append("积累更多工作经验将有助于申请更多政策")
                elif field == 'talent_code':
                    suggestions.append("申请人才码认定可以显著提升政策匹配度")
                elif field == 'location':
                    suggestions.append("注意政策的地域限制，优先关注本地政策")
        
        # 相似度改进建议
        low_similarity_count = sum(1 for rec in recommendations 
                                 if any(d['field'] == 'keyword_similarity' and d['severity'] in ['critical', 'moderate'] 
                                       for d in rec.deduction_score.similarity_deductions))
        
        if low_similarity_count >= len(recommendations) * 0.5:
            suggestions.append("完善个人资料，增加专业技能和工作经历描述")
            suggestions.append("关注与您专业背景更相关的政策类型")
        
        # 优先推荐建议
        high_match_policies = [rec for rec in recommendations if rec.match_level == '高度匹配']
        if high_match_policies:
            top_policy = high_match_policies[0]
            suggestions.append(f"优先申请：{top_policy.policy_id}（{top_policy.policy_title}），匹配度最高")
        
        medium_match_policies = [rec for rec in recommendations if rec.match_level == '中度匹配']
        if medium_match_policies and len(high_match_policies) < 3:
            suggestions.append(f"备选方案：关注中度匹配的政策，如{medium_match_policies[0].policy_id}")
        
        return suggestions if suggestions else ["您的条件总体不错，建议重点关注排名靠前的政策"]
    
    def batch_recommend_for_all_users(self, users: List[Dict], policies: List[Dict], 
                                    output_dir: str = "deduction_recommendations"):
        """为所有用户批量生成推荐"""
        import os
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print(f"🚀 开始为{len(users)}个用户生成扣分制政策推荐...")
        print(f"📁 输出目录: {output_dir}")
        print(f"⚙️ 权重配置: 规则{self.deduction_weights['rule_weight']:.1%} + 相似度{self.deduction_weights['similarity_weight']:.1%}")
        print("=" * 60)
        
        # 为每个用户生成推荐
        for i, user_info in enumerate(users, 1):
            user_id = user_info.get('用户ID', f'User_{i}')
            print(f"📝 处理用户 {i}/{len(users)}: {user_id}")
            
            try:
                # 生成推荐
                recommendations = self.recommend_policies_for_user(user_info, policies)
                
                # 生成报告
                report = self.generate_user_recommendation_report(user_info, recommendations)
                
                # 保存文件
                filename = os.path.join(output_dir, f"recommendation_{user_id}.txt")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                # 简要统计
                high_match = len([r for r in recommendations if r.match_level == '高度匹配'])
                medium_match = len([r for r in recommendations if r.match_level == '中度匹配'])
                avg_score = sum(r.final_score for r in recommendations) / len(recommendations) if recommendations else 0
                
                print(f"   ✅ 完成 | 高度匹配:{high_match} 中度匹配:{medium_match} 平均分:{avg_score:.1f}")
                
            except Exception as e:
                print(f"   ❌ 失败: {e}")
        
        print("=" * 60)
        print("✅ 所有用户推荐生成完成！")
        
        # 生成汇总报告
        self._generate_batch_summary_report(users, policies, output_dir)
    
    def _generate_batch_summary_report(self, users: List[Dict], policies: List[Dict], output_dir: str):
        """生成批量推荐汇总报告"""
        print("📊 生成汇总统计报告...")
        
        summary = []
        summary.append("扣分制政策推荐系统 - 汇总报告")
        summary.append("=" * 80)
        summary.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"用户数量: {len(users)}")
        summary.append(f"政策数量: {len(policies)}")
        summary.append(f"算法配置: 规则权重{self.deduction_weights['rule_weight']:.1%} + 相似度权重{self.deduction_weights['similarity_weight']:.1%}")
        summary.append("")
        
        # 统计所有用户的推荐结果
        all_recommendations = []
        user_stats = []
        
        for user_info in users:
            try:
                recommendations = self.recommend_policies_for_user(user_info, policies)
                all_recommendations.extend(recommendations)
                
                high_match = len([r for r in recommendations if r.match_level == '高度匹配'])
                medium_match = len([r for r in recommendations if r.match_level == '中度匹配'])
                avg_score = sum(r.final_score for r in recommendations) / len(recommendations) if recommendations else 0
                
                user_stats.append({
                    'user_id': user_info.get('用户ID', ''),
                    'high_match': high_match,
                    'medium_match': medium_match,
                    'avg_score': avg_score,
                    'recommendations': recommendations
                })
            except:
                continue
        
        # 整体统计
        total_recommendations = len(all_recommendations)
        if total_recommendations > 0:
            overall_high = len([r for r in all_recommendations if r.match_level == '高度匹配'])
            overall_medium = len([r for r in all_recommendations if r.match_level == '中度匹配'])
            overall_low = len([r for r in all_recommendations if r.match_level == '低度匹配'])
            overall_improve = len([r for r in all_recommendations if r.match_level == '需改进'])
            
            overall_avg_score = sum(r.final_score for r in all_recommendations) / total_recommendations
            
            summary.append("📊 整体推荐统计")
            summary.append("-" * 40)
            summary.append(f"总推荐数: {total_recommendations}")
            summary.append(f"高度匹配: {overall_high} ({overall_high/total_recommendations:.1%})")
            summary.append(f"中度匹配: {overall_medium} ({overall_medium/total_recommendations:.1%})")
            summary.append(f"低度匹配: {overall_low} ({overall_low/total_recommendations:.1%})")
            summary.append(f"需改进: {overall_improve} ({overall_improve/total_recommendations:.1%})")
            summary.append(f"平均得分: {overall_avg_score:.1f}")
            summary.append("")
        
        # 用户表现排行
        summary.append("👥 用户匹配度排行（按高度匹配政策数）")
        summary.append("-" * 60)
        user_stats.sort(key=lambda x: x['high_match'], reverse=True)
        
        for i, stat in enumerate(user_stats[:10], 1):  # 显示前10名
            summary.append(f"{i:2d}. {stat['user_id']} | 高度匹配:{stat['high_match']} 平均分:{stat['avg_score']:.1f}")
        
        summary.append("")
        
        # 政策热度排行
        summary.append("🔥 政策推荐热度排行（按高度匹配用户数）")
        summary.append("-" * 60)
        
        policy_stats = {}
        for rec in all_recommendations:
            if rec.policy_id not in policy_stats:
                policy_stats[rec.policy_id] = {
                    'title': rec.policy_title,
                    'high_match': 0,
                    'medium_match': 0,
                    'total_score': 0,
                    'count': 0
                }
            
            policy_stats[rec.policy_id]['count'] += 1
            policy_stats[rec.policy_id]['total_score'] += rec.final_score
            
            if rec.match_level == '高度匹配':
                policy_stats[rec.policy_id]['high_match'] += 1
            elif rec.match_level == '中度匹配':
                policy_stats[rec.policy_id]['medium_match'] += 1
        
        # 按高度匹配用户数排序
        policy_ranking = sorted(policy_stats.items(), 
                              key=lambda x: x[1]['high_match'], reverse=True)
        
        for i, (policy_id, stats) in enumerate(policy_ranking[:10], 1):  # 显示前10名
            avg_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
            summary.append(f"{i:2d}. {policy_id} | 高度匹配用户:{stats['high_match']} 平均分:{avg_score:.1f}")
            summary.append(f"    {stats['title'][:50]}...")
        
        summary.append("")
        
        # 系统效果分析
        summary.append("📈 系统效果分析")
        summary.append("-" * 40)
        
        if user_stats:
            # 计算用户平均匹配政策数
            avg_high_match = sum(s['high_match'] for s in user_stats) / len(user_stats)
            avg_medium_match = sum(s['medium_match'] for s in user_stats) / len(user_stats)
            
            summary.append(f"用户平均高度匹配政策数: {avg_high_match:.1f}")
            summary.append(f"用户平均中度匹配政策数: {avg_medium_match:.1f}")
            summary.append(f"系统推荐精准度: {(overall_high + overall_medium)/total_recommendations:.1%}")
            
            # 扣分制效果
            summary.append(f"扣分制评分分布:")
            score_ranges = {
                '优秀(85-100)': len([r for r in all_recommendations if r.final_score >= 85]),
                '良好(65-84)': len([r for r in all_recommendations if 65 <= r.final_score < 85]),
                '一般(40-64)': len([r for r in all_recommendations if 40 <= r.final_score < 65]),
                '较差(0-39)': len([r for r in all_recommendations if r.final_score < 40])
            }
            
            for range_name, count in score_ranges.items():
                percentage = count / total_recommendations * 100 if total_recommendations > 0 else 0
                summary.append(f"  {range_name}: {count} ({percentage:.1f}%)")
        
        # 保存汇总报告
        summary_file = os.path.join(output_dir, "deduction_summary_report.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary))
        
        print(f"✅ 汇总报告已保存: {summary_file}")

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
                    users.append(user_data)
                    print(f"✅ 加载用户: {user_data.get('用户ID', filename)}")
            except Exception as e:
                print(f"❌ 加载失败 {filename}: {e}")
        
        return users

def main():
    """主函数"""
    print("🚀 扣分制政策推荐系统启动")
    print("=" * 60)
    
    # 初始化推荐器
    recommender = DeductionPolicyRecommender()
    
    # 加载数据
    print("📁 加载数据...")
    policies = recommender.load_policies()
    users = recommender.load_users()
    
    if not policies:
        print("❌ 没有加载到政策数据")
        return
    
    if not users:
        print("❌ 没有加载到用户数据")
        return
    
    print(f"\n✅ 数据加载完成：{len(policies)}个政策，{len(users)}个用户")
    
    # 显示当前配置
    print(f"\n⚙️ 当前权重配置:")
    print(f"   规则匹配权重: {recommender.deduction_weights['rule_weight']:.1%}")
    print(f"   相似度权重: {recommender.deduction_weights['similarity_weight']:.1%}")
    
    # 选择运行模式
    print(f"\n🎯 选择运行模式:")
    print("1. 单用户推荐示例")
    print("2. 批量推荐所有用户")
    print("3. 仅查看数据统计")
    
    try:
        choice = input("\n请选择 (1-3): ").strip()
        
        if choice == '1':
            # 单用户推荐示例
            if users:
                user_info = users[0]  # 使用第一个用户作为示例
                user_id = user_info.get('用户ID', 'Unknown')
                print(f"\n📝 为用户 {user_id} 生成推荐...")
                
                recommendations = recommender.recommend_policies_for_user(user_info, policies)
                report = recommender.generate_user_recommendation_report(user_info, recommendations)
                
                # 显示报告
                print("\n" + "="*80)
                print(report)
                print("="*80)
                
                # 保存到文件
                with open(f"sample_recommendation_{user_id}.txt", 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ 报告已保存为: sample_recommendation_{user_id}.txt")
        
        elif choice == '2':
            # 批量推荐
            print(f"\n🚀 开始批量推荐...")
            recommender.batch_recommend_for_all_users(users, policies)
            print(f"\n✅ 批量推荐完成！请查看 deduction_recommendations/ 目录")
        
        elif choice == '3':
            # 数据统计
            print(f"\n📊 数据统计:")
            print(f"   政策总数: {len(policies)}")
            print(f"   用户总数: {len(users)}")
            print(f"   预计生成推荐数: {len(users) * len(policies)}")
            
            # 显示部分政策和用户信息
            print(f"\n📋 政策列表（前5个）:")
            for i, policy in enumerate(policies[:5], 1):
                print(f"   {i}. {policy.get('政策编号', 'Unknown')} - {policy.get('标题', 'Unknown')}")
            
            print(f"\n👥 用户列表（前5个）:")
            for i, user in enumerate(users[:5], 1):
                user_id = user.get('用户ID', 'Unknown')
                education = user.get('最高学历', 'Unknown')
                major = user.get('专业', 'Unknown')
                print(f"   {i}. {user_id} - {education} - {major}")
        
        else:
            print("❌ 无效选择")
    
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()