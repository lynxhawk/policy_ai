#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人才流动数据生成器
生成2023-2025年各行业月度人才数量数据
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
import random
import os

def generate_talent_data():
    """生成人才流动数据"""
    
    # 设置随机种子确保数据可重现
    np.random.seed(12) #42 12
    random.seed(12) #42 12
    
    # 定义基本参数
    years = [2023, 2024, 2025]
    months = list(range(1, 13))
    industries = ['互联网', '电子', '财务', '金融', '贸易', '人力资源', '生物']
    
    # 为每个行业定义基础数据和增长模式
    industry_profiles = {
        '互联网': {
            'base': 15000,
            'growth_rate': -0.1,  # 年增长率8%
            'seasonality': [0.9, 0.85, 1.1, 1.15, 1.2, 1.25, 1.05, 0.95, 1.0, 1.1, 0.9, 0.8],  # 季节性因子
            'volatility': 0.15,
            'trend_type': 'stable'  # 指数增长
        },
        '电子': {
            'base': 12000,
            'growth_rate': 0.09,
            'seasonality': [0.95, 0.9, 1.05, 1.1, 1.15, 1.2, 1.1, 1.05, 1.0, 1.05, 0.95, 0.85],
            'volatility': 0.12,
            'trend_type': 'linear'  # 线性增长
        },
        '财务': {
            'base': 8000,
            'growth_rate': -0.05,
            'seasonality': [1.0, 1.0, 1.1, 1.05, 1.0, 1.0, 0.95, 0.9, 1.0, 1.05, 1.1, 1.15],  # 年末较高
            'volatility': 0.08,
            'trend_type': 'exponential'  # 稳定增长
        },
        '金融': {
            'base': 18000,
            'growth_rate': -0.09,
            'seasonality': [1.0, 0.95, 1.05, 1.0, 1.0, 1.05, 0.95, 0.9, 1.0, 1.05, 1.1, 1.2],
            'volatility': 0.10,
            'trend_type': 'linear'
        },
        '贸易': {
            'base': 10000,
            'growth_rate': -0.04,
            'seasonality': [0.8, 0.75, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.1, 1.0, 0.9, 0.85],  # 春节后低，下半年高
            'volatility': 0.20,
            'trend_type': 'cyclical'  # 周期性
        },
        '人力资源': {
            'base': 5000,
            'growth_rate': -0.05,
            'seasonality': [0.9, 0.85, 1.2, 1.15, 1.1, 1.25, 1.05, 0.95, 1.0, 1.05, 0.95, 0.9],  # 招聘旺季较高
            'volatility': 0.18,
            'trend_type': 'seasonal'  # 季节性明显
        },
        '生物': {
            'base': 6000,
            'growth_rate': 0.12,  # 新兴行业，高增长
            'seasonality': [1.0, 0.95, 1.05, 1.1, 1.15, 1.2, 1.1, 1.05, 1.0, 1.05, 0.95, 0.9],
            'volatility': 0.25,
            'trend_type': 'exponential'  # 指数增长
        }
    }
    
    print("🚀 开始生成人才流动数据...")
    print(f"📅 年份范围: {years}")
    print(f"📊 行业数量: {len(industries)}")
    print(f"🔢 预计生成记录数: {len(years) * len(months) * len(industries)}")
    
    # 生成数据
    data_list = []
    
    for year in years:
        for month in months:
            for industry in industries:
                profile = industry_profiles[industry]
                
                # 计算时间因子（从2023年1月开始的月数）
                time_factor = (year - 2023) * 12 + (month - 1)
                
                # 根据趋势类型计算增长因子
                if profile['trend_type'] == 'exponential':
                    # 指数增长
                    growth_factor = (1 + profile['growth_rate']) ** (time_factor / 12)
                elif profile['trend_type'] == 'linear':
                    # 线性增长
                    growth_factor = 1 + profile['growth_rate'] * (time_factor / 12)
                elif profile['trend_type'] == 'cyclical':
                    # 周期性变化
                    cycle_factor = 1 + 0.1 * np.sin(2 * np.pi * time_factor / 12)
                    growth_factor = (1 + profile['growth_rate'] * 0.5) ** (time_factor / 12) * cycle_factor
                elif profile['trend_type'] == 'seasonal':
                    # 主要受季节影响
                    growth_factor = 1 + profile['growth_rate'] * 0.3 * (time_factor / 12)
                else:  # stable
                    # 稳定增长
                    growth_factor = 1 + profile['growth_rate'] * 0.8 * (time_factor / 12)
                
                # 季节性因子
                seasonal_factor = profile['seasonality'][month - 1]
                
                # 随机波动
                random_factor = 1 + np.random.normal(0, profile['volatility'])
                
                # 添加一些特殊事件影响
                event_factor = 1.0
                # 2024年春节影响
                if year == 2024 and month == 2:
                    event_factor = 0.7  # 春节期间人数下降
                # 2024年毕业季
                if year == 2024 and month in [6, 7]:
                    event_factor = 1.3  # 毕业季人数增加
                # 2025年政策影响（假设）
                if year == 2025 and industry in ['生物', '互联网']:
                    event_factor = 1.2  # 政策扶持
                
                # 计算最终人数
                base_count = profile['base']
                final_count = int(base_count * growth_factor * seasonal_factor * random_factor * event_factor)
                
                # 确保数值合理（不为负，不超过合理上限）
                final_count = max(final_count, int(base_count * 0.2))
                final_count = min(final_count, int(base_count * 3.0))
                
                # 添加到数据列表
                data_record = {
                    "year": year,
                    "month": month,
                    "industry": industry,
                    "count": final_count,
                }
                
                data_list.append(data_record)
    
    # 创建完整的JSON数据结构
    json_data = {
        "data": data_list
    }
    
    # 保存为JSON文件
    output_filename = "talent_flow_data.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存为CSV文件（便于Excel打开）
    df = pd.DataFrame(data_list)
    csv_filename = "talent_flow_data.csv"
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    
    # 生成统计报告
    print("\n" + "="*60)
    print("📊 数据生成完成！统计信息：")
    print("="*60)
    print(f"✅ 总记录数: {len(data_list)}")
    print(f"📁 JSON文件: {output_filename}")
    print(f"📁 CSV文件: {csv_filename}")
    print(f"🏭 行业数量: {len(industries)}")
    print(f"📅 时间跨度: {len(years)}年 × {len(months)}月")
    
    # 按行业统计
    industry_stats = df.groupby('industry')['count'].agg(['mean', 'min', 'max', 'std']).round(0)
    print("\n🏭 各行业统计信息:")
    print(industry_stats)
    
    # 按年份统计
    yearly_stats = df.groupby('year')['count'].agg(['mean', 'sum']).round(0)
    print("\n📅 各年份统计信息:")
    print(yearly_stats)
    
    # 显示部分数据样例
    print("\n📋 数据样例（前10条）:")
    for i, record in enumerate(data_list[:10]):
        print(f"{i+1:2d}. {record['year']}-{record['month']:02d} {record['industry']:6s} {record['count']:6d}人")
    
    return json_data, df

def analyze_data_trends(df):
    """快速分析数据趋势"""
    print("\n" + "="*60)
    print("📈 趋势分析预览")
    print("="*60)
    
    # 各行业总体趋势
    for industry in df['industry'].unique():
        industry_data = df[df['industry'] == industry].sort_values(['year', 'month'])
        start_val = industry_data['count'].iloc[0]
        end_val = industry_data['count'].iloc[-1]
        change_pct = (end_val - start_val) / start_val * 100
        
        trend_desc = "📈 增长" if change_pct > 5 else "📉 下降" if change_pct < -5 else "📊 稳定"
        print(f"{industry:8s}: {start_val:5d} → {end_val:5d} ({change_pct:+5.1f}%) {trend_desc}")

if __name__ == "__main__":
    # 生成数据
    json_output, df = generate_talent_data()
    
    # 分析趋势
    analyze_data_trends(df)
    
    print(f"\n🎉 数据生成完成！文件已保存到当前目录。")
    print("📝 您可以使用生成的 talent_flow_data.json 或 talent_flow_data.csv 文件进行趋势分析。")