"""
政策系统FastAPI接口服务 - 统一版本
提供政策匹配和政策预审的RESTful API接口
即使输入数据不合法也不会返回错误，而是将非法条件当作不通过处理
"""

from fastapi import FastAPI, Request
from typing import Dict, List, Any, Optional, Union
import uvicorn
import logging
import traceback

# 导入核心模块和数据处理工具
from policy_user_match import PolicyMatchEngine
from policy_user_audit import PolicyPreAuditEngine
from data_processor import DataProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策系统统一API",
    description="集成政策匹配和政策预审功能的统一系统，基于用户数据和政策条件进行严格规则处理，自动处理非法输入",
    version="3.0.0"
)

# 初始化核心组件
match_engine = PolicyMatchEngine()
audit_engine = PolicyPreAuditEngine()
data_processor = DataProcessor()


# ==================== 系统管理接口 ====================

@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy",
        "service": "政策系统统一API",
        "modules": ["政策匹配", "政策预审"],
        "match_mode": "strict",
        "audit_mode": "strict",
        "result_type": "binary (0 or 1)",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


# ==================== 政策匹配接口 (保持原有接口名) ====================

@app.post("/recommend-single",
          summary="单个政策匹配",
          description="针对单个用户和单个政策进行匹配，自动处理非法输入")
async def recommend_single_policy(request: Request):
    """
    单个政策匹配接口
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取用户和政策数据
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        user_dict = data_processor.process_user_data(user_data)
        policy_dict = data_processor.process_policy_data(policy_data)

        # 验证并匹配
        if data_processor.validate_match_input(user_dict, policy_dict):
            result = match_engine.match_policy(user_dict, policy_dict)
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
          summary="批量用户匹配",
          description="多个用户与单个政策进行匹配，只返回匹配成功的用户ID")
async def batch_recommend(request: Request):
    """
    批量用户匹配接口 - 多个用户与单个政策匹配，只返回匹配的用户ID
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取用户列表和政策数据
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        # 确保users是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = data_processor.process_policy_data(policy_data)

        matched_user_ids = []
        for user_data in users_data:
            try:
                # 处理用户数据
                user_dict = data_processor.process_user_data(user_data)

                # 验证并匹配
                if data_processor.validate_match_input(user_dict, policy_dict):
                    result = match_engine.match_policy(user_dict, policy_dict)
                    if result == 1:  # 匹配成功
                        user_id = user_dict.get("用户ID")
                        if user_id:
                            matched_user_ids.append(str(user_id))
                        else:
                            # 如果没有用户ID，使用原始数据中的ID
                            raw_user_dict = data_processor.safe_convert_to_dict(user_data)
                            raw_user_id = raw_user_dict.get("用户ID")
                            if raw_user_id:
                                matched_user_ids.append(str(raw_user_id))

            except Exception as e:
                logger.error(f"处理用户时出错: {e}")
                continue  # 跳过出错的用户，继续处理下一个

        return {
            "status_code": 200,
            "matched_user_ids": matched_user_ids,
            "message": "批量匹配完成"
        }

    except Exception as e:
        logger.error(f"批量匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "matched_user_ids": [],
            "message": "批量匹配完成"
        }


# ==================== 政策预审接口 (保持原有接口名) ====================

@app.post("/audit-single",
          summary="单个政策预审",
          description="针对单个用户和单个政策进行预审，自动处理非法输入")
async def audit_single_policy(request: Request):
    """
    单个政策预审接口
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取用户和政策数据
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        user_dict = data_processor.process_user_data(user_data)
        policy_dict = data_processor.process_policy_data(policy_data)

        # 验证并预审
        if data_processor.validate_match_input(user_dict, policy_dict):
            result = audit_engine.audit_policy(user_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0

        return {
            "status_code": 200,
            "result": result,
            "message": "预审完成"
        }

    except Exception as e:
        logger.error(f"单个政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "预审完成"
        }


@app.post("/batch-audit",
          summary="批量用户预审",
          description="多个用户与单个政策进行预审，只返回预审通过的用户ID")
async def batch_audit(request: Request):
    """
    批量用户预审接口 - 多个用户与单个政策预审，只返回通过的用户ID
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取用户列表和政策数据
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        # 确保users是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = data_processor.process_policy_data(policy_data)

        passed_user_ids = []
        for user_data in users_data:
            try:
                # 处理用户数据
                user_dict = data_processor.process_user_data(user_data)

                # 验证并预审
                if data_processor.validate_match_input(user_dict, policy_dict):
                    result = audit_engine.audit_policy(user_dict, policy_dict)
                    if result == 1:  # 预审通过
                        user_id = user_dict.get("用户ID")
                        if user_id:
                            passed_user_ids.append(str(user_id))
                        else:
                            # 如果没有用户ID，使用原始数据中的ID
                            raw_user_dict = data_processor.safe_convert_to_dict(user_data)
                            raw_user_id = raw_user_dict.get("用户ID")
                            if raw_user_id:
                                passed_user_ids.append(str(raw_user_id))

            except Exception as e:
                logger.error(f"处理用户时出错: {e}")
                continue  # 跳过出错的用户，继续处理下一个

        return {
            "status_code": 200,
            "passed_user_ids": passed_user_ids,
            "message": "批量预审完成"
        }

    except Exception as e:
        logger.error(f"批量预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "passed_user_ids": [],
            "message": "批量预审完成"
        }


@app.post("/audit-summary",
          summary="预审统计摘要",
          description="多个用户与单个政策预审的详细统计信息")
async def audit_summary(request: Request):
    """
    预审统计摘要接口 - 返回详细的预审统计信息
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)

        # 提取用户列表和政策数据
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        # 确保users是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        if not users_data:
            return {
                "status_code": 200,
                "summary": {
                    "总用户数": 0,
                    "预审通过数": 0,
                    "通过率": 0.0,
                    "用户预审详情": []
                },
                "message": "预审统计完成"
            }

        # 批量预审
        audit_results = audit_engine.multi_user_audit_policy(users_data, policy_data)
        
        # 生成摘要
        summary = audit_engine.get_audit_summary(users_data, policy_data, audit_results)

        return {
            "status_code": 200,
            "summary": summary,
            "message": "预审统计完成"
        }

    except Exception as e:
        logger.error(f"预审统计异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "summary": {
                "总用户数": 0,
                "预审通过数": 0,
                "通过率": 0.0,
                "用户预审详情": []
            },
            "message": "预审统计完成"
        }


# ==================== 全局异常处理器 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return {
        "status_code": 200,
        "result": 0,
        "message": "处理完成"
    }


# ==================== 启动配置 ====================

if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策系统统一API服务...")
    print("📖 API文档地址: http://localhost:8081/docs")
    print("🩺 健康检查: http://localhost:8081/health")
    print()
    print("🔧 政策匹配接口:")
    print("   • 单个匹配: http://localhost:8081/recommend-single")
    print("   • 批量匹配: http://localhost:8081/batch-recommend")
    print()
    print("🔍 政策预审接口:")
    print("   • 单个预审: http://localhost:8081/audit-single")
    print("   • 批量预审: http://localhost:8081/batch-audit")
    print("   • 预审统计: http://localhost:8081/audit-summary")
    print()
    print("✨ 特性: 严格0或1结果 + 最大容错性，非法输入返回0而不是错误")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")

    uvicorn.run(
        "run:app",
        host="127.0.0.1",
        port=8081,
        reload=True,
        log_level="info"
    )