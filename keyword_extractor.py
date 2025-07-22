import os
import json
import re
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import jieba
import jieba.analyse
from datetime import datetime

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
            
        # 设置jieba关键词提取参数
        jieba.analyse.set_stop_words("stopwords.txt")  # 如果有停用词文件
        
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
    
    def extract_all_policies_keywords(self, policy_dir: str = "policy_dataset", 
                                    output_file: str = "policy_keywords.json") -> List[PolicyKeywords]:
        """提取所有政策的关键词"""
        if not os.path.exists(policy_dir):
            print(f"❌ 政策目录不存在: {policy_dir}")
            return []
        
        policies_keywords = []
        json_files = [f for f in os.listdir(policy_dir) if f.endswith('.json')]
        
        print(f"🔍 开始提取 {len(json_files)} 个政策的关键词...")
        
        for i, filename in enumerate(sorted(json_files), 1):
            file_path = os.path.join(policy_dir, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    policy_data = json.load(f)
                
                print(f"  {i:2d}. 处理 {policy_data.get('政策编号', filename)}")
                
                # 提取关键词
                keywords_result = self.extract_keywords_from_policy(policy_data)
                policies_keywords.append(keywords_result)
                
                # 显示提取结果
                print(f"      关键词: {', '.join(keywords_result.keywords[:5])}...")
                print(f"      福利词: {', '.join(keywords_result.benefit_keywords[:3])}")
                print(f"      条件词: {', '.join(keywords_result.condition_keywords[:3])}")
                
            except Exception as e:
                print(f"❌ 处理失败 {filename}: {e}")
        
        # 保存结果
        self.save_keywords_to_file(policies_keywords, output_file)
        
        return policies_keywords
    
    def save_keywords_to_file(self, policies_keywords: List[PolicyKeywords], 
                             output_file: str = "policy_keywords.json"):
        """保存关键词到文件"""
        keywords_data = []
        
        for pk in policies_keywords:
            keywords_data.append(asdict(pk))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(keywords_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 关键词提取结果已保存到: {output_file}")
    
    def load_keywords_from_file(self, input_file: str = "policy_keywords.json") -> List[PolicyKeywords]:
        """从文件加载关键词"""
        if not os.path.exists(input_file):
            print(f"❌ 关键词文件不存在: {input_file}")
            return []
        
        with open(input_file, 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
        
        policies_keywords = []
        for data in keywords_data:
            pk = PolicyKeywords(**data)
            policies_keywords.append(pk)
        
        print(f"✅ 从 {input_file} 加载了 {len(policies_keywords)} 个政策的关键词")
        return policies_keywords
    
    def analyze_keywords_statistics(self, policies_keywords: List[PolicyKeywords]) -> Dict:
        """分析关键词统计信息"""
        stats = {
            'total_policies': len(policies_keywords),
            'total_keywords': 0,
            'most_common_keywords': Counter(),
            'benefit_keywords_count': Counter(),
            'condition_keywords_count': Counter(),
            'target_keywords_count': Counter(),
            'entities_count': Counter(),
            'policy_keyword_counts': {}
        }
        
        for pk in policies_keywords:
            # 统计总关键词数
            stats['total_keywords'] += len(pk.keywords)
            
            # 统计最常见关键词
            stats['most_common_keywords'].update(pk.keywords)
            
            # 统计各类关键词
            stats['benefit_keywords_count'].update(pk.benefit_keywords)
            stats['condition_keywords_count'].update(pk.condition_keywords)
            stats['target_keywords_count'].update(pk.target_group_keywords)
            stats['entities_count'].update(pk.entities)
            
            # 每个政策的关键词数量
            stats['policy_keyword_counts'][pk.policy_id] = len(pk.keywords)
        
        return stats
    
    def generate_keywords_report(self, policies_keywords: List[PolicyKeywords], 
                               output_file: str = "keywords_analysis_report.txt"):
        """生成关键词分析报告"""
        stats = self.analyze_keywords_statistics(policies_keywords)
        
        report = []
        report.append("政策关键词分析报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"分析政策数量: {stats['total_policies']}")
        report.append(f"提取关键词总数: {stats['total_keywords']}")
        report.append(f"平均每个政策关键词数: {stats['total_keywords']/stats['total_policies']:.1f}")
        report.append("")
        
        # 最常见关键词
        report.append("最常见关键词 TOP 20:")
        report.append("-" * 40)
        for keyword, count in stats['most_common_keywords'].most_common(20):
            report.append(f"{keyword:15s} : {count:2d} 次")
        report.append("")
        
        # 福利关键词统计
        report.append("最常见福利关键词 TOP 10:")
        report.append("-" * 40)
        for keyword, count in stats['benefit_keywords_count'].most_common(10):
            report.append(f"{keyword:15s} : {count:2d} 次")
        report.append("")
        
        # 条件关键词统计
        report.append("最常见条件关键词 TOP 10:")
        report.append("-" * 40)
        for keyword, count in stats['condition_keywords_count'].most_common(10):
            report.append(f"{keyword:15s} : {count:2d} 次")
        report.append("")
        
        # 目标人群关键词统计
        report.append("最常见目标人群关键词 TOP 10:")
        report.append("-" * 40)
        for keyword, count in stats['target_keywords_count'].most_common(10):
            report.append(f"{keyword:15s} : {count:2d} 次")
        report.append("")
        
        # 实体词统计
        report.append("最常见实体词 TOP 10:")
        report.append("-" * 40)
        for keyword, count in stats['entities_count'].most_common(10):
            report.append(f"{keyword:15s} : {count:2d} 次")
        report.append("")
        
        # 每个政策的详细信息
        report.append("各政策关键词详情:")
        report.append("-" * 40)
        for pk in policies_keywords:
            report.append(f"\n政策 {pk.policy_id}: {pk.title}")
            report.append(f"  关键词({len(pk.keywords)}个): {', '.join(pk.keywords[:10])}")
            if len(pk.keywords) > 10:
                report.append(f"  ... 还有 {len(pk.keywords)-10} 个关键词")
            
            if pk.benefit_keywords:
                report.append(f"  福利词: {', '.join(pk.benefit_keywords)}")
            if pk.condition_keywords:
                report.append(f"  条件词: {', '.join(pk.condition_keywords[:5])}")
            if pk.target_group_keywords:
                report.append(f"  目标词: {', '.join(pk.target_group_keywords)}")
        
        # 保存报告
        report_content = "\n".join(report)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 关键词分析报告已保存到: {output_file}")
        return report_content

def main():
    """关键词提取主程序"""
    print("🔍 政策关键词提取系统启动")
    print("=" * 60)
    
    # 初始化提取器
    extractor = PolicyKeywordExtractor()
    
    # 提取所有政策关键词
    policies_keywords = extractor.extract_all_policies_keywords()
    
    if policies_keywords:
        print(f"\n✅ 成功提取 {len(policies_keywords)} 个政策的关键词")
        
        # 生成分析报告
        extractor.generate_keywords_report(policies_keywords)
        
        print("\n🎉 关键词提取和分析完成！")
        print("\n📂 输出文件：")
        print("  - policy_keywords.json (关键词数据)")
        print("  - keywords_analysis_report.txt (分析报告)")
        
    else:
        print("❌ 关键词提取失败")

if __name__ == "__main__":
    main()