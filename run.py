"""
统一政策和人才流动分析FastAPI接口服务
集成政策匹配（用户和企业）、政策预审、人才流动分析、社会风险评估、热度分析和信用风险评估功能
"""

from fastapi import FastAPI, Request
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel
import pandas as pd
import uvicorn
from datetime import datetime
import logging
import traceback

# 导入政策系统核心模块
from policy_user_match import PolicyMatchEngine as UserPolicyMatchEngine
from policy_enterprise_match import PolicyMatchEngine as EnterprisePolicyMatchEngine
from policy_user_audit import PolicyPreAuditEngine
from policy_enterprise_audit import PolicyAuditEngine
from data_processor_user import DataProcessor as UserDataProcessor
from data_processor_enterprise import DataProcessor as EnterpriseDataProcessor

# 导入人才流动分析核心模块
from talent_analyzer import TalentDataAnalyzer

# 导入风险评估和热度分析模块
from socialRiskModelV2 import SocialAuditModel2
from newHeatModel import NewHeatModelAnalysis
from creditRiskModel import creditRiskModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== Pydantic模型定义 ====================

class RiskRequest(BaseModel):
    data: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None


class RiskResponse(BaseModel):
    status_code: int
    result: List
    message: str


class HeatRequestBody(BaseModel):
    data: List[Dict]


# ==================== 初始化FastAPI应用 ====================

app = FastAPI(
    title="政策与人才流动统一分析API",
    description="集成用户政策匹配、企业政策匹配、政策预审、人才流动分析、社会风险评估、热度分析和信用风险评估功能的统一系统",
    version="6.0.0"
)

# 初始化政策系统组件
user_match_engine = UserPolicyMatchEngine()
enterprise_match_engine = EnterprisePolicyMatchEngine()
user_audit_engine = PolicyPreAuditEngine()
enterprise_audit_engine = PolicyAuditEngine()
user_data_processor = UserDataProcessor()
enterprise_data_processor = EnterpriseDataProcessor()

# 初始化人才流动分析组件
talent_analyzer = TalentDataAnalyzer()

# 初始化风险评估和热度分析组件
social_risk_obj = SocialAuditModel2()
new_heat_obj = NewHeatModelAnalysis()
credit_risk_obj = creditRiskModel()


# ==================== 人才流动分析通用函数 ====================

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


# ==================== 系统管理接口 ====================

@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy",
        "service": "政策与人才流动统一分析API",
        "modules": [
            "用户政策匹配", "企业政策匹配", "用户政策预审", "企业政策预审",
            "求职者意向分析", "企业招聘分析", "外地户籍分析",
            "社会风险评估", "热度分析", "信用风险评估"
        ],
        "version": "6.0.0"
    }


# ==================== 用户政策匹配接口 ====================

@app.post("/user/recommend-single",
          summary="单个用户政策匹配",
          description="针对单个用户和单个政策进行匹配，自动处理非法输入")
async def user_recommend_single_policy(request: Request):
    """单个用户政策匹配接口"""
    try:
        request_data = await user_data_processor.parse_request_safely(request)
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})

        user_dict = user_data_processor.process_user_data(user_data)
        policy_dict = user_data_processor.process_policy_data(policy_data)

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
    """批量用户匹配接口"""
    try:
        request_data = await user_data_processor.parse_request_safely(request)
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        policy_dict = user_data_processor.process_policy_data(policy_data)
        matched_user_ids = []

        for user_data in users_data:
            try:
                user_dict = user_data_processor.process_user_data(user_data)
                if user_data_processor.validate_match_input(user_dict, policy_dict):
                    result = user_match_engine.match_policy(
                        user_dict, policy_dict)
                    if result == 1:
                        user_id = user_dict.get("用户ID")
                        if user_id:
                            matched_user_ids.append(str(user_id))
                        else:
                            raw_user_dict = user_data_processor.safe_convert_to_dict(
                                user_data)
                            raw_user_id = raw_user_dict.get("用户ID")
                            if raw_user_id:
                                matched_user_ids.append(str(raw_user_id))
            except Exception as e:
                logger.error(f"处理用户时出错: {e}")
                continue

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
    """单个企业政策匹配接口"""
    try:
        request_data = await enterprise_data_processor.parse_request_safely(request)
        enterprise_data = request_data.get('enterprise', {})
        policy_data = request_data.get('policy', {})

        enterprise_dict = enterprise_data_processor.process_enterprise_data(
            enterprise_data)
        policy_dict = enterprise_data_processor.process_policy_data(
            policy_data)

        if enterprise_data_processor.validate_match_input(enterprise_dict, policy_dict):
            result = enterprise_match_engine.match_policy(
                enterprise_dict, policy_dict)
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
    """批量企业匹配接口"""
    try:
        request_data = await enterprise_data_processor.parse_request_safely(request)
        enterprises_data = request_data.get('enterprises', [])
        policy_data = request_data.get('policy', {})

        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []

        policy_dict = enterprise_data_processor.process_policy_data(
            policy_data)
        matched_enterprise_ids = []

        for enterprise_data in enterprises_data:
            try:
                enterprise_dict = enterprise_data_processor.process_enterprise_data(
                    enterprise_data)
                if enterprise_data_processor.validate_match_input(enterprise_dict, policy_dict):
                    result = enterprise_match_engine.match_policy(
                        enterprise_dict, policy_dict)
                    if result == 1:
                        enterprise_id = enterprise_dict.get("企业ID")
                        if enterprise_id:
                            matched_enterprise_ids.append(str(enterprise_id))
                        else:
                            raw_enterprise_dict = enterprise_data_processor.safe_convert_to_dict(
                                enterprise_data)
                            raw_enterprise_id = raw_enterprise_dict.get("企业ID")
                            if raw_enterprise_id:
                                matched_enterprise_ids.append(
                                    str(raw_enterprise_id))
            except Exception as e:
                logger.error(f"处理企业时出错: {e}")
                continue

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
          description="针对单个用户和单个政策进行预审，返回审核结果和不符合的条件详情")
async def user_audit_single_policy(request: Request):
    """单个用户政策预审接口"""
    try:
        request_data = await user_data_processor.parse_request_safely(request)
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})

        audit_result = user_audit_engine.audit_policy(user_data, policy_data)

        return {
            "status_code": 200,
            "result": audit_result.get("result", 0),
            "failed_conditions": audit_result.get("failed_conditions", []),
            "message": audit_result.get("message", "预审完成")
        }

    except Exception as e:
        logger.error(f"单个用户政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "failed_conditions": [f"系统异常: {str(e)}"],
            "message": "预审过程中发生异常"
        }


@app.post("/user/batch-audit",
          summary="批量用户预审",
          description="多个用户与单个政策进行预审，返回所有用户的预审结果和不符合条件详情")
async def user_batch_audit(request: Request):
    """批量用户预审接口"""
    try:
        request_data = await user_data_processor.parse_request_safely(request)
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})

        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []

        audit_results = user_audit_engine.multi_user_audit_policy(
            users_data, policy_data)

        passed_user_ids = []
        detailed_results = []

        for i, user_data in enumerate(users_data):
            if i < len(audit_results):
                result = audit_results[i]

                try:
                    user_dict = user_data_processor.process_user_data(
                        user_data)
                    user_id = user_dict.get("用户ID")
                    if not user_id:
                        raw_user_dict = user_data_processor.safe_convert_to_dict(
                            user_data)
                        user_id = raw_user_dict.get("用户ID", f"User_{i}")
                except:
                    user_id = f"User_{i}"

                if result.get("result", 0) == 1:
                    passed_user_ids.append(str(user_id))

                detailed_results.append({
                    "user_id": str(user_id),
                    "result": result.get("result", 0),
                    "failed_conditions": result.get("failed_conditions", []),
                    "message": result.get("message", "")
                })

        return {
            "status_code": 200,
            "passed_user_ids": passed_user_ids,
            "detailed_results": detailed_results,
            "summary": {
                "total_users": len(users_data),
                "passed_users": len(passed_user_ids),
                "pass_rate": round(len(passed_user_ids) / len(users_data), 3) if users_data else 0
            },
            "message": "批量预审完成"
        }

    except Exception as e:
        logger.error(f"批量用户预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "passed_user_ids": [],
            "detailed_results": [],
            "summary": {
                "total_users": 0,
                "passed_users": 0,
                "pass_rate": 0
            },
            "message": "批量预审过程中发生异常"
        }


# ==================== 企业政策预审接口 ====================

@app.post("/enterprise/audit-single",
          summary="单个企业政策预审",
          description="针对单个企业和单个政策进行预审，返回审核结果和不符合的条件详情")
async def enterprise_audit_single_policy(request: Request):
    """单个企业政策预审接口"""
    try:
        request_data = await enterprise_data_processor.parse_request_safely(request)
        enterprise_data = request_data.get('enterprise', {})
        policy_data = request_data.get('policy', {})

        audit_result = enterprise_audit_engine.audit_policy(
            enterprise_data, policy_data)

        return {
            "status_code": 200,
            "result": audit_result.get("result", 0),
            "failed_conditions": audit_result.get("failed_conditions", []),
            "message": audit_result.get("message", "预审完成")
        }

    except Exception as e:
        logger.error(f"单个企业政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "failed_conditions": [f"系统异常: {str(e)}"],
            "message": "预审过程中发生异常"
        }


@app.post("/enterprise/batch-audit",
          summary="批量企业预审",
          description="多个企业与单个政策进行预审，返回所有企业的预审结果和不符合条件详情")
async def enterprise_batch_audit(request: Request):
    """批量企业预审接口"""
    try:
        request_data = await enterprise_data_processor.parse_request_safely(request)
        enterprises_data = request_data.get('enterprises', [])
        policy_data = request_data.get('policy', {})

        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []

        audit_results = enterprise_audit_engine.multi_enterprise_audit_policy(
            enterprises_data, policy_data)

        passed_enterprise_ids = []
        detailed_results = []

        for i, enterprise_data in enumerate(enterprises_data):
            if i < len(audit_results):
                result = audit_results[i]

                try:
                    enterprise_dict = enterprise_data_processor.process_enterprise_data(
                        enterprise_data)
                    enterprise_id = enterprise_dict.get("企业ID")
                    if not enterprise_id:
                        raw_enterprise_dict = enterprise_data_processor.safe_convert_to_dict(
                            enterprise_data)
                        enterprise_id = raw_enterprise_dict.get(
                            "企业ID", f"Enterprise_{i}")
                except:
                    enterprise_id = f"Enterprise_{i}"

                if result.get("result", 0) == 1:
                    passed_enterprise_ids.append(str(enterprise_id))

                detailed_results.append({
                    "enterprise_id": str(enterprise_id),
                    "result": result.get("result", 0),
                    "failed_conditions": result.get("failed_conditions", []),
                    "message": result.get("message", "")
                })

        return {
            "status_code": 200,
            "passed_enterprise_ids": passed_enterprise_ids,
            "detailed_results": detailed_results,
            "summary": {
                "total_enterprises": len(enterprises_data),
                "passed_enterprises": len(passed_enterprise_ids),
                "pass_rate": round(len(passed_enterprise_ids) / len(enterprises_data), 3) if enterprises_data else 0
            },
            "message": "批量预审完成"
        }

    except Exception as e:
        logger.error(f"批量企业预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "passed_enterprise_ids": [],
            "detailed_results": [],
            "summary": {
                "total_enterprises": 0,
                "passed_enterprises": 0,
                "pass_rate": 0
            },
            "message": "批量预审过程中发生异常"
        }


# ==================== 人才流动分析接口 ====================

@app.post("/talent/analyze-applicant",
          summary="求职者意向行业变化趋势分析",
          description="分析求职者求职意向的行业变化趋势")
async def analyze_applicant_position(request: Request):
    """求职者意向行业变化趋势分析"""
    try:
        request_data = await request.json()

        if not isinstance(request_data, dict) or 'data' not in request_data:
            return create_error_response("请求格式错误：需要包含data字段的字典")

        data_type = request_data.get('data_type', '求职者求职意向')
        validated_data = talent_analyzer.validate_industry_data(
            request_data['data'])

        df = pd.DataFrame(validated_data)
        df = talent_analyzer.preprocess_data(df)
        results = talent_analyzer.analyze_industry_data(df, data_type)

        if not results:
            return create_error_response("未能生成有效的分析结果")

        api_results = [result.to_dict() for result in results]
        summary = talent_analyzer.generate_summary(results)

        return create_success_response(
            message=f"求职者意向行业趋势分析完成，共分析{len(results)}个行业",
            data=api_results,
            summary=summary
        )

    except Exception as e:
        logger.error(f"求职者分析异常: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("分析过程出错")


@app.post("/talent/analyze-corporate",
          summary="企业招聘岗位行业变化趋势分析",
          description="分析企业招聘岗位的行业变化趋势")
async def analyze_corporate_position(request: Request):
    """企业招聘岗位行业变化趋势分析"""
    try:
        request_data = await request.json()

        if not isinstance(request_data, dict) or 'data' not in request_data:
            return create_error_response("请求格式错误：需要包含data字段的字典")

        data_type = request_data.get('data_type', '企业招聘岗位')
        validated_data = talent_analyzer.validate_industry_data(
            request_data['data'])

        df = pd.DataFrame(validated_data)
        df = talent_analyzer.preprocess_data(df)
        results = talent_analyzer.analyze_industry_data(df, data_type)

        if not results:
            return create_error_response("未能生成有效的分析结果")

        api_results = [result.to_dict() for result in results]
        summary = talent_analyzer.generate_summary(results)

        return create_success_response(
            message=f"企业招聘岗位行业趋势分析完成，共分析{len(results)}个行业",
            data=api_results,
            summary=summary
        )

    except Exception as e:
        logger.error(f"企业分析异常: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("分析过程出错")


@app.post("/talent/analyze-nonlocal",
          summary="外地户籍在本城市就职人数变化趋势分析",
          description="分析外地户籍人员在本城市就职的人数变化趋势")
async def analyze_nonlocal_count(request: Request):
    """外地户籍在本城市就职人数变化趋势分析"""
    try:
        request_data = await request.json()

        if not isinstance(request_data, dict) or 'data' not in request_data:
            return create_error_response("请求格式错误：需要包含data字段的字典")

        validated_data = talent_analyzer.validate_nonlocal_data(
            request_data['data'])

        df = pd.DataFrame(validated_data)
        df = talent_analyzer.preprocess_data(df)
        result = talent_analyzer.analyze_nonlocal_data(df)

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


# ==================== 社会风险评估接口 ====================

@app.post("/getSocialRisks",
          response_model=RiskResponse,
          summary="社会风险评估",
          description="评估企业/个体的社会风险，返回风险评分、等级和直判结果")
def get_social_risks(req: RiskRequest):
    """
    传入：
    - req.data: 企业/个体列表（中文字段）
    - req.config: 可选配置（如 hard_limits/thresholds/weight_amp_factor 等）
    返回：
    - summary + data（包含 RiskScore、风险等级、是否直判等）
    """
    try:
        return social_risk_obj.evaluate_payload(req.data, req.config)
    except Exception as e:
        logger.error(f"社会风险评估异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 500,
            "result": [],
            "message": f"社会风险评估失败: {str(e)}"
        }


# ==================== 热度分析接口 ====================

@app.post("/getHeat",
          summary="热度分析",
          description="分析数据的热度值")
def get_heat(body: HeatRequestBody):
    """
    传入：
    - body.data: 需要分析的数据列表
    返回：
    - 热度分析结果
    """
    try:
        heat_data = body.data
        new_heat_num = new_heat_obj.entrance(heat_data)
        return new_heat_num
    except Exception as e:
        logger.error(f"热度分析异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 500,
            "result": None,
            "message": f"热度分析失败: {str(e)}"
        }


# ==================== 信用风险评估接口 ====================

@app.post("/getCreditRisks",
          response_model=RiskResponse,
          summary="信用风险评估",
          description="评估企业/个体的信用风险，返回风险评分、等级和直判结果")
def get_credit_risks(req: RiskRequest):
    """
    传入：
    - req.data: 企业/个体列表（中文字段）
    - req.config: 可选配置（如 hard_limits/thresholds/weight_amp_factor 等）
    返回：
    - summary + data（包含 RiskScore、风险等级、是否直判等）
    """
    try:
        return credit_risk_obj.evaluate_payload({"data": req.data}, req.config)
    except Exception as e:
        logger.error(f"信用风险评估异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 500,
            "result": [],
            "message": f"信用风险评估失败: {str(e)}"
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
    print("🚀 正在启动政策与人才流动统一分析API服务...")
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
    print("📊 人才流动分析接口:")
    print("   • 求职者分析: http://localhost:8081/talent/analyze-applicant")
    print("   • 企业招聘分析: http://localhost:8081/talent/analyze-corporate")
    print("   • 外地户籍分析: http://localhost:8081/talent/analyze-nonlocal")
    print()
    print("⚠️  风险评估接口:")
    print("   • 社会风险评估: http://localhost:8081/getSocialRisks")
    print("   • 信用风险评估: http://localhost:8081/getCreditRisks")
    print()
    print("🔥 热度分析接口:")
    print("   • 热度分析: http://localhost:8081/getHeat")
    print()
    print("=" * 70)
    print("按 Ctrl+C 停止服务")

    uvicorn.run(
        "run:app",
        host="10.1.50.96",
        port=8081,
        reload=True,
        log_level="info"
    )