#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版政策AI主系统
整合关键词提取和增强版政策匹配功能（正则+相似度）
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 导入子模块
try:
    from keyword_extractor import PolicyKeywordExtractor
    from enhanced_matcher import EnhancedPolicyMatcher
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保以下文件存在:")
    print("  - keyword_extractor.py (关键词提取模块)")
    print("  - enhanced_matcher.py (增强版政策匹配模块)")
    sys.exit(1)

class EnhancedPolicyAISystem:
    """增强版政策AI主系统"""
    
    def __init__(self):
        """初始化系统"""
        print("🚀 增强版政策AI系统初始化...")
        
        # 初始化子系统
        self.keyword_extractor = PolicyKeywordExtractor()
        self.policy_matcher = EnhancedPolicyMatcher()
        
        # 系统配置
        self.config = {
            'policy_dir': 'policy_dataset',
            'user_dir': 'user_dataset',
            'keywords_file': 'policy_keywords.json',
            'reports_dir': 'enhanced_match_reports',
            'keywords_report': 'keywords_analysis_report.txt',
            'match_weights': {
                'rule_weight': 0.6,        # 正则规则权重
                'similarity_weight': 0.4   # 相似度权重
            }
        }
        
        print("✅ 系统初始化完成")
        print(f"📊 匹配算法配置:")
        print(f"   - 规则匹配权重: {self.config['match_weights']['rule_weight']:.1%}")
        print(f"   - 相似度匹配权重: {self.config['match_weights']['similarity_weight']:.1%}")
    
    def check_directories(self):
        """检查必要目录"""
        required_dirs = [
            self.config['policy_dir'],
            self.config['user_dir']
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            print("❌ 缺少必要目录:")
            for dir_path in missing_dirs:
                print(f"   - {dir_path}")
            return False
        
        return True
    
    def extract_keywords(self):
        """执行关键词提取"""
        print("\n" + "="*60)
        print("🔍 开始关键词提取...")
        print("="*60)
        
        # 提取关键词
        policies_keywords = self.keyword_extractor.extract_all_policies_keywords(
            policy_dir=self.config['policy_dir'],
            output_file=self.config['keywords_file']
        )
        
        if policies_keywords:
            # 生成分析报告
            report = self.keyword_extractor.generate_keywords_report(
                policies_keywords, 
                self.config['keywords_report']
            )
            
            print(f"\n✅ 关键词提取完成!")
            print(f"   - 处理政策数: {len(policies_keywords)}")
            print(f"   - 关键词文件: {self.config['keywords_file']}")
            print(f"   - 分析报告: {self.config['keywords_report']}")
            
            return True
        else:
            print("❌ 关键词提取失败")
            return False
    
    def match_policies_enhanced(self):
        """执行增强版政策匹配"""
        print("\n" + "="*60)
        print("🎯 开始增强版政策匹配（正则+相似度）...")
        print("="*60)
        
        # 加载数据
        policies = self.policy_matcher.load_policies()
        users = self.policy_matcher.load_users()
        policy_keywords = self.policy_matcher.load_policy_keywords(self.config['keywords_file'])
        
        if not policies or not users:
            print("❌ 数据加载失败")
            return False
        
        print(f"📊 数据统计:")
        print(f"   - 政策数量: {len(policies)}")
        print(f"   - 用户数量: {len(users)}")
        print(f"   - 关键词数据: {'✅' if policy_keywords else '❌'}")
        
        if not policy_keywords:
            print("⚠️ 未找到关键词数据，建议先执行关键词提取")
            print("   系统将仅使用正则规则匹配")
        
        # 执行匹配
        self.policy_matcher.save_enhanced_reports(
            users, 
            policies, 
            policy_keywords,
            self.config['reports_dir']
        )
        
        print(f"\n✅ 增强版政策匹配完成!")
        print(f"   - 报告目录: {self.config['reports_dir']}")
        
        return True
    
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("\n🎯 开始完整增强版分析流程...")
        
        start_time = datetime.now()
        
        # 1. 检查目录
        if not self.check_directories():
            return False
        
        # 2. 关键词提取
        print("\n📝 步骤1: 关键词提取")
        if not self.extract_keywords():
            return False
        
        # 3. 增强版政策匹配
        print("\n📝 步骤2: 增强版政策匹配")
        if not self.match_policies_enhanced():
            return False
        
        # 4. 生成综合报告
        print("\n📝 步骤3: 生成综合报告")
        self.generate_comprehensive_report()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("🎉 完整增强版分析流程完成!")
        print("="*60)
        print(f"⏱️  总耗时: {duration:.1f} 秒")
        print(f"📁 输出文件:")
        print(f"   - {self.config['keywords_file']} (关键词数据)")
        print(f"   - {self.config['keywords_report']} (关键词分析)")
        print(f"   - {self.config['reports_dir']}/ (增强版匹配报告)")
        print(f"   - enhanced_comprehensive_report.txt (增强版综合报告)")
        
        return True
    
    def generate_comprehensive_report(self):
        """生成增强版综合报告"""
        print("\n📊 生成增强版综合报告...")
        
        report = []
        report.append("增强版政策AI系统综合分析报告")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"系统版本: 增强版 (正则规则匹配 + 语义相似度匹配)")
        report.append("")
        
        # 1. 系统概览
        report.append("一、系统概览")
        report.append("-" * 40)
        
        # 统计政策数量
        if os.path.exists(self.config['policy_dir']):
            policy_files = [f for f in os.listdir(self.config['policy_dir']) if f.endswith('.json')]
            report.append(f"政策文件数量: {len(policy_files)}")
        
        # 统计用户数量
        if os.path.exists(self.config['user_dir']):
            user_files = [f for f in os.listdir(self.config['user_dir']) if f.endswith('.json')]
            report.append(f"用户文件数量: {len(user_files)}")
        
        # 匹配算法配置
        report.append(f"匹配算法配置:")
        report.append(f"  - 正则规则权重: {self.config['match_weights']['rule_weight']:.1%}")
        report.append(f"  - 相似度权重: {self.config['match_weights']['similarity_weight']:.1%}")
        
        report.append("")
        
        # 2. 关键词提取结果
        report.append("二、关键词提取结果")
        report.append("-" * 40)
        
        if os.path.exists(self.config['keywords_file']):
            # 加载关键词数据
            policies_keywords = self.keyword_extractor.load_keywords_from_file(self.config['keywords_file'])
            if policies_keywords:
                total_keywords = sum(len(pk.keywords) for pk in policies_keywords)
                avg_keywords = total_keywords / len(policies_keywords)
                
                report.append(f"成功提取政策数: {len(policies_keywords)}")
                report.append(f"关键词总数: {total_keywords}")
                report.append(f"平均每政策关键词数: {avg_keywords:.1f}")
                
                # 统计关键词分布
                from collections import Counter
                all_keywords = []
                all_benefit_keywords = []
                all_condition_keywords = []
                all_target_keywords = []
                
                for pk in policies_keywords:
                    all_keywords.extend(pk.keywords)
                    all_benefit_keywords.extend(pk.benefit_keywords)
                    all_condition_keywords.extend(pk.condition_keywords)
                    all_target_keywords.extend(pk.target_group_keywords)
                
                keyword_counter = Counter(all_keywords)
                report.append(f"唯一关键词数: {len(keyword_counter)}")
                report.append(f"福利关键词数: {len(set(all_benefit_keywords))}")
                report.append(f"条件关键词数: {len(set(all_condition_keywords))}")
                report.append(f"目标人群关键词数: {len(set(all_target_keywords))}")
                
                report.append("高频关键词TOP5:")
                for kw, count in keyword_counter.most_common(5):
                    report.append(f"  - {kw}: {count}次")
        else:
            report.append("关键词提取未完成")
        
        report.append("")
        
        # 3. 增强版政策匹配结果
        report.append("三、增强版政策匹配结果")
        report.append("-" * 40)
        
        if os.path.exists(self.config['reports_dir']):
            # 统计报告文件
            user_reports_dir = os.path.join(self.config['reports_dir'], 'user_reports')
            policy_reports_dir = os.path.join(self.config['reports_dir'], 'policy_reports')
            
            if os.path.exists(user_reports_dir):
                user_reports = [f for f in os.listdir(user_reports_dir) if f.endswith('.txt')]
                report.append(f"增强版用户匹配报告数: {len(user_reports)}")
            
            if os.path.exists(policy_reports_dir):
                policy_reports = [f for f in os.listdir(policy_reports_dir) if f.endswith('.txt')]
                report.append(f"增强版政策匹配报告数: {len(policy_reports)}")
            
            # 读取增强版汇总报告
            summary_file = os.path.join(self.config['reports_dir'], 'enhanced_summary_report.txt')
            if os.path.exists(summary_file):
                report.append("增强版匹配汇总统计:")
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_content = f.read()
                        
                        # 提取关键统计信息
                        lines = summary_content.split('\n')
                        for line in lines:
                            if any(keyword in line for keyword in [
                                "整体匹配率:", "平均规则匹配分:", "平均相似度分:", 
                                "平均综合分:", "相似度算法贡献:"
                            ]):
                                report.append(f"  - {line.strip()}")
                except:
                    pass
        else:
            report.append("增强版政策匹配未完成")
        
        report.append("")
        
        # 4. 算法效果分析
        report.append("四、算法效果分析")
        report.append("-" * 40)
        report.append("增强版匹配算法优势:")
        report.append("1. 双重匹配机制:")
        report.append("   - 正则规则匹配: 精确匹配明确条件")
        report.append("   - 语义相似度匹配: 发现潜在适用政策")
        report.append("2. 智能权重分配:")
        report.append("   - 规则匹配确保基本条件满足")
        report.append("   - 相似度匹配提升覆盖率和发现率")
        report.append("3. 多维度分析:")
        report.append("   - 关键词匹配分析")
        report.append("   - 专业领域相似度")
        report.append("   - 学历等级智能对比")
        
        report.append("")
        
        # 5. 系统建议
        report.append("五、系统建议")
        report.append("-" * 40)
        report.append("1. 数据质量优化:")
        report.append("   - 定期更新政策数据，确保时效性")
        report.append("   - 完善用户画像数据，提高匹配精度")
        report.append("   - 建立政策标签体系，优化关键词提取")
        
        report.append("2. 算法持续改进:")
        report.append("   - 根据实际应用效果调整权重配置")
        report.append("   - 引入更多语义理解技术")
        report.append("   - 考虑用户历史行为数据")
        
        report.append("3. 系统功能扩展:")
        report.append("   - 增加政策推荐排序功能")
        report.append("   - 建立用户反馈机制")
        report.append("   - 开发实时政策更新提醒")
        
        report.append("")
        
        # 6. 文件清单
        report.append("六、输出文件清单")
        report.append("-" * 40)
        output_files = [
            (self.config['keywords_file'], "政策关键词数据"),
            (self.config['keywords_report'], "关键词分析报告"),
            (os.path.join(self.config['reports_dir'], 'user_reports'), "增强版用户匹配报告目录"),
            (os.path.join(self.config['reports_dir'], 'policy_reports'), "增强版政策匹配报告目录"),
            (os.path.join(self.config['reports_dir'], 'enhanced_summary_report.txt'), "增强版匹配汇总报告"),
            ("enhanced_comprehensive_report.txt", "增强版综合分析报告(本文件)")
        ]
        
        for file_path, description in output_files:
            status = "✅" if os.path.exists(file_path) else "❌"
            report.append(f"{status} {file_path} - {description}")
        
        report.append("")
        
        # 7. 技术特性总结
        report.append("七、技术特性总结")
        report.append("-" * 40)
        report.append("增强版政策AI系统技术特性:")
        report.append("- 🔍 智能关键词提取: TF-IDF + TextRank双算法")
        report.append("- ⚖️ 混合匹配算法: 正则规则 + 语义相似度")
        report.append("- 🎯 多维度分析: 专业、学历、地域等多方面匹配")
        report.append("- 📊 详细评分机制: 规则分、相似度分、综合分")
        report.append("- 🔄 灵活权重配置: 可根据需求调整匹配策略")
        report.append("- 📈 效果量化分析: 算法贡献度统计")
        
        # 保存综合报告
        report_content = "\n".join(report)
        with open("enhanced_comprehensive_report.txt", 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print("✅ 增强版综合报告生成完成: enhanced_comprehensive_report.txt")
    
    def configure_weights(self):
        """配置匹配权重"""
        print("\n⚙️ 匹配权重配置")
        print("=" * 40)
        print(f"当前配置:")
        print(f"  正则规则权重: {self.config['match_weights']['rule_weight']:.1%}")
        print(f"  相似度权重: {self.config['match_weights']['similarity_weight']:.1%}")
        print()
        
        try:
            rule_weight = float(input("请输入正则规则权重 (0-1): "))
            if 0 <= rule_weight <= 1:
                similarity_weight = 1.0 - rule_weight
                
                self.config['match_weights']['rule_weight'] = rule_weight
                self.config['match_weights']['similarity_weight'] = similarity_weight
                
                # 更新匹配器的权重配置
                self.policy_matcher.match_weights['rule_weight'] = rule_weight
                self.policy_matcher.match_weights['similarity_weight'] = similarity_weight
                
                print(f"✅ 权重配置已更新:")
                print(f"  正则规则权重: {rule_weight:.1%}")
                print(f"  相似度权重: {similarity_weight:.1%}")
            else:
                print("❌ 权重必须在0-1之间")
        except ValueError:
            print("❌ 请输入有效的数字")
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "="*60)
        print("🎯 增强版政策AI系统 - 主菜单")
        print("="*60)
        print("1. 关键词提取")
        print("2. 增强版政策匹配 (正则+相似度)")
        print("3. 完整增强版分析流程")
        print("4. 配置匹配权重")
        print("5. 查看系统状态")
        print("6. 帮助信息")
        print("0. 退出系统")
        print("-"*60)
    
    def show_status(self):
        """显示系统状态"""
        print("\n📊 增强版系统状态检查")
        print("="*50)
        
        # 检查目录
        print("📁 目录状态:")
        dirs_to_check = [
            (self.config['policy_dir'], "政策数据目录"),
            (self.config['user_dir'], "用户数据目录"),
            (self.config['reports_dir'], "增强版报告输出目录")
        ]
        
        for dir_path, desc in dirs_to_check:
            if os.path.exists(dir_path):
                if dir_path.endswith('_dataset'):
                    files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
                    print(f"  ✅ {desc}: {len(files)} 个文件")
                else:
                    print(f"  ✅ {desc}: 存在")
            else:
                print(f"  ❌ {desc}: 不存在")
        
        print()
        
        # 检查输出文件
        print("📄 输出文件状态:")
        files_to_check = [
            (self.config['keywords_file'], "关键词数据文件"),
            (self.config['keywords_report'], "关键词分析报告"),
            ("enhanced_comprehensive_report.txt", "增强版综合分析报告")
        ]
        
        for file_path, desc in files_to_check:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {desc}: {size} 字节")
            else:
                print(f"  ❌ {desc}: 不存在")
        
        print()
        
        # 显示当前配置
        print("⚙️ 当前配置:")
        print(f"  正则规则权重: {self.config['match_weights']['rule_weight']:.1%}")
        print(f"  相似度权重: {self.config['match_weights']['similarity_weight']:.1%}")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n📖 增强版政策AI系统使用帮助")
        print("="*60)
        print("🎯 系统功能:")
        print("  1. 关键词提取 - 从政策文本中提取关键词和实体")
        print("  2. 增强版政策匹配 - 正则规则 + 语义相似度双重匹配")
        print("  3. 完整分析 - 执行关键词提取+增强版政策匹配")
        print("  4. 权重配置 - 调整规则匹配和相似度匹配的权重")
        print()
        
        print("🔧 增强版匹配算法:")
        print("  - 正则规则匹配: 精确匹配政策条件")
        print("  - 语义相似度匹配: 基于关键词的语义理解")
        print("  - 加权组合: 最终分数 = 规则分×权重 + 相似度分×权重")
        print("  - 智能判定: 综合多个维度决定是否符合条件")
        print()
        
        print("📊 评分体系:")
        print("  - 规则匹配分: 满足条件数/总条件数")
        print("  - 相似度分: 余弦相似度计算")
        print("  - 综合分: 加权平均分数")
        print("  - 符合判定: 规则分≥80% 或 (规则分≥60% 且 相似度分≥30%)")
        print()
        
        print("📁 目录结构:")
        print("  policy_dataset/    - 政策JSON文件目录")
        print("  user_dataset/      - 用户JSON文件目录")
        print("  enhanced_match_reports/ - 增强版匹配报告输出目录")
        print()
        
        print("🔧 命令行参数:")
        print("  python enhanced_main.py --extract     # 只执行关键词提取")
        print("  python enhanced_main.py --match       # 只执行增强版政策匹配") 
        print("  python enhanced_main.py --full        # 执行完整增强版分析流程")
        print("  python enhanced_main.py --status      # 查看系统状态")
    
    def run_interactive(self):
        """交互式运行"""
        while True:
            self.show_menu()
            
            try:
                choice = input("\n请选择功能 (0-6): ").strip()
                
                if choice == '0':
                    print("\n👋 感谢使用增强版政策AI系统，再见!")
                    break
                elif choice == '1':
                    self.extract_keywords()
                elif choice == '2':
                    self.match_policies_enhanced()
                elif choice == '3':
                    self.run_full_analysis()
                elif choice == '4':
                    self.configure_weights()
                elif choice == '5':
                    self.show_status()
                elif choice == '6':
                    self.show_help()
                else:
                    print("❌ 无效选择，请输入 0-6")
                
                if choice in ['1', '2', '3', '4']:
                    input("\n按回车键继续...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 系统已退出")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                input("按回车键继续...")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='增强版政策AI系统 - 关键词提取与增强版政策匹配')
    parser.add_argument('--extract', action='store_true', help='执行关键词提取')
    parser.add_argument('--match', action='store_true', help='执行增强版政策匹配')
    parser.add_argument('--full', action='store_true', help='执行完整增强版分析流程')
    parser.add_argument('--status', action='store_true', help='查看系统状态')
    parser.add_argument('--help-detail', action='store_true', help='显示详细帮助')
    
    args = parser.parse_args()
    
    # 初始化系统
    try:
        system = EnhancedPolicyAISystem()
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return
    
    # 根据参数执行相应功能
    if args.extract:
        system.extract_keywords()
    elif args.match:
        system.match_policies_enhanced()
    elif args.full:
        system.run_full_analysis()
    elif args.status:
        system.show_status()
    elif args.help_detail:
        system.show_help()
    else:
        # 没有参数时运行交互式界面
        print("🎯 欢迎使用增强版政策AI系统!")
        print("   整合关键词提取和增强版政策匹配功能")
        print("   🔥 新特性: 正则规则 + 语义相似度双重匹配")
        system.run_interactive()

if __name__ == "__main__":
    main()