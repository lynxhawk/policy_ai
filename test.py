#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版人才流动趋势分析模型
包含多种拟合方法的实现
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import curve_fit
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
import warnings
warnings.filterwarnings('ignore')

class EnhancedTrendAnalysis:
    """增强版趋势分析类"""
    
    def __init__(self):
        self.models = {}
        self.results = {}
    
    def linear_trend(self, x, y):
        """线性趋势拟合"""
        model = LinearRegression()
        X = x.reshape(-1, 1)
        model.fit(X, y)
        
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return {
            'name': '线性回归',
            'params': {'slope': model.coef_[0], 'intercept': model.intercept_},
            'predictions': y_pred,
            'r2': r2,
            'mse': mse,
            'aic': len(y) * np.log(mse) + 2 * 2  # 2个参数
        }
    
    def polynomial_trend(self, x, y, degree=2):
        """多项式趋势拟合"""
        poly_model = Pipeline([
            ('poly', PolynomialFeatures(degree=degree)),
            ('linear', LinearRegression())
        ])
        
        X = x.reshape(-1, 1)
        poly_model.fit(X, y)
        
        y_pred = poly_model.predict(X)
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return {
            'name': f'{degree}次多项式',
            'model': poly_model,
            'predictions': y_pred,
            'r2': r2,
            'mse': mse,
            'aic': len(y) * np.log(mse) + 2 * (degree + 1)
        }
    
    def exponential_trend(self, x, y):
        """指数趋势拟合"""
        def exp_func(x, a, b):
            return a * np.exp(b * x)
        
        try:
            # 确保y值为正
            y_pos = np.maximum(y, 0.001)
            
            # 初始参数估计
            p0 = [y_pos[0], 0.01]
            
            popt, pcov = curve_fit(exp_func, x, y_pos, p0=p0, maxfev=1000)
            y_pred = exp_func(x, *popt)
            
            r2 = r2_score(y, y_pred)
            mse = mean_squared_error(y, y_pred)
            
            return {
                'name': '指数函数',
                'params': {'a': popt[0], 'b': popt[1]},
                'predictions': y_pred,
                'r2': r2,
                'mse': mse,
                'aic': len(y) * np.log(mse) + 2 * 2
            }
        except:
            return self.linear_trend(x, y)  # 拟合失败时回退到线性
    
    def logarithmic_trend(self, x, y):
        """对数趋势拟合"""
        def log_func(x, a, b):
            return a * np.log(x + 1) + b  # +1避免log(0)
        
        try:
            popt, pcov = curve_fit(log_func, x, y, maxfev=1000)
            y_pred = log_func(x, *popt)
            
            r2 = r2_score(y, y_pred)
            mse = mean_squared_error(y, y_pred)
            
            return {
                'name': '对数函数',
                'params': {'a': popt[0], 'b': popt[1]},
                'predictions': y_pred,
                'r2': r2,
                'mse': mse,
                'aic': len(y) * np.log(mse) + 2 * 2
            }
        except:
            return self.linear_trend(x, y)
    
    def power_trend(self, x, y):
        """幂函数趋势拟合"""
        def power_func(x, a, b):
            return a * np.power(x + 1, b)  # +1避免0^b的问题
        
        try:
            y_pos = np.maximum(y, 0.001)
            p0 = [y_pos[0], 0.5]
            
            popt, pcov = curve_fit(power_func, x, y_pos, p0=p0, maxfev=1000)
            y_pred = power_func(x, *popt)
            
            r2 = r2_score(y, y_pred)
            mse = mean_squared_error(y, y_pred)
            
            return {
                'name': '幂函数',
                'params': {'a': popt[0], 'b': popt[1]},
                'predictions': y_pred,
                'r2': r2,
                'mse': mse,
                'aic': len(y) * np.log(mse) + 2 * 2
            }
        except:
            return self.linear_trend(x, y)
    
    def sinusoidal_trend(self, x, y):
        """正弦波趋势拟合（适合周期性数据）"""
        def sin_func(x, A, omega, phi, offset):
            return A * np.sin(omega * x + phi) + offset
        
        try:
            # 初始参数估计
            A_init = (np.max(y) - np.min(y)) / 2
            offset_init = np.mean(y)
            omega_init = 2 * np.pi / (len(x) / 2)  # 假设半个周期
            phi_init = 0
            
            p0 = [A_init, omega_init, phi_init, offset_init]
            
            popt, pcov = curve_fit(sin_func, x, y, p0=p0, maxfev=2000)
            y_pred = sin_func(x, *popt)
            
            r2 = r2_score(y, y_pred)
            mse = mean_squared_error(y, y_pred)
            
            return {
                'name': '正弦函数',
                'params': {'A': popt[0], 'omega': popt[1], 'phi': popt[2], 'offset': popt[3]},
                'predictions': y_pred,
                'r2': r2,
                'mse': mse,
                'aic': len(y) * np.log(mse) + 2 * 4
            }
        except:
            return self.linear_trend(x, y)
    
    def lowess_trend(self, x, y, frac=0.3):
        """LOWESS平滑趋势（需要statsmodels，这里用简化版本）"""
        # 简化的局部加权回归
        y_smooth = np.zeros_like(y)
        window = max(3, int(len(y) * frac))
        
        for i in range(len(y)):
            start = max(0, i - window//2)
            end = min(len(y), i + window//2 + 1)
            
            # 局部线性拟合
            x_local = x[start:end]
            y_local = y[start:end]
            
            if len(x_local) > 1:
                z = np.polyfit(x_local, y_local, 1)
                y_smooth[i] = z[0] * x[i] + z[1]
            else:
                y_smooth[i] = y[i]
        
        r2 = r2_score(y, y_smooth)
        mse = mean_squared_error(y, y_smooth)
        
        return {
            'name': 'LOWESS平滑',
            'predictions': y_smooth,
            'r2': r2,
            'mse': mse,
            'aic': len(y) * np.log(mse) + 2 * window
        }
    
    def random_forest_trend(self, x, y):
        """随机森林趋势拟合"""
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        X = x.reshape(-1, 1)
        
        model.fit(X, y)
        y_pred = model.predict(X)
        
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return {
            'name': '随机森林',
            'model': model,
            'predictions': y_pred,
            'r2': r2,
            'mse': mse,
            'aic': len(y) * np.log(mse) + 2 * 50  # 近似AIC
        }
    
    def svr_trend(self, x, y):
        """支持向量回归趋势拟合"""
        model = SVR(kernel='rbf', C=1.0, gamma='auto')
        X = x.reshape(-1, 1)
        
        model.fit(X, y)
        y_pred = model.predict(X)
        
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return {
            'name': '支持向量回归',
            'model': model,
            'predictions': y_pred,
            'r2': r2,
            'mse': mse,
            'aic': len(y) * np.log(mse) + 2 * len(model.support_)
        }
    
    def comprehensive_trend_analysis(self, x, y, methods='all'):
        """综合趋势分析"""
        x = np.array(x)
        y = np.array(y)
        
        if len(x) != len(y) or len(x) < 3:
            raise ValueError("数据长度不足或x、y长度不匹配")
        
        # 标准化x为0到len-1的序列
        x_norm = np.arange(len(x))
        
        # 可用方法
        all_methods = {
            'linear': self.linear_trend,
            'poly2': lambda x, y: self.polynomial_trend(x, y, 2),
            'poly3': lambda x, y: self.polynomial_trend(x, y, 3),
            'exponential': self.exponential_trend,
            'logarithmic': self.logarithmic_trend,
            'power': self.power_trend,
            'sinusoidal': self.sinusoidal_trend,
            'lowess': self.lowess_trend,
            'random_forest': self.random_forest_trend,
            'svr': self.svr_trend
        }
        
        # 选择要使用的方法
        if methods == 'all':
            selected_methods = all_methods
        elif isinstance(methods, list):
            selected_methods = {k: v for k, v in all_methods.items() if k in methods}
        else:
            raise ValueError("methods参数应为'all'或方法名列表")
        
        results = {}
        
        # 应用各种方法
        for name, method in selected_methods.items():
            try:
                result = method(x_norm, y)
                results[name] = result
                print(f"✓ {result['name']}: R² = {result['r2']:.4f}, MSE = {result['mse']:.2f}")
            except Exception as e:
                print(f"✗ {name}方法失败: {str(e)}")
                continue
        
        # 根据AIC选择最佳模型
        if results:
            best_method = min(results.keys(), key=lambda k: results[k]['aic'])
            results['best_method'] = best_method
            print(f"\n🏆 最佳模型: {results[best_method]['name']} (AIC = {results[best_method]['aic']:.2f})")
        
        return results
    
    def visualize_trend_comparison(self, x, y, results):
        """可视化趋势比较"""
        n_methods = len([k for k in results.keys() if k != 'best_method'])
        
        if n_methods == 0:
            print("没有有效的拟合结果可供可视化")
            return
        
        # 计算图形布局
        cols = 3
        rows = (n_methods + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
        if rows == 1:
            axes = axes.reshape(1, -1)
        elif n_methods == 1:
            axes = np.array([[axes]])
        
        axes = axes.flatten()
        
        x_plot = np.arange(len(x))
        
        plot_idx = 0
        for method_name, result in results.items():
            if method_name == 'best_method':
                continue
                
            ax = axes[plot_idx]
            
            # 绘制原始数据
            ax.scatter(x_plot, y, alpha=0.6, color='blue', label='原始数据')
            
            # 绘制拟合曲线
            ax.plot(x_plot, result['predictions'], 'r-', linewidth=2, label='拟合曲线')
            
            # 标注信息
            ax.set_title(f"{result['name']}\nR² = {result['r2']:.4f}, MSE = {result['mse']:.2f}")
            ax.set_xlabel('时间点')
            ax.set_ylabel('数值')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 高亮最佳方法
            if method_name == results.get('best_method'):
                ax.set_facecolor('#f0f8ff')
                ax.set_title(ax.get_title() + " ⭐最佳", fontweight='bold')
            
            plot_idx += 1
        
        # 隐藏多余的子图
        for i in range(plot_idx, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        plt.show()
        
        return fig

# 测试函数
def test_enhanced_trend_analysis():
    """测试增强版趋势分析"""
    print("🚀 开始增强版趋势分析测试...")
    
    # 创建测试数据
    np.random.seed(42)
    x = np.arange(20)
    
    # 测试不同类型的趋势
    test_cases = {
        '线性上升趋势': 10 + 2*x + np.random.normal(0, 3, len(x)),
        '二次增长趋势': 5 + 0.5*x + 0.1*x**2 + np.random.normal(0, 2, len(x)),
        '指数增长趋势': 10 * np.exp(0.1*x) + np.random.normal(0, 5, len(x)),
        '周期性趋势': 50 + 20*np.sin(0.5*x) + np.random.normal(0, 3, len(x)),
        '复杂非线性趋势': 30 + 5*np.sin(x) + 0.2*x**2 - 0.01*x**3 + np.random.normal(0, 4, len(x))
    }
    
    analyzer = EnhancedTrendAnalysis()
    
    for case_name, y_data in test_cases.items():
        print(f"\n{'='*60}")
        print(f"测试案例: {case_name}")
        print('='*60)
        
        # 进行综合分析
        results = analyzer.comprehensive_trend_analysis(x, y_data)
        
        # 可视化结果
        if results:
            analyzer.visualize_trend_comparison(x, y_data, results)
    
    print("\n✅ 增强版趋势分析测试完成！")

if __name__ == "__main__":
    test_enhanced_trend_analysis()