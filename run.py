"""
政策系统FastAPI接口服务 - 统一版本
提供政策匹配（用户和企业）和政策预审的RESTful API接口
即使输入数据不合法也不会返回错误，而是将非法条件当作不通过处理
"""

from fastapi import FastAPI, Request
from typing import Dict, List, Any, Optional, Union
import uvicorn
import logging
import traceback

# 导入核心模块和数据处理工具
from policy_user_match import PolicyMatchEngine as UserPolicyMatchEngine
from policy_enterprise_match import PolicyMatchEngine as EnterprisePolicyMatchEngine
from policy_user_audit import PolicyPreAuditEngine
from policy_enterprise_audit import PolicyAuditEngine
from data_processor_user import DataProcessor as UserDataProcessor
from data_processor_enterprise import DataProcessor as EnterpriseDataProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策系统统一API",
    description="集成用户政策匹配、企业政策匹配和政策预审功能的统一系统，基于数据和政策条件进行严格规则处理，自动处理非法输入",
    version="4.0.0"
)

# 初始化核心组件
user_match_engine = UserPolicyMatchEngine()
enterprise_match_engine = EnterprisePolicyMatchEngine()
user_audit_engine = PolicyPreAuditEngine()
enterprise_audit_engine = PolicyAuditEngine()
user_data_processor = UserDataProcessor()
enterprise_data_processor = EnterpriseDataProcessor()


# ==================== 系统管理接口 ====================

@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy",
        "service": "政策系统统一API",
        "modules": ["用户政策匹配", "企业政策匹配", "用户政策预审", "企业政策预审"],
        "match_mode": "strict",
        "audit_mode": "strict",
        "result_type": "binary (0 or 1)",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


# ==================== 用户政策匹配接口 ====================

@app.post("/user/recommend-single",
          summary="单个用户政策匹配",
          description="针对单个用户和单个政策进行匹配，自动处理非法输入")
async def user_recommend_single_policy(request: Request):
    """
    单个用户政策匹配接口
    """
    try:
        # 解析请求
        request_data = await user_data_processor.parse_request_safely(request)

        # 提取用户和政策数据
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        user_dict = user_data_processor.process_user_data(user_data)
        policy_dict = user_data_processor.process_policy_data(policy_data)

        # 验证并匹配
        if user_data_processor.validate_match_input(user_dict, policy_dict):
            result = user_match_engine.match_policy(user_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0

        return {
            "status_code": 200,
            "result": result,
            "message": "匹配完成"
        }

    except Exception as e:
        logger.error(f"单个用户政策匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "匹配完成"
        }


@app.post("/user/batch-recommend",
          summary="批量用户匹配",
          description="多个用户与单个政策进行匹配，只返回匹配成功的用户ID")
async def user_batch_recommend(request: Request):
    """
    批量用户匹配接口 - 多个用户与单个政策匹配，只返回匹配的用户ID
    """
    try:
        # 解析请求
        request_data = await user_data_processor.parse_request_safely(request)

        # 提取用户列表和政策数据
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        # 确保users是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = user_data_processor.process_policy_data(policy_data)

        matched_user_ids = []
        for user_data in users_data:
            try:
                # 处理用户数据
                user_dict = user_data_processor.process_user_data(user_data)

                # 验证并匹配
                if user_data_processor.validate_match_input(user_dict, policy_dict):
                    result = user_match_engine.match_policy(user_dict, policy_dict)
                    if result == 1:  # 匹配成功
                        user_id = user_dict.get("用户ID")
                        if user_id:
                            matched_user_ids.append(str(user_id))
                        else:
                            # 如果没有用户ID，使用原始数据中的ID
                            raw_user_dict = user_data_processor.safe_convert_to_dict(user_data)
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
        logger.error(f"批量用户匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "matched_user_ids": [],
            "message": "批量匹配完成"
        }


# ==================== 企业政策匹配接口 ====================

@app.post("/enterprise/recommend-single",
          summary="单个企业政策匹配",
          description="针对单个企业和单个政策进行匹配，自动处理非法输入")
async def enterprise_recommend_single_policy(request: Request):
    """
    单个企业政策匹配接口
    """
    try:
        # 解析请求
        request_data = await enterprise_data_processor.parse_request_safely(request)

        # 提取企业和政策数据
        enterprise_data = request_data.get('enterprise', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        enterprise_dict = enterprise_data_processor.process_enterprise_data(enterprise_data)
        policy_dict = enterprise_data_processor.process_policy_data(policy_data)

        # 验证并匹配
        if enterprise_data_processor.validate_match_input(enterprise_dict, policy_dict):
            result = enterprise_match_engine.match_policy(enterprise_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0

        return {
            "status_code": 200,
            "result": result,
            "message": "匹配完成"
        }

    except Exception as e:
        logger.error(f"单个企业政策匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "匹配完成"
        }


@app.post("/enterprise/batch-recommend",
          summary="批量企业匹配",
          description="多个企业与单个政策进行匹配，只返回匹配成功的企业ID")
async def enterprise_batch_recommend(request: Request):
    """
    批量企业匹配接口 - 多个企业与单个政策匹配，只返回匹配的企业ID
    """
    try:
        # 解析请求
        request_data = await enterprise_data_processor.parse_request_safely(request)

        # 提取企业列表和政策数据
        enterprises_data = request_data.get('enterprises', [])
        policy_data = request_data.get('policy', {})

        # 确保enterprises是列表
        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = enterprise_data_processor.process_policy_data(policy_data)

        matched_enterprise_ids = []
        for enterprise_data in enterprises_data:
            try:
                # 处理企业数据
                enterprise_dict = enterprise_data_processor.process_enterprise_data(enterprise_data)

                # 验证并匹配
                if enterprise_data_processor.validate_match_input(enterprise_dict, policy_dict):
                    result = enterprise_match_engine.match_policy(enterprise_dict, policy_dict)
                    if result == 1:  # 匹配成功
                        enterprise_id = enterprise_dict.get("企业ID")
                        if enterprise_id:
                            matched_enterprise_ids.append(str(enterprise_id))
                        else:
                            # 如果没有企业ID，使用原始数据中的ID
                            raw_enterprise_dict = enterprise_data_processor.safe_convert_to_dict(enterprise_data)
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
        logger.error(f"批量企业匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "matched_enterprise_ids": [],
            "message": "批量匹配完成"
        }


# ==================== 用户政策预审接口 ====================

@app.post("/user/audit-single",
          summary="单个用户政策预审",
          description="针对单个用户和单个政策进行预审，自动处理非法输入")
async def user_audit_single_policy(request: Request):
    """
    单个用户政策预审接口
    """
    try:
        # 解析请求
        request_data = await user_data_processor.parse_request_safely(request)

        # 提取用户和政策数据
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        user_dict = user_data_processor.process_user_data(user_data)
        policy_dict = user_data_processor.process_policy_data(policy_data)

        # 验证并预审
        if user_data_processor.validate_match_input(user_dict, policy_dict):
            result = user_audit_engine.audit_policy(user_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0

        return {
            "status_code": 200,
            "result": result,
            "message": "预审完成"
        }

    except Exception as e:
        logger.error(f"单个用户政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "预审完成"
        }


@app.post("/user/batch-audit",
          summary="批量用户预审",
          description="多个用户与单个政策进行预审，只返回预审通过的用户ID")
async def user_batch_audit(request: Request):
    """
    批量用户预审接口 - 多个用户与单个政策预审，只返回通过的用户ID
    """
    try:
        # 解析请求
        request_data = await user_data_processor.parse_request_safely(request)

        # 提取用户列表和政策数据
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        # 确保users是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = user_data_processor.process_policy_data(policy_data)

        passed_user_ids = []
        for user_data in users_data:
            try:
                # 处理用户数据
                user_dict = user_data_processor.process_user_data(user_data)

                # 验证并预审
                if user_data_processor.validate_match_input(user_dict, policy_dict):
                    result = user_audit_engine.audit_policy(user_dict, policy_dict)
                    if result == 1:  # 预审通过
                        user_id = user_dict.get("用户ID")
                        if user_id:
                            passed_user_ids.append(str(user_id))
                        else:
                            # 如果没有用户ID，使用原始数据中的ID
                            raw_user_dict = user_data_processor.safe_convert_to_dict(user_data)
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
        logger.error(f"批量用户预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "passed_user_ids": [],
            "message": "批量预审完成"
        }


# ==================== 企业政策预审接口 ====================

@app.post("/enterprise/audit-single",
          summary="单个企业政策预审",
          description="针对单个企业和单个政策进行预审，自动处理非法输入")
async def enterprise_audit_single_policy(request: Request):
    """
    单个企业政策预审接口
    """
    try:
        # 解析请求
        request_data = await enterprise_data_processor.parse_request_safely(request)

        # 提取企业和政策数据
        enterprise_data = request_data.get('enterprise', {})
        policy_data = request_data.get('policy', {})

        # 处理数据
        enterprise_dict = enterprise_data_processor.process_enterprise_data(enterprise_data)
        policy_dict = enterprise_data_processor.process_policy_data(policy_data)

        # 验证并预审
        if enterprise_data_processor.validate_audit_input(enterprise_dict, policy_dict):
            result = enterprise_audit_engine.audit_policy(enterprise_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0

        return {
            "status_code": 200,
            "result": result,
            "message": "预审完成"
        }

    except Exception as e:
        logger.error(f"单个企业政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "预审完成"
        }


@app.post("/enterprise/batch-audit",
          summary="批量企业预审",
          description="多个企业与单个政策进行预审，只返回预审通过的企业ID")
async def enterprise_batch_audit(request: Request):
    """
    批量企业预审接口 - 多个企业与单个政策预审，只返回通过预审的企业ID
    """
    try:
        # 解析请求
        request_data = await enterprise_data_processor.parse_request_safely(request)

        # 提取企业列表和政策数据
        enterprises_data = request_data.get('enterprises', [])
        policy_data = request_data.get('policy', {})

        # 确保enterprises是列表
        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []

        # 处理政策数据（只需要处理一次）
        policy_dict = enterprise_data_processor.process_policy_data(policy_data)

        passed_enterprise_ids = []
        for enterprise_data in enterprises_data:
            try:
                # 处理企业数据
                enterprise_dict = enterprise_data_processor.process_enterprise_data(enterprise_data)

                # 验证并预审
                if enterprise_data_processor.validate_audit_input(enterprise_dict, policy_dict):
                    result = enterprise_audit_engine.audit_policy(enterprise_dict, policy_dict)
                    if result == 1:  # 预审通过
                        enterprise_id = enterprise_dict.get("企业ID")
                        if enterprise_id:
                            passed_enterprise_ids.append(str(enterprise_id))
                        else:
                            # 如果没有企业ID，使用原始数据中的ID
                            raw_enterprise_dict = enterprise_data_processor.safe_convert_to_dict(
                                enterprise_data)
                            raw_enterprise_id = raw_enterprise_dict.get("企业ID")
                            if raw_enterprise_id:
                                passed_enterprise_ids.append(str(raw_enterprise_id))

            except Exception as e:
                logger.error(f"处理企业时出错: {e}")
                continue  # 跳过出错的企业，继续处理下一个

        return {
            "status_code": 200,
            "passed_enterprise_ids": passed_enterprise_ids,
            "message": "批量预审完成"
        }

    except Exception as e:
        logger.error(f"批量企业预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "passed_enterprise_ids": [],
            "message": "批量预审完成"
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
    print("👤 用户政策匹配接口:")
    print("   • 单个匹配: http://localhost:8081/user/recommend-single")
    print("   • 批量匹配: http://localhost:8081/user/batch-recommend")
    print()
    print("🏢 企业政策匹配接口:")
    print("   • 单个匹配: http://localhost:8081/enterprise/recommend-single")
    print("   • 批量匹配: http://localhost:8081/enterprise/batch-recommend")
    print()
    print("🔍 用户政策预审接口:")
    print("   • 单个预审: http://localhost:8081/user/audit-single")
    print("   • 批量预审: http://localhost:8081/user/batch-audit")
    print()
    print("🔍 企业政策预审接口:")
    print("   • 单个预审: http://localhost:8081/enterprise/audit-single")
    print("   • 批量预审: http://localhost:8081/enterprise/batch-audit")
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