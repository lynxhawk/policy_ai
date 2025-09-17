"""
政策匹配系统FastAPI接口服务
提供RESTful API接口调用政策匹配核心功能
即使输入数据不合法也不会返回错误，而是将非法条件当作不匹配处理
"""

from fastapi import FastAPI, Request
from typing import Dict, List, Any, Optional, Union
import uvicorn
import logging
import traceback

# 导入核心匹配模块和数据处理工具
from policy_enterprise_match import PolicyMatchEngine
from data_processor_enterprise import DataProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策匹配系统API",
    description="基于企业数据和政策条件进行严格规则匹配的系统，自动处理非法输入",
    version="2.0.0"
)

# 初始化核心组件
match_engine = PolicyMatchEngine()
data_processor = DataProcessor()


# API端点定义
@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy",
        "service": "政策匹配系统",
        "match_mode": "strict",
        "result_type": "binary (0 or 1)",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


@app.post("/recommend-single",
          summary="单个政策匹配",
          description="针对单个企业和单个政策进行匹配，自动处理非法输入")
async def recommend_single_policy(request: Request):
    """
    单个政策匹配接口
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取企业和政策数据
        enterprise_data = request_data.get('enterprise', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        enterprise_dict = data_processor.process_enterprise_data(enterprise_data)
        policy_dict = data_processor.process_policy_data(policy_data)

        # 验证并匹配
        if data_processor.validate_match_input(enterprise_dict, policy_dict):
            result = match_engine.match_policy(enterprise_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0

        return {
            "status_code": 200,
            "result": result,
            "message": "匹配完成"
        }

    except Exception as e:
        logger.error(f"单个政策匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "匹配完成"
        }


@app.post("/batch-recommend",
          summary="批量企业匹配",
          description="多个企业与单个政策进行匹配，只返回匹配成功的企业ID")
async def batch_recommend(request: Request):
    """
    批量企业匹配接口 - 多个企业与单个政策匹配，只返回匹配的企业ID
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取企业列表和政策数据
        enterprises_data = request_data.get('enterprises', [])
        policy_data = request_data.get('policy', {})

        # 确保enterprises是列表
        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = data_processor.process_policy_data(policy_data)

        matched_enterprise_ids = []
        for enterprise_data in enterprises_data:
            try:
                # 处理企业数据
                enterprise_dict = data_processor.process_enterprise_data(enterprise_data)

                # 验证并匹配
                if data_processor.validate_match_input(enterprise_dict, policy_dict):
                    result = match_engine.match_policy(enterprise_dict, policy_dict)
                    if result == 1:  # 匹配成功
                        enterprise_id = enterprise_dict.get("企业ID")
                        if enterprise_id:
                            matched_enterprise_ids.append(str(enterprise_id))
                        else:
                            # 如果没有企业ID，使用原始数据中的ID
                            raw_enterprise_dict = data_processor.safe_convert_to_dict(
                                enterprise_data)
                            raw_enterprise_id = raw_enterprise_dict.get("企业ID")
                            if raw_enterprise_id:
                                matched_enterprise_ids.append(str(raw_enterprise_id))

            except Exception as e:
                logger.error(f"处理企业时出错: {e}")
                continue  # 跳过出错的企业，继续处理下一个

        return {
            "status_code": 200,
            "matched_enterprise_ids": matched_enterprise_ids,
            "message": "批量匹配完成"
        }

    except Exception as e:
        logger.error(f"批量匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "matched_enterprise_ids": [],
            "message": "批量匹配完成"
        }


@app.post("/match-summary",
          summary="企业匹配统计摘要",
          description="获取企业与政策匹配的详细统计信息")
async def match_summary(request: Request):
    """
    企业匹配统计摘要接口
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取企业列表和政策数据
        enterprises_data = request_data.get('enterprises', [])
        policy_data = request_data.get('policy', {})

        # 确保enterprises是列表
        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []

        # 处理政策数据
        policy_dict = data_processor.process_policy_data(policy_data)

        # 处理企业数据列表
        processed_enterprises = []
        for enterprise_data in enterprises_data:
            try:
                enterprise_dict = data_processor.process_enterprise_data(enterprise_data)
                processed_enterprises.append(enterprise_dict)
            except Exception as e:
                logger.error(f"处理企业数据时出错: {e}")
                # 添加一个空的企业记录，避免索引错位
                processed_enterprises.append({"企业ID": "Unknown"})

        # 执行批量匹配
        match_results = match_engine.multi_enterprise_match_policy(
            processed_enterprises, policy_dict)

        # 生成统计摘要
        summary = match_engine.get_match_summary(
            processed_enterprises, policy_dict, match_results)

        return {
            "status_code": 200,
            "summary": summary,
            "message": "统计摘要生成完成"
        }

    except Exception as e:
        logger.error(f"生成统计摘要异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "summary": {"错误": "统计摘要生成失败"},
            "message": "统计摘要生成完成"
        }


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return {
        "status_code": 200,
        "result": 0,
        "message": "匹配完成"
    }


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策匹配API服务...")
    print("📖 API文档地址: http://localhost:8083/docs")
    print("🩺 健康检查: http://localhost:8083/health")
    print("🔧 单个匹配接口: http://localhost:8083/recommend-single")
    print("📊 批量匹配接口: http://localhost:8083/batch-recommend")
    print("📈 匹配统计接口: http://localhost:8083/match-summary")
    print("✨ 特性: 严格0或1结果 + 最大容错性，非法输入返回0而不是错误")
    print("按 Ctrl+C 停止服务")

    uvicorn.run(
        "fastapi_policy_enterprise_match:app",
        host="127.0.0.1",
        port=8083,
        reload=True,
        log_level="info"
    )