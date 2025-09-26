import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class PinghuTalentFlowModel:
    def __init__(self):
        self.data = None
        # 国民经济行业分类一级目录
        self.industries = [
            '农、林、牧、渔业', '采矿业', '制造业', '电力、热力、燃气及水生产和供应业',
            '建筑业', '批发和零售业', '交通运输、仓储和邮政业', '住宿和餐饮业',
            '信息传输、软件和信息技术服务业', '金融业', '房地产业', '租赁和商务服务业',
            '科学研究和技术服务业', '水利、环境和公共设施管理业', '居民服务、修理和其他服务业',
            '教育', '卫生和社会工作', '文化、体育和娱乐业', '公共管理、社会保障和社会组织'
        ]
        
        # 二三级工种分类（根据平湖市主要产业特点）
        self.job_types = [
            # 制造业相关
            '机械工程师', '电气工程师', '质量工程师', '工艺工程师', '设备维护工',
            '生产主管', '技术员', '操作工', '检验员', '仓储管理员',
            # 服务业相关
            '销售经理', '销售代表', '客户经理', '市场专员', '采购专员',
            '财务经理', '会计', '出纳', '审计', '税务专员',
            # 管理类
            '人力资源经理', 'HR专员', '行政专员', '办公室主任', '总经理助理',
            # IT相关
            '软件工程师', '网络管理员', '数据分析师', '系统维护员', 'UI设计师',
            # 其他专业
            '法务专员', '企业顾问', '项目经理', '运营专员', '物流专员'
        ]
        
        # 平湖市主要来源地区（户籍地）
        self.origin_areas = [
            '平湖市', '嘉兴市其他', '杭州市', '上海市', '湖州市', '绍兴市',
            '安徽省', '江西省', '河南省', '湖南省', '四川省', '贵州省',
            '云南省', '江苏省', '山东省', '其他地区'
        ]
        
    def generate_sample_data(self, n_records=15000, months=24):
        """生成平湖市人才流动模拟数据"""
        np.random.seed(42)
        
        # 生成时间序列
        start_date = datetime(2023, 1, 1)
        dates = [start_date + timedelta(days=30*i) for i in range(months)]
        
        data_list = []
        
        # 平湖市产业特点权重
        industry_base_weights = np.array([
            2,   # 农、林、牧、渔业
            1,   # 采矿业
            35,  # 制造业（平湖主导产业）
            3,   # 电力、热力、燃气及水生产和供应业
            8,   # 建筑业
            12,  # 批发和零售业
            6,   # 交通运输、仓储和邮政业
            4,   # 住宿和餐饮业
            8,   # 信息传输、软件和信息技术服务业
            3,   # 金融业
            5,   # 房地产业
            6,   # 租赁和商务服务业
            4,   # 科学研究和技术服务业
            2,   # 水利、环境和公共设施管理业
            3,   # 居民服务、修理和其他服务业
            4,   # 教育
            3,   # 卫生和社会工作
            2,   # 文化、体育和娱乐业
            2    # 公共管理、社会保障和社会组织
        ])
        
        for month_idx, date in enumerate(dates):
            # 每月生成一定数量的记录
            month_records = n_records // months + np.random.randint(-100, 100)
            
            for _ in range(month_records):
                # 季节性调整
                seasonal_factor = 1.0
                month = month_idx % 12
                if month in [2, 3, 8, 9]:  # 春季和秋季求职高峰
                    seasonal_factor = 1.3
                elif month in [0, 1, 6, 7]:  # 新年和暑期相对低迷
                    seasonal_factor = 0.8
                
                # 动态调整行业权重
                industry_weights = industry_base_weights.copy().astype(float)
                if month_idx > 12:  # 第二年制造业转型升级
                    industry_weights[2] *= 0.95  # 制造业权重略降
                    industry_weights[8] *= 1.2   # IT服务业权重上升
                
                industry_weights *= seasonal_factor
                industry_weights = industry_weights / industry_weights.sum()
                
                # 户籍地权重（外地务工特点）
                origin_weights = np.array([30, 10, 8, 6, 5, 5, 8, 6, 5, 4, 4, 3, 3, 2, 2, 4])
                origin_weights = origin_weights / origin_weights.sum()
                
                origin_area = np.random.choice(self.origin_areas, p=origin_weights)
                is_local = 1 if origin_area == '平湖市' else 0
                
                # 根据行业选择对应的工种
                selected_industry = np.random.choice(self.industries, p=industry_weights)
                
                # 工种选择逻辑
                if '制造业' in selected_industry:
                    job_pool = self.job_types[0:10]  # 制造业相关工种
                elif selected_industry in ['批发和零售业', '住宿和餐饮业']:
                    job_pool = self.job_types[10:15]  # 服务业相关工种
                elif '信息传输' in selected_industry:
                    job_pool = self.job_types[25:30]  # IT相关工种
                else:
                    job_pool = self.job_types[15:25]  # 管理和其他专业工种
                
                selected_job = np.random.choice(job_pool)
                
                # 薪资水平（根据平湖市实际情况）
                base_salary = 6000
                if '工程师' in selected_job or '经理' in selected_job:
                    base_salary = 8000
                elif '总经理' in selected_job or '项目经理' in selected_job:
                    base_salary = 12000
                elif '操作工' in selected_job or '技术员' in selected_job:
                    base_salary = 5000
                
                salary = np.random.normal(base_salary, base_salary * 0.3)
                salary = max(3000, salary)  # 最低工资保障
                
                record = {
                    'date': date,
                    'industry': selected_industry,
                    'job_type': selected_job,
                    'city': '平湖市',  # 固定为平湖市
                    'origin_area': origin_area,  # 户籍地
                    'is_local': is_local,
                    'action_type': np.random.choice(['招聘', '求职', '入职'], p=[0.4, 0.4, 0.2]),
                    'salary': salary,
                    'person_id': f"PH{np.random.randint(100000, 999999)}",
                    'company_size': np.random.choice(['小型', '中型', '大型'], p=[0.6, 0.3, 0.1]),
                    'education': np.random.choice(['高中及以下', '大专', '本科', '硕士及以上'], p=[0.4, 0.35, 0.2, 0.05])
                }
                data_list.append(record)
        
        self.data = pd.DataFrame(data_list)
        self.data['year_month'] = self.data['date'].dt.to_period('M')
        return self.data
    
    def analyze_industry_trends(self):
        """分析一级行业人数变化趋势"""
        # 按月统计各行业人数
        industry_trends = self.data.groupby(['year_month', 'industry', 'action_type']).size().reset_index(name='count')
        industry_trends_pivot = industry_trends.pivot_table(
            index=['year_month', 'industry'], 
            columns='action_type', 
            values='count', 
            fill_value=0
        ).reset_index()
        
        # 计算趋势指标
        results = {}
        for industry in self.industries:
            industry_data = industry_trends_pivot[industry_trends_pivot['industry'] == industry].copy()
            if industry_data.empty:
                continue
                
            industry_data = industry_data.sort_values('year_month')
            
            # 计算各类型人数变化趋势
            for action_type in ['招聘', '求职', '入职']:
                if action_type in industry_data.columns:
                    values = industry_data[action_type].values
                    if len(values) > 1:
                        # 增长率计算
                        growth_rates = np.diff(values) / (values[:-1] + 1) * 100
                        # 趋势强度（线性回归斜率）
                        x = np.arange(len(values))
                        slope = np.polyfit(x, values, 1)[0]
                        
                        results[f"{industry}_{action_type}"] = {
                            'values': values,
                            'avg_growth_rate': np.mean(growth_rates),
                            'trend_strength': slope,
                            'volatility': np.std(values) / (np.mean(values) + 1),
                            'total_count': np.sum(values)
                        }
        
        return results, industry_trends_pivot
    
    def analyze_job_type_trends(self):
        """分析二三级工种人数变化趋势"""
        job_trends = self.data.groupby(['year_month', 'job_type', 'action_type']).size().reset_index(name='count')
        job_trends_pivot = job_trends.pivot_table(
            index=['year_month', 'job_type'], 
            columns='action_type', 
            values='count', 
            fill_value=0
        ).reset_index()
        
        # 工种与行业关联分析
        job_industry_matrix = self.data.groupby(['job_type', 'industry']).size().unstack(fill_value=0)
        
        # 工种薪资水平分析
        job_salary_stats = self.data.groupby('job_type')['salary'].agg(['mean', 'median', 'std', 'count']).reset_index()
        
        # 工种需求热度分析
        job_demand = self.data[self.data['action_type'] == '招聘'].groupby('job_type').size().reset_index(name='demand_count')
        job_supply = self.data[self.data['action_type'] == '求职'].groupby('job_type').size().reset_index(name='supply_count')
        
        job_market_balance = pd.merge(job_demand, job_supply, on='job_type', how='outer').fillna(0)
        job_market_balance['demand_supply_ratio'] = job_market_balance['demand_count'] / (job_market_balance['supply_count'] + 1)
        
        # 工种相似度分析（基于薪资和需求分布）
        from sklearn.metrics.pairwise import cosine_similarity
        job_features = self.data.groupby('job_type').agg({
            'salary': 'mean',
            'is_local': 'mean',
            'education': lambda x: (x == '本科').sum() / len(x)
        }).fillna(0)
        
        job_similarity = cosine_similarity(job_features)
        job_similarity_df = pd.DataFrame(
            job_similarity, 
            index=job_features.index, 
            columns=job_features.index
        )
        
        return job_trends_pivot, job_industry_matrix, job_salary_stats, job_market_balance, job_similarity_df
    
    def analyze_migration_trends(self):
        """分析外地户籍在平湖市就职人数变化趋势"""
        # 按时间和户籍地统计
        migration_data = self.data.groupby(['year_month', 'origin_area', 'action_type']).size().reset_index(name='count')
        
        # 外地人才流入趋势
        non_local_data = self.data[self.data['is_local'] == 0]
        non_local_trends = non_local_data.groupby(['year_month', 'origin_area']).size().reset_index(name='count')
        
        # 各地区流入平湖的人才数量统计
        origin_stats = self.data.groupby(['origin_area', 'action_type']).size().unstack(fill_value=0).reset_index()
        
        # 外地人才的行业分布
        non_local_industry = non_local_data.groupby(['industry', 'action_type']).size().unstack(fill_value=0).reset_index()
        
        # 外地人才薪资水平对比
        salary_comparison = self.data.groupby(['is_local', 'job_type'])['salary'].mean().unstack().fillna(0)
        
        # 按月统计本地vs外地人才比例
        monthly_ratio = self.data.groupby(['year_month', 'is_local']).size().unstack(fill_value=0).reset_index()
        monthly_ratio['total'] = monthly_ratio[0] + monthly_ratio[1]
        monthly_ratio['non_local_ratio'] = monthly_ratio[0] / monthly_ratio['total']
        monthly_ratio['local_ratio'] = monthly_ratio[1] / monthly_ratio['total']
        
        # 外地人才集中度分析
        non_local_concentration = non_local_data.groupby('origin_area').agg({
            'person_id': 'count',
            'salary': 'mean',
            'education': lambda x: (x.isin(['本科', '硕士及以上'])).sum() / len(x)
        }).reset_index()
        non_local_concentration.columns = ['origin_area', 'talent_count', 'avg_salary', 'high_edu_ratio']
        non_local_concentration = non_local_concentration.sort_values('talent_count', ascending=False)
        
        return migration_data, non_local_trends, origin_stats, non_local_industry, salary_comparison, monthly_ratio, non_local_concentration
    
    def calculate_output_indicators(self):
        """计算所有输出指标"""
        print("🔄 正在分析一级行业人数变化趋势...")
        industry_results, industry_pivot = self.analyze_industry_trends()
        
        print("🔄 正在分析二三级工种人数变化趋势...")
        job_pivot, job_industry_matrix, job_salary_stats, job_market_balance, job_similarity = self.analyze_job_type_trends()
        
        print("🔄 正在分析外地户籍在平湖市就职人数变化趋势...")
        migration_data, non_local_trends, origin_stats, non_local_industry, salary_comparison, monthly_ratio, non_local_concentration = self.analyze_migration_trends()
        
        return {
            'industry_trends': industry_results,
            'industry_data': industry_pivot,
            'job_data': job_pivot,
            'job_industry_matrix': job_industry_matrix,
            'job_salary_stats': job_salary_stats,
            'job_market_balance': job_market_balance,
            'job_similarity': job_similarity,
            'migration_data': migration_data,
            'non_local_trends': non_local_trends,
            'origin_stats': origin_stats,
            'non_local_industry': non_local_industry,
            'salary_comparison': salary_comparison,
            'monthly_ratio': monthly_ratio,
            'non_local_concentration': non_local_concentration
        }
    
    def visualize_results(self, results):
        """可视化分析结果"""
        fig, axes = plt.subplots(4, 2, figsize=(20, 24))
        fig.suptitle('平湖市人才流动模型分析结果', fontsize=18, fontweight='bold')
        
        # 1. 主要行业招聘趋势
        ax1 = axes[0, 0]
        industry_data = results['industry_data']
        main_industries = ['制造业', '批发和零售业', '信息传输、软件和信息技术服务业', '建筑业', '交通运输、仓储和邮政业']
        
        for industry in main_industries:
            data = industry_data[industry_data['industry'] == industry]
            if not data.empty and '招聘' in data.columns:
                ax1.plot(range(len(data)), data['招聘'].values, marker='o', label=industry, linewidth=2)
        
        ax1.set_title('平湖市主要行业招聘人数趋势', fontsize=14, fontweight='bold')
        ax1.set_xlabel('时间（月）')
        ax1.set_ylabel('招聘人数')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. 工种薪资水平对比
        ax2 = axes[0, 1]
        job_salary = results['job_salary_stats'].sort_values('mean', ascending=False).head(10)
        bars = ax2.barh(job_salary['job_type'], job_salary['mean'])
        ax2.set_title('平湖市主要工种平均薪资对比', fontsize=14, fontweight='bold')
        ax2.set_xlabel('平均薪资（元）')
        
        # 添加数值标签
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax2.text(width + 100, bar.get_y() + bar.get_height()/2., 
                    f'{width:.0f}', ha='left', va='center', fontsize=10)
        
        # 3. 外地人才来源地分布
        ax3 = axes[1, 0]
        origin_data = results['non_local_concentration'].head(8)
        wedges, texts, autotexts = ax3.pie(origin_data['talent_count'], 
                                          labels=origin_data['origin_area'], 
                                          autopct='%1.1f%%',
                                          startangle=90)
        ax3.set_title('外地人才来源地分布', fontsize=14, fontweight='bold')
        
        # 4. 本地vs外地人才比例变化
        ax4 = axes[1, 1]
        ratio_data = results['monthly_ratio']
        ax4.plot(range(len(ratio_data)), ratio_data['non_local_ratio'] * 100, 
                marker='s', color='red', label='外地人才比例', linewidth=2)
        ax4.plot(range(len(ratio_data)), ratio_data['local_ratio'] * 100, 
                marker='o', color='blue', label='本地人才比例', linewidth=2)
        ax4.set_title('平湖市本地vs外地人才比例变化趋势', fontsize=14, fontweight='bold')
        ax4.set_xlabel('时间（月）')
        ax4.set_ylabel('比例 (%)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. 工种供需平衡分析
        ax5 = axes[2, 0]
        market_balance = results['job_market_balance'].sort_values('demand_supply_ratio', ascending=False).head(10)
        x = np.arange(len(market_balance))
        width = 0.35
        
        bars1 = ax5.bar(x - width/2, market_balance['demand_count'], width, label='需求量', color='skyblue')
        bars2 = ax5.bar(x + width/2, market_balance['supply_count'], width, label='供给量', color='orange')
        
        ax5.set_title('工种供需平衡分析（Top10）', fontsize=14, fontweight='bold')
        ax5.set_xlabel('工种')
        ax5.set_ylabel('人数')
        ax5.set_xticks(x)
        ax5.set_xticklabels(market_balance['job_type'], rotation=45, ha='right')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. 外地人才行业分布
        ax6 = axes[2, 1]
        non_local_ind = results['non_local_industry'].head(8)
        if '入职' in non_local_ind.columns:
            bars = ax6.bar(range(len(non_local_ind)), non_local_ind['入职'])
            ax6.set_title('外地人才主要就职行业分布', fontsize=14, fontweight='bold')
            ax6.set_xlabel('行业')
            ax6.set_ylabel('入职人数')
            ax6.set_xticks(range(len(non_local_ind)))
            ax6.set_xticklabels(non_local_ind['industry'], rotation=45, ha='right')
            
            # 添加数值标签
            for i, bar in enumerate(bars):
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.0f}', ha='center', va='bottom', fontsize=10)
        
        # 7. 行业增长率热力图
        ax7 = axes[3, 0]
        industry_growth_data = []
        industry_names = []
        
        for key, value in results['industry_trends'].items():
            if '招聘' in key and value['total_count'] > 50:  # 过滤掉样本量太小的行业
                industry_names.append(key.replace('_招聘', ''))
                industry_growth_data.append(value['avg_growth_rate'])
        
        if industry_growth_data:
            colors = ['green' if x >= 0 else 'red' for x in industry_growth_data]
            bars = ax7.barh(industry_names, industry_growth_data, color=colors)
            ax7.set_title('各行业平均增长率', fontsize=14, fontweight='bold')
            ax7.set_xlabel('平均增长率 (%)')
            
            # 添加数值标签
            for i, (bar, growth) in enumerate(zip(bars, industry_growth_data)):
                if growth >= 0:
                    ax7.text(growth + 0.1, i, f'{growth:.1f}%', va='center', ha='left')
                else:
                    ax7.text(growth - 0.1, i, f'{growth:.1f}%', va='center', ha='right')
        
        # 8. 外地人才教育水平对比
        ax8 = axes[3, 1]
        edu_data = self.data.groupby(['is_local', 'education']).size().unstack(fill_value=0)
        edu_data_pct = edu_data.div(edu_data.sum(axis=1), axis=0) * 100
        
        if not edu_data_pct.empty:
            x = np.arange(len(edu_data_pct.columns))
            width = 0.35
            
            if 0 in edu_data_pct.index and 1 in edu_data_pct.index:
                bars1 = ax8.bar(x - width/2, edu_data_pct.loc[0], width, label='外地人才', color='lightcoral')
                bars2 = ax8.bar(x + width/2, edu_data_pct.loc[1], width, label='本地人才', color='lightblue')
                
                ax8.set_title('本地vs外地人才教育水平对比', fontsize=14, fontweight='bold')
                ax8.set_xlabel('教育水平')
                ax8.set_ylabel('比例 (%)')
                ax8.set_xticks(x)
                ax8.set_xticklabels(edu_data_pct.columns, rotation=45, ha='right')
                ax8.legend()
                ax8.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        return fig
    
    def generate_report(self, results):
        """生成平湖市人才流动分析报告"""
        print("=" * 80)
        print("平湖市人才流动模型分析报告")
        print("=" * 80)
        
        # 一级行业趋势分析
        print("\n📊 一级行业人数变化趋势分析")
        print("-" * 50)
        industry_trends = results['industry_trends']
        
        # 筛选出有效数据的行业
        valid_industries = [(k.replace('_招聘', ''), v['avg_growth_rate'], v['total_count']) 
                           for k, v in industry_trends.items() 
                           if '招聘' in k and v['total_count'] > 50]
        valid_industries.sort(key=lambda x: x[1], reverse=True)
        
        print("各行业招聘增长率排名（按总量筛选）：")
        for i, (industry, growth, total) in enumerate(valid_industries[:8], 1):
            trend_desc = "📈 增长" if growth > 0 else "📉 下降"
            print(f"{i:2d}. {industry:<25} {growth:+6.2f}% {trend_desc} (总招聘: {total:4.0f}人)")
        
        # 二三级工种趋势分析
        print("\n🛠️ 二三级工种人数变化趋势分析")
        print("-" * 50)
        
        # 最热门工种
        job_market = results['job_market_balance'].sort_values('demand_count', ascending=False)
        print("最热门工种（招聘需求排名）：")
        for i, row in enumerate(job_market.head(8).itertuples(), 1):
            ratio = row.demand_supply_ratio
            market_status = "🔥 供不应求" if ratio > 1.5 else "⚖️ 供需平衡" if ratio > 0.8 else "📊 供过于求"
            print(f"{i:2d}. {row.job_type:<15} 需求:{row.demand_count:3.0f} 供给:{row.supply_count:3.0f} {market_status}")
        
        # 薪资最高工种
        job_salary = results['job_salary_stats'].sort_values('mean', ascending=False)
        print(f"\n💰 薪资水平最高的工种：")
        for i, row in enumerate(job_salary.head(5).itertuples(), 1):
            print(f"{i:2d}. {row.job_type:<15} 平均薪资: ¥{row.mean:6,.0f}")
        
        # 外地户籍在平湖市就职分析
        print("\n🌍 外地户籍在平湖市就职人数变化趋势")
        print("-" * 50)
        
        non_local_conc = results['non_local_concentration']
        total_non_local = non_local_conc['talent_count'].sum()
        
        print("外地人才来源地统计：")
        print(f"外地人才总数: {total_non_local:,} 人")
        for i, row in enumerate(non_local_conc.head(8).itertuples(), 1):
            percentage = row.talent_count / total_non_local * 100
            print(f"{i:2d}. {row.origin_area:<12} {row.talent_count:4.0f}人 ({percentage:5.1f}%) "
                  f"平均薪资:¥{row.avg_salary:6,.0f} 高学历比例:{row.high_edu_ratio:.1%}")
        
        # 本地vs外地人才对比
        monthly_ratio = results['monthly_ratio']
        latest_ratio = monthly_ratio.iloc[-1]
        print(f"\n📈 最新人才结构：")
        print(f"   外地人才比例: {latest_ratio['non_local_ratio']:.1%}")
        print(f"   本地人才比例: {latest_ratio['local_ratio']:.1%}")
