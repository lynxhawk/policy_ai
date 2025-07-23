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
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from datetime import datetime
import jieba
import jieba.analyse

@dataclass
class PolicyKeywords:
    """政策关键词数据类"""
    policy_id: str
    title: str
    keywords: List[str]          # 关键词列表
    keyword_scores: Dict[str, float]  # 关键词权重分数
    entities: List[str]          # 实体词（地名、机构名等）
    benefit_keywords: List[str]  # 福利相关关键词
    condition_keywords: List[str] # 条件相关关键词
    target_group_keywords: List[str] # 目标人群关键词
    extracted_time: str          # 提取时间

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

class PolicyKeywordExtractor:
    """政策关键词提取器"""
    
    def __init__(self):
        self._init_jieba()
        self._init_keyword_dict()
        
    def _init_jieba(self):
        """初始化jieba分词和关键词提取"""
        # 添加自定义词典
        custom_words = [
            ('高校毕业生', 10), ('就业困难人员', 10), ('灵活就业', 10),
            ('创业担保贷款', 10), ('社保补贴', 10), ('人才码', 10),
            ('被征地人员', 10), ('职业培训', 10), ('见习补贴', 10),
            ('平湖市', 10), ('嘉兴市', 10), ('法定退休年龄', 10),
            ('小微企业', 10), ('中小微企业', 10), ('事业单位', 10),
            ('民办非企业', 10), ('租房补贴', 10), ('人才公寓', 10),
            ('一次性补贴', 8), ('创业孵化', 8), ('技能培训', 8),
            ('就业见习', 8), ('社会保险', 8), ('基本生活保障', 8)
        ]
        
        for word, freq in custom_words:
            jieba.add_word(word, freq)
            
    def _init_keyword_dict(self):
        """初始化关键词分类词典"""
        # 福利相关关键词
        self.benefit_keywords = {
            '补贴': ['补贴', '补助', '资助', '津贴', '奖励'],
            '贷款': ['贷款', '借款', '融资', '资金支持'],
            '减免': ['减免', '减征', '免缴', '优惠'],
            '培训': ['培训', '教育', '学习', '技能提升'],
            '服务': ['服务', '指导', '咨询', '帮扶']
        }
        
        # 条件相关关键词
        self.condition_keywords = {
            '年龄': ['年龄', '周岁', '退休年龄', '法定退休'],
            '学历': ['学历', '文凭', '本科', '专科', '硕士', '博士', '高中', '初中'],
            '工作': ['工作年限', '从业', '就业', '创业', '经营'],
            '地域': ['平湖', '本市', '市域', '嘉兴', '户籍', '居住'],
            '状态': ['困难', '失业', '灵活就业', '在职', '离职'],
            '企业': ['企业', '单位', '公司', '机构', '组织']
        }
        
        # 目标人群关键词
        self.target_group_keywords = {
            '毕业生': ['毕业生', '大学生', '应届', '往届'],
            '就业困难': ['就业困难', '失业', '下岗', '待业'],
            '创业者': ['创业', '创办', '自主创业', '初次创业'],
            '人才': ['人才', '专业人才', '高层次人才', '技能人才'],
            '农民': ['农民', '农村', '农业', '被征地'],
            '退役军人': ['退役军人', '军人', '转业'],
            '残疾人': ['残疾人', '残障', '特殊群体'],
            '老年人': ['老年', '养老', '退休'],
            '企业职工': ['职工', '员工', '从业人员']
        }
        
        # 实体识别词典
        self.entity_keywords = {
            '地名': ['平湖市', '嘉兴市', '浙江省', '北京市', '上海市', '杭州市'],
            '机构': ['人力社保局', '财政局', '教育局', '民政局', '税务局', '银行'],
            '政策法规': ['通知', '办法', '意见', '规定', '条例', '实施方案']
        }
    
    def extract_keywords_from_policy(self, policy_data: Dict) -> PolicyKeywords:
        """从单个政策中提取关键词"""
        policy_id = policy_data.get('政策编号', '')
        title = policy_data.get('标题', '')
        content = policy_data.get('内容', '')
        
        # 处理内容格式
        if isinstance(content, list):
            content_text = ' '.join(content)
        else:
            content_text = str(content)
        
        # 合并标题和内容
        full_text = title + ' ' + content_text
        
        # 1. 使用TF-IDF提取关键词
        keywords_tfidf = self._extract_tfidf_keywords(full_text)
        
        # 2. 使用TextRank提取关键词
        keywords_textrank = self._extract_textrank_keywords(full_text)
        
        # 3. 合并并评分
        all_keywords = self._merge_keywords(keywords_tfidf, keywords_textrank)
        
        # 4. 分类提取专门关键词
        benefit_kws = self._extract_benefit_keywords(full_text)
        condition_kws = self._extract_condition_keywords(full_text)
        target_kws = self._extract_target_group_keywords(full_text)
        entities = self._extract_entities(full_text)
        
        # 5. 去重和过滤
        final_keywords = self._filter_keywords(list(all_keywords.keys()))
        
        return PolicyKeywords(
            policy_id=policy_id,
            title=title,
            keywords=final_keywords[:20],  # 取前20个关键词
            keyword_scores=dict(list(all_keywords.items())[:20]),
            entities=entities,
            benefit_keywords=benefit_kws,
            condition_keywords=condition_kws,
            target_group_keywords=target_kws,
            extracted_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def _extract_tfidf_keywords(self, text: str, topK: int = 30) -> Dict[str, float]:
        """使用TF-IDF提取关键词"""
        try:
            keywords = jieba.analyse.extract_tags(
                text, 
                topK=topK, 
                withWeight=True, 
                allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn', 'a', 'ad')
            )
            return dict(keywords)
        except:
            return {}
    
    def _extract_textrank_keywords(self, text: str, topK: int = 30) -> Dict[str, float]:
        """使用TextRank提取关键词"""
        try:
            keywords = jieba.analyse.textrank(
                text, 
                topK=topK, 
                withWeight=True, 
                allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vd', 'vn', 'a', 'ad')
            )
            return dict(keywords)
        except:
            return {}
    
    def _merge_keywords(self, tfidf_kws: Dict[str, float], textrank_kws: Dict[str, float]) -> Dict[str, float]:
        """合并两种算法的关键词结果"""
        merged = {}
        
        # 合并关键词，取平均分
        all_keywords = set(tfidf_kws.keys()) | set(textrank_kws.keys())
        
        for kw in all_keywords:
            tfidf_score = tfidf_kws.get(kw, 0)
            textrank_score = textrank_kws.get(kw, 0)
            
            # 如果两个算法都提取到了，给予更高权重
            if tfidf_score > 0 and textrank_score > 0:
                merged[kw] = (tfidf_score + textrank_score) * 1.5
            else:
                merged[kw] = tfidf_score + textrank_score
        
        # 按分数排序
        return dict(sorted(merged.items(), key=lambda x: x[1], reverse=True))
    
    def _extract_benefit_keywords(self, text: str) -> List[str]:
        """提取福利相关关键词"""
        benefit_kws = []
        
        for category, keywords in self.benefit_keywords.items():
            for kw in keywords:
                if kw in text:
                    benefit_kws.append(kw)
        
        # 使用正则表达式提取金额、比例等
        amount_patterns = [
            r'(\d+)万?元', r'(\d+)%', r'每月(\d+)元', 
            r'每年(\d+)元', r'不超过(\d+)元'
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    benefit_kws.extend([m for m in match if m])
                else:
                    benefit_kws.append(match)
        
        return list(set(benefit_kws))
    
    def _extract_condition_keywords(self, text: str) -> List[str]:
        """提取条件相关关键词"""
        condition_kws = []
        
        for category, keywords in self.condition_keywords.items():
            for kw in keywords:
                if kw in text:
                    condition_kws.append(kw)
        
        # 提取具体的条件数值
        condition_patterns = [
            r'(\d+)周岁以上', r'(\d+)年以上', r'(\d+)个月',
            r'([A-G])类.*?人才码', r'毕业(\d+)年'
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    condition_kws.extend([m for m in match if m])
                else:
                    condition_kws.append(match)
        
        return list(set(condition_kws))
    
    def _extract_target_group_keywords(self, text: str) -> List[str]:
        """提取目标人群关键词"""
        target_kws = []
        
        for category, keywords in self.target_group_keywords.items():
            for kw in keywords:
                if kw in text:
                    target_kws.append(kw)
        
        return list(set(target_kws))
    
    def _extract_entities(self, text: str) -> List[str]:
        """提取实体词"""
        entities = []
        
        for category, keywords in self.entity_keywords.items():
            for kw in keywords:
                if kw in text:
                    entities.append(kw)
        
        # 使用正则提取更多实体
        entity_patterns = [
            r'([^，。、！？\s]{2,6}市)', r'([^，。、！？\s]{2,6}局)',
            r'([^，。、！？\s]{2,6}部)', r'([^，。、！？\s]{2,10}有限公司)'
        ]
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        return list(set(entities))
    
    def _filter_keywords(self, keywords: List[str]) -> List[str]:
        """过滤关键词"""
        # 过滤停用词和无意义词
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那'
        }
        
        filtered = []
        for kw in keywords:
            if (len(kw) >= 2 and 
                kw not in stop_words and 
                not kw.isdigit() and 
                not all(c in '，。！？、' for c in kw)):
                filtered.append(kw)
        
        return filtered

class DeductionPolicyRecommender:
    """扣分制政策推荐系统"""
    
    def __init__(self, policy_dir="policy_dataset", user_dir="user_dataset"):
        self.policy_dir = policy_dir
        self.user_dir = user_dir
        self.keyword_extractor = PolicyKeywordExtractor()  # 集成关键词提取器
        self.policy_keywords_cache = {}  # 缓存政策关键词
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
    
    def load_or_extract_policy_keywords(self, keywords_file: str = "policy_keywords.json", 
                                       force_extract: bool = False) -> Dict[str, PolicyKeywords]:
        """加载或提取政策关键词"""
        if not force_extract and os.path.exists(keywords_file):
            print(f"📁 从文件加载政策关键词: {keywords_file}")
            return self._load_keywords_from_file(keywords_file)
        else:
            print("🔍 实时提取政策关键词...")
            return self._extract_all_policy_keywords(keywords_file)
    
    def _load_keywords_from_file(self, keywords_file: str) -> Dict[str, PolicyKeywords]:
        """从文件加载关键词"""
        try:
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords_data = json.load(f)
            
            policy_keywords = {}
            for data in keywords_data:
                pk = PolicyKeywords(**data)
                policy_keywords[pk.policy_id] = pk
            
            print(f"✅ 加载了 {len(policy_keywords)} 个政策的关键词")
            return policy_keywords
        except Exception as e:
            print(f"❌ 加载关键词文件失败: {e}")
            return {}
    
    def _extract_all_policy_keywords(self, keywords_file: str) -> Dict[str, PolicyKeywords]:
        """提取所有政策关键词"""
        policies = self.load_policies()
        policy_keywords = {}
        
        print(f"🔍 开始提取 {len(policies)} 个政策的关键词...")
        
        for i, policy_data in enumerate(policies, 1):
            policy_id = policy_data.get('政策编号', f'Policy_{i}')
            print(f"  {i:2d}. 处理 {policy_id}")
            
            try:
                keywords_result = self.keyword_extractor.extract_keywords_from_policy(policy_data)
                policy_keywords[policy_id] = keywords_result
                
                print(f"      关键词: {', '.join(keywords_result.keywords[:5])}...")
                print(f"      福利词: {', '.join(keywords_result.benefit_keywords[:3])}")
                print(f"      条件词: {', '.join(keywords_result.condition_keywords[:3])}")
            except Exception as e:
                print(f"❌ 处理失败 {policy_id}: {e}")
        
        # 保存到文件
        self._save_keywords_to_file(policy_keywords, keywords_file)
        
        return policy_keywords
    
    def _save_keywords_to_file(self, policy_keywords: Dict[str, PolicyKeywords], 
                              keywords_file: str):
        """保存关键词到文件"""
        keywords_data = []
        for pk in policy_keywords.values():
            keywords_data.append(asdict(pk))
        
        with open(keywords_file, 'w', encoding='utf-8') as f:
            json.dump(keywords_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 关键词提取结果已保存到: {keywords_file}")
    
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
    
    def calculate_enhanced_similarity(self, user_info: Dict, policy_keywords: PolicyKeywords) -> Dict:
        """计算增强版相似度（使用分类关键词）"""
        similarity_details = {
            'overall_similarity': 0.0,
            'professional_similarity': 0.0,
            'benefit_relevance': 0.0,
            'condition_similarity': 0.0,
            'keyword_matches': [],
            'user_keywords': [],
            'policy_keywords': policy_keywords.keywords
        }
        
        # 提取用户关键词
        user_keywords = self.extract_user_keywords(user_info)
        similarity_details['user_keywords'] = user_keywords
        
        # 1. 专业匹配度计算
        user_major = user_info.get('专业', '')
        professional_sim = self._calculate_professional_similarity(
            user_major, policy_keywords.target_group_keywords
        )
        similarity_details['professional_similarity'] = professional_sim
        
        # 2. 福利相关性计算
        benefit_relevance = self._calculate_benefit_relevance(
            user_info, policy_keywords.benefit_keywords
        )
        similarity_details['benefit_relevance'] = benefit_relevance
        
        # 3. 条件相似度计算
        condition_sim = self._calculate_condition_similarity(
            user_info, policy_keywords.condition_keywords
        )
        similarity_details['condition_similarity'] = condition_sim
        
        # 4. 整体关键词相似度
        overall_sim = self.calculate_keyword_similarity(user_keywords, policy_keywords.keywords)
        
        # 5. 加权计算最终相似度
        final_similarity = (
            overall_sim * 0.4 +
            professional_sim * 0.3 +
            benefit_relevance * 0.2 +
            condition_sim * 0.1
        )
        
        similarity_details['overall_similarity'] = final_similarity
        
        # 6. 找出关键词匹配
        matched_keywords = []
        all_policy_keywords = (policy_keywords.keywords + 
                              policy_keywords.target_group_keywords + 
                              policy_keywords.benefit_keywords)
        
        for user_kw in user_keywords:
            for policy_kw in all_policy_keywords:
                if user_kw in policy_kw or policy_kw in user_kw:
                    matched_keywords.append((user_kw, policy_kw))
        
        similarity_details['keyword_matches'] = matched_keywords
        
        return similarity_details
    
    def _calculate_professional_similarity(self, user_major: str, target_keywords: List[str]) -> float:
        """计算专业匹配度"""
        if not user_major or not target_keywords:
            return 0.0
        
        user_major_keywords = jieba.analyse.extract_tags(user_major, topK=5)
        
        # 检查专业关键词与目标人群关键词的匹配
        match_score = 0.0
        for user_kw in user_major_keywords:
            for target_kw in target_keywords:
                if user_kw in target_kw or target_kw in user_kw:
                    match_score += 0.2
                    
        # 特殊专业匹配规则
        tech_majors = ['计算机', '软件', '信息', '电子', '网络', '数据']
        business_majors = ['管理', '经济', '金融', '会计', '市场']
        
        user_major_lower = user_major.lower()
        is_tech = any(tech in user_major_lower for tech in tech_majors)
        is_business = any(business in user_major_lower for business in business_majors)
        
        # 检查政策是否针对技术人才或商业人才
        target_text = ' '.join(target_keywords).lower()
        if is_tech and any(tech in target_text for tech in ['技术', '信息', '科技', '研发']):
            match_score += 0.3
        if is_business and any(biz in target_text for biz in ['创业', '管理', '经营', '金融']):
            match_score += 0.3
            
        return min(1.0, match_score)
    
    def _calculate_benefit_relevance(self, user_info: Dict, benefit_keywords: List[str]) -> float:
        """计算福利相关性"""
        if not benefit_keywords:
            return 0.0
        
        relevance_score = 0.0
        
        # 根据用户状态判断福利相关性
        work_years = user_info.get('工作年限', 0)
        education = user_info.get('最高学历', '')
        
        # 新毕业生更关注就业补贴
        if work_years <= 2:
            if any(kw in benefit_keywords for kw in ['就业', '见习', '培训']):
                relevance_score += 0.3
        
        # 有经验人员更关注创业支持
        if work_years >= 3:
            if any(kw in benefit_keywords for kw in ['创业', '贷款', '资助']):
                relevance_score += 0.3
        
        # 高学历人员更关注人才政策
        if education in ['本科', '硕士', '博士']:
            if any(kw in benefit_keywords for kw in ['人才', '补贴', '住房']):
                relevance_score += 0.2
        
        # 基础福利相关性
        if benefit_keywords:
            relevance_score += 0.2
            
        return min(1.0, relevance_score)
    
    def _calculate_condition_similarity(self, user_info: Dict, condition_keywords: List[str]) -> float:
        """计算条件相似度"""
        if not condition_keywords:
            return 0.0
        
        similarity_score = 0.0
        
        # 学历相关
        user_education = user_info.get('最高学历', '')
        if user_education and any(edu in condition_keywords for edu in ['学历', '本科', '专科', '硕士']):
            similarity_score += 0.3
        
        # 年龄相关
        if any(age in condition_keywords for age in ['年龄', '周岁']):
            similarity_score += 0.2
        
        # 工作经验相关
        if user_info.get('工作年限', 0) > 0 and any(work in condition_keywords for work in ['工作', '从业', '经验']):
            similarity_score += 0.3
        
        # 地域相关
        user_location = user_info.get('籍贯', '')
        if user_location and any(loc in condition_keywords for loc in ['平湖', '嘉兴', '本市']):
            similarity_score += 0.2
            
        return min(1.0, similarity_score)
    
    def calculate_deduction_score(self, user_info: Dict, policy_data: Dict, 
                                policy_keywords: PolicyKeywords = None) -> DeductionScore:
        """计算扣分制分数（使用增强版相似度）"""
        deduction_score = DeductionScore()
        
        # 1. 提取政策要求
        requirements = self.extract_policy_requirements(policy_data.get('内容', ''))
        
        # 2. 如果没有预提取的关键词，实时提取
        if policy_keywords is None:
            policy_keywords = self.keyword_extractor.extract_keywords_from_policy(policy_data)
        
        # 3. 计算规则匹配扣分
        rule_deductions = self._calculate_rule_deductions(user_info, requirements)
        deduction_score.rule_deductions = rule_deductions
        
        # 4. 计算增强版相似度扣分
        similarity_details = self.calculate_enhanced_similarity(user_info, policy_keywords)
        similarity_deductions = self._calculate_enhanced_similarity_deductions(
            user_info, similarity_details
        )
        deduction_score.similarity_deductions = similarity_deductions
        
        # 5. 计算总扣分
        total_rule_deduction = sum(d['deduction'] for d in rule_deductions)
        total_similarity_deduction = sum(d['deduction'] for d in similarity_deductions)
        
        weighted_rule_deduction = total_rule_deduction * self.deduction_weights['rule_weight']
        weighted_similarity_deduction = total_similarity_deduction * self.deduction_weights['similarity_weight']
        
        total_deduction = weighted_rule_deduction + weighted_similarity_deduction
        
        # 6. 计算最终分数
        deduction_score.final_score = max(0, deduction_score.base_score - total_deduction)
        
        # 7. 生成扣分原因
        deduction_score.deduction_reasons = self._generate_deduction_reasons(
            rule_deductions, similarity_deductions
        )
        
        return deduction_score
    
    def _calculate_enhanced_similarity_deductions(self, user_info: Dict, similarity_details: Dict) -> List[Dict]:
        """计算增强版相似度扣分"""
        deductions = []
        
        overall_sim = similarity_details['overall_similarity']
        professional_sim = similarity_details['professional_similarity']
        benefit_relevance = similarity_details['benefit_relevance']
        condition_sim = similarity_details['condition_similarity']
        
        # 1. 整体相似度扣分
        if overall_sim == 0:
            deductions.append({
                'reason': '关键词完全不匹配',
                'deduction': 25,
                'severity': 'critical',
                'field': 'overall_similarity',
                'similarity_score': overall_sim
            })
        elif overall_sim < 0.2:
            deductions.append({
                'reason': '关键词相似度很低',
                'deduction': 18,
                'severity': 'critical',
                'field': 'overall_similarity',
                'similarity_score': overall_sim
            })
        elif overall_sim < 0.4:
            deductions.append({
                'reason': '关键词相似度较低',
                'deduction': 12,
                'severity': 'moderate',
                'field': 'overall_similarity',
                'similarity_score': overall_sim
            })
        elif overall_sim < 0.6:
            deductions.append({
                'reason': '关键词相似度中等',
                'deduction': 6,
                'severity': 'minor',
                'field': 'overall_similarity',
                'similarity_score': overall_sim
            })
        
        # 2. 专业匹配度扣分
        if professional_sim == 0:
            deductions.append({
                'reason': '专业完全不相关',
                'deduction': 20,
                'severity': 'critical',
                'field': 'professional_match',
                'similarity_score': professional_sim
            })
        elif professional_sim < 0.3:
            deductions.append({
                'reason': '专业相关性较低',
                'deduction': 12,
                'severity': 'moderate',
                'field': 'professional_match',
                'similarity_score': professional_sim
            })
        elif professional_sim < 0.6:
            deductions.append({
                'reason': '专业部分相关',
                'deduction': 6,
                'severity': 'minor',
                'field': 'professional_match',
                'similarity_score': professional_sim
            })
        
        # 3. 福利相关性扣分
        if benefit_relevance < 0.2:
            deductions.append({
                'reason': '政策福利与个人需求不匹配',
                'deduction': 8,
                'severity': 'moderate',
                'field': 'benefit_relevance',
                'similarity_score': benefit_relevance
            })
        elif benefit_relevance < 0.5:
            deductions.append({
                'reason': '政策福利相关性一般',
                'deduction': 4,
                'severity': 'minor',
                'field': 'benefit_relevance',
                'similarity_score': benefit_relevance
            })
        
        # 4. 条件相似度扣分
        if condition_sim < 0.2:
            deductions.append({
                'reason': '申请条件匹配度低',
                'deduction': 6,
                'severity': 'moderate',
                'field': 'condition_similarity',
                'similarity_score': condition_sim
            })
        
        # 5. 关键词匹配分析
        keyword_matches = similarity_details.get('keyword_matches', [])
        if len(keyword_matches) == 0:
            deductions.append({
                'reason': '无共同关键词',
                'deduction': 10,
                'severity': 'moderate',
                'field': 'keyword_matches',
                'match_count': 0
            })
        elif len(keyword_matches) < 2:
            deductions.append({
                'reason': '共同关键词极少',
                'deduction': 5,
                'severity': 'minor',
                'field': 'keyword_matches',
                'match_count': len(keyword_matches)
            })
        
        return deductions
    
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
        
        # 针对数据结构的特殊处理
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
    
    def recommend_policies_for_user(self, user_info: Dict, policies: List[Dict], 
                                  policy_keywords_dict: Dict[str, PolicyKeywords] = None) -> List[PolicyRecommendation]:
        """为用户推荐所有政策（使用增强版关键词匹配）"""
        recommendations = []
        
        # 如果没有提供预提取的关键词，则加载或提取
        if policy_keywords_dict is None:
            policy_keywords_dict = self.load_or_extract_policy_keywords()
        
        for policy_data in policies:
            policy_id = policy_data.get('政策编号', '')
            
            # 获取对应的关键词数据
            policy_keywords = policy_keywords_dict.get(policy_id)
            
            # 计算扣分制分数
            deduction_score = self.calculate_deduction_score(user_info, policy_data, policy_keywords)
            
            # 获取匹配等级
            match_level = self.get_match_level(deduction_score.final_score)
            
            # 生成推荐理由
            recommendation_reason = self.generate_recommendation_reason(
                deduction_score.final_score, deduction_score
            )
            
            # 提取政策福利
            benefits = self.extract_policy_benefits(policy_data.get('内容', ''))
            
            recommendation = PolicyRecommendation(
                policy_id=policy_id,
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
        
        # 生成改进建议
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
                                 if any(d['field'] == 'overall_similarity' and d['severity'] in ['critical', 'moderate'] 
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
        """为所有用户批量生成推荐（使用增强版关键词匹配）"""
        import os
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        print(f"🚀 开始为{len(users)}个用户生成扣分制政策推荐...")
        print(f"📁 输出目录: {output_dir}")
        print(f"⚙️ 权重配置: 规则{self.deduction_weights['rule_weight']:.1%} + 相似度{self.deduction_weights['similarity_weight']:.1%}")
        print("🔍 使用增强版关键词匹配算法")
        print("=" * 60)
        
        # 预加载或提取所有政策关键词
        print("📝 准备政策关键词数据...")
        policy_keywords_dict = self.load_or_extract_policy_keywords()
        
        # 为每个用户生成推荐
        for i, user_info in enumerate(users, 1):
            user_id = user_info.get('用户ID', f'User_{i}')
            print(f"📝 处理用户 {i}/{len(users)}: {user_id}")
            
            try:
                # 生成推荐
                recommendations = self.recommend_policies_for_user(user_info, policies, policy_keywords_dict)
                
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
        self._generate_batch_summary_report(users, policies, output_dir, policy_keywords_dict)
    
    def _generate_batch_summary_report(self, users: List[Dict], policies: List[Dict], 
                                      output_dir: str, policy_keywords_dict: Dict[str, PolicyKeywords] = None):
        """生成批量推荐汇总报告"""
        print("📊 生成汇总统计报告...")
        
        summary = []
        summary.append("增强版扣分制政策推荐系统 - 汇总报告")
        summary.append("=" * 80)
        summary.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"用户数量: {len(users)}")
        summary.append(f"政策数量: {len(policies)}")
        summary.append(f"算法配置: 规则权重{self.deduction_weights['rule_weight']:.1%} + 相似度权重{self.deduction_weights['similarity_weight']:.1%}")
        summary.append(f"相似度算法: 增强版分类关键词匹配")
        if policy_keywords_dict:
            summary.append(f"关键词数据: 已加载{len(policy_keywords_dict)}个政策的分类关键词")
        summary.append("")
        
        # 统计所有用户的推荐结果
        all_recommendations = []
        user_stats = []
        
        for user_info in users:
            try:
                recommendations = self.recommend_policies_for_user(user_info, policies, policy_keywords_dict)
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
        
        # 保存汇总报告
        summary_file = os.path.join(output_dir, "enhanced_deduction_summary_report.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary))
        
        print(f"✅ 增强版汇总报告已保存: {summary_file}")

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
    print("🚀 增强版扣分制政策推荐系统启动")
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
    print(f"\n⚙️ 增强版算法配置:")
    print(f"   规则匹配权重: {recommender.deduction_weights['rule_weight']:.1%}")
    print(f"   相似度权重: {recommender.deduction_weights['similarity_weight']:.1%}")
    print(f"   相似度算法: 分类关键词匹配 (专业40% + 整体30% + 福利20% + 条件10%)")
    
    # 选择运行模式
    print(f"\n🎯 选择运行模式:")
    print("1. 单用户推荐示例 (展示增强版效果)")
    print("2. 批量推荐所有用户 (生成完整报告)")
    print("3. 仅查看数据统计")
    print("4. 测试关键词提取效果")
    
    try:
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '1':
            # 单用户推荐示例
            if users:
                user_info = users[0]  # 使用第一个用户作为示例
                user_id = user_info.get('用户ID', 'Unknown')
                print(f"\n📝 为用户 {user_id} 生成增强版推荐...")
                
                # 展示关键词提取过程
                print(f"👤 用户信息: 学历{user_info.get('最高学历', '未知')} | 专业{user_info.get('专业', '未知')} | 工作{user_info.get('工作年限', 0)}年")
                
                recommendations = recommender.recommend_policies_for_user(user_info, policies)
                report = recommender.generate_user_recommendation_report(user_info, recommendations)
                
                # 显示报告
                print("\n" + "="*80)
                print(report)
                print("="*80)
                
                # 保存到文件
                with open(f"enhanced_sample_recommendation_{user_id}.txt", 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ 增强版报告已保存为: enhanced_sample_recommendation_{user_id}.txt")
        
        elif choice == '2':
            # 批量推荐
            print(f"\n🚀 开始增强版批量推荐...")
            print("📝 将自动加载/提取政策关键词，提升匹配精度")
            recommender.batch_recommend_for_all_users(users, policies)
            print(f"\n✅ 增强版批量推荐完成！请查看 deduction_recommendations/ 目录")
        
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
        
        elif choice == '4':
            # 测试关键词提取效果
            print(f"\n🔍 测试关键词提取效果...")
            if policies:
                policy_data = policies[0]
                policy_id = policy_data.get('政策编号', 'Unknown')
                
                print(f"📋 测试政策: {policy_id}")
                print(f"标题: {policy_data.get('标题', 'Unknown')}")
                
                # 提取关键词
                keywords_result = recommender.keyword_extractor.extract_keywords_from_policy(policy_data)
                
                print(f"\n🔍 提取结果:")
                print(f"关键词 ({len(keywords_result.keywords)}个): {', '.join(keywords_result.keywords)}")
                print(f"福利词 ({len(keywords_result.benefit_keywords)}个): {', '.join(keywords_result.benefit_keywords)}")
                print(f"条件词 ({len(keywords_result.condition_keywords)}个): {', '.join(keywords_result.condition_keywords)}")
                print(f"目标词 ({len(keywords_result.target_group_keywords)}个): {', '.join(keywords_result.target_group_keywords)}")
                print(f"实体词 ({len(keywords_result.entities)}个): {', '.join(keywords_result.entities)}")
                
                # 测试用户匹配
                if users:
                    user_info = users[0]
                    user_id = user_info.get('用户ID', 'Unknown')
                    print(f"\n👤 测试用户匹配: {user_id}")
                    
                    similarity_details = recommender.calculate_enhanced_similarity(user_info, keywords_result)
                    print(f"整体相似度: {similarity_details['overall_similarity']:.3f}")
                    print(f"专业匹配度: {similarity_details['professional_similarity']:.3f}")
                    print(f"福利相关性: {similarity_details['benefit_relevance']:.3f}")
                    print(f"条件相似度: {similarity_details['condition_similarity']:.3f}")
                    
                    if similarity_details['keyword_matches']:
                        print(f"关键词匹配: {similarity_details['keyword_matches'][:3]}...")
        
        else:
            print("❌ 无效选择")
    
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()