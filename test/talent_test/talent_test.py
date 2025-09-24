#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人才流动数据分析工具
分析企业招聘岗位、求职者意向、外地户籍就职的同比环比及稳定性指标
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TalentDataAnalyzer:
    """人才流动数据分析器"""
    
    def __init__(self):
        self.enterprise_data = None  # 企业招聘数据
        self.jobseeker_data = None   # 求职者数据  
        self.nonlocal_data = None    # 外地户籍数据
        
    def load_data(self, enterprise_file, jobseeker_file, nonlocal_file):
        """
        加载三类数据文件
        参数:
        - enterprise_file: 企业招聘岗位数据文件路径
        - jobseeker_file: 求职者求职意向数据文件路径  
        - nonlocal_file: 外地户籍就职数据文件路径
        """
        print("正在加载数据文件...")
        
        # 加载企业招聘数据
        with open(enterprise_file, 'r', encoding='utf-8') as f:
            enterprise_raw = json.load(f)
        self.enterprise_data = pd.DataFrame(enterprise_raw)
        
        # 加载求职者数据
        with open(jobseeker_file, 'r', encoding='utf-8') as f:
            jobseeker_raw = json.load(f)
        self.jobseeker_data = pd.DataFrame(jobseeker_raw)
        
        # 加载外地户籍数据
        with open(nonlocal_file, 'r', encoding='utf-8') as f:
            nonlocal_raw = json.load(f)
        self.nonlocal_data = pd.DataFrame(nonlocal_raw)
        
        # 数据预处理
        self._preprocess_data()
        
        print(f"数据加载完成:")
        print(f"- 企业招聘数据: {len(self.enterprise_data)} 条记录")
        print(f"- 求职者数据: {len(self.jobseeker_data)} 条记录") 
        print(f"- 外地户籍数据: {len(self.nonlocal_data)} 条记录")
        
    def _preprocess_data(self):
        """数据预处理"""
        # 处理企业招聘数据
        if 'year' in self.enterprise_data.columns and 'month' in self.enterprise_data.columns:
            self.enterprise_data['date'] = pd.to_datetime(
                self.enterprise_data[['year', 'month']].assign(day=1)
            )
        self.enterprise_data = self.enterprise_data.sort_values('date').reset_index(drop=True)
        
        # 处理求职者数据
        if 'year' in self.jobseeker_data.columns and 'month' in self.jobseeker_data.columns:
            self.jobseeker_data['date'] = pd.to_datetime(
                self.jobseeker_data[['year', 'month']].assign(day=1)
            )
        self.jobseeker_data = self.jobseeker_data.sort_values('date').reset_index(drop=True)
        
        # 处理外地户籍数据
        if 'year' in self.nonlocal_data.columns and 'month' in self.nonlocal_data.columns:
            self.nonlocal_data['date'] = pd.to_datetime(
                self.nonlocal_data[['year', 'month']].assign(day=1)
            )
        self.nonlocal_data = self.nonlocal_data.sort_values('date').reset_index(drop=True)
        
    def calculate_growth_rates(self, data, value_column='count'):
        """
        计算环比和同比增长率
        """
        data = data.copy().sort_values('date')
        
        # 环比增长率 (月度对比)
        data['mom_growth'] = data[value_column].pct_change() * 100
        
        # 同比增长率 (年度对比，12个月前)
        data['yoy_growth'] = data[value_column].pct_change(periods=12) * 100
        
        return data
        
    def calculate_stability_metrics(self, values):
        """
        计算稳定性指标和趋势强度
        """
        values = np.array(values)
        if len(values) < 2:
            return {
                'stability_index': 0,
                'trend_strength': 0,
                'volatility': 0,
                'mean_value': 0
            }
            
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        
        # 变异系数
        cv = std_val / mean_val if mean_val != 0 else np.inf
        
        # 稳定性指数 (0-100分，值越大越稳定)
        stability_index = (1 / (1 + cv)) * 100 if cv != np.inf else 0
        
        # 趋势强度 (线性回归斜率的归一化值)
        if len(values) >= 3:
            x = np.arange(len(values))
            trend_slope = np.polyfit(x, values, 1)[0]
            trend_strength = abs(trend_slope) / mean_val if mean_val != 0 else 0
        else:
            trend_strength = 0
            
        # 波动率
        if len(values) > 1:
            changes = np.diff(values) / values[:-1]
            volatility = np.std(changes, ddof=1) * 100
        else:
            volatility = 0
            
        return {
            'stability_index': stability_index,
            'trend_strength': trend_strength, 
            'volatility': volatility,
            'mean_value': mean_val
        }
    
    def analyze_industry_data(self, data, data_type, value_column='count'):
        """
        按行业分析数据
        """
        results = {}
        
        if 'industry' not in data.columns:
            print(f"警告: {data_type}数据中没有industry列")
            return results
            
        # 计算增长率
        data_with_growth = data.groupby('industry').apply(
            lambda x: self.calculate_growth_rates(x, value_column)
        ).reset_index(drop=True)
        
        # 按行业统计
        for industry in data['industry'].unique():
            industry_data = data_with_growth[data_with_growth['industry'] == industry].copy()
            
            if len(industry_data) < 2:
                continue
                
            values = industry_data[value_column].values
            
            # 计算各项指标
            stability_metrics = self.calculate_stability_metrics(values)
            
            # 计算增长率统计
            mom_growth = industry_data['mom_growth'].dropna()
            yoy_growth = industry_data['yoy_growth'].dropna()
            
            results[industry] = {
                'data_type': data_type,
                'total_records': len(industry_data),
                'mean_count': stability_metrics['mean_value'],
                'stability_index': stability_metrics['stability_index'],
                'trend_strength': stability_metrics['trend_strength'],
                'volatility': stability_metrics['volatility'],
                'avg_mom_growth': mom_growth.mean() if len(mom_growth) > 0 else 0,
                'avg_yoy_growth': yoy_growth.mean() if len(yoy_growth) > 0 else 0,
                'latest_mom_growth': mom_growth.iloc[-1] if len(mom_growth) > 0 else 0,
                'latest_yoy_growth': yoy_growth.iloc[-1] if len(yoy_growth) > 0 else 0,
                'max_count': values.max(),
                'min_count': values.min(),
                'total_change_pct': ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
            }
            
        return results
    
    def analyze_nonlocal_data(self, value_column='count'):
        """
        分析外地户籍就职数据
        """
        if self.nonlocal_data is None or len(self.nonlocal_data) < 2:
            return {}
            
        # 计算增长率
        data_with_growth = self.calculate_growth_rates(self.nonlocal_data, value_column)
        
        values = data_with_growth[value_column].values
        
        # 计算稳定性指标
        stability_metrics = self.calculate_stability_metrics(values)
        
        # 计算增长率统计
        mom_growth = data_with_growth['mom_growth'].dropna()
        yoy_growth = data_with_growth['yoy_growth'].dropna()
        
        result = {
            'data_type': '外地户籍就职',
            'total_records': len(data_with_growth),
            'mean_count': stability_metrics['mean_value'],
            'stability_index': stability_metrics['stability_index'],
            'trend_strength': stability_metrics['trend_strength'],
            'volatility': stability_metrics['volatility'],
            'avg_mom_growth': mom_growth.mean() if len(mom_growth) > 0 else 0,
            'avg_yoy_growth': yoy_growth.mean() if len(yoy_growth) > 0 else 0,
            'latest_mom_growth': mom_growth.iloc[-1] if len(mom_growth) > 0 else 0,
            'latest_yoy_growth': yoy_growth.iloc[-1] if len(yoy_growth) > 0 else 0,
            'max_count': values.max(),
            'min_count': values.min(),
            'total_change_pct': ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
        }
        
        return result
    
    def generate_comprehensive_report(self):
        """
        生成综合分析报告
        """
        print("\n" + "="*80)
        print("人才流动数据分析报告")
        print("="*80)
        
        all_results = {}
        
        # 分析企业招聘数据
        if self.enterprise_data is not None:
            print("\n分析企业招聘岗位数据...")
            enterprise_results = self.analyze_industry_data(
                self.enterprise_data, '企业招聘岗位'
            )
            all_results['enterprise'] = enterprise_results
            
        # 分析求职者数据  
        if self.jobseeker_data is not None:
            print("分析求职者求职意向数据...")
            jobseeker_results = self.analyze_industry_data(
                self.jobseeker_data, '求职者求职意向'
            )
            all_results['jobseeker'] = jobseeker_results
            
        # 分析外地户籍数据
        if self.nonlocal_data is not None:
            print("分析外地户籍就职数据...")
            nonlocal_result = self.analyze_nonlocal_data()
            all_results['nonlocal'] = nonlocal_result
        
        # 生成报告
        self._print_detailed_report(all_results)
        
        return all_results
    
    def _print_detailed_report(self, all_results):
        """打印详细报告"""
        
        # 企业招聘数据报告
        if 'enterprise' in all_results:
            print("\n" + "="*60)
            print("企业招聘岗位涉及行业分析")
            print("="*60)
            
            enterprise_data = all_results['enterprise']
            for industry, metrics in enterprise_data.items():
                self._print_industry_metrics(industry, metrics)
        
        # 求职者数据报告        
        if 'jobseeker' in all_results:
            print("\n" + "="*60)
            print("求职者求职意向涉及行业分析") 
            print("="*60)
            
            jobseeker_data = all_results['jobseeker']
            for industry, metrics in jobseeker_data.items():
                self._print_industry_metrics(industry, metrics)
        
        # 外地户籍数据报告
        if 'nonlocal' in all_results:
            print("\n" + "="*60)
            print("外地户籍在本城市就职人数分析")
            print("="*60)
            
            nonlocal_data = all_results['nonlocal']
            self._print_nonlocal_metrics(nonlocal_data)
    
    def _print_industry_metrics(self, industry, metrics):
        """打印行业指标"""
        print(f"\n行业: {industry}")
        print("-" * 50)
        print(f"数据记录数: {metrics['total_records']}")
        print(f"平均人数: {metrics['mean_count']:.1f}")
        print(f"最大人数: {metrics['max_count']:.0f}")
        print(f"最小人数: {metrics['min_count']:.0f}")
        print(f"总体变化: {metrics['total_change_pct']:+.1f}%")
        print()
        print("增长率指标:")
        print(f"  平均环比增长率: {metrics['avg_mom_growth']:+.2f}%")
        print(f"  平均同比增长率: {metrics['avg_yoy_growth']:+.2f}%") 
        print(f"  最新环比增长率: {metrics['latest_mom_growth']:+.2f}%")
        print(f"  最新同比增长率: {metrics['latest_yoy_growth']:+.2f}%")
        print()
        print("稳定性指标:")
        print(f"  稳定性指数: {metrics['stability_index']:.1f}/100")
        print(f"  趋势强度: {metrics['trend_strength']:.4f}")
        print(f"  波动率: {metrics['volatility']:.2f}%")
        
        # 趋势判断
        if metrics['trend_strength'] > 0.05:
            trend_desc = "强趋势"
        elif metrics['trend_strength'] > 0.02:
            trend_desc = "中等趋势"
        else:
            trend_desc = "弱趋势"
            
        if metrics['stability_index'] > 80:
            stability_desc = "高稳定"
        elif metrics['stability_index'] > 60:
            stability_desc = "中等稳定"
        else:
            stability_desc = "不稳定"
            
        print(f"  趋势评级: {trend_desc}")
        print(f"  稳定性评级: {stability_desc}")
    
    def _print_nonlocal_metrics(self, metrics):
        """打印外地户籍指标"""
        print(f"数据记录数: {metrics['total_records']}")
        print(f"平均人数: {metrics['mean_count']:.1f}")
        print(f"最大人数: {metrics['max_count']:.0f}")
        print(f"最小人数: {metrics['min_count']:.0f}")
        print(f"总体变化: {metrics['total_change_pct']:+.1f}%")
        print()
        print("增长率指标:")
        print(f"  平均环比增长率: {metrics['avg_mom_growth']:+.2f}%")
        print(f"  平均同比增长率: {metrics['avg_yoy_growth']:+.2f}%")
        print(f"  最新环比增长率: {metrics['latest_mom_growth']:+.2f}%")  
        print(f"  最新同比增长率: {metrics['latest_yoy_growth']:+.2f}%")
        print()
        print("稳定性指标:")
        print(f"  稳定性指数: {metrics['stability_index']:.1f}/100")
        print(f"  趋势强度: {metrics['trend_strength']:.4f}")
        print(f"  波动率: {metrics['volatility']:.2f}%")
        
        # 趋势判断
        if metrics['trend_strength'] > 0.05:
            trend_desc = "强趋势"
        elif metrics['trend_strength'] > 0.02:
            trend_desc = "中等趋势" 
        else:
            trend_desc = "弱趋势"
            
        if metrics['stability_index'] > 80:
            stability_desc = "高稳定"
        elif metrics['stability_index'] > 60:
            stability_desc = "中等稳定"
        else:
            stability_desc = "不稳定"
            
        print(f"  趋势评级: {trend_desc}")
        print(f"  稳定性评级: {stability_desc}")
    
    def export_report_to_txt(self, all_results, filename=None):
        """导出分析报告到TXT文件"""
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"人才流动分析报告_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入报告标题
            f.write("="*80 + "\n")
            f.write("人才流动数据分析报告\n")
            f.write("="*80 + "\n")
            f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 企业招聘数据报告
            if 'enterprise' in all_results:
                f.write("="*60 + "\n")
                f.write("企业招聘岗位涉及行业分析\n")
                f.write("="*60 + "\n\n")
                
                enterprise_data = all_results['enterprise']
                for industry, metrics in enterprise_data.items():
                    self._write_industry_metrics_to_file(f, industry, metrics)
            
            # 求职者数据报告        
            if 'jobseeker' in all_results:
                f.write("="*60 + "\n")
                f.write("求职者求职意向涉及行业分析\n") 
                f.write("="*60 + "\n\n")
                
                jobseeker_data = all_results['jobseeker']
                for industry, metrics in jobseeker_data.items():
                    self._write_industry_metrics_to_file(f, industry, metrics)
            
            # 外地户籍数据报告
            if 'nonlocal' in all_results:
                f.write("="*60 + "\n")
                f.write("外地户籍在本城市就职人数分析\n")
                f.write("="*60 + "\n\n")
                
                nonlocal_data = all_results['nonlocal']
                self._write_nonlocal_metrics_to_file(f, nonlocal_data)
            
            # 写入总结
            f.write("="*60 + "\n")
            f.write("分析总结\n")
            f.write("="*60 + "\n")
            f.write("本报告包含以下分析内容:\n")
            f.write("1. 企业招聘岗位涉及行业的同比环比增长率分析\n")
            f.write("2. 求职者求职意向涉及行业的趋势强度分析\n")
            f.write("3. 外地户籍在本城市就职人数的稳定性指数分析\n")
            f.write("4. 各项数据的波动率和趋势评级\n\n")
            f.write("说明:\n")
            f.write("- 环比增长率: 与上月相比的增长百分比\n")
            f.write("- 同比增长率: 与去年同期相比的增长百分比\n")
            f.write("- 稳定性指数: 0-100分，分数越高表示数据越稳定\n")
            f.write("- 趋势强度: 反映数据变化趋势的强弱程度\n")
            f.write("- 波动率: 数据变化的波动幅度百分比\n")
        
        print(f"报告已导出到文件: {filename}")
        return filename
    
    def _write_industry_metrics_to_file(self, f, industry, metrics):
        """将行业指标写入文件"""
        f.write(f"行业: {industry}\n")
        f.write("-" * 50 + "\n")
        f.write(f"数据记录数: {metrics['total_records']}\n")
        f.write(f"平均人数: {metrics['mean_count']:.1f}\n")
        f.write(f"最大人数: {metrics['max_count']:.0f}\n")
        f.write(f"最小人数: {metrics['min_count']:.0f}\n")
        f.write(f"总体变化: {metrics['total_change_pct']:+.1f}%\n")
        f.write("\n")
        f.write("增长率指标:\n")
        f.write(f"  平均环比增长率: {metrics['avg_mom_growth']:+.2f}%\n")
        f.write(f"  平均同比增长率: {metrics['avg_yoy_growth']:+.2f}%\n") 
        f.write(f"  最新环比增长率: {metrics['latest_mom_growth']:+.2f}%\n")
        f.write(f"  最新同比增长率: {metrics['latest_yoy_growth']:+.2f}%\n")
        f.write("\n")
        f.write("稳定性指标:\n")
        f.write(f"  稳定性指数: {metrics['stability_index']:.1f}/100\n")
        f.write(f"  趋势强度: {metrics['trend_strength']:.4f}\n")
        f.write(f"  波动率: {metrics['volatility']:.2f}%\n")
        
        # 趋势判断
        if metrics['trend_strength'] > 0.05:
            trend_desc = "强趋势"
        elif metrics['trend_strength'] > 0.02:
            trend_desc = "中等趋势"
        else:
            trend_desc = "弱趋势"
            
        if metrics['stability_index'] > 80:
            stability_desc = "高稳定"
        elif metrics['stability_index'] > 60:
            stability_desc = "中等稳定"
        else:
            stability_desc = "不稳定"
            
        f.write(f"  趋势评级: {trend_desc}\n")
        f.write(f"  稳定性评级: {stability_desc}\n\n")
    
    def _write_nonlocal_metrics_to_file(self, f, metrics):
        """将外地户籍指标写入文件"""
        f.write(f"数据记录数: {metrics['total_records']}\n")
        f.write(f"平均人数: {metrics['mean_count']:.1f}\n")
        f.write(f"最大人数: {metrics['max_count']:.0f}\n")
        f.write(f"最小人数: {metrics['min_count']:.0f}\n")
        f.write(f"总体变化: {metrics['total_change_pct']:+.1f}%\n")
        f.write("\n")
        f.write("增长率指标:\n")
        f.write(f"  平均环比增长率: {metrics['avg_mom_growth']:+.2f}%\n")
        f.write(f"  平均同比增长率: {metrics['avg_yoy_growth']:+.2f}%\n")
        f.write(f"  最新环比增长率: {metrics['latest_mom_growth']:+.2f}%\n")  
        f.write(f"  最新同比增长率: {metrics['latest_yoy_growth']:+.2f}%\n")
        f.write("\n")
        f.write("稳定性指标:\n")
        f.write(f"  稳定性指数: {metrics['stability_index']:.1f}/100\n")
        f.write(f"  趋势强度: {metrics['trend_strength']:.4f}\n")
        f.write(f"  波动率: {metrics['volatility']:.2f}%\n")
        
        # 趋势判断
        if metrics['trend_strength'] > 0.05:
            trend_desc = "强趋势"
        elif metrics['trend_strength'] > 0.02:
            trend_desc = "中等趋势" 
        else:
            trend_desc = "弱趋势"
            
        if metrics['stability_index'] > 80:
            stability_desc = "高稳定"
        elif metrics['stability_index'] > 60:
            stability_desc = "中等稳定"
        else:
            stability_desc = "不稳定"
            
        f.write(f"  趋势评级: {trend_desc}\n")
        f.write(f"  稳定性评级: {stability_desc}\n\n")


def main():
    """主函数示例"""
    print("人才流动数据分析工具")
    print("请确保以下文件存在:")
    print("1. applicant_position.json (求职者数据)")  
    print("2. corporate_position.json (企业招聘数据)")
    print("3. local_count.json (外地户籍数据)")
    
    # 创建分析器实例
    analyzer = TalentDataAnalyzer()
    
    try:
        # 加载数据
        analyzer.load_data(
            enterprise_file="corporate_position.json",
            jobseeker_file="applicant_position.json", 
            nonlocal_file="local_count.json"
        )
        
        # 生成综合报告
        results = analyzer.generate_comprehensive_report()
        
        # 导出TXT报告
        txt_filename = analyzer.export_report_to_txt(results)
        
        print("\n分析完成!")
        print(f"报告已保存为: {txt_filename}")
        
        return analyzer, results
        
    except FileNotFoundError as e:
        print(f"文件未找到: {e}")
        print("请检查文件路径是否正确")
    except Exception as e:
        print(f"分析过程出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyzer, results = main()