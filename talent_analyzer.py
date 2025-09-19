#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人才流动分析核心算法模块
talent_analyzer.py
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import warnings
warnings.filterwarnings('ignore')


def safe_convert_numpy(value):
    """安全转换numpy类型为Python原生类型"""
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    elif isinstance(value, (np.bool_, bool)):
        return bool(value)
    else:
        return value


class AnalysisResult:
    """分析结果数据类"""

    def __init__(self, data_type: str, industry: Optional[str] = None, **kwargs):
        self.data_type = data_type
        self.industry = industry
        self.total_records = kwargs.get('total_records', 0)
        self.mean_count = kwargs.get('mean_count', 0.0)
        self.stability_index = kwargs.get('stability_index', 0.0)
        self.trend_strength = kwargs.get('trend_strength', 0.0)
        self.volatility = kwargs.get('volatility', 0.0)
        self.avg_mom_growth = kwargs.get('avg_mom_growth', 0.0)
        self.avg_yoy_growth = kwargs.get('avg_yoy_growth', 0.0)
        self.latest_mom_growth = kwargs.get('latest_mom_growth', 0.0)
        self.latest_yoy_growth = kwargs.get('latest_yoy_growth', 0.0)
        self.max_count = kwargs.get('max_count', 0.0)
        self.min_count = kwargs.get('min_count', 0.0)
        self.total_change_pct = kwargs.get('total_change_pct', 0.0)
        self.trend_rating = kwargs.get('trend_rating', '未知')
        self.stability_rating = kwargs.get('stability_rating', '未知')

    def to_dict(self):
        """转换为字典"""
        result = {
            'data_type': self.data_type,
            'total_records': safe_convert_numpy(self.total_records),
            'mean_count': safe_convert_numpy(self.mean_count),
            'stability_index': safe_convert_numpy(self.stability_index),
            'trend_strength': safe_convert_numpy(self.trend_strength),
            'volatility': safe_convert_numpy(self.volatility),
            'avg_mom_growth': safe_convert_numpy(self.avg_mom_growth),
            'avg_yoy_growth': safe_convert_numpy(self.avg_yoy_growth),
            'latest_mom_growth': safe_convert_numpy(self.latest_mom_growth),
            'latest_yoy_growth': safe_convert_numpy(self.latest_yoy_growth),
            'max_count': safe_convert_numpy(self.max_count),
            'min_count': safe_convert_numpy(self.min_count),
            'total_change_pct': safe_convert_numpy(self.total_change_pct),
            'trend_rating': self.trend_rating,
            'stability_rating': self.stability_rating
        }

        # 只有当 industry 不为 None 时才添加到结果中
        if self.industry is not None:
            result['industry'] = self.industry

        return result


class TalentDataAnalyzer:
    """人才流动数据分析器核心类"""

    def __init__(self):
        pass

    def validate_data_record(self, record: dict) -> dict:
        """验证单条数据记录"""
        errors = []

        if 'year' not in record:
            errors.append("缺少year字段")
        elif not isinstance(record['year'], int) or record['year'] < 2000 or record['year'] > 2030:
            errors.append("year字段必须是2000-2030之间的整数")

        if 'month' not in record:
            errors.append("缺少month字段")
        elif not isinstance(record['month'], int) or record['month'] < 1 or record['month'] > 12:
            errors.append("month字段必须是1-12之间的整数")

        if 'count' not in record:
            errors.append("缺少count字段")
        elif not isinstance(record['count'], int) or record['count'] < 0:
            errors.append("count字段必须是非负整数")

        if errors:
            raise ValueError(f"数据验证失败: {'; '.join(errors)}")

        return record

    def validate_industry_data(self, data: list) -> list:
        """验证行业数据"""
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("数据必须是非空列表")

        validated_data = []
        for i, record in enumerate(data):
            if not isinstance(record, dict):
                raise ValueError(f"第{i+1}条记录必须是字典格式")

            if 'industry' not in record:
                raise ValueError(f"第{i+1}条记录缺少industry字段")
            if not isinstance(record['industry'], str) or len(record['industry'].strip()) == 0:
                raise ValueError(f"第{i+1}条记录的industry字段必须是非空字符串")

            validated_record = self.validate_data_record(record)
            validated_data.append(validated_record)

        return validated_data

    def validate_nonlocal_data(self, data: list) -> list:
        """验证外地户籍数据"""
        if not isinstance(data, list) or len(data) < 2:
            raise ValueError("外地户籍分析至少需要2条数据记录")

        validated_data = []
        for i, record in enumerate(data):
            if not isinstance(record, dict):
                raise ValueError(f"第{i+1}条记录必须是字典格式")

            validated_record = self.validate_data_record(record)
            validated_data.append(validated_record)

        return validated_data

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理

        Args:
            df (pd.DataFrame): 原始数据框

        Returns:
            pd.DataFrame: 预处理后的数据框
        """
        df = df.copy()

        # 处理日期字段
        if 'year' in df.columns and 'month' in df.columns:
            df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        # 按日期排序
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)

        return df

    def calculate_growth_rates(self, data: pd.DataFrame, value_column: str = 'count') -> pd.DataFrame:
        """
        计算环比和同比增长率

        Args:
            data (pd.DataFrame): 输入数据
            value_column (str): 数值列名，默认为'count'

        Returns:
            pd.DataFrame: 包含增长率的数据框
        """
        data = data.copy().sort_values('date')

        # 环比增长率 (月度对比)
        data['mom_growth'] = data[value_column].pct_change() * 100

        # 同比增长率 (12个月前对比)
        data['yoy_growth'] = data[value_column].pct_change(periods=12) * 100

        return data

    def calculate_stability_metrics(self, values: Union[List, np.ndarray]) -> Dict:
        """
        计算稳定性指标和趋势强度

        Args:
            values: 数值序列

        Returns:
            Dict: 包含稳定性指标的字典
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
        std_val = np.std(values, ddof=1) if len(values) > 1 else 0

        # 变异系数 (Coefficient of Variation)
        cv = std_val / mean_val if mean_val != 0 else np.inf

        # 稳定性指数 (0-100分，值越大越稳定)
        stability_index = (1 / (1 + cv)) * 100 if cv != np.inf else 0

        # 趋势强度 (基于线性回归斜率)
        trend_strength = 0
        if len(values) >= 3:
            x = np.arange(len(values))
            try:
                trend_slope = np.polyfit(x, values, 1)[0]
                trend_strength = abs(trend_slope) / \
                    mean_val if mean_val != 0 else 0
            except:
                trend_strength = 0

        # 波动率 (基于相对变化)
        volatility = 0
        if len(values) > 1:
            changes = np.diff(values) / (values[:-1] + 1e-10)  # 避免除零
            volatility = np.std(changes, ddof=1) * \
                100 if len(changes) > 0 else 0

        return {
            'stability_index': stability_index,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'mean_value': mean_val
        }

    def get_trend_rating(self, trend_strength: float) -> str:
        """获取趋势评级"""
        if trend_strength > 0.05:
            return "强趋势"
        elif trend_strength > 0.02:
            return "中等趋势"
        else:
            return "弱趋势"

    def get_stability_rating(self, stability_index: float) -> str:
        """获取稳定性评级"""
        if stability_index > 80:
            return "高稳定"
        elif stability_index > 60:
            return "中等稳定"
        else:
            return "不稳定"

    def analyze_industry_data(self, data: pd.DataFrame, data_type: str, value_column: str = 'count') -> List[AnalysisResult]:
        """
        按行业分析数据

        Args:
            data (pd.DataFrame): 输入数据
            data_type (str): 数据类型描述
            value_column (str): 数值列名

        Returns:
            List[AnalysisResult]: 分析结果列表
        """
        results = []

        if 'industry' not in data.columns:
            raise ValueError(f"数据中缺少'industry'列")

        if value_column not in data.columns:
            raise ValueError(f"数据中缺少'{value_column}'列")

        # 按行业分组计算增长率
        data_with_growth = data.groupby('industry').apply(
            lambda x: self.calculate_growth_rates(x, value_column)
        ).reset_index(drop=True)

        # 按行业统计分析
        for industry in data['industry'].unique():
            industry_data = data_with_growth[data_with_growth['industry'] == industry].copy(
            )

            if len(industry_data) < 2:
                continue

            values = industry_data[value_column].values
            stability_metrics = self.calculate_stability_metrics(values)

            # 计算增长率统计
            mom_growth = industry_data['mom_growth'].dropna()
            yoy_growth = industry_data['yoy_growth'].dropna()

            # 创建分析结果
            result = AnalysisResult(
                data_type=data_type,
                industry=industry,
                total_records=len(industry_data),
                mean_count=stability_metrics['mean_value'],
                stability_index=stability_metrics['stability_index'],
                trend_strength=stability_metrics['trend_strength'],
                volatility=stability_metrics['volatility'],
                avg_mom_growth=mom_growth.mean() if len(mom_growth) > 0 else 0,
                avg_yoy_growth=yoy_growth.mean() if len(yoy_growth) > 0 else 0,
                latest_mom_growth=mom_growth.iloc[-1] if len(
                    mom_growth) > 0 else 0,
                latest_yoy_growth=yoy_growth.iloc[-1] if len(
                    yoy_growth) > 0 else 0,
                max_count=values.max(),
                min_count=values.min(),
                total_change_pct=(
                    (values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
                trend_rating=self.get_trend_rating(
                    stability_metrics['trend_strength']),
                stability_rating=self.get_stability_rating(
                    stability_metrics['stability_index'])
            )
            results.append(result)

        return results

    def analyze_nonlocal_data(self, data: pd.DataFrame, value_column: str = 'count') -> Optional[AnalysisResult]:
        """
        分析外地户籍数据

        Args:
            data (pd.DataFrame): 输入数据
            value_column (str): 数值列名

        Returns:
            Optional[AnalysisResult]: 分析结果或None
        """
        if len(data) < 2:
            return None

        if value_column not in data.columns:
            raise ValueError(f"数据中缺少'{value_column}'列")

        # 计算增长率
        data_with_growth = self.calculate_growth_rates(data, value_column)

        values = data_with_growth[value_column].values
        stability_metrics = self.calculate_stability_metrics(values)

        # 计算增长率统计
        mom_growth = data_with_growth['mom_growth'].dropna()
        yoy_growth = data_with_growth['yoy_growth'].dropna()

        result = AnalysisResult(
            data_type='外地户籍就职',
            total_records=len(data_with_growth),
            mean_count=stability_metrics['mean_value'],
            stability_index=stability_metrics['stability_index'],
            trend_strength=stability_metrics['trend_strength'],
            volatility=stability_metrics['volatility'],
            avg_mom_growth=mom_growth.mean() if len(mom_growth) > 0 else 0,
            avg_yoy_growth=yoy_growth.mean() if len(yoy_growth) > 0 else 0,
            latest_mom_growth=mom_growth.iloc[-1] if len(
                mom_growth) > 0 else 0,
            latest_yoy_growth=yoy_growth.iloc[-1] if len(
                yoy_growth) > 0 else 0,
            max_count=values.max(),
            min_count=values.min(),
            total_change_pct=(
                (values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
            trend_rating=self.get_trend_rating(
                stability_metrics['trend_strength']),
            stability_rating=self.get_stability_rating(
                stability_metrics['stability_index'])
        )

        return result

    def generate_summary(self, results: List[AnalysisResult]) -> Dict:
        """
        生成分析摘要

        Args:
            results (List[AnalysisResult]): 分析结果列表

        Returns:
            Dict: 摘要信息
        """
        if not results:
            return {}

        return {
            "total_industries": len(results),
            "avg_stability_index": np.mean([r.stability_index for r in results]),
            "avg_trend_strength": np.mean([r.trend_strength for r in results]),
            "high_stability_industries": len([r for r in results if r.stability_index > 80]),
            "strong_trend_industries": len([r for r in results if r.trend_strength > 0.05]),
            "growing_industries": len([r for r in results if r.total_change_pct > 0]),
            "declining_industries": len([r for r in results if r.total_change_pct < 0])
        }
