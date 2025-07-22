#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策AI主系统
整合关键词提取和政策匹配功能
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 导入子模块
try:
    from keyword_extractor import PolicyKeywordExtractor
    from matcher import PolicyDatasetMatcher
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保以下文件存在:")
    print("  - keyword_extractor.py (关键词提取模块)")
    print("  - matcher.py (政策匹配模块)")
    sys.exit(1)

class PolicyAISystem:
    """政策AI主系统"""
    
    def __init__(self):
        """初始化系统"""
        print("🚀 政策AI系统初始化...")
        
        # 初始化子系统
        self.keyword_extractor = PolicyKeywordExtractor()
        self.policy_matcher = PolicyDatasetMatcher()
        
        # 系统配置
        self.config = {
            'policy_dir': 'policy_dataset',
            'user_dir': 'user_dataset',
            'keywords_file': 'policy_keywords.json',
            'reports_dir': 'match_reports',
            'keywords_report': 'keywords_analysis_report.txt'
        }
        
        print("✅ 系统初始化完成")
    
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
    
    def match_policies(self):
        """执行政策匹配"""
        print("\n" + "="*60)
        print("👥 开始政策匹配...")
        print("="*60)
        
        # 加载数据
        policies = self.policy_matcher.load_policies()
        users = self.policy_matcher.load_users()
        
        if not policies or not users:
            print("❌ 数据加载失败")
            return False
        
        print(f"📊 数据统计: {len(policies)}个政策, {len(users)}个用户")
        
        # 执行匹配
        self.policy_matcher.save_all_reports(
            users, 
            policies, 
            self.config['reports_dir']
        )
        
        print(f"\n✅ 政策匹配完成!")
        print(f"   - 报告目录: {self.config['reports_dir']}")
        
        return True
    
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("\n🎯 开始完整分析流程...")
        
        start_time = datetime.now()
        
        # 1. 检查目录
        if not self.check_directories():
            return False
        
        # 2. 关键词提取
        if not self.extract_keywords():
            return False
        
        # 3. 政策匹配
        if not self.match_policies():
            return False
        
        # 4. 生成综合报告
        self.generate_comprehensive_report()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("🎉 完整分析流程完成!")
        print("="*60)
        print(f"⏱️  总耗时: {duration:.1f} 秒")
        print(f"📁 输出文件:")
        print(f"   - {self.config['keywords_file']} (关键词数据)")
        print(f"   - {self.config['keywords_report']} (关键词分析)")
        print(f"   - {self.config['reports_dir']}/ (匹配报告)")
        print(f"   - comprehensive_report.txt (综合报告)")
        
        return True
    
    def generate_comprehensive_report(self):
        """生成综合报告"""
        print("\n📊 生成综合报告...")
        
        report = []
        report.append("政策AI系统综合分析报告")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
                for pk in policies_keywords:
                    all_keywords.extend(pk.keywords)
                
                keyword_counter = Counter(all_keywords)
                report.append(f"唯一关键词数: {len(keyword_counter)}")
                report.append("高频关键词TOP5:")
                for kw, count in keyword_counter.most_common(5):
                    report.append(f"  - {kw}: {count}次")
        else:
            report.append("关键词提取未完成")
        
        report.append("")
        
        # 3. 政策匹配结果
        report.append("三、政策匹配结果")
        report.append("-" * 40)
        
        if os.path.exists(self.config['reports_dir']):
            # 统计报告文件
            user_reports_dir = os.path.join(self.config['reports_dir'], 'user_reports')
            policy_reports_dir = os.path.join(self.config['reports_dir'], 'policy_reports')
            
            if os.path.exists(user_reports_dir):
                user_reports = [f for f in os.listdir(user_reports_dir) if f.endswith('.txt')]
                report.append(f"用户匹配报告数: {len(user_reports)}")
            
            if os.path.exists(policy_reports_dir):
                policy_reports = [f for f in os.listdir(policy_reports_dir) if f.endswith('.txt')]
                report.append(f"政策匹配报告数: {len(policy_reports)}")
            
            # 读取汇总报告
            summary_file = os.path.join(self.config['reports_dir'], 'summary_report.txt')
            if os.path.exists(summary_file):
                report.append("匹配汇总统计:")
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_content = f.read()
                        # 提取关键统计信息
                        if "整体匹配率:" in summary_content:
                            lines = summary_content.split('\n')
                            for line in lines:
                                if "整体匹配率:" in line:
                                    report.append(f"  - {line.strip()}")
                                elif "总匹配数:" in line:
                                    report.append(f"  - {line.strip()}")
                except:
                    pass
        else:
            report.append("政策匹配未完成")
        
        report.append("")
        
        # 4. 系统建议
        report.append("四、系统建议")
        report.append("-" * 40)
        report.append("1. 定期更新政策数据，确保时效性")
        report.append("2. 扩充用户画像数据，提高匹配精度")
        report.append("3. 优化关键词提取算法，提升语义理解")
        report.append("4. 建立反馈机制，持续改进匹配效果")
        report.append("5. 考虑引入机器学习模型进行智能推荐")
        
        report.append("")
        
        # 5. 文件清单
        report.append("五、输出文件清单")
        report.append("-" * 40)
        output_files = [
            (self.config['keywords_file'], "政策关键词数据"),
            (self.config['keywords_report'], "关键词分析报告"),
            (os.path.join(self.config['reports_dir'], 'user_reports'), "用户匹配报告目录"),
            (os.path.join(self.config['reports_dir'], 'policy_reports'), "政策匹配报告目录"),
            (os.path.join(self.config['reports_dir'], 'summary_report.txt'), "匹配汇总报告"),
            ("comprehensive_report.txt", "综合分析报告(本文件)")
        ]
        
        for file_path, description in output_files:
            status = "✅" if os.path.exists(file_path) else "❌"
            report.append(f"{status} {file_path} - {description}")
        
        # 保存综合报告
        report_content = "\n".join(report)
        with open("comprehensive_report.txt", 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print("✅ 综合报告生成完成: comprehensive_report.txt")
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "="*60)
        print("🎯 政策AI系统 - 主菜单")
        print("="*60)
        print("1. 关键词提取")
        print("2. 政策匹配")
        print("3. 完整分析流程")
        print("4. 查看系统状态")
        print("5. 帮助信息")
        print("0. 退出系统")
        print("-"*60)
    
    def show_status(self):
        """显示系统状态"""
        print("\n📊 系统状态检查")
        print("="*50)
        
        # 检查目录
        print("📁 目录状态:")
        dirs_to_check = [
            (self.config['policy_dir'], "政策数据目录"),
            (self.config['user_dir'], "用户数据目录"),
            (self.config['reports_dir'], "报告输出目录")
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
            ("comprehensive_report.txt", "综合分析报告")
        ]
        
        for file_path, desc in files_to_check:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {desc}: {size} 字节")
            else:
                print(f"  ❌ {desc}: 不存在")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n📖 政策AI系统使用帮助")
        print("="*60)
        print("🎯 系统功能:")
        print("  1. 关键词提取 - 从政策文本中提取关键词和实体")
        print("  2. 政策匹配 - 将用户信息与政策进行智能匹配")
        print("  3. 完整分析 - 执行关键词提取+政策匹配的完整流程")
        print()
        
        print("📁 目录结构:")
        print("  policy_dataset/    - 政策JSON文件目录")
        print("  user_dataset/      - 用户JSON文件目录")
        print("  match_reports/     - 匹配报告输出目录")
        print()
        
        print("📋 数据格式:")
        print("  政策文件格式:")
        print('    {"政策编号": "POL001", "标题": "...", "内容": [...]}')
        print("  用户文件格式:")
        print('    {"用户ID": "U001", "最高学历": "本科", "工作年限": 5, ...}')
        print()
        
        print("🔧 命令行参数:")
        print("  python main.py --extract     # 只执行关键词提取")
        print("  python main.py --match       # 只执行政策匹配") 
        print("  python main.py --full        # 执行完整分析流程")
        print("  python main.py --status      # 查看系统状态")
    
    def run_interactive(self):
        """交互式运行"""
        while True:
            self.show_menu()
            
            try:
                choice = input("\n请选择功能 (0-5): ").strip()
                
                if choice == '0':
                    print("\n👋 感谢使用政策AI系统，再见!")
                    break
                elif choice == '1':
                    self.extract_keywords()
                elif choice == '2':
                    self.match_policies()
                elif choice == '3':
                    self.run_full_analysis()
                elif choice == '4':
                    self.show_status()
                elif choice == '5':
                    self.show_help()
                else:
                    print("❌ 无效选择，请输入 0-5")
                
                if choice in ['1', '2', '3']:
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
    parser = argparse.ArgumentParser(description='政策AI系统 - 关键词提取与政策匹配')
    parser.add_argument('--extract', action='store_true', help='执行关键词提取')
    parser.add_argument('--match', action='store_true', help='执行政策匹配')
    parser.add_argument('--full', action='store_true', help='执行完整分析流程')
    parser.add_argument('--status', action='store_true', help='查看系统状态')
    parser.add_argument('--help-detail', action='store_true', help='显示详细帮助')
    
    args = parser.parse_args()
    
    # 初始化系统
    try:
        system = PolicyAISystem()
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return
    
    # 根据参数执行相应功能
    if args.extract:
        system.extract_keywords()
    elif args.match:
        system.match_policies()
    elif args.full:
        system.run_full_analysis()
    elif args.status:
        system.show_status()
    elif args.help_detail:
        system.show_help()
    else:
        # 没有参数时运行交互式界面
        print("🎯 欢迎使用政策AI系统!")
        print("   整合关键词提取和政策匹配功能")
        system.run_interactive()

if __name__ == "__main__":
    main()