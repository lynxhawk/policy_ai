import os
import json
import re
import math
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from collections import Counter
from datetime import datetime
import jieba
import jieba.analyse

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
    rule_match_score: float      # 正则规则匹配分数
    similarity_score: float      # 相似度匹配分数
    final_score: float          # 最终加权分数
    is_eligible: bool
    matched_rules: List[Dict]
    unmatched_rules: List[Dict]
    benefits: List[PolicyBenefit]
    recommendations: List[str]
    similarity_details: Dict    # 相似度计算详情

class EnhancedPolicyMatcher:
    """增强版政策匹配系统（正则+相似度）"""
    
    def __init__(self, policy_dir="policy_dataset", user_dir="user_dataset"):
        self.policy_dir = policy_dir
        self.user_dir = user_dir
        self._init_jieba()
        self._init_patterns()
        self._init_similarity_config()
        
    def _init_jieba(self):
        """初始化jieba分词"""
        custom_words = [
            '高校毕业生', '就业困难人员', '灵活就业', '创业担保贷款',
            '社保补贴', '人才码', '被征地人员', '职业培训', '见习补贴',
            '平湖市', '嘉兴市', '法定退休年龄', '小微企业'
        ]
        for word in custom_words:
            jieba.add_word(word, 10)
    
    def _init_similarity_config(self):
        """初始化相似度计算配置"""
        # 匹配权重配置
        self.match_weights = {
            'rule_weight': 0.6,        # 正则规则匹配权重
            'similarity_weight': 0.4   # 相似度匹配权重
        }
        
        # 用户信息字段权重
        self.user_field_weights = {
            '最高学历': 0.25,
            '专业': 0.2,
            '工作年限': 0.15,
            '籍贯': 0.15,
            '技能等级': 0.1,
            '就业状态': 0.1,
            '年龄': 0.05
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
    
    def _init_patterns(self):
        """初始化正则匹配模式"""
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
                    
                    if isinstance(user_data, dict):
                        users.append(user_data)
                        print(f"✅ 加载用户: {user_data.get('用户ID', filename)}")
                    else:
                        print(f"⚠️ 跳过非字典格式文件: {filename}")
                        
            except Exception as e:
                print(f"❌ 加载失败 {filename}: {e}")
        
        return users
    
    def load_policy_keywords(self, keywords_file: str = "policy_keywords.json") -> Dict[str, Dict]:
        """加载政策关键词数据"""
        if not os.path.exists(keywords_file):
            print(f"⚠️ 关键词文件不存在: {keywords_file}")
            return {}
        
        try:
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords_data = json.load(f)
            
            # 转换为以政策ID为键的字典
            policy_keywords = {}
            for item in keywords_data:
                policy_id = item.get('policy_id', '')
                if policy_id:
                    policy_keywords[policy_id] = item
            
            print(f"✅ 加载了 {len(policy_keywords)} 个政策的关键词数据")
            return policy_keywords
            
        except Exception as e:
            print(f"❌ 加载关键词文件失败: {e}")
            return {}
    
    def extract_user_keywords(self, user_info: Dict) -> List[str]:
        """提取用户信息关键词"""
        user_text = ""
        
        # 收集用户信息文本
        for key, value in user_info.items():
            if key != '用户ID' and key != '工作经历':
                user_text += str(value) + " "
        
        # 添加工作经历信息
        if '工作经历' in user_info:
            for work in user_info['工作经历']:
                user_text += str(work.get('公司名称', '')) + " "
                user_text += str(work.get('职位', '')) + " "
        
        # 使用jieba提取关键词
        try:
            keywords = jieba.analyse.extract_tags(user_text, topK=20)
            return keywords
        except:
            return []
    
    def calculate_text_similarity(self, text1_keywords: List[str], text2_keywords: List[str]) -> float:
        """计算两个关键词列表的相似度（余弦相似度）"""
        if not text1_keywords or not text2_keywords:
            return 0.0
        
        # 创建词汇表
        all_words = list(set(text1_keywords + text2_keywords))
        
        # 创建向量
        vector1 = [text1_keywords.count(word) for word in all_words]
        vector2 = [text2_keywords.count(word) for word in all_words]
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(a * a for a in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def calculate_semantic_similarity(self, user_info: Dict, policy_keywords: Dict) -> Dict:
        """计算用户信息与政策的语义相似度"""
        similarity_details = {
            'overall_similarity': 0.0,
            'field_similarities': {},
            'keyword_matches': [],
            'user_keywords': [],
            'policy_keywords': []
        }
        
        # 提取用户关键词
        user_keywords = self.extract_user_keywords(user_info)
        similarity_details['user_keywords'] = user_keywords
        
        # 获取政策关键词
        policy_kws = policy_keywords.get('keywords', [])
        target_kws = policy_keywords.get('target_group_keywords', [])
        condition_kws = policy_keywords.get('condition_keywords', [])
        
        all_policy_keywords = policy_kws + target_kws + condition_kws
        similarity_details['policy_keywords'] = all_policy_keywords
        
        # 计算整体相似度
        overall_sim = self.calculate_text_similarity(user_keywords, all_policy_keywords)
        similarity_details['overall_similarity'] = overall_sim
        
        # 计算各字段的相似度
        field_similarities = {}
        
        # 专业相似度
        if '专业' in user_info:
            user_major = str(user_info['专业'])
            major_keywords = jieba.analyse.extract_tags(user_major, topK=5)
            major_sim = self.calculate_text_similarity(major_keywords, all_policy_keywords)
            field_similarities['专业'] = major_sim
        
        # 学历相似度（基于等级）
        if '最高学历' in user_info:
            user_education = user_info['最高学历']
            education_sim = self._calculate_education_similarity(user_education, condition_kws)
            field_similarities['学历'] = education_sim
        
        # 地域相似度
        if '籍贯' in user_info:
            user_location = str(user_info['籍贯'])
            location_keywords = [user_location]
            location_sim = self.calculate_text_similarity(location_keywords, all_policy_keywords)
            field_similarities['地域'] = location_sim
        
        similarity_details['field_similarities'] = field_similarities
        
        # 找出关键词匹配
        matched_keywords = []
        for user_kw in user_keywords:
            for policy_kw in all_policy_keywords:
                if user_kw in policy_kw or policy_kw in user_kw:
                    matched_keywords.append((user_kw, policy_kw))
        
        similarity_details['keyword_matches'] = matched_keywords
        
        return similarity_details
    
    def _calculate_education_similarity(self, user_education: str, condition_keywords: List[str]) -> float:
        """计算学历相似度"""
        if not user_education:
            return 0.0
        
        user_level = self.education_levels.get(user_education, 0)
        
        # 检查政策中的学历要求
        max_similarity = 0.0
        for kw in condition_keywords:
            if kw in self.education_levels:
                required_level = self.education_levels[kw]
                # 计算学历匹配度
                if user_level >= required_level:
                    similarity = 1.0 - abs(user_level - required_level) / 7  # 7是最大学历等级
                else:
                    similarity = 0.5 - abs(user_level - required_level) / 14  # 不满足但有一定相似度
                max_similarity = max(max_similarity, similarity)
        
        return max(0.0, max_similarity)
    
    def extract_policy_rules(self, policy_content) -> List[PolicyRule]:
        """提取政策规则（支持字符串和数组格式）"""
        # 处理不同格式的内容
        if isinstance(policy_content, list):
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            content_text = policy_content
        else:
            print(f"⚠️ 未知的内容格式: {type(policy_content)}")
            return []
        
        rules = []
        
        for category, patterns in self.rule_patterns.items():
            for pattern_info in patterns:
                if len(pattern_info) == 3:
                    pattern, field, operator = pattern_info
                    
                    if pattern.startswith('r'):
                        # 正则表达式
                        regex_pattern = pattern[1:]
                        try:
                            matches = re.finditer(regex_pattern, content_text)
                            for match in matches:
                                try:
                                    if field in ['age', 'work_years', 'work_months', 'insurance_years', 'graduation_years', 'retirement_years_left']:
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
                            continue
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
        """提取政策福利"""
        if isinstance(policy_content, list):
            content_text = ' '.join(policy_content)
        elif isinstance(policy_content, str):
            content_text = policy_content
        else:
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
    
    def match_user_to_policy(self, user_info: Dict, policy_data: Dict, policy_keywords: Dict = None) -> MatchResult:
        """匹配用户与单个政策（正则+相似度）"""
        policy_content = policy_data.get('内容', '')
        
        # 1. 正则规则匹配
        rules = self.extract_policy_rules(policy_content)
        benefits = self.extract_policy_benefits(policy_content)
        
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
                
                recommendation = self._generate_recommendation(rule, gap)
                if recommendation:
                    recommendations.append(recommendation)
        
        # 计算正则规则匹配分数
        total_rules = len(rules)
        rule_match_score = len(matched_rules) / total_rules if total_rules > 0 else 0.8
        
        # 2. 相似度匹配
        similarity_details = {'overall_similarity': 0.0}
        similarity_score = 0.0
        
        if policy_keywords:
            policy_id = policy_data.get('政策编号', '')
            if policy_id in policy_keywords:
                similarity_details = self.calculate_semantic_similarity(
                    user_info, policy_keywords[policy_id]
                )
                similarity_score = similarity_details['overall_similarity']
        
        # 3. 计算最终加权分数
        final_score = (
            rule_match_score * self.match_weights['rule_weight'] +
            similarity_score * self.match_weights['similarity_weight']
        )
        
        # 判断是否符合条件
        is_eligible = rule_match_score >= 0.8 or (rule_match_score >= 0.6 and similarity_score >= 0.3)
        
        return MatchResult(
            policy_id=policy_data.get('政策编号', ''),
            policy_title=policy_data.get('标题', ''),
            rule_match_score=rule_match_score,
            similarity_score=similarity_score,
            final_score=final_score,
            is_eligible=is_eligible,
            matched_rules=matched_rules,
            unmatched_rules=unmatched_rules,
            benefits=benefits,
            recommendations=recommendations,
            similarity_details=similarity_details
        )
    
    def match_user_to_all_policies(self, user_info: Dict, policies: List[Dict], 
                                 policy_keywords: Dict = None) -> List[MatchResult]:
        """匹配用户与所有政策"""
        results = []
        
        for policy_data in policies:
            result = self.match_user_to_policy(user_info, policy_data, policy_keywords)
            results.append(result)
        
        # 按最终分数排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        
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
                return max(0, 60 - age)
            return None
        
        if field == 'graduation_years':
            grad_year = user_info.get('毕业年份')
            if grad_year:
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
    
    def generate_enhanced_user_match_report(self, user_info: Dict, match_results: List[MatchResult]) -> str:
        """生成增强版用户匹配报告（包含相似度分析）"""
        report = []
        user_id = user_info.get('用户ID', '未知')
        
        report.append(f"用户ID: {user_id}")
        report.append(f"学历: {user_info.get('最高学历', '未知')}")
        report.append(f"专业: {user_info.get('专业', '未知')}")
        report.append(f"工作年限: {user_info.get('工作年限', '未知')}年")
        report.append(f"籍贯: {user_info.get('籍贯', '未知')}")
        report.append("-" * 60)
        
        # 匹配统计
        total_policies = len(match_results)
        eligible_policies = len([r for r in match_results if r.is_eligible])
        
        report.append(f"总政策数: {total_policies}")
        report.append(f"符合条件: {eligible_policies}")
        report.append(f"符合率: {eligible_policies/total_policies:.1%}")
        
        # 分数统计
        avg_rule_score = sum(r.rule_match_score for r in match_results) / len(match_results)
        avg_similarity_score = sum(r.similarity_score for r in match_results) / len(match_results)
        avg_final_score = sum(r.final_score for r in match_results) / len(match_results)
        
        report.append(f"平均规则匹配分: {avg_rule_score:.1%}")
        report.append(f"平均相似度分: {avg_similarity_score:.1%}")
        report.append(f"平均综合分: {avg_final_score:.1%}")
        report.append("-" * 60)
        
        # 详细匹配结果
        for i, result in enumerate(match_results, 1):
            status = "✅" if result.is_eligible else "❌"
            report.append(f"{i}. {status} {result.policy_id} | 综合分: {result.final_score:.1%}")
            report.append(f"   标题: {result.policy_title}")
            
            # 分项得分
            report.append(f"   规则匹配: {result.rule_match_score:.1%} | 相似度: {result.similarity_score:.1%}")
            
            # 福利信息
            if result.benefits:
                benefit_info = " | ".join([f"{b.benefit_type}:{b.amount}" for b in result.benefits])
                report.append(f"   福利: {benefit_info}")
            
            # 满足条件数量
            matched_count = len(result.matched_rules)
            unmatched_count = len(result.unmatched_rules)
            report.append(f"   满足条件: {matched_count}项 | 不满足: {unmatched_count}项")
            
            # 相似度详情
            if result.similarity_details:
                sim_details = result.similarity_details
                if sim_details.get('keyword_matches'):
                    matches = sim_details['keyword_matches'][:3]  # 显示前3个关键词匹配
                    match_str = " | ".join([f"{m[0]}↔{m[1]}" for m in matches])
                    report.append(f"   关键词匹配: {match_str}")
            
            # 关键不满足条件
            if result.unmatched_rules and not result.is_eligible:
                key_issues = [unmatch['gap'] for unmatch in result.unmatched_rules[:2]]
                report.append(f"   主要问题: {' | '.join(key_issues)}")
            
            report.append("")
        
        return "\n".join(report)
    
    def generate_enhanced_policy_match_report(self, policy_data: Dict, all_users: List[Dict], 
                                            policy_keywords: Dict = None) -> str:
        """生成增强版政策匹配报告"""
        policy_id = policy_data.get('政策编号', '未知')
        policy_title = policy_data.get('标题', '未知')
        
        report = []
        report.append(f"政策编号: {policy_id}")
        report.append(f"政策标题: {policy_title}")
        report.append("-" * 60)
        
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
        
        # 政策关键词信息
        if policy_keywords and policy_id in policy_keywords:
            pk = policy_keywords[policy_id]
            if pk.get('keywords'):
                report.append("政策关键词:")
                report.append(f"  - 核心词: {', '.join(pk['keywords'][:10])}")
            if pk.get('target_group_keywords'):
                report.append(f"  - 目标人群: {', '.join(pk['target_group_keywords'])}")
        
        report.append("-" * 60)
        
        # 匹配统计
        user_results = []
        eligible_users = 0
        total_users = len(all_users)
        
        rule_scores = []
        similarity_scores = []
        final_scores = []
        
        for user_info in all_users:
            result = self.match_user_to_policy(user_info, policy_data, policy_keywords)
            user_results.append((user_info, result))
            if result.is_eligible:
                eligible_users += 1
            
            rule_scores.append(result.rule_match_score)
            similarity_scores.append(result.similarity_score)
            final_scores.append(result.final_score)
        
        report.append(f"总用户数: {total_users}")
        report.append(f"符合条件用户: {eligible_users}")
        report.append(f"政策适用率: {eligible_users/total_users:.1%}")
        
        # 分数统计
        avg_rule_score = sum(rule_scores) / len(rule_scores)
        avg_similarity_score = sum(similarity_scores) / len(similarity_scores)
        avg_final_score = sum(final_scores) / len(final_scores)
        
        report.append(f"平均规则匹配分: {avg_rule_score:.1%}")
        report.append(f"平均相似度分: {avg_similarity_score:.1%}")
        report.append(f"平均综合分: {avg_final_score:.1%}")
        report.append("-" * 60)
        
        # 用户匹配详情
        report.append("用户匹配详情:")
        
        # 按综合分数排序
        user_results.sort(key=lambda x: x[1].final_score, reverse=True)
        
        for user_info, result in user_results:
            user_id = user_info.get('用户ID', '未知')
            status = "✅" if result.is_eligible else "❌"
            
            report.append(f"{status} {user_id} | 综合分: {result.final_score:.1%}")
            report.append(f"   规则:{result.rule_match_score:.1%} | 相似度:{result.similarity_score:.1%}")
            
            # 用户基本信息
            user_details = []
            if '最高学历' in user_info:
                user_details.append(f"学历:{user_info['最高学历']}")
            if '专业' in user_info:
                user_details.append(f"专业:{user_info['专业']}")
            if '工作年限' in user_info:
                user_details.append(f"工作年限:{user_info['工作年限']}年")
            if '籍贯' in user_info:
                user_details.append(f"籍贯:{user_info['籍贯']}")
            
            if user_details:
                report.append(f"   用户信息: {' | '.join(user_details)}")
            
            # 匹配情况
            matched_count = len(result.matched_rules)
            unmatched_count = len(result.unmatched_rules)
            report.append(f"   匹配情况: 满足{matched_count}项 | 不满足{unmatched_count}项")
            
            # 相似度详情
            if result.similarity_details and result.similarity_details.get('keyword_matches'):
                matches = result.similarity_details['keyword_matches'][:2]
                if matches:
                    match_str = " | ".join([f"{m[0]}↔{m[1]}" for m in matches])
                    report.append(f"   关键词匹配: {match_str}")
            
            # 不满足的关键条件
            if result.unmatched_rules:
                key_issues = [unmatch['gap'] for unmatch in result.unmatched_rules[:2]]
                report.append(f"   主要问题: {' | '.join(key_issues)}")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_enhanced_reports(self, users: List[Dict], policies: List[Dict], 
                            policy_keywords: Dict = None, output_dir: str = "enhanced_match_reports"):
        """保存增强版匹配报告"""
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
        
        print(f"\n📁 创建增强版报告目录: {output_dir}")
        
        # 生成用户匹配报告
        print("\n📝 生成增强版用户匹配报告...")
        for user_info in users:
            user_id = user_info.get('用户ID', 'Unknown')
            print(f"  处理用户: {user_id}")
            
            # 匹配所有政策
            match_results = self.match_user_to_all_policies(user_info, policies, policy_keywords)
            
            # 生成报告
            report = self.generate_enhanced_user_match_report(user_info, match_results)
            
            # 保存文件
            filename = os.path.join(user_reports_dir, f"enhanced_user_{user_id}_matches.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
        
        print(f"✅ 增强版用户报告保存完成: {len(users)}个文件")
        
        # 生成政策匹配报告
        print("\n📝 生成增强版政策匹配报告...")
        for policy_data in policies:
            policy_id = policy_data.get('政策编号', 'Unknown')
            print(f"  处理政策: {policy_id}")
            
            # 生成报告
            report = self.generate_enhanced_policy_match_report(policy_data, users, policy_keywords)
            
            # 保存文件
            filename = os.path.join(policy_reports_dir, f"enhanced_policy_{policy_id}_matches.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
        
        print(f"✅ 增强版政策报告保存完成: {len(policies)}个文件")
        
        # 生成增强版汇总报告
        self._generate_enhanced_summary_report(users, policies, policy_keywords, output_dir)
    
    def _generate_enhanced_summary_report(self, users: List[Dict], policies: List[Dict], 
                                        policy_keywords: Dict, output_dir: str):
        """生成增强版汇总报告"""
        print("\n📊 生成增强版汇总报告...")
        
        summary = []
        summary.append("增强版政策匹配系统汇总报告")
        summary.append("=" * 80)
        summary.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"用户数量: {len(users)}")
        summary.append(f"政策数量: {len(policies)}")
        summary.append(f"匹配算法: 正则规则匹配 + 语义相似度匹配")
        summary.append(f"规则权重: {self.match_weights['rule_weight']:.1%}")
        summary.append(f"相似度权重: {self.match_weights['similarity_weight']:.1%}")
        summary.append("")
        
        # 用户匹配统计
        summary.append("用户匹配统计:")
        summary.append("-" * 40)
        
        user_stats = []
        total_rule_scores = 0
        total_similarity_scores = 0
        total_final_scores = 0
        total_matches = 0
        
        for user_info in users:
            user_id = user_info.get('用户ID', 'Unknown')
            match_results = self.match_user_to_all_policies(user_info, policies, policy_keywords)
            
            eligible_count = len([r for r in match_results if r.is_eligible])
            avg_rule_score = sum(r.rule_match_score for r in match_results) / len(match_results)
            avg_similarity_score = sum(r.similarity_score for r in match_results) / len(match_results)
            avg_final_score = sum(r.final_score for r in match_results) / len(match_results)
            
            total_rule_scores += avg_rule_score
            total_similarity_scores += avg_similarity_score
            total_final_scores += avg_final_score
            total_matches += eligible_count
            
            user_stats.append({
                'user_id': user_id,
                'eligible_policies': eligible_count,
                'avg_rule_score': avg_rule_score,
                'avg_similarity_score': avg_similarity_score,
                'avg_final_score': avg_final_score
            })
            
            summary.append(f"{user_id}: 符合{eligible_count}个政策")
            summary.append(f"  规则:{avg_rule_score:.1%} | 相似度:{avg_similarity_score:.1%} | 综合:{avg_final_score:.1%}")
        
        summary.append("")
        
        # 政策匹配统计
        summary.append("政策匹配统计:")
        summary.append("-" * 40)
        
        for policy_data in policies:
            policy_id = policy_data.get('政策编号', 'Unknown')
            eligible_users = 0
            rule_scores = []
            similarity_scores = []
            final_scores = []
            
            for user_info in users:
                result = self.match_user_to_policy(user_info, policy_data, policy_keywords)
                if result.is_eligible:
                    eligible_users += 1
                rule_scores.append(result.rule_match_score)
                similarity_scores.append(result.similarity_score)
                final_scores.append(result.final_score)
            
            avg_rule = sum(rule_scores) / len(rule_scores)
            avg_sim = sum(similarity_scores) / len(similarity_scores)
            avg_final = sum(final_scores) / len(final_scores)
            
            coverage_rate = eligible_users / len(users) if users else 0
            summary.append(f"{policy_id}: 适用于{eligible_users}个用户 (覆盖率: {coverage_rate:.1%})")
            summary.append(f"  规则:{avg_rule:.1%} | 相似度:{avg_sim:.1%} | 综合:{avg_final:.1%}")
        
        summary.append("")
        
        # 整体统计
        overall_avg_rule = total_rule_scores / len(users)
        overall_avg_similarity = total_similarity_scores / len(users)
        overall_avg_final = total_final_scores / len(users)
        total_possible = len(users) * len(policies)
        overall_match_rate = total_matches / total_possible if total_possible > 0 else 0
        
        summary.append("整体统计:")
        summary.append("-" * 40)
        summary.append(f"总匹配数: {total_matches}")
        summary.append(f"总可能匹配数: {total_possible}")
        summary.append(f"整体匹配率: {overall_match_rate:.1%}")
        summary.append(f"平均规则匹配分: {overall_avg_rule:.1%}")
        summary.append(f"平均相似度分: {overall_avg_similarity:.1%}")
        summary.append(f"平均综合分: {overall_avg_final:.1%}")
        
        summary.append("")
        
        # 算法效果分析
        summary.append("算法效果分析:")
        summary.append("-" * 40)
        
        # 统计单独使用规则匹配vs综合匹配的差异
        rule_only_matches = 0
        combined_matches = 0
        
        for user_info in users:
            match_results = self.match_user_to_all_policies(user_info, policies, policy_keywords)
            for result in match_results:
                if result.rule_match_score >= 0.8:
                    rule_only_matches += 1
                if result.is_eligible:
                    combined_matches += 1
        
        improvement = combined_matches - rule_only_matches
        improvement_rate = improvement / rule_only_matches if rule_only_matches > 0 else 0
        
        summary.append(f"仅规则匹配: {rule_only_matches} 个匹配")
        summary.append(f"综合匹配: {combined_matches} 个匹配")
        summary.append(f"相似度算法贡献: +{improvement} 个匹配 ({improvement_rate:.1%})")
        
        # 保存汇总报告
        summary_file = os.path.join(output_dir, "enhanced_summary_report.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary))
        
        print(f"✅ 增强版汇总报告保存完成: {summary_file}")

def main():
    """主函数"""
    print("🚀 增强版政策匹配系统启动")
    print("=" * 60)
    
    # 初始化匹配器
    matcher = EnhancedPolicyMatcher()
    
    # 加载数据
    print("\n📁 加载数据...")
    policies = matcher.load_policies()
    users = matcher.load_users()
    policy_keywords = matcher.load_policy_keywords()
    
    if not policies:
        print("❌ 没有加载到政策数据")
        return
    
    if not users:
        print("❌ 没有加载到用户数据")
        return
    
    print(f"\n✅ 数据加载完成：{len(policies)}个政策，{len(users)}个用户")
    if policy_keywords:
        print(f"✅ 关键词数据：{len(policy_keywords)}个政策")
    else:
        print("⚠️ 未找到关键词数据，将仅使用规则匹配")
    
    # 生成增强版报告
    matcher.save_enhanced_reports(users, policies, policy_keywords)
    
    print("\n🎉 增强版报告生成完成！")
    print("\n📂 报告文件结构：")
    print("enhanced_match_reports/")
    print("├── user_reports/")
    print("│   ├── enhanced_user_U001_matches.txt")
    print("│   └── ...")
    print("├── policy_reports/")
    print("│   ├── enhanced_policy_POL0001_matches.txt")
    print("│   └── ...")
    print("└── enhanced_summary_report.txt")

if __name__ == "__main__":
    main()