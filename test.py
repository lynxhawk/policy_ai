#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人才流动趋势分析工具
分析行业和工种的人才数量变化趋势，以及外地户籍就职人数变化
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class TalentFlowAnalyzer:
    """人才流动趋势分析器"""
    
    def __init__(self):
        self.data = None
        self.local_data = None
        self.results = {}
        self.local_results = {}
        
    def load_data(self, file1_path, file2_path, local_file_path):
        """加载三个JSON数据文件"""
        print("📁 正在加载人才流动数据...")
        
        # 读取第一个文件（求职者数据）
        with open(file1_path, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        
        # 读取第二个文件（企业需求数据）
        with open(file2_path, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
            
        # 读取外地户籍就职数据
        with open(local_file_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        # 转换为DataFrame
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)
        df_local = pd.DataFrame(local_data)
        
        # 标记数据来源
        df1['dataset'] = '求职者数据'
        df2['dataset'] = '企业需求数据'
        
        # 合并求职者和企业需求数据
        self.data = pd.concat([df1, df2], ignore_index=True)
        
        # 处理外地户籍数据
        self.local_data = df_local
        
        # 数据预处理
        self.data['date'] = pd.to_datetime(self.data[['year', 'month']].assign(day=1))
        self.data = self.data.sort_values(['dataset', 'industry', 'date']).reset_index(drop=True)
        
        self.local_data['date'] = pd.to_datetime(self.local_data[['year', 'month']].assign(day=1))
        self.local_data = self.local_data.sort_values('date').reset_index(drop=True)
        
        print(f"✅ 数据加载完成！")
        print(f"📊 人才流动数据: {len(self.data)} 条记录")
        print(f"🏠 外地户籍数据: {len(self.local_data)} 条记录")
        print(f"📊 数据类型: {', '.join(self.data['dataset'].unique())}")
        print(f"🏭 行业数量: {self.data['industry'].nunique()}")
        print(f"📅 时间跨度: {self.data['date'].min().strftime('%Y-%m')} 至 {self.data['date'].max().strftime('%Y-%m')}")
        
        return self.data, self.local_data
    
    def calculate_mom_growth(self, group):
        """
        计算环比增长率 (Month-over-Month Growth)
        公式: MoM = (当期人数 - 上期人数) / 上期人数 × 100%
        """
        group = group.sort_values('date')
        group['mom_growth'] = group['count'].pct_change() * 100
        return group
    
    def calculate_yoy_growth(self, group):
        """
        计算同比增长率 (Year-over-Year Growth)  
        公式: YoY = (当期人数 - 去年同期人数) / 去年同期人数 × 100%
        """
        group = group.sort_values('date')
        # 计算12个月前的值
        group['yoy_growth'] = group['count'].pct_change(periods=12) * 100
        return group
    
    def calculate_growth_rates(self):
        """计算所有人才流动增长率指标"""
        print("\n📈 计算人才流动增长率...")
        
        # 按数据集和行业分组计算
        self.data = self.data.groupby(['dataset', 'industry']).apply(
            lambda x: self.calculate_yoy_growth(self.calculate_mom_growth(x))
        ).reset_index(drop=True)
        
        # 计算外地户籍数据增长率
        self.local_data = self.calculate_yoy_growth(self.calculate_mom_growth(self.local_data))
        
        # 统计结果
        mom_stats = self.data['mom_growth'].describe()
        yoy_stats = self.data['yoy_growth'].describe()
        
        print("环比人才流动统计:")
        print(f"  平均变化: {mom_stats['mean']:.2f}%")
        print(f"  标准差: {mom_stats['std']:.2f}%")
        print(f"  最大增幅: {mom_stats['max']:.2f}%")
        print(f"  最大降幅: {mom_stats['min']:.2f}%")
        
        print("\n同比人才流动统计:")
        print(f"  平均变化: {yoy_stats['mean']:.2f}%")
        print(f"  标准差: {yoy_stats['std']:.2f}%")
        print(f"  最大增幅: {yoy_stats['max']:.2f}%")
        print(f"  最大降幅: {yoy_stats['min']:.2f}%")
        
        # 外地户籍数据统计
        local_mom_stats = self.local_data['mom_growth'].describe()
        local_yoy_stats = self.local_data['yoy_growth'].describe()
        
        print("\n🏠 外地户籍就职统计:")
        print(f"  环比平均变化: {local_mom_stats['mean']:.2f}%")
        print(f"  同比平均变化: {local_yoy_stats['mean']:.2f}%")
        
        return self.data, self.local_data
    
    def calculate_talent_flow_metrics(self, values):
        """
        计算人才流动波动性指标
        
        指标说明:
        1. 变异系数 CV = 标准差/均值 (衡量人数变化的相对波动)
        2. 人才流失率 = 最大人数下降幅度
        3. 人才增长稳定性 = 基于月度变化的稳定性指标
        4. 季节性波动 = 人才数量的季节性变化模式
        """
        values = np.array(values)
        
        # 基本统计量
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        var_val = np.var(values, ddof=1)
        
        # 变异系数 - 衡量人才数量变化的相对稳定性
        cv = std_val / mean_val if mean_val != 0 else np.inf
        
        # 最大人才流失计算 (类似最大回撤)
        peak = values[0]
        max_talent_loss = 0
        for val in values:
            if val > peak:
                peak = val
            if peak != 0:
                loss_rate = (peak - val) / peak
                max_talent_loss = max(max_talent_loss, loss_rate)
        
        # 人才流动率波动 (基于期间变化率)
        if len(values) > 1:
            changes = np.diff(values) / values[:-1]
            flow_volatility = np.std(changes, ddof=1)
        else:
            flow_volatility = 0
        
        # 计算趋势强度
        if len(values) >= 3:
            x = np.arange(len(values))
            trend_slope = np.polyfit(x, values, 1)[0]  # 线性趋势斜率
            trend_strength = abs(trend_slope) / mean_val if mean_val != 0 else 0
        else:
            trend_slope = 0
            trend_strength = 0
        
        return {
            'mean_talent_count': mean_val,
            'std_talent_count': std_val,
            'variance': var_val,
            'cv': cv,  # 变异系数
            'max_talent_loss_rate': max_talent_loss * 100,  # 最大人才流失率百分比
            'flow_volatility': flow_volatility * 100,  # 人才流动波动率
            'trend_slope': trend_slope,  # 趋势斜率
            'trend_strength': trend_strength,  # 趋势强度
            'stability_index': (1 / (1 + cv)) * 100  # 稳定性指数 (0-100)
        }
    
    def trend_analysis(self):
        """进行人才流动趋势分析"""
        print("\n🔍 进行人才流动趋势分析...")
        
        analysis_results = {}
        
        # 分析求职者和企业需求数据
        for dataset in self.data['dataset'].unique():
            for industry in self.data['industry'].unique():
                # 筛选数据
                subset = self.data[
                    (self.data['dataset'] == dataset) & 
                    (self.data['industry'] == industry)
                ].sort_values('date')
                
                if len(subset) < 3:  # 至少需要3个数据点
                    continue
                
                # 准备数据
                x = np.arange(len(subset))
                y = subset['count'].values
                
                # 人才流动指标
                flow_metrics = self.calculate_talent_flow_metrics(y)
                
                # 存储结果
                key = f"{dataset}_{industry}"
                analysis_results[key] = {
                    'dataset': dataset,
                    'industry': industry,
                    'data_points': len(subset),
                    'flow_metrics': flow_metrics,
                    'raw_data': {'x': x, 'y': y, 'dates': subset['date'].values}
                }
        
        # 分析外地户籍数据
        if len(self.local_data) >= 3:
            x_local = np.arange(len(self.local_data))
            y_local = self.local_data['count'].values
            flow_metrics_local = self.calculate_talent_flow_metrics(y_local)
            
            self.local_results = {
                'dataset': '外地户籍就职数据',
                'data_points': len(self.local_data),
                'flow_metrics': flow_metrics_local,
                'raw_data': {'x': x_local, 'y': y_local, 'dates': self.local_data['date'].values}
            }
        
        self.results = analysis_results
        return analysis_results, self.local_results
    
    def generate_talent_trend_description(self, result, is_local=False):
        """生成人才流动趋势描述"""
        
        # 获取基础数据
        y = result['raw_data']['y']
        dataset = result['dataset']
        industry = result.get('industry', '')
        flow_metrics = result['flow_metrics']
        
        # 计算基础指标
        start_count = int(y[0])
        end_count = int(y[-1])
        total_change = end_count - start_count
        total_change_pct = (total_change / start_count) * 100 if start_count != 0 else 0
        
        # 计算平均月度变化
        if len(y) > 1:
            monthly_changes = np.diff(y)
            avg_monthly_change = np.mean(monthly_changes)
        else:
            avg_monthly_change = 0
        
        # 开始生成描述
        description = []
        
        # 1. 基本概况
        if is_local:
            description.append(f"🏠 **外地户籍在本市就职** 人才流动分析")
        else:
            description.append(f"👥 **{dataset} - {industry}行业** 人才流动分析")
        
        # 2. 人才数量趋势判断
        if abs(total_change_pct) < 3:
            trend_desc = "人才数量基本稳定"
            trend_emoji = "📊"
        elif total_change_pct >= 20:
            trend_desc = "人才需求/供给大幅增长"
            trend_emoji = "🚀"
        elif total_change_pct >= 10:
            trend_desc = "人才需求/供给稳步增长"
            trend_emoji = "📈"
        elif total_change_pct >= 3:
            trend_desc = "人才需求/供给温和增长"
            trend_emoji = "📈"
        elif total_change_pct <= -20:
            trend_desc = "人才需求/供给大幅下降"
            trend_emoji = "📉"
        elif total_change_pct <= -10:
            trend_desc = "人才需求/供给明显下降"
            trend_emoji = "📉"
        else:
            trend_desc = "人才需求/供给小幅下降"
            trend_emoji = "📉"
        
        if is_local:
            if total_change_pct >= 10:
                trend_desc = trend_desc.replace("需求/供给", "流入")
            elif total_change_pct <= -10:
                trend_desc = trend_desc.replace("需求/供给", "流出")
            else:
                trend_desc = trend_desc.replace("需求/供给", "流动")
        
        description.append(f"\n{trend_emoji} **总体趋势**: {trend_desc}，变化幅度为{total_change_pct:+.1f}%")
        
        # 3. 具体人数变化
        description.append(f"   - 人才数量从 {start_count:,} 人变化至 {end_count:,} 人")
        description.append(f"   - 净变化 {total_change:+,} 人，月均变化 {avg_monthly_change:+.0f} 人")
        
        # 4. 人才流动稳定性分析
        cv = flow_metrics['cv']
        stability_index = flow_metrics['stability_index']
        max_loss_rate = flow_metrics['max_talent_loss_rate']
        
        if cv < 0.1:
            stability_desc = "非常稳定"
            stability_emoji = "🟢"
        elif cv < 0.2:
            stability_desc = "相对稳定"
            stability_emoji = "🟡"
        elif cv < 0.3:
            stability_desc = "波动较大"
            stability_emoji = "🟠"
        else:
            stability_desc = "波动剧烈"
            stability_emoji = "🔴"
        
        description.append(f"\n{stability_emoji} **流动稳定性**: {stability_desc}")
        description.append(f"   - 稳定性指数: {stability_index:.1f}/100")
        description.append(f"   - 最大流失率: {max_loss_rate:.1f}%")
        description.append(f"   - 变异系数: {cv:.3f}")
        
        # 5. 人才配置建议
        description.append(f"\n💡 **人才配置建议**:")
        
        if is_local:
            # 外地户籍就职建议
            if total_change_pct > 15 and cv < 0.2:
                description.append("   - ✅ 外地人才持续流入且稳定，城市吸引力强")
            elif total_change_pct > 10 and cv > 0.3:
                description.append("   - ⚠️ 外地人才流入较快但波动大，需关注留才政策")
            elif total_change_pct < -10:
                description.append("   - 📉 外地人才出现流出趋势，需加强人才吸引政策")
            else:
                description.append("   - 📊 外地人才流动相对平稳")
        else:
            if dataset == '求职者数据':
                if total_change_pct > 15 and cv < 0.2:
                    description.append("   - ✅ 该行业求职者增长强劲且稳定，是热门就业方向")
                elif total_change_pct > 10 and cv > 0.3:
                    description.append("   - ⚠️ 该行业求职者增长较快但波动大，需关注就业稳定性")
                elif total_change_pct < -10:
                    description.append("   - 📉 该行业求职者数量下降，可能就业机会减少")
                else:
                    description.append("   - 📊 该行业求职者数量相对稳定")
            else:  # 企业需求数据
                if total_change_pct > 15 and cv < 0.2:
                    description.append("   - ✅ 该行业人才需求旺盛且稳定，值得重点关注")
                elif total_change_pct > 10 and cv > 0.3:
                    description.append("   - ⚠️ 该行业人才需求增长较快但不稳定，需注意市场变化")
                elif total_change_pct < -10:
                    description.append("   - 📉 该行业人才需求下降，建议谨慎进入")
                else:
                    description.append("   - 📊 该行业人才需求相对平稳")
        
        if max_loss_rate > 25:
            description.append("   - 🚨 注意：该领域历史上曾出现大幅人才流失")
        
        return "\n".join(description)
    
    def generate_talent_flow_report(self):
        """生成人才流动完整报告"""
        print("\n" + "="*80)
        print("👥 人才流动趋势分析报告")
        print("="*80)
        
        # 为每个数据集生成描述
        for key, result in self.results.items():
            description = self.generate_talent_trend_description(result)
            print("\n" + description)
            print("\n" + "-"*60)
        
        # 生成外地户籍分析
        if self.local_results:
            local_description = self.generate_talent_trend_description(self.local_results, is_local=True)
            print("\n" + local_description)
            print("\n" + "-"*60)
        
        # 生成供需对比分析
        print(f"\n📊 **人才供需对比分析**")
        self._generate_supply_demand_comparison()
        
        return self.results, self.local_results
    
    def _generate_supply_demand_comparison(self):
        """生成人才供需对比分析"""
        # 按行业分组，比较求职者和企业需求
        industries = set()
        for result in self.results.values():
            industries.add(result['industry'])
        
        for industry in industries:
            supply_data = None  # 求职者数据
            demand_data = None  # 企业需求数据
            
            for key, result in self.results.items():
                if result['industry'] == industry:
                    if '求职者数据' in result['dataset']:
                        supply_data = result
                    elif '企业需求数据' in result['dataset']:
                        demand_data = result
            
            if supply_data and demand_data:
                supply_trend = (supply_data['raw_data']['y'][-1] - supply_data['raw_data']['y'][0]) / supply_data['raw_data']['y'][0] * 100
                demand_trend = (demand_data['raw_data']['y'][-1] - demand_data['raw_data']['y'][0]) / demand_data['raw_data']['y'][0] * 100
                
                supply_avg = np.mean(supply_data['raw_data']['y'])
                demand_avg = np.mean(demand_data['raw_data']['y'])
                
                if supply_avg > demand_avg * 1.2:
                    market_status = "人才供过于求"
                    status_emoji = "📊"
                elif demand_avg > supply_avg * 1.2:
                    market_status = "人才供不应求"
                    status_emoji = "🔥"
                else:
                    market_status = "人才供需基本平衡"
                    status_emoji = "⚖️"
                
                print(f"\n{status_emoji} **{industry}行业**: {market_status}")
                print(f"   - 求职者变化趋势: {supply_trend:+.1f}% | 企业需求变化趋势: {demand_trend:+.1f}%")
                print(f"   - 平均求职者: {supply_avg:.0f}人 | 平均企业需求: {demand_avg:.0f}人")
    
    def visualize_talent_trends(self, max_plots=8):
        """可视化人才流动趋势"""
        print(f"\n🎨 生成人才流动趋势图表...")
        
        # 选择结果进行可视化
        plot_keys = list(self.results.keys())[:max_plots]
        
        # 如果有外地户籍数据，添加到可视化中
        include_local = bool(self.local_results)
        total_plots = len(plot_keys) + (1 if include_local else 0)
        
        cols = 2
        rows = (total_plots + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(16, 6*rows))
        if rows == 1:
            axes = axes.reshape(1, -1)
        elif total_plots == 1:
            axes = np.array([[axes]])
        axes = axes.flatten()
        
        plot_idx = 0
        
        # 绘制人才流动数据
        for i, key in enumerate(plot_keys):
            result = self.results[key]
            ax = axes[plot_idx]
            
            # 获取数据
            x = result['raw_data']['x']
            y = result['raw_data']['y']
            
            # 绘制原始数据
            ax.scatter(x, y, alpha=0.7, color='steelblue', label='实际人数', s=80)
            
            # 绘制趋势线
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax.plot(x, p(x), 'orange', linewidth=3, label='趋势线')
            
            # 设置标题和标签
            dataset_short = '求职者' if '求职者' in result['dataset'] else '企业需求'
            ax.set_title(f"{dataset_short} - {result['industry']}", fontsize=12, fontweight='bold')
            ax.set_xlabel('时间点')
            ax.set_ylabel('人数')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 根据稳定性设置背景色
            stability = result['flow_metrics']['stability_index']
            if stability > 80:
                ax.set_facecolor('#f0f8ff')  # 高稳定性 - 浅蓝
            elif stability > 60:
                ax.set_facecolor('#fffaf0')  # 中等稳定性 - 浅橙
            else:
                ax.set_facecolor('#fff5f5')  # 低稳定性 - 浅红
            
            plot_idx += 1
        
        # 绘制外地户籍数据
        if include_local:
            ax = axes[plot_idx]
            result = self.local_results
            
            # 获取数据
            x = result['raw_data']['x']
            y = result['raw_data']['y']
            
            # 绘制原始数据
            ax.scatter(x, y, alpha=0.7, color='green', label='实际人数', s=80)
            
            # 绘制趋势线
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax.plot(x, p(x), 'red', linewidth=3, label='趋势线')
            
            # 设置标题和标签
            ax.set_title("外地户籍在本市就职", fontsize=12, fontweight='bold')
            ax.set_xlabel('时间点')
            ax.set_ylabel('人数')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 设置背景色
            stability = result['flow_metrics']['stability_index']
            if stability > 80:
                ax.set_facecolor('#f0fff0')  # 高稳定性 - 浅绿
            elif stability > 60:
                ax.set_facecolor('#fffaf0')  # 中等稳定性 - 浅橙
            else:
                ax.set_facecolor('#fff5f5')  # 低稳定性 - 浅红
            
            plot_idx += 1
        
        # 隐藏多余的子图
        for i in range(plot_idx, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        plt.savefig('talent_flow_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return fig
    
    def print_technical_summary(self):
        """打印技术分析摘要"""
        print("\n" + "="*80)
        print("📊 技术分析摘要")
        print("="*80)
        
        all_stability_scores = []
        
        for key, result in self.results.items():
            dataset = result['dataset']
            industry = result['industry']
            
            print(f"\n🏭 {dataset} - {industry}")
            print("-" * 50)
            
            # 基本信息
            print(f"数据点数: {result['data_points']}")
            
            # 流动性指标
            flow = result['flow_metrics']
            print(f"📊 人才流动指标:")
            print(f"   平均人数: {flow['mean_talent_count']:.0f}")
            print(f"   变异系数: {flow['cv']:.4f}")
            print(f"   稳定性指数: {flow['stability_index']:.1f}/100")
            print(f"   趋势强度: {flow['trend_strength']:.4f}")
            
            all_stability_scores.append(flow['stability_index'])
        
        # 外地户籍数据摘要
        if self.local_results:
            print(f"\n🏠 外地户籍在本市就职")
            print("-" * 50)
            print(f"数据点数: {self.local_results['data_points']}")
            
            flow = self.local_results['flow_metrics']
            print(f"📊 人才流动指标:")
            print(f"   平均人数: {flow['mean_talent_count']:.0f}")
            print(f"   变异系数: {flow['cv']:.4f}")
            print(f"   稳定性指数: {flow['stability_index']:.1f}/100")
            print(f"   趋势强度: {flow['trend_strength']:.4f}")
            
            all_stability_scores.append(flow['stability_index'])
        
        # 整体稳定性
        print(f"\n🎯 整体分析结果:")
        print(f"平均稳定性指数: {np.mean(all_stability_scores):.1f}/100")


def main():
    """主函数"""
    print("🚀 人才流动趋势分析开始...")
    
    # 创建分析器
    analyzer = TalentFlowAnalyzer()
    
    # 加载数据（请修改为实际的文件路径）
    file1 = "applicant_position.json"  # 求职者数据文件
    file2 = "corporate_position.json"  # 企业需求数据文件
    file3 = "local_count.json"         # 外地户籍就职数据文件
    
    try:
        # 加载数据
        data, local_data = analyzer.load_data(file1, file2, file3)
        
        # 计算增长率
        analyzer.calculate_growth_rates()
        
        # 趋势分析
        analyzer.trend_analysis()
        
        # 生成人才流动报告（主要功能）
        analyzer.generate_talent_flow_report()
        
        # 生成可视化
        analyzer.visualize_talent_trends()
        
        # 打印技术摘要（可选）
        analyzer.print_technical_summary()
        
        print("\n✅ 人才流动分析完成！")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("请确保 applicant_position.json、corporate_position.json 和 local_count.json 文件在当前目录下")
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()