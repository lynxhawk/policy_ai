#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人才流动分析API接口服务
api_server.py
"""

from fastapi import FastAPI, Request
import pandas as pd
import uvicorn
from datetime import datetime
import logging
import traceback

# 导入核心算法模块
from talent_analyzer import TalentDataAnalyzer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="人才流动数据分析API",
    description="人才趋势分析接口服务，支持行业和外地户籍数据分析",
    version="2.1.0"
)

# 全局分析器实例
analyzer = TalentDataAnalyzer()


def create_success_response(message: str, data, summary=None):
    """创建成功响应"""
    response = {
        "status_code": 200,
        "data": data,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if summary:
        response["summary"] = summary
    return response


def create_error_response(message: str):
    """创建错误响应"""
    return {
        "status_code": 200,
        "data": None,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "人才流动数据分析API",
        "version": "2.1.0",
        "features": ["行业趋势分析", "外地户籍分析", "批量分析", "稳定性评估"]
    }


@app.post("/analyze-applicant")
async def analyze_applicant_position(request: Request):
    """求职者意向行业变化趋势分析"""
    try:
        request_data = await request.json()
        
        if not isinstance(request_data, dict) or 'data' not in request_data:
            return create_error_response("请求格式错误：需要包含data字段的字典")
        
        data_type = request_data.get('data_type', '求职者求职意向')
        validated_data = analyzer.validate_industry_data(request_data['data'])
        
        df = pd.DataFrame(validated_data)
        df = analyzer.preprocess_data(df)
        results = analyzer.analyze_industry_data(df, data_type)
        
        if not results:
            return create_error_response("未能生成有效的分析结果")
        
        api_results = [result.to_dict() for result in results]
        summary = analyzer.generate_summary(results)
        
        return create_success_response(
            message=f"求职者意向行业趋势分析完成，共分析{len(results)}个行业",
            data=api_results,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"求职者分析异常: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("分析过程出错")


@app.post("/analyze-corporate")
async def analyze_corporate_position(request: Request):
    """企业招聘岗位行业变化趋势分析"""
    try:
        request_data = await request.json()
        
        if not isinstance(request_data, dict) or 'data' not in request_data:
            return create_error_response("请求格式错误：需要包含data字段的字典")
        
        data_type = request_data.get('data_type', '企业招聘岗位')
        validated_data = analyzer.validate_industry_data(request_data['data'])
        
        df = pd.DataFrame(validated_data)
        df = analyzer.preprocess_data(df)
        results = analyzer.analyze_industry_data(df, data_type)
        
        if not results:
            return create_error_response("未能生成有效的分析结果")
        
        api_results = [result.to_dict() for result in results]
        summary = analyzer.generate_summary(results)
        
        return create_success_response(
            message=f"企业招聘岗位行业趋势分析完成，共分析{len(results)}个行业",
            data=api_results,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"企业分析异常: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("分析过程出错")


@app.post("/analyze-nonlocal")
async def analyze_nonlocal_count(request: Request):
    """外地户籍在本城市就职人数变化趋势分析"""
    try:
        request_data = await request.json()
        
        if not isinstance(request_data, dict) or 'data' not in request_data:
            return create_error_response("请求格式错误：需要包含data字段的字典")
        
        validated_data = analyzer.validate_nonlocal_data(request_data['data'])
        
        df = pd.DataFrame(validated_data)
        df = analyzer.preprocess_data(df)
        result = analyzer.analyze_nonlocal_data(df)
        
        if not result:
            return create_error_response("未能生成有效的分析结果")
        
        api_result = result.to_dict()
        
        summary = {
            "data_points": result.total_records,
            "stability_level": result.stability_rating,
            "trend_level": result.trend_rating,
            "overall_change": result.total_change_pct,
            "is_growing": bool(result.total_change_pct > 0)
        }
        
        return create_success_response(
            message="外地户籍就职趋势分析完成",
            data=api_result,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"外地户籍分析异常: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("分析过程出错")


@app.post("/batch-analyze")
async def batch_analyze(request: Request):
    """批量分析所有数据类型"""
    try:
        request_data = await request.json()
        
        if not isinstance(request_data, dict):
            return create_error_response("请求数据必须是字典格式")
        
        applicant_results = None
        corporate_results = None
        nonlocal_result = None
        
        # 分析求职者数据
        if 'applicant_data' in request_data and request_data['applicant_data']:
            try:
                validated_data = analyzer.validate_industry_data(request_data['applicant_data'])
                df = pd.DataFrame(validated_data)
                df = analyzer.preprocess_data(df)
                results = analyzer.analyze_industry_data(df, "求职者求职意向")
                applicant_results = [r.to_dict() for r in results]
            except Exception as e:
                logger.error(f"求职者数据分析出错: {e}")
        
        # 分析企业招聘数据
        if 'corporate_data' in request_data and request_data['corporate_data']:
            try:
                validated_data = analyzer.validate_industry_data(request_data['corporate_data'])
                df = pd.DataFrame(validated_data)
                df = analyzer.preprocess_data(df)
                results = analyzer.analyze_industry_data(df, "企业招聘岗位")
                corporate_results = [r.to_dict() for r in results]
            except Exception as e:
                logger.error(f"企业数据分析出错: {e}")
        
        # 分析外地户籍数据
        if 'nonlocal_data' in request_data and request_data['nonlocal_data']:
            try:
                validated_data = analyzer.validate_nonlocal_data(request_data['nonlocal_data'])
                df = pd.DataFrame(validated_data)
                df = analyzer.preprocess_data(df)
                result = analyzer.analyze_nonlocal_data(df)
                if result:
                    nonlocal_result = result.to_dict()
            except Exception as e:
                logger.error(f"外地户籍数据分析出错: {e}")
        
        # 生成总体摘要
        processed_types = []
        total_industries = 0
        
        if applicant_results:
            processed_types.append("求职者意向")
            total_industries += len(applicant_results)
            
        if corporate_results:
            processed_types.append("企业招聘")
            total_industries += len(corporate_results)
            
        if nonlocal_result:
            processed_types.append("外地户籍")
        
        if not processed_types:
            return create_error_response("至少需要提供一种类型的数据进行分析")
        
        response_data = {
            "applicant_results": applicant_results,
            "corporate_results": corporate_results,
            "nonlocal_result": nonlocal_result,
            "processed_data_types": processed_types,
            "total_industries_analyzed": total_industries
        }
        
        return create_success_response(
            message=f"批量分析完成，处理了{len(processed_types)}种数据类型",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"批量分析异常: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("批量分析过程出错")


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return create_error_response("服务异常")


if __name__ == "__main__":
    print("🚀 正在启动人才流动分析API服务...")
    print("📖 API文档地址: http://localhost:8000/docs")
    print("🩺 健康检查: http://localhost:8000/health")
    print("👥 求职者分析: http://localhost:8000/analyze-applicant")
    print("🏢 企业分析: http://localhost:8000/analyze-corporate")
    print("🌍 外地户籍分析: http://localhost:8000/analyze-nonlocal")
    print("📊 批量分析: http://localhost:8000/batch-analyze")
    print("✨ 特性: 完整的人才流动趋势分析 + 稳定性评估")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "fastapi_talent:app",
        host="127.0.0.1", 
        port=8000,
        reload=True
    )