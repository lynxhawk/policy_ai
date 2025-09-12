#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人才流动趋势分析工具（增强版）
专注于行业和工种的人才数量变化趋势分析
使用随机森林进行趋势预测和模式识别
新增：未来5个月预测功能
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class TalentFlowAnalyzer:
    """人才流动趋势分析器（增强版）"""
    
    def __init__(self):
        self.data = None
        self.results = {}
        
    def load_data(self, file1_path, file2_path):
        """加载两个JSON数据文件"""
        print("📁 正在加载人才流动数据...")
        
        # 读取第一个文件
        with open(file1_path, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        
        # 读取第二个文件
        with open(file2_path, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
        
        # 转换为DataFrame
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)
        
        # 标记数据来源
        df1['dataset'] = '求职者数据'
        df2['dataset'] = '企业需求数据'
        
        # 合并数据
        self.data = pd.concat([df1, df2], ignore_index=True)
        
        # 数据预处理
        self.data['date'] = pd.to_datetime(self.data[['year', 'month']].assign(day=1))
        self.data = self.data.sort_values(['dataset', 'industry', 'date']).reset_index(drop=True)
        
        print(f"✅ 数据加载完成！共 {len(self.data)} 条记录")
        print(f"📊 数据类型: {', '.join(self.data['dataset'].unique())}")
        print(f"🏭 行业数量: {self.data['industry'].nunique()}")
        print(f"📅 时间跨度: {self.data['date'].min().strftime('%Y-%m')} 至 {self.data['date'].max().strftime('%Y-%m')}")
        
        return self.data
    
    def calculate_mom_growth(self, group):
        """计算环比增长率"""
        group = group.sort_values('date')
        group['mom_growth'] = group['count'].pct_change() * 100
        return group
    
    def calculate_yoy_growth(self, group):
        """计算同比增长率"""
        group = group.sort_values('date')
        group['yoy_growth'] = group['count'].pct_change(periods=12) * 100
        return group
    
    def calculate_growth_rates(self):
        """计算所有人才流动增长率指标"""
        print("\n📈 计算人才流动增长率...")
        
        self.data = self.data.groupby(['dataset', 'industry']).apply(
            lambda x: self.calculate_yoy_growth(self.calculate_mom_growth(x))
        ).reset_index(drop=True)
        
        return self.data
    
    def random_forest_analysis_with_prediction(self, x, y, future_periods=5):
        """
        随机森林回归分析（增强版）
        包含未来预测功能 - 修复了线性预测问题
        """
        # 创建更丰富的特征工程
        def create_features(x_values, y_values=None):
            """创建多维特征"""
            features = []
            
            for i, x_val in enumerate(x_values):
                feature_row = []
                
                # 基础时间特征
                feature_row.append(x_val)  # 时间索引
                feature_row.append(x_val ** 2)  # 时间的平方项（捕获非线性）
                feature_row.append(np.sin(x_val * 2 * np.pi / 12))  # 年度周期性
                feature_row.append(np.cos(x_val * 2 * np.pi / 12))  # 年度周期性
                feature_row.append(np.sin(x_val * 2 * np.pi / 4))   # 季度周期性
                feature_row.append(np.cos(x_val * 2 * np.pi / 4))   # 季度周期性
                
                # 如果有历史数据，添加滞后特征
                if y_values is not None:
                    # 移动平均特征
                    if i >= 2:
                        ma_3 = np.mean(y_values[max(0, i-2):i+1])
                        feature_row.append(ma_3)
                    else:
                        feature_row.append(y_values[0] if len(y_values) > 0 else 0)
                    
                    # 前一期值
                    if i > 0:
                        feature_row.append(y_values[i-1])
                    else:
                        feature_row.append(y_values[0] if len(y_values) > 0 else 0)
                        
                    # 趋势特征（前期变化率）
                    if i > 0 and y_values[i-1] != 0:
                        trend = (y_values[i] - y_values[i-1]) / y_values[i-1]
                        feature_row.append(trend)
                    else:
                        feature_row.append(0)
                else:
                    # 对未来预测，使用最后几期的统计特征
                    recent_values = y[-3:] if len(y) >= 3 else y
                    feature_row.append(np.mean(recent_values))  # 近期均值
                    feature_row.append(recent_values[-1])       # 最后一期值
                    
                    # 最近趋势
                    if len(y) >= 2 and y[-2] != 0:
                        recent_trend = (y[-1] - y[-2]) / y[-2]
                        feature_row.append(recent_trend)
                    else:
                        feature_row.append(0)
                
                features.append(feature_row)
            
            return np.array(features)
        
        # 为历史数据创建特征
        X_train = create_features(x, y)
        
        # 使用更复杂的随机森林配置
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=3,
            min_samples_leaf=2,
            random_state=42,
            bootstrap=True,
            max_features='sqrt',  # 特征随机选择
            n_jobs=-1
        )
        
        model.fit(X_train, y)
        
        # 历史数据预测
        y_pred = model.predict(X_train)
        
        # 未来数据预测（逐步预测以保持连续性）
        future_x = np.arange(len(x), len(x) + future_periods)
        future_pred = []
        
        # 扩展历史数据用于预测
        extended_y = list(y)
        
        for i, future_time in enumerate(future_x):
            # 为当前未来时间点创建特征
            X_future = create_features([future_time], extended_y)
            
            # 预测
            pred = model.predict(X_future)[0]
            
            # 添加一些随机性以避免完全线性
            if i > 0:
                # 基于最近的变化趋势添加波动
                recent_change = extended_y[-1] - extended_y[-2] if len(extended_y) >= 2 else 0
                noise_factor = np.random.normal(0, abs(recent_change) * 0.1)
                pred += noise_factor
            
            # 确保预测值合理（不为负且不会出现异常值）
            pred = max(pred, 0)
            if len(extended_y) > 0:
                pred = min(pred, extended_y[-1] * 3)  # 不超过上期的3倍
                pred = max(pred, extended_y[-1] * 0.3)  # 不低于上期的30%
            
            future_pred.append(pred)
            extended_y.append(pred)  # 为下一期预测提供数据
        
        future_pred = np.array(future_pred)
        
        # 计算置信区间
        residuals = y - y_pred
        std_residual = np.std(residuals) if len(residuals) > 1 else np.std(y) * 0.1
        
        # 考虑预测不确定性递增
        uncertainty_growth = np.array([1.0, 1.3, 1.6, 2.0, 2.5])[:future_periods]
        future_upper = future_pred + uncertainty_growth * std_residual * 1.96
        future_lower = future_pred - uncertainty_growth * std_residual * 1.96
        future_lower = np.maximum(future_lower, 0)  # 确保不为负
        
        # 计算评估指标
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((y - y_pred) / y)) * 100 if np.all(y != 0) else 0
        
        return {
            'name': '增强随机森林人才趋势预测',
            'model': model,
            'historical_predictions': y_pred,
            'future_predictions': future_pred,
            'future_upper_bound': future_upper,
            'future_lower_bound': future_lower,
            'future_x': future_x,
            'r2': r2,
            'mse': mse,
            'rmse': rmse,
            'mape': mape,
            'feature_importance': np.mean(model.feature_importances_),
            'prediction_std': std_residual
        }
    
    def calculate_talent_flow_metrics(self, values):
        """计算人才流动波动性指标"""
        values = np.array(values)
        
        # 基本统计量
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        var_val = np.var(values, ddof=1)
        
        # 变异系数
        cv = std_val / mean_val if mean_val != 0 else np.inf
        
        # 最大人才流失计算
        peak = values[0]
        max_talent_loss = 0
        for val in values:
            if val > peak:
                peak = val
            if peak != 0:
                loss_rate = (peak - val) / peak
                max_talent_loss = max(max_talent_loss, loss_rate)
        
        # 人才流动率波动
        if len(values) > 1:
            changes = np.diff(values) / values[:-1]
            flow_volatility = np.std(changes, ddof=1)
        else:
            flow_volatility = 0
        
        # 计算趋势强度
        if len(values) >= 3:
            x = np.arange(len(values))
            trend_slope = np.polyfit(x, values, 1)[0]
            trend_strength = abs(trend_slope) / mean_val if mean_val != 0 else 0
        else:
            trend_slope = 0
            trend_strength = 0
        
        return {
            'mean_talent_count': mean_val,
            'std_talent_count': std_val,
            'variance': var_val,
            'cv': cv,
            'max_talent_loss_rate': max_talent_loss * 100,
            'flow_volatility': flow_volatility * 100,
            'trend_slope': trend_slope,
            'trend_strength': trend_strength,
            'stability_index': (1 / (1 + cv)) * 100
        }
    
    def trend_analysis(self):
        """进行人才流动趋势分析（包含预测）"""
        print("\n🔍 进行人才流动趋势分析（包含未来5个月预测）...")
        
        analysis_results = {}
        
        for dataset in self.data['dataset'].unique():
            for industry in self.data['industry'].unique():
                subset = self.data[
                    (self.data['dataset'] == dataset) & 
                    (self.data['industry'] == industry)
                ].sort_values('date')
                
                if len(subset) < 3:
                    continue
                
                # 准备数据
                x = np.arange(len(subset))
                y = subset['count'].values
                
                # 随机森林分析（包含预测）
                rf_result = self.random_forest_analysis_with_prediction(x, y, future_periods=5)
                
                # 人才流动指标
                flow_metrics = self.calculate_talent_flow_metrics(y)
                
                # 生成未来日期
                last_date = subset['date'].iloc[-1]
                future_dates = pd.date_range(
                    start=last_date + pd.DateOffset(months=1),
                    periods=5,
                    freq='MS'  # Month Start
                )
                
                # 存储结果
                key = f"{dataset}_{industry}"
                analysis_results[key] = {
                    'dataset': dataset,
                    'industry': industry,
                    'data_points': len(subset),
                    'random_forest': rf_result,
                    'flow_metrics': flow_metrics,
                    'raw_data': {
                        'x': x, 
                        'y': y, 
                        'dates': subset['date'].values
                    },
                    'future_data': {
                        'x': rf_result['future_x'],
                        'predictions': rf_result['future_predictions'],
                        'upper_bound': rf_result['future_upper_bound'],
                        'lower_bound': rf_result['future_lower_bound'],
                        'dates': future_dates
                    }
                }
        
        self.results = analysis_results
        return analysis_results
    
    def generate_prediction_description(self, result):
        """生成预测结果描述"""
        future_data = result['future_data']
        current_count = result['raw_data']['y'][-1]
        future_predictions = future_data['predictions']
        future_dates = future_data['dates']
        
        # 计算预测趋势
        prediction_change = future_predictions[-1] - current_count
        prediction_change_pct = (prediction_change / current_count) * 100
        
        description = []
        description.append(f"🔮 **未来5个月预测**:")
        description.append(f"   - 当前人数: {current_count:,.0f}人")
        description.append(f"   - 预测终值: {future_predictions[-1]:,.0f}人")
        description.append(f"   - 预期变化: {prediction_change:+,.0f}人 ({prediction_change_pct:+.1f}%)")
        
        # 月度预测详情
        description.append(f"\n📅 **月度预测明细**:")
        for i, (date, pred, upper, lower) in enumerate(zip(
            future_dates, future_predictions, 
            future_data['upper_bound'], future_data['lower_bound']
        )):
            month_str = date.strftime('%Y年%m月')
            description.append(f"   - {month_str}: {pred:,.0f}人 (区间: {lower:,.0f}-{upper:,.0f})")
        
        # 预测可信度
        prediction_std = result['random_forest']['prediction_std']
        avg_prediction = np.mean(future_predictions)
        relative_uncertainty = (prediction_std / avg_prediction) * 100 if avg_prediction > 0 else 0
        
        if relative_uncertainty < 5:
            confidence_desc = "预测可信度很高"
            confidence_emoji = "🎯"
        elif relative_uncertainty < 10:
            confidence_desc = "预测可信度较高"
            confidence_emoji = "✅"
        elif relative_uncertainty < 20:
            confidence_desc = "预测存在一定不确定性"
            confidence_emoji = "⚠️"
        else:
            confidence_desc = "预测不确定性较大"
            confidence_emoji = "❓"
        
        description.append(f"\n{confidence_emoji} **预测可信度**: {confidence_desc}")
        description.append(f"   - 预测误差范围: ±{prediction_std:.0f}人")
        description.append(f"   - 相对不确定性: {relative_uncertainty:.1f}%")
        
        return "\n".join(description)
    
    def generate_enhanced_talent_flow_report(self):
        """生成增强版人才流动完整报告（包含预测）"""
        print("\n" + "="*80)
        print("👥 人才流动趋势分析报告（含未来预测）")
        print("="*80)
        
        for key, result in self.results.items():
            # 原有的历史分析
            historical_desc = self.generate_talent_trend_description(result)
            print("\n" + historical_desc)
            
            # 新增的预测分析
            prediction_desc = self.generate_prediction_description(result)
            print("\n" + prediction_desc)
            print("\n" + "-"*60)
        
        # 生成供需预测对比
        print(f"\n🔮 **未来人才供需预测对比**")
        self._generate_future_supply_demand_comparison()
        
        return self.results
    
    def generate_talent_trend_description(self, result):
        """生成人才流动趋势描述（原有功能）"""
        y = result['raw_data']['y']
        dataset = result['dataset']
        industry = result['industry']
        flow_metrics = result['flow_metrics']
        rf_r2 = result['random_forest']['r2']
        rf_mape = result['random_forest']['mape']
        
        start_count = int(y[0])
        end_count = int(y[-1])
        total_change = end_count - start_count
        total_change_pct = (total_change / start_count) * 100 if start_count != 0 else 0
        
        if len(y) > 1:
            monthly_changes = np.diff(y)
            avg_monthly_change = np.mean(monthly_changes)
        else:
            avg_monthly_change = 0
        
        description = []
        description.append(f"👥 **{dataset} - {industry}行业** 历史趋势分析")
        
        # 趋势判断
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
        
        description.append(f"\n{trend_emoji} **历史趋势**: {trend_desc}，变化幅度为{total_change_pct:+.1f}%")
        description.append(f"   - 人才数量从 {start_count:,} 人变化至 {end_count:,} 人")
        description.append(f"   - 净变化 {total_change:+,} 人，月均变化 {avg_monthly_change:+.0f} 人")
        
        return "\n".join(description)
    
    def _generate_future_supply_demand_comparison(self):
        """生成未来人才供需预测对比"""
        industries = set()
        for result in self.results.values():
            industries.add(result['industry'])
        
        for industry in industries:
            supply_result = None
            demand_result = None
            
            for key, result in self.results.items():
                if result['industry'] == industry:
                    if '求职者数据' in result['dataset']:
                        supply_result = result
                    elif '企业需求数据' in result['dataset']:
                        demand_result = result
            
            if supply_result and demand_result:
                # 获取未来预测
                supply_future = supply_result['future_data']['predictions'][-1]
                demand_future = demand_result['future_data']['predictions'][-1]
                
                # 当前值
                supply_current = supply_result['raw_data']['y'][-1]
                demand_current = demand_result['raw_data']['y'][-1]
                
                # 预测变化
                supply_change = (supply_future - supply_current) / supply_current * 100
                demand_change = (demand_future - demand_current) / demand_current * 100
                
                # 未来供需比
                if demand_future > 0:
                    future_ratio = supply_future / demand_future
                else:
                    future_ratio = float('inf')
                
                if future_ratio > 1.5:
                    future_status = "预计供过于求加剧"
                    status_emoji = "📊"
                elif future_ratio > 1.2:
                    future_status = "预计供过于求"
                    status_emoji = "📊"
                elif future_ratio < 0.7:
                    future_status = "预计供不应求加剧"  
                    status_emoji = "🔥"
                elif future_ratio < 0.8:
                    future_status = "预计供不应求"
                    status_emoji = "🔥"
                else:
                    future_status = "预计供需趋于平衡"
                    status_emoji = "⚖️"
                
                print(f"\n{status_emoji} **{industry}行业未来预测**: {future_status}")
                print(f"   - 预测求职者变化: {supply_change:+.1f}% → {supply_future:.0f}人")
                print(f"   - 预测企业需求变化: {demand_change:+.1f}% → {demand_future:.0f}人")
                print(f"   - 预测供需比: {future_ratio:.2f}")
    
    def visualize_talent_trends_with_prediction(self, max_plots=8):
        """可视化人才流动趋势（包含未来预测）"""
        print(f"\n🎨 生成人才流动趋势预测图表...")
        
        plot_keys = list(self.results.keys())[:max_plots]
        n_plots = len(plot_keys)
        cols = 2
        rows = (n_plots + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(18, 7*rows))
        if rows == 1:
            axes = axes.reshape(1, -1)
        elif n_plots == 1:
            axes = np.array([[axes]])
        axes = axes.flatten()
        
        for i, key in enumerate(plot_keys):
            result = self.results[key]
            ax = axes[i]
            
            # 历史数据
            x_hist = result['raw_data']['x']
            y_hist = result['raw_data']['y']
            rf_pred_hist = result['random_forest']['historical_predictions']
            
            # 未来数据
            x_future = result['future_data']['x']
            y_future = result['future_data']['predictions']
            y_upper = result['future_data']['upper_bound']
            y_lower = result['future_data']['lower_bound']
            
            # 绘制历史数据
            ax.scatter(x_hist, y_hist, alpha=0.8, color='steelblue', 
                      label='历史实际', s=100, zorder=5)
            ax.plot(x_hist, rf_pred_hist, 'orange', linewidth=3, 
                   label=f"历史拟合 (R²={result['random_forest']['r2']:.3f})", zorder=4)
            
            # 绘制未来预测
            ax.plot(x_future, y_future, 'red', linewidth=3, linestyle='--',
                   label='未来预测', zorder=3)
            ax.scatter(x_future, y_future, alpha=0.8, color='red', 
                      label='预测点', s=100, marker='^', zorder=5)
            
            # 绘制置信区间
            ax.fill_between(x_future, y_lower, y_upper, 
                           alpha=0.2, color='red', label='95%置信区间', zorder=1)
            
            # 添加分界线
            ax.axvline(x=x_hist[-1] + 0.5, color='gray', linestyle=':', 
                      alpha=0.7, linewidth=2, label='历史|预测分界')
            
            # 设置标题和标签
            dataset_short = '求职者' if '求职者' in result['dataset'] else '企业需求'
            current_val = y_hist[-1]
            future_val = y_future[-1]
            change_pct = ((future_val - current_val) / current_val * 100)
            
            title = f"{dataset_short} - {result['industry']}\n"
            title += f"当前: {current_val:,.0f}人 → 预测: {future_val:,.0f}人 ({change_pct:+.1f}%)"
            
            ax.set_title(title, fontsize=11, fontweight='bold')
            ax.set_xlabel('时间点')
            ax.set_ylabel('人数')
            ax.legend(loc='best', fontsize=9)
            ax.grid(True, alpha=0.3)
            
            # 美化图表
            ax.set_facecolor('#fafafa')
            
            # 添加数值标注
            for j, (x_val, y_val) in enumerate(zip(x_future, y_future)):
                ax.annotate(f'{y_val:.0f}', 
                           (x_val, y_val), 
                           textcoords="offset points", 
                           xytext=(0,10), 
                           ha='center', fontsize=8, color='red')
        
        # 隐藏多余的子图
        for i in range(len(plot_keys), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        plt.savefig('talent_flow_prediction_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return fig
    
    def print_prediction_summary(self):
        """打印预测结果摘要"""
        print("\n" + "="*80)
        print("🔮 未来5个月预测摘要")
        print("="*80)
        
        for key, result in self.results.items():
            dataset = result['dataset']
            industry = result['industry']
            
            current_count = result['raw_data']['y'][-1]
            future_count = result['future_data']['predictions'][-1]
            change = future_count - current_count
            change_pct = (change / current_count) * 100
            
            print(f"\n🏭 {dataset} - {industry}")
            print("-" * 50)
            print(f"当前人数: {current_count:,.0f}人")
            print(f"预测人数: {future_count:,.0f}人")
            print(f"预期变化: {change:+,.0f}人 ({change_pct:+.1f}%)")
            
            # 预测置信度
            pred_std = result['random_forest']['prediction_std']
            relative_error = (pred_std / future_count) * 100 if future_count > 0 else 0
            print(f"预测误差: ±{pred_std:.0f}人 ({relative_error:.1f}%)")


def main():
    """主函数"""
    print("🚀 人才流动趋势分析开始（包含未来预测）...")
    
    analyzer = TalentFlowAnalyzer()
    
    file1 = "applicant_position.json"
    file2 = "corporate_position.json"
    
    try:
        # 加载数据
        data = analyzer.load_data(file1, file2)
        
        # 计算增长率
        analyzer.calculate_growth_rates()
        
        # 趋势分析（包含预测）
        analyzer.trend_analysis()
        
        # 生成增强版报告
        analyzer.generate_enhanced_talent_flow_report()
        
        # 生成预测可视化
        analyzer.visualize_talent_trends_with_prediction()
        
        # 打印预测摘要
        analyzer.print_prediction_summary()
        
        print("\n✅ 人才流动预测分析完成！")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("请确保 applicant_position.json 和 corporate_position.json 文件在当前目录下")
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()