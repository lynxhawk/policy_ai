#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版扣分制政策推荐系统
基于正则规则匹配和关键词相似度的扣分制评分算法
增加关键词提取输出功能
"""

import os
import json
import re
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import jieba
import jieba.analyse

@dataclass
class PolicyKeywords:
    """政策关键词数据类"""
    policy_id: str
    title: str
    keywords: List[str]
    keyword_scores: Dict[str, float]
    entities: List[str]
    benefit_keywords: List[str]
    condition_keywords: List[str]
    target_group_keywords: List[str]
    extracted_time: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@dataclass
class DeductionScore:
    """扣分详情"""
    base_score: float = 100.0
    rule_deductions: List[Dict] = field(default_factory=list)
    similarity_deductions: List[Dict] = field(default_factory=list)
    final_score: float = 0.0
    deduction_reasons: List[str] = field(default_factory=list)

@dataclass
class PolicyRecommendation:
    """政策推荐结果"""
    policy_id: str
    policy_title: str
    final_score: float
    rank: int
    deduction_score: DeductionScore
    match_level: str
    recommendation_reason: str
    benefits: List[str]

class PolicyKeywordExtractor:
    """政策关键词提取器"""
    
    def __init__(self):
        self._init_dictionaries()
        self._setup_jieba()
        
    def _setup_jieba(self):
        """初始化jieba分词"""
        custom_words = [
            '高校毕业生', '就业困难人员', '灵活就业', '创业担保贷款',
            '社保补贴', '人才码', '被征地人员', '职业培训', '见习补贴',
            '平湖市', '嘉兴市', '法定退休年龄', '小微企业', '初次创业'
        ]
        for word in custom_words:
            jieba.add_word(word, 10)
            
    def _init_dictionaries(self):
        """初始化分类词典"""
        self.benefit_keywords = {
            '补贴': ['补贴', '补助', '资助', '津贴', '奖励'],
            '贷款': ['贷款', '借款', '融资', '资金支持'],
            '减免': ['减免', '减征', '免缴', '优惠'],
            '培训': ['培训', '教育', '学习', '技能提升'],
            '服务': ['服务', '指导', '咨询', '帮扶']
        }
        
        self.condition_keywords = {
            '年龄': ['年龄', '周岁', '退休年龄', '法定退休'],
            '学历': ['学历', '文凭', '本科', '专科', '硕士', '博士'],
            '工作': ['工作年限', '从业', '就业', '创业', '经营'],
            '地域': ['平湖', '本市', '嘉兴', '户籍', '居住'],
            '状态': ['困难', '失业', '灵活就业', '在职'],
            '社保': ['社保缴纳', '当地社保', '本地社保', '社会保险']
        }
        
        self.target_group_keywords = {
            '毕业生': ['毕业生', '大学生', '应届', '往届'],
            '就业困难': ['就业困难', '失业', '下岗', '待业'],
            '创业者': ['创业', '创办', '自主创业', '初次创业'],
            '征地人员': ['被征地人员', '征地农民', '失地农民'],
            '困难群体': ['困难人员', '低保', '特困', '救助']
        }
    
    def extract_keywords_from_policy(self, policy_data: Dict) -> PolicyKeywords:
        """从政策中提取关键词"""
        policy_id = policy_data.get('政策编号', '')
        title = policy_data.get('标题', '')
        content = policy_data.get('内容', '')
        
        # 统一处理内容格式
        content_text = ' '.join(content) if isinstance(content, list) else str(content)
        full_text = f"{title} {content_text}"
        
        # 提取关键词
        tfidf_keywords = self._extract_tfidf_keywords(full_text)
        textrank_keywords = self._extract_textrank_keywords(full_text)
        merged_keywords = self._merge_keywords(tfidf_keywords, textrank_keywords)
        
        # 分类提取
        benefit_kws = self._extract_category_keywords(full_text, self.benefit_keywords)
        condition_kws = self._extract_category_keywords(full_text, self.condition_keywords)
        target_kws = self._extract_category_keywords(full_text, self.target_group_keywords)
        entities = self._extract_entities(full_text)
        
        return PolicyKeywords(
            policy_id=policy_id,
            title=title,
            keywords=list(merged_keywords.keys())[:20],
            keyword_scores=dict(list(merged_keywords.items())[:20]),
            entities=entities,
            benefit_keywords=benefit_kws,
            condition_keywords=condition_kws,
            target_group_keywords=target_kws
        )
    
    def _extract_tfidf_keywords(self, text: str, topK: int = 30) -> Dict[str, float]:
        """TF-IDF关键词提取"""
        try:
            keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=True)
            return dict(keywords)
        except:
            return {}
    
    def _extract_textrank_keywords(self, text: str, topK: int = 30) -> Dict[str, float]:
        """TextRank关键词提取"""
        try:
            keywords = jieba.analyse.textrank(text, topK=topK, withWeight=True)
            return dict(keywords)
        except:
            return {}
    
    def _merge_keywords(self, tfidf_kws: Dict[str, float], textrank_kws: Dict[str, float]) -> Dict[str, float]:
        """合并关键词"""
        merged = {}
        all_keywords = set(tfidf_kws.keys()) | set(textrank_kws.keys())
        
        for kw in all_keywords:
            tfidf_score = tfidf_kws.get(kw, 0)
            textrank_score = textrank_kws.get(kw, 0)
            
            if tfidf_score > 0 and textrank_score > 0:
                merged[kw] = (tfidf_score + textrank_score) * 1.5
            else:
                merged[kw] = tfidf_score + textrank_score
        
        return dict(sorted(merged.items(), key=lambda x: x[1], reverse=True))
    
    def _extract_category_keywords(self, text: str, category_dict: Dict) -> List[str]:
        """提取分类关键词"""
        found_keywords = []
        for category, keywords in category_dict.items():
            for kw in keywords:
                if kw in text:
                    found_keywords.append(kw)
        return list(set(found_keywords))
    
    def _extract_entities(self, text: str) -> List[str]:
        """提取实体词"""
        entity_patterns = [
            r'([^，。、！？\s]{2,6}市)', r'([^，。、！？\s]{2,6}局)',
            r'([^，。、！？\s]{2,10}有限公司)'
        ]
        
        entities = []
        for pattern in entity_patterns:
            entities.extend(re.findall(pattern, text))
        
        return list(set(entities))

class DeductionPolicyRecommender:
    """扣分制政策推荐系统"""
    
    def __init__(self, policy_dir="policy_dataset", user_dir="user_dataset"):
        self.policy_dir = policy_dir
        self.user_dir = user_dir
        self.keyword_extractor = PolicyKeywordExtractor()
        self._init_config()
        self._init_patterns()
        
    def _init_config(self):
        """初始化配置"""
        # 权重配置
        self.weights = {
            'rule_weight': 0.7,
            'similarity_weight': 0.3
        }
        
        # 扣分标准
        self.deduction_standards = {
            'critical': {'age_gap_major': 30, 'education_gap': 25, 'location_mismatch': 35, 'employment_wrong': 30},
            'moderate': {'age_gap_minor': 15, 'experience_gap': 20, 'talent_code_lower': 15},
            'minor': {'partial_requirement': 8, 'documentation_missing': 5}
        }
        
        # 等级映射
        self.education_levels = {'小学': 1, '初中': 2, '高中': 3, '专科': 4, '本科': 5, '硕士': 6, '博士': 7}
        self.talent_code_levels = {'G': 1, 'F': 2, 'E': 3, 'D': 4, 'C': 5, 'B': 6, 'A': 7}
        
        # 匹配等级阈值
        self.match_thresholds = {'high': 85, 'medium': 65, 'low': 40}
    
    def _init_patterns(self):
        """初始化匹配模式"""
        self.rule_patterns = {
            'age': [(r'(\d+)周岁以上', 'age', '>='), (r'(\d+)岁以上', 'age', '>=')],
            'education': [('博士', 'education', '>='), ('硕士', 'education', '>='), ('本科', 'education', '>=')],
            'work_experience': [(r'工作年限(\d+)年以上', 'work_years', '>=')],
            'talent_code': [(r'([A-G])类.*?人才码', 'talent_code', '>=')],
            'location': [('平湖市', 'location', 'in'), ('本市', 'location', 'in')]
        }
    
    def extract_keywords_from_policies(self, policies: List[Dict], output_file: str = None) -> List[PolicyKeywords]:
        """提取所有政策的关键词并可选择输出到文件"""
        print(f"🔍 开始提取 {len(policies)} 个政策的关键词...")
        
        all_keywords = []
        for i, policy_data in enumerate(policies, 1):
            policy_id = policy_data.get('政策编号', f'Policy_{i}')
            print(f"   处理政策 {i}/{len(policies)}: {policy_id}")
            
            try:
                keywords = self.keyword_extractor.extract_keywords_from_policy(policy_data)
                all_keywords.append(keywords)
            except Exception as e:
                print(f"   ❌ 提取失败: {e}")
        
        print(f"✅ 关键词提取完成！成功处理 {len(all_keywords)} 个政策")
        
        # 输出到文件
        if output_file:
            self._save_keywords_to_file(all_keywords, output_file)
        
        return all_keywords
    
    def _save_keywords_to_file(self, keywords_list: List[PolicyKeywords], output_file: str):
        """保存关键词到文件"""
        try:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            # 保存为JSON格式
            if output_file.endswith('.json'):
                keywords_data = [asdict(keywords) for keywords in keywords_list]
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(keywords_data, f, ensure_ascii=False, indent=2)
                print(f"✅ 关键词数据已保存为JSON: {output_file}")
            
            # 保存为可读的文本格式
            else:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("政策关键词提取报告\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"处理政策数: {len(keywords_list)}\n\n")
                    
                    for i, keywords in enumerate(keywords_list, 1):
                        f.write(f"#{i} 政策编号: {keywords.policy_id}\n")
                        f.write(f"标题: {keywords.title}\n")
                        f.write("-" * 60 + "\n")
                        
                        # 核心关键词（前10个）
                        f.write("🔑 核心关键词（权重排序）:\n")
                        for j, (kw, score) in enumerate(list(keywords.keyword_scores.items())[:10], 1):
                            f.write(f"   {j}. {kw} (权重: {score:.3f})\n")
                        
                        # 分类关键词
                        if keywords.benefit_keywords:
                            f.write(f"💰 福利关键词: {', '.join(keywords.benefit_keywords)}\n")
                        
                        if keywords.condition_keywords:
                            f.write(f"📋 条件关键词: {', '.join(keywords.condition_keywords)}\n")
                        
                        if keywords.target_group_keywords:
                            f.write(f"🎯 目标群体: {', '.join(keywords.target_group_keywords)}\n")
                        
                        if keywords.entities:
                            f.write(f"🏢 实体词: {', '.join(keywords.entities)}\n")
                        
                        f.write(f"⏰ 提取时间: {keywords.extracted_time}\n")
                        f.write("\n" + "=" * 60 + "\n\n")
                
                print(f"✅ 关键词报告已保存为文本: {output_file}")
                
        except Exception as e:
            print(f"❌ 保存关键词文件失败: {e}")
    
    def generate_keywords_summary(self, keywords_list: List[PolicyKeywords]) -> str:
        """生成关键词统计摘要"""
        if not keywords_list:
            return "❌ 没有关键词数据"
        
        # 统计所有关键词频率
        all_keywords = {}
        all_benefits = {}
        all_conditions = {}
        all_targets = {}
        
        for keywords in keywords_list:
            # 统计核心关键词
            for kw in keywords.keywords:
                all_keywords[kw] = all_keywords.get(kw, 0) + 1
            
            # 统计分类关键词
            for kw in keywords.benefit_keywords:
                all_benefits[kw] = all_benefits.get(kw, 0) + 1
            
            for kw in keywords.condition_keywords:
                all_conditions[kw] = all_conditions.get(kw, 0) + 1
            
            for kw in keywords.target_group_keywords:
                all_targets[kw] = all_targets.get(kw, 0) + 1
        
        # 生成摘要
        summary = []
        summary.extend([
            "📊 关键词提取统计摘要",
            "=" * 50,
            f"处理政策数量: {len(keywords_list)}",
            f"提取关键词总数: {len(all_keywords)}",
            ""
        ])
        
        # 高频关键词Top10
        top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
        summary.append("🔥 高频关键词 Top10:")
        for i, (kw, count) in enumerate(top_keywords, 1):
            percentage = count / len(keywords_list) * 100
            summary.append(f"   {i}. {kw} ({count}次, {percentage:.1f}%)")
        
        summary.append("")
        
        # 高频福利关键词
        if all_benefits:
            top_benefits = sorted(all_benefits.items(), key=lambda x: x[1], reverse=True)[:5]
            summary.append("💰 高频福利关键词:")
            for kw, count in top_benefits:
                summary.append(f"   • {kw} ({count}次)")
            summary.append("")
        
        # 高频条件关键词
        if all_conditions:
            top_conditions = sorted(all_conditions.items(), key=lambda x: x[1], reverse=True)[:5]
            summary.append("📋 高频条件关键词:")
            for kw, count in top_conditions:
                summary.append(f"   • {kw} ({count}次)")
            summary.append("")
        
        # 高频目标群体关键词
        if all_targets:
            top_targets = sorted(all_targets.items(), key=lambda x: x[1], reverse=True)[:5]
            summary.append("🎯 高频目标群体:")
            for kw, count in top_targets:
                summary.append(f"   • {kw} ({count}次)")
        
        return "\n".join(summary)
    
    def calculate_deduction_score(self, user_info: Dict, policy_data: Dict, 
                                policy_keywords: Optional[PolicyKeywords] = None) -> DeductionScore:
        """计算扣分制分数"""
        deduction_score = DeductionScore()
        
        # 获取政策关键词
        if policy_keywords is None:
            policy_keywords = self.keyword_extractor.extract_keywords_from_policy(policy_data)
        
        # 检查排除条件
        exclusion_penalty = self._check_exclusions(user_info, policy_data, policy_keywords)
        if exclusion_penalty > 0:
            deduction_score.rule_deductions.append({
                'reason': '不符合政策目标人群',
                'deduction': exclusion_penalty,
                'severity': 'critical',
                'field': 'target_group'
            })
        
        # 计算规则扣分
        requirements = self._extract_requirements(policy_data.get('内容', ''))
        rule_deductions = self._calculate_rule_deductions(user_info, requirements)
        deduction_score.rule_deductions.extend(rule_deductions)
        
        # 计算相似度扣分
        similarity_details = self._calculate_similarity(user_info, policy_keywords)
        similarity_deductions = self._calculate_similarity_deductions(similarity_details)
        deduction_score.similarity_deductions = similarity_deductions
        
        # 计算最终分数
        total_rule = sum(d['deduction'] for d in deduction_score.rule_deductions)
        total_similarity = sum(d['deduction'] for d in similarity_deductions)
        
        weighted_deduction = (total_rule * self.weights['rule_weight'] + 
                            total_similarity * self.weights['similarity_weight'])
        
        deduction_score.final_score = max(0, deduction_score.base_score - weighted_deduction)
        deduction_score.deduction_reasons = self._generate_reasons(
            deduction_score.rule_deductions, similarity_deductions
        )
        
        return deduction_score
    
    def _check_exclusions(self, user_info: Dict, policy_data: Dict, 
                         policy_keywords: PolicyKeywords) -> float:
        """检查排除条件"""
        policy_text = self._get_policy_text(policy_data)
        policy_id = policy_data.get('政策编号', '')
        
        # 排除条件映射
        exclusion_map = {
            ('被征地人员', '征地农民'): ('征地人员', 80.0),
            ('残疾人', '残障'): ('残疾人', 85.0),
            ('退役军人', '军转干部'): ('退役军人', 75.0),
            ('低保户', '特困人员'): ('困难人员', 70.0)
        }
        
        # 特殊政策的目标群体检查（更精确的匹配）
        special_policy_mapping = {
            'POL0004': '征地人员',  # 被征地人员政策
            'POL0006': '困难人员',  # 就业困难人员政策 
            'POL0007': '残疾人',   # 残疾人政策
            'POL0008': '退役军人'  # 退役军人政策（如果存在）
        }
        
        # 优先检查特殊政策ID映射
        if policy_id in special_policy_mapping:
            required_identity = special_policy_mapping[policy_id]
            user_value = user_info.get(required_identity, '否')
            
            if user_value != '是':
                penalty_mapping = {
                    '征地人员': 80.0,
                    '残疾人': 85.0, 
                    '退役军人': 75.0,
                    '困难人员': 70.0
                }
                penalty = penalty_mapping.get(required_identity, 80.0)
                print(f"   🎯 特殊政策检查: {policy_id} 需要{required_identity}身份，用户为{user_value}，扣{penalty}分")
                return penalty
            else:
                print(f"   ✅ 特殊政策匹配: {policy_id} 用户{required_identity}身份符合")
                return 0.0
        
        # 通用关键词检查（用于其他政策）
        for keywords, (user_field, penalty) in exclusion_map.items():
            if any(kw in policy_text for kw in keywords):
                user_value = user_info.get(user_field, '否')
                if user_value != '是':
                    print(f"   🎯 关键词检查: 政策包含{keywords}，用户{user_field}为{user_value}，扣{penalty}分")
                    return penalty
                else:
                    print(f"   ✅ 关键词匹配: 用户{user_field}身份符合")
                    return 0.0
        
        return 0.0
    
    def _extract_requirements(self, policy_content) -> List[Dict]:
        """提取政策要求"""
        content_text = self._normalize_content(policy_content)
        requirements = []
        
        for category, patterns in self.rule_patterns.items():
            for pattern_info in patterns:
                pattern, field, operator = pattern_info[:3]
                
                if pattern.startswith('r') or '(' in pattern:
                    matches = re.finditer(pattern, content_text)
                    for match in matches:
                        value = match.group(1) if match.groups() else match.group(0)
                        if field in ['age', 'work_years'] and value.isdigit():
                            value = int(value)
                        requirements.append({
                            'field': field, 'operator': operator, 'value': value,
                            'description': f"{field}要求：{value}"
                        })
                else:
                    if pattern in content_text:
                        requirements.append({
                            'field': field, 'operator': operator, 'value': pattern,
                            'description': f"{field}要求：{pattern}"
                        })
        
        return requirements
    
    def _calculate_rule_deductions(self, user_info: Dict, requirements: List[Dict]) -> List[Dict]:
        """计算规则扣分"""
        deductions = []
        
        for req in requirements:
            user_value = self._get_user_value(user_info, req['field'])
            
            if user_value is None:
                deductions.append({
                    'reason': f"缺少{req['field']}信息",
                    'deduction': self.deduction_standards['minor']['documentation_missing'],
                    'severity': 'minor',
                    'field': req['field']
                })
                continue
            
            is_match, gap_info = self._check_match(user_value, req['operator'], req['value'], req['field'])
            
            if not is_match:
                deduction_amount, severity = self._get_deduction_amount(req['field'], gap_info)
                deductions.append({
                    'reason': gap_info,
                    'deduction': deduction_amount,
                    'severity': severity,
                    'field': req['field']
                })
        
        return deductions
    
    def _calculate_similarity(self, user_info: Dict, policy_keywords: PolicyKeywords) -> Dict:
        """计算相似度"""
        user_keywords = self._extract_user_keywords(user_info)
        
        # 计算各种相似度
        overall_sim = self._cosine_similarity(user_keywords, policy_keywords.keywords)
        professional_sim = self._calculate_professional_similarity(
            user_info.get('专业', ''), policy_keywords.target_group_keywords
        )
        benefit_relevance = self._calculate_benefit_relevance(
            user_info, policy_keywords.benefit_keywords
        )
        
        # 加权计算
        final_similarity = (overall_sim * 0.5 + professional_sim * 0.2 + 
                          benefit_relevance * 0.3)
        
        return {
            'overall_similarity': overall_sim,
            'professional_similarity': professional_sim,
            'benefit_relevance': benefit_relevance,
            'final_similarity': final_similarity,
            'user_keywords': user_keywords
        }
    
    def _calculate_similarity_deductions(self, similarity_details: Dict) -> List[Dict]:
        """计算相似度扣分"""
        deductions = []
        
        sim_thresholds = [
            (0.0, 25, 'critical', '关键词完全不匹配'),
            (0.2, 18, 'critical', '关键词相似度很低'),
            (0.4, 12, 'moderate', '关键词相似度较低'),
            (0.6, 6, 'minor', '关键词相似度中等')
        ]
        
        overall_sim = similarity_details['overall_similarity']
        for threshold, deduction, severity, reason in sim_thresholds:
            if overall_sim <= threshold:
                deductions.append({
                    'reason': reason,
                    'deduction': deduction,
                    'severity': severity,
                    'field': 'similarity'
                })
                break
        
        return deductions
    
    def recommend_policies_for_user(self, user_info: Dict, policies: List[Dict]) -> List[PolicyRecommendation]:
        """为企业推荐政策"""
        recommendations = []
        
        # 过滤政策类型：只推荐"个人"和"企业和个人"类型的政策
        filtered_policies = []
        for policy_data in policies:
            policy_type = policy_data.get('类型', '')
            if policy_type in ['企业', '企业和个人']:
                filtered_policies.append(policy_data)
            else:
                # 记录被过滤的政策
                print(f"📋 跳过个人专用政策: {policy_data.get('个人编号', 'Unknown')} - {policy_type}")
        
        print(f"🔍 政策过滤结果: 总数{len(policies)} → 适用{len(filtered_policies)} (过滤掉{len(policies) - len(filtered_policies)}个企业专用政策)")
        
        for policy_data in filtered_policies:
            policy_id = policy_data.get('政策编号', '')
            deduction_score = self.calculate_deduction_score(user_info, policy_data)
            
            match_level = self._get_match_level(deduction_score.final_score)
            recommendation_reason = self._generate_recommendation_reason(
                deduction_score.final_score, match_level
            )
            benefits = self._extract_benefits(policy_data.get('内容', ''))
            
            recommendation = PolicyRecommendation(
                policy_id=policy_id,
                policy_title=policy_data.get('标题', ''),
                final_score=deduction_score.final_score,
                rank=0,
                deduction_score=deduction_score,
                match_level=match_level,
                recommendation_reason=recommendation_reason,
                benefits=benefits
            )
            recommendations.append(recommendation)
        
        # 应用硬性条件优先级排序
        recommendations = self._apply_priority_rules(user_info, recommendations)
        
        return recommendations
    
    def _apply_priority_rules(self, user_info: Dict, recommendations: List[PolicyRecommendation]) -> List[PolicyRecommendation]:
        """应用硬性条件优先级排序规则"""
        print(f"\n🔝 检查硬性条件优先级...")
        
        # 定义硬性条件优先政策映射
        priority_rules = {
            '当地缴纳社保': ['POL0001'],  # 最高优先级
            '征地人员': ['POL0004'],
            '困难人员': ['POL0006', 'POL0009']  # 按顺序排列
        }
        
        # 检查用户符合的硬性条件
        matched_conditions = []
        for condition, policy_ids in priority_rules.items():
            user_value = user_info.get(condition, '否')
            if user_value == '是':
                matched_conditions.append((condition, policy_ids))
                print(f"   ✅ 检测到硬性条件: {condition} = 是")
        
        if not matched_conditions:
            print(f"   📋 无硬性条件匹配，使用常规得分排序")
            # 常规排序：按得分降序
            recommendations.sort(key=lambda x: x.final_score, reverse=True)
            for i, rec in enumerate(recommendations, 1):
                rec.rank = i
            return recommendations
        
        # 收集所有优先政策ID，按规则顺序排列
        priority_policy_ids = []
        for condition, policy_ids in matched_conditions:
            for policy_id in policy_ids:
                if policy_id not in priority_policy_ids:
                    priority_policy_ids.append(policy_id)
        
        print(f"   🎯 优先政策序列: {priority_policy_ids}")
        
        # 分离优先政策和普通政策
        priority_recommendations = []
        normal_recommendations = []
        
        # 创建推荐政策ID映射
        rec_by_id = {rec.policy_id: rec for rec in recommendations}
        
        # 按优先级顺序添加优先政策
        for policy_id in priority_policy_ids:
            if policy_id in rec_by_id:
                priority_rec = rec_by_id[policy_id]
                # 修改推荐理由，说明优先原因
                original_reason = priority_rec.recommendation_reason
                priority_reason = self._get_priority_reason(user_info, policy_id)
                priority_rec.recommendation_reason = f"🔝 {priority_reason} {original_reason}"
                priority_recommendations.append(priority_rec)
                print(f"   ⭐ 优先推荐: {policy_id} - {priority_rec.policy_title}")
        
        # 添加其他政策（按得分排序）
        for rec in recommendations:
            if rec.policy_id not in priority_policy_ids:
                normal_recommendations.append(rec)
        
        # 对普通推荐按得分排序
        normal_recommendations.sort(key=lambda x: x.final_score, reverse=True)
        
        # 合并结果：优先政策在前，普通政策在后
        final_recommendations = priority_recommendations + normal_recommendations
        
        # 重新设置排名
        for i, rec in enumerate(final_recommendations, 1):
            rec.rank = i
        
        print(f"   📊 排序结果: {len(priority_recommendations)}个优先政策 + {len(normal_recommendations)}个常规政策")
        
        return final_recommendations
    
    def _get_priority_reason(self, user_info: Dict, policy_id: str) -> str:
        """获取优先推荐的原因说明"""
        priority_reasons = {
            'POL0001': '当地社保缴纳优先！',
            'POL0004': '征地人员专享政策！', 
            'POL0006': '困难人员帮扶政策！',
            'POL0009': '困难人员配套政策！'
        }
        
        return priority_reasons.get(policy_id, '特殊条件匹配！')
    
    # 辅助方法
    def _get_policy_text(self, policy_data: Dict) -> str:
        title = policy_data.get('标题', '')
        content = self._normalize_content(policy_data.get('内容', ''))
        return f"{title} {content}"
    
    def _normalize_content(self, content) -> str:
        if isinstance(content, list):
            return ' '.join(content)
        return str(content)
    
    def _extract_user_keywords(self, user_info: Dict) -> List[str]:
        user_text = " ".join(str(v) for k, v in user_info.items() 
                           if k not in ['用户ID', '工作经历'])
        try:
            return jieba.analyse.extract_tags(user_text, topK=20)
        except:
            return []
    
    def _cosine_similarity(self, list1: List[str], list2: List[str]) -> float:
        if not list1 or not list2:
            return 0.0
        
        all_words = list(set(list1 + list2))
        vec1 = [list1.count(word) for word in all_words]
        vec2 = [list2.count(word) for word in all_words]
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _calculate_professional_similarity(self, user_major: str, target_keywords: List[str]) -> float:
        if not user_major:
            return 0.3
        
        base_score = 0.4
        policy_text = ' '.join(target_keywords).lower()
        
        # 专业匹配度逻辑简化
        major_categories = {
            '理工科': ['计算机', '软件', '工程', '技术'],
            '商科': ['管理', '经济', '金融', '商务'],
            '文科': ['中文', '法学', '新闻'],
            '教育': ['教育', '师范']
        }
        
        user_category = None
        for category, majors in major_categories.items():
            if any(major in user_major for major in majors):
                user_category = category
                break
        
        if user_category == '理工科' and any(tech in policy_text for tech in ['技术', '创新', '科技']):
            base_score += 0.3
        elif user_category == '商科' and any(biz in policy_text for biz in ['创业', '企业', '管理']):
            base_score += 0.3
        
        return min(1.0, base_score)
    
    def _calculate_benefit_relevance(self, user_info: Dict, benefit_keywords: List[str]) -> float:
        if not benefit_keywords:
            return 0.0
        
        relevance = 0.0
        
        # 特殊身份匹配
        special_identities = {
            '征地人员': (['征地', '补偿', '安置'], 0.5),
            '困难人员': (['困难', '救助', '帮扶'], 0.5),
            '残疾人': (['残疾', '助残'], 0.5)
        }
        
        for identity, (keywords, score) in special_identities.items():
            if user_info.get(identity, '否') == '是':
                if any(kw in benefit_keywords for kw in keywords):
                    relevance += score
                    break
        
        # 基础匹配
        if user_info.get('工作年限', 0) <= 2:
            if any(kw in benefit_keywords for kw in ['就业', '见习', '培训']):
                relevance += 0.2
        
        return min(1.0, max(0.0, relevance + 0.1))
    
    def _get_user_value(self, user_info: Dict, field: str):
        field_mapping = {
            'age': '年龄', 'education': '最高学历', 'work_years': '工作年限',
            'talent_code': '人才码等级', 'location': '籍贯'
        }
        
        if field == 'age' and '年龄' not in user_info:
            work_years = user_info.get('工作年限', 0)
            return 22 + work_years if work_years > 0 else None
        
        chinese_field = field_mapping.get(field, field)
        return user_info.get(chinese_field)
    
    def _check_match(self, user_value, operator: str, required_value, field: str) -> Tuple[bool, str]:
        try:
            if field == 'education':
                user_level = self.education_levels.get(user_value, 0)
                required_level = self.education_levels.get(required_value, 0)
                is_match = user_level >= required_level
                gap = f"需要{required_value}及以上，当前{user_value}" if not is_match else ""
                return is_match, gap
            
            elif operator == '>=':
                is_match = user_value >= required_value
                gap = f"需要≥{required_value}，当前{user_value}" if not is_match else ""
                return is_match, gap
            
            elif operator == 'in':
                is_match = required_value in str(user_value)
                gap = f"需要在{required_value}，当前在{user_value}" if not is_match else ""
                return is_match, gap
            
            return False, "无法比较"
        except:
            return False, "比较失败"
    
    def _get_deduction_amount(self, field: str, gap_info: str) -> Tuple[float, str]:
        deduction_map = {
            'age': (self.deduction_standards['moderate']['age_gap_minor'], 'moderate'),
            'education': (self.deduction_standards['critical']['education_gap'], 'critical'),
            'location': (self.deduction_standards['critical']['location_mismatch'], 'critical'),
            'work_years': (self.deduction_standards['moderate']['experience_gap'], 'moderate')
        }
        
        return deduction_map.get(field, (self.deduction_standards['minor']['partial_requirement'], 'minor'))
    
    def _get_match_level(self, score: float) -> str:
        if score >= self.match_thresholds['high']:
            return '高度匹配'
        elif score >= self.match_thresholds['medium']:
            return '中度匹配'
        elif score >= self.match_thresholds['low']:
            return '低度匹配'
        else:
            return '需改进'
    
    def _generate_recommendation_reason(self, score: float, match_level: str) -> str:
        reasons = {
            '高度匹配': f"强烈推荐！您的条件与该政策高度匹配（得分{score:.1f}），建议优先申请。",
            '中度匹配': f"推荐申请。您的条件与该政策中度匹配（得分{score:.1f}），有较大申请成功可能。",
            '低度匹配': f"可考虑申请。您的条件与该政策匹配度一般（得分{score:.1f}），需要完善部分条件。",
            '需改进': f"暂不推荐。您的条件与该政策匹配度较低（得分{score:.1f}），需要改进多项条件。"
        }
        return reasons.get(match_level, "")
    
    def _extract_benefits(self, policy_content) -> List[str]:
        content_text = self._normalize_content(policy_content)
        benefits = []
        
        # 金额提取
        amount_patterns = [r'每人每月(\d+)元', r'每年(\d+)元', r'最高(\d+)万?元']
        for pattern in amount_patterns:
            matches = re.findall(pattern, content_text)
            for match in matches:
                benefits.append(f"补贴金额：{match}元")
        
        # 类型识别
        benefit_types = {
            '社保': '社保补贴', '培训': '培训补贴', '就业': '就业补贴',
            '创业': '创业扶持', '租房': '住房补贴', '贷款': '贷款支持'
        }
        
        for keyword, benefit in benefit_types.items():
            if keyword in content_text:
                benefits.append(benefit)
        
        return list(set(benefits)) if benefits else ["详见政策内容"]
    
    def _generate_reasons(self, rule_deductions: List[Dict], similarity_deductions: List[Dict]) -> List[str]:
        reasons = []
        
        severity_icons = {'critical': '❗', 'moderate': '⚠️', 'minor': '📝'}
        
        for deduction in rule_deductions + similarity_deductions:
            icon = severity_icons.get(deduction['severity'], '📝')
            reasons.append(f"{icon} {deduction['reason']} (扣{deduction['deduction']:.1f}分)")
        
        return reasons
    
    def load_data(self, data_type: str) -> List[Dict]:
        """加载数据"""
        directory = self.policy_dir if data_type == 'policies' else self.user_dir
        data = []
        
        if not os.path.exists(directory):
            print(f"❌ {data_type}目录不存在: {directory}")
            return data
        
        json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
        
        for filename in sorted(json_files):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    data.append(file_data)
            except Exception as e:
                print(f"❌ 加载失败 {filename}: {e}")
        
        print(f"✅ 加载了 {len(data)} 个{data_type}")
        return data
    
    def generate_report(self, user_info: Dict, recommendations: List[PolicyRecommendation], 
                       total_policies: int = None) -> str:
        """生成推荐报告"""
        user_id = user_info.get('用户ID', '未知')
        report = []
        
        # 报告头部
        report.extend([
            "=" * 80,
            f"政策推荐报告（扣分制 + 硬性条件优先）- 用户ID: {user_id}",
            "=" * 80,
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"推荐算法: 扣分制评分（规则权重{self.weights['rule_weight']:.1%} + 相似度权重{self.weights['similarity_weight']:.1%}）+ 硬性条件优先级",
            ""
        ])
        
        # 硬性条件检查结果
        priority_conditions = self._check_priority_conditions(user_info)
        if priority_conditions:
            report.extend([
                "🔝 硬性条件优先级检查",
                "-" * 40
            ])
            for condition, status, policies in priority_conditions:
                status_icon = "✅" if status else "❌"
                report.append(f"  {status_icon} {condition}: {user_info.get(condition, '否')}")
                if status and policies:
                    report.append(f"     优先推荐政策: {', '.join(policies)}")
            report.append("")
        
        # 政策过滤信息
        if total_policies:
            filtered_count = len(recommendations)
            excluded_count = total_policies - filtered_count
            report.extend([
                "🔍 政策筛选信息",
                "-" * 40,
                f"  政策总数: {total_policies}",
                f"  适用政策: {filtered_count} (个人 + 企业和个人)",
                f"  排除政策: {excluded_count} (仅限企业)",
                ""
            ])
        
        # 用户信息
        report.append("👤 用户基本信息")
        report.append("-" * 40)
        
        basic_fields = ['最高学历', '专业', '工作年限', '籍贯', '当地缴纳社保', '征地人员', '困难人员', '残疾人', '退役军人']
        for field in basic_fields:
            # 确保显示所有字段，即使值为空或默认值
            value = user_info.get(field, '否' if field in ['当地缴纳社保', '征地人员', '困难人员', '残疾人', '退役军人'] else '未知')
            
            # 为硬性条件添加特殊标识
            if field in ['当地缴纳社保', '征地人员', '困难人员'] and value == '是':
                icons = {'当地缴纳社保': '🏛️', '征地人员': '🏗️', '困难人员': '🆘'}
                value = f"{icons.get(field, '')} {value} 【优先条件】"
            elif field in ['残疾人', '退役军人'] and value == '是':
                icons = {'残疾人': '♿', '退役军人': '🎖️'}
                value = f"{icons.get(field, '')} {value}"
            
            report.append(f"  {field}: {value}")
        
        # 工作经历
        if '工作经历' in user_info and user_info['工作经历']:
            report.append("  工作经历:")
            for i, work in enumerate(user_info['工作经历'], 1):
                company = work.get('公司名称', '未知')
                position = work.get('职位', '未知')
                report.append(f"    {i}. {company} - {position}")
        
        report.append("")
        
        # 推荐统计
        total = len(recommendations)
        if total == 0:
            report.extend([
                "📊 推荐统计",
                "-" * 40,
                "  ⚠️ 没有找到适合的政策推荐",
                "  💡 建议: 检查政策数据或用户信息",
                ""
            ])
            return "\n".join(report)
        
        # 统计优先推荐和常规推荐
        priority_count = len([r for r in recommendations if '🔝' in r.recommendation_reason])
        normal_count = total - priority_count
        
        stats = {level: len([r for r in recommendations if r.match_level == level]) 
                for level in ['高度匹配', '中度匹配', '低度匹配', '需改进']}
        
        report.extend([
            "📊 推荐统计",
            "-" * 40,
            f"  适用政策数: {total}",
            f"  🔝 优先推荐: {priority_count} (硬性条件匹配)",
            f"  📋 常规推荐: {normal_count} (得分排序)",
            "",
            f"  🟢 高度匹配: {stats['高度匹配']} ({stats['高度匹配']/total:.1%})",
            f"  🟡 中度匹配: {stats['中度匹配']} ({stats['中度匹配']/total:.1%})",
            f"  🟠 低度匹配: {stats['低度匹配']} ({stats['低度匹配']/total:.1%})",
            f"  🔴 需改进: {stats['需改进']} ({stats['需改进']/total:.1%})",
            ""
        ])
        
        if recommendations:
            avg_score = sum(r.final_score for r in recommendations) / len(recommendations)
            report.append(f"  平均得分: {avg_score:.1f}")
            report.append("")
        
        # 详细推荐结果
        report.extend([
            "🎯 详细推荐结果（优先级 + 匹配度排序）",
            "=" * 80
        ])
        
        level_icons = {'高度匹配': '🟢', '中度匹配': '🟡', '低度匹配': '🟠', '需改进': '🔴'}
        
        for rec in recommendations[:10]:  # 只显示前10个
            icon = level_icons.get(rec.match_level, '⚪')
            priority_mark = "【优先】" if '🔝' in rec.recommendation_reason else ""
            
            report.extend([
                f"#{rec.rank} {icon} {rec.policy_id} {priority_mark} | 得分: {rec.final_score:.1f} | {rec.match_level}",
                f"   标题: {rec.policy_title}",
                f"   推荐理由: {rec.recommendation_reason}",
                f"   政策福利: {' | '.join(rec.benefits[:3])}"
            ])
            
            # 主要扣分原因
            if rec.deduction_score.deduction_reasons:
                for reason in rec.deduction_score.deduction_reasons[:2]:
                    report.append(f"   {reason}")
            
            report.append("")
        
        # 改进建议
        report.extend([
            "💡 改进建议",
            "=" * 40
        ])
        
        suggestions = self._generate_suggestions(recommendations, user_info)
        for suggestion in suggestions:
            report.append(f"  • {suggestion}")
        
        return "\n".join(report)
    
    def _check_priority_conditions(self, user_info: Dict) -> List[Tuple[str, bool, List[str]]]:
        """检查硬性条件优先级"""
        priority_rules = {
            '当地缴纳社保': ['POL0001'],
            '征地人员': ['POL0004'],
            '困难人员': ['POL0006', 'POL0009']
        }
        
        results = []
        for condition, policy_ids in priority_rules.items():
            user_value = user_info.get(condition, '否')
            is_matched = user_value == '是'
            results.append((condition, is_matched, policy_ids if is_matched else []))
        
        return results
    
    def _generate_suggestions(self, recommendations: List[PolicyRecommendation], user_info: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 统计扣分字段
        field_counts = {}
        for rec in recommendations:
            for deduction in rec.deduction_score.rule_deductions:
                field = deduction.get('field', '')
                if field:
                    field_counts[field] = field_counts.get(field, 0) + 1
        
        # 根据高频扣分字段生成建议
        total_policies = len(recommendations)
        for field, count in field_counts.items():
            if count >= total_policies * 0.3:  # 超过30%的政策都在此字段扣分
                field_suggestions = {
                    'education': "📚 考虑提升学历水平，更多政策对学历有较高要求",
                    'age': "⏰ 部分政策有年龄限制，建议关注适合当前年龄段的政策",
                    'work_years': "💼 积累更多工作经验将有助于申请更多政策",
                    'talent_code': "🏆 申请人才码认定可以显著提升政策匹配度",
                    'location': "📍 注意政策的地域限制，优先关注本地政策",
                    'target_group': "🎯 关注更符合您身份特征的专项政策",
                    'similarity': "📝 完善个人资料，增加专业技能描述"
                }
                
                if field in field_suggestions:
                    suggestions.append(field_suggestions[field])
        
        # 特殊身份建议
        special_identities = ['征地人员', '困难人员', '残疾人', '退役军人']
        for identity in special_identities:
            if user_info.get(identity, '否') == '是':
                suggestions.append(f"✅ {identity}身份：重点关注相关专项政策")
        
        # 优先推荐建议
        high_match = [r for r in recommendations if r.match_level == '高度匹配']
        if high_match:
            suggestions.append(f"⭐ 优先申请：{high_match[0].policy_id}，匹配度最高")
        
        return suggestions if suggestions else ["您的条件总体不错，建议重点关注排名靠前的政策"]
    
    def batch_recommend(self, users: List[Dict], policies: List[Dict], output_dir: str = "recommendations"):
        """批量推荐"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"🚀 开始为{len(users)}个用户生成推荐...")
        
        for i, user_info in enumerate(users, 1):
            user_id = user_info.get('用户ID', f'User_{i}')
            print(f"📝 处理用户 {i}/{len(users)}: {user_id}")
            
            try:
                recommendations = self.recommend_policies_for_user(user_info, policies)
                report = self.generate_report(user_info, recommendations)
                
                filename = os.path.join(output_dir, f"recommendation_{user_id}.txt")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                high_match = len([r for r in recommendations if r.match_level == '高度匹配'])
                print(f"   ✅ 完成 | 高度匹配: {high_match}")
                
            except Exception as e:
                print(f"   ❌ 失败: {e}")
        
        print("✅ 批量推荐完成！")

def main():
    """主函数"""
    print("🚀 扣分制政策推荐系统启动")
    
    recommender = DeductionPolicyRecommender()
    
    # 加载数据
    policies = recommender.load_data('policies')
    users = recommender.load_data('users')
    
    if not policies or not users:
        print("❌ 数据加载失败")
        return
    
    print(f"\n✅ 数据加载完成：{len(policies)}个政策，{len(users)}个用户")
    
    # 运行模式选择
    print(f"\n🎯 选择运行模式:")
    print("1. 单用户推荐示例")
    print("2. 批量推荐所有用户")
    print("3. 查看数据统计")
    print("4. 🔑 提取政策关键词")
    print("5. 🔍 查看单个政策关键词详情")
    
    try:
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == '1':
            user_info = users[0]
            user_id = user_info.get('用户ID', 'Unknown')
            print(f"\n📝 为用户 {user_id} 生成推荐...")
            
            recommendations = recommender.recommend_policies_for_user(user_info, policies)
            report = recommender.generate_report(user_info, recommendations)
            
            print("\n" + "="*80)
            print(report)
            print("="*80)
            
            # 保存报告
            with open(f"sample_recommendation_{user_id}.txt", 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ 报告已保存为: sample_recommendation_{user_id}.txt")
        
        elif choice == '2':
            print(f"\n🚀 开始批量推荐...")
            recommender.batch_recommend(users, policies)
        
        elif choice == '3':
            print(f"\n📊 数据统计:")
            print(f"   政策总数: {len(policies)}")
            print(f"   用户总数: {len(users)}")
            
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
            print(f"\n🔑 开始提取所有政策关键词...")
            
            # 询问输出格式
            format_choice = input("选择输出格式 (1-文本报告 / 2-JSON数据 / 3-两者都要): ").strip()
            
            output_files = []
            if format_choice in ['1', '3']:
                output_files.append(f"policy_keywords_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            if format_choice in ['2', '3']:
                output_files.append(f"policy_keywords_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            # 提取关键词
            for output_file in output_files:
                keywords_list = recommender.extract_keywords_from_policies(policies, output_file)
            
            # 显示统计摘要
            if keywords_list:
                summary = recommender.generate_keywords_summary(keywords_list)
                print("\n" + "="*60)
                print(summary)
                print("="*60)
        
        elif choice == '5':
            print(f"\n🔍 查看单个政策关键词详情")
            print("可用政策:")
            for i, policy in enumerate(policies[:10], 1):
                policy_id = policy.get('政策编号', f'Policy_{i}')
                title = policy.get('标题', 'Unknown')[:50] + ('...' if len(policy.get('标题', '')) > 50 else '')
                print(f"   {i}. {policy_id} - {title}")
            
            try:
                index = int(input(f"\n请选择政策编号 (1-{min(10, len(policies))}): ")) - 1
                if 0 <= index < len(policies):
                    selected_policy = policies[index]
                    print(f"\n🔍 正在分析政策: {selected_policy.get('政策编号', 'Unknown')}")
                    
                    keywords = recommender.keyword_extractor.extract_keywords_from_policy(selected_policy)
                    
                    # 显示详细信息
                    print("\n" + "="*60)
                    print(f"政策编号: {keywords.policy_id}")
                    print(f"标题: {keywords.title}")
                    print(f"提取时间: {keywords.extracted_time}")
                    print("-" * 60)
                    
                    print(f"\n🔑 核心关键词 (Top 15):")
                    for i, (kw, score) in enumerate(list(keywords.keyword_scores.items())[:15], 1):
                        print(f"   {i:2d}. {kw:<15} (权重: {score:.4f})")
                    
                    if keywords.benefit_keywords:
                        print(f"\n💰 福利关键词: {', '.join(keywords.benefit_keywords)}")
                    
                    if keywords.condition_keywords:
                        print(f"\n📋 条件关键词: {', '.join(keywords.condition_keywords)}")
                    
                    if keywords.target_group_keywords:
                        print(f"\n🎯 目标群体: {', '.join(keywords.target_group_keywords)}")
                    
                    if keywords.entities:
                        print(f"\n🏢 实体词: {', '.join(keywords.entities)}")
                    
                    print("="*60)
                    
                    # 询问是否保存
                    save_choice = input(f"\n是否保存该政策的关键词分析? (y/n): ").strip().lower()
                    if save_choice == 'y':
                        filename = f"keywords_analysis_{keywords.policy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(asdict(keywords), f, ensure_ascii=False, indent=2)
                        print(f"✅ 关键词分析已保存为: {filename}")
                
                else:
                    print("❌ 无效的政策编号")
                    
            except ValueError:
                print("❌ 请输入有效的数字")
        
        else:
            print("❌ 无效选择")
    
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()