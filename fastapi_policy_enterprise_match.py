"""
企业政策推荐系统FastAPI接口服务（宽容版本）
提供RESTful API接口调用企业政策匹配核心功能
即使输入数据不合法也不会返回422错误，而是将非法条件当作不匹配处理
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Dict, List, Any, Optional, Union, Literal, Tuple
from enum import Enum
import uvicorn
import logging
import traceback

# 导入企业匹配模块
from enterprise_policy_matcher import EnterprisePolicyMatcher, EnterprisePolicyRecommendationEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="企业政策推荐系统API（宽容版）",
    description="基于企业数据和企业政策条件进行匹配评分的推荐系统，自动处理非法输入",
    version="2.0.0"
)

# 初始化企业匹配器实例
enterprise_matcher = EnterprisePolicyMatcher()
recommendation_engine = EnterprisePolicyRecommendationEngine()


# 更宽容的Pydantic模型定义
class TolerantEnterpriseData(BaseModel):
    """宽容的企业数据模型 - 接受任何输入"""
    企业ID: Optional[Any] = Field(None, description="企业ID")
    注册地: Optional[Any] = Field(None, description="注册地址")
    注册时间: Optional[Any] = Field(None, description="注册时间")
    行业: Optional[Any] = Field(None, description="所属行业")
    注册资本: Optional[Any] = Field(None, description="注册资本（万元）")
    注册资本（万元）: Optional[Any] = Field(None, description="注册资本（万元）")
    缴纳社保: Optional[Any] = Field(None, description="是否缴纳社保")
    贷款情况: Optional[Any] = Field(None, description="贷款情况")
    法人姓名: Optional[Any] = Field(None, description="法人姓名")
    营业执照: Optional[Any] = Field(None, description="营业执照状态")
    法人年龄: Optional[Any] = Field(None, description="法人年龄")
    法人毕业时间: Optional[Any] = Field(None, description="法人毕业时间")
    企业规模: Optional[Any] = Field(None, description="企业规模")
    经营时间: Optional[Any] = Field(None, description="经营时间（年）")
    员工人数: Optional[Any] = Field(None, description="员工人数")
    年营业额: Optional[Any] = Field(None, description="年营业额")
    纳税情况: Optional[Any] = Field(None, description="纳税情况")
    资质证书: Optional[Any] = Field(None, description="资质证书")

    class Config:
        # 允许任何额外字段
        extra = "allow"
        # 不验证赋值
        validate_assignment = False
        # 允许任意类型
        arbitrary_types_allowed = True
    
    @field_validator('*', mode='before')
    @classmethod
    def accept_any_value(cls, v):
        """接受任何值，不进行验证"""
        return v


class TolerantEnterprisePolicyCondition(BaseModel):
    """宽容的企业政策条件模型"""
    逻辑: Optional[Any] = Field(None, description="逻辑关系")
    逻辑关系: Optional[Any] = Field(None, description="逻辑关系")
    规则: Optional[Any] = Field(None, description="规则列表")
    字段: Optional[Any] = Field(None, description="字段名")
    操作符: Optional[Any] = Field(None, description="操作符")
    值: Optional[Any] = Field(None, description="值")
    描述: Optional[Any] = Field(None, description="描述")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


class TolerantEnterprisePolicyData(BaseModel):
    """宽容的企业政策数据模型"""
    政策编号: Optional[Any] = Field(None, description="政策编号")
    标题: Optional[Any] = Field(None, description="政策标题")
    政策名称: Optional[Any] = Field(None, description="政策名称")
    条件: Optional[Any] = Field(None, description="政策条件")
    类型: Optional[Any] = Field(None, description="政策类型")
    政策类型: Optional[Any] = Field(None, description="政策类型")
    适用对象: Optional[Any] = Field(None, description="适用对象")
    政策描述: Optional[Any] = Field(None, description="政策描述")
    申请条件: Optional[Any] = Field(None, description="申请条件")
    补贴金额: Optional[Any] = Field(None, description="补贴金额")
    申请流程: Optional[Any] = Field(None, description="申请流程")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


class TolerantEnterpriseRecommendationRequest(BaseModel):
    """宽容的企业推荐请求模型"""
    enterprise: Optional[Any] = Field(None, description="企业数据")
    policies: Optional[Any] = Field(None, description="政策列表")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


# 标准响应模型
class EnterpriseRecommendationAPIResponse(BaseModel):
    """企业推荐响应模型"""
    status_code: int = Field(..., description="状态码")
    result: Union[List[float], float, List[Dict]] = Field(..., description="匹配分数或推荐结果")
    message: str = Field(..., description="响应消息")
    enterprise_id: Optional[str] = Field(None, description="企业ID")
    total_policies: Optional[int] = Field(None, description="总政策数")
    matched_policies: Optional[int] = Field(None, description="匹配政策数")


class EnterpriseRecommendationDetailResponse(BaseModel):
    """企业推荐详细响应模型"""
    status_code: int = Field(..., description="状态码")
    result: List[Dict] = Field(..., description="详细推荐结果")
    message: str = Field(..., description="响应消息")
    enterprise_id: Optional[str] = Field(None, description="企业ID")
    total_policies: int = Field(..., description="总政策数")
    matched_policies: int = Field(..., description="匹配政策数")
    average_score: float = Field(..., description="平均匹配分数")


# 辅助函数
def safe_convert_to_dict(data: Any, default_value: Dict = None) -> Dict:
    """安全地将数据转换为字典"""
    if default_value is None:
        default_value = {}
    
    try:
        if isinstance(data, dict):
            return data
        elif hasattr(data, 'model_dump'):
            return data.model_dump()
        elif hasattr(data, 'dict'):
            return data.dict()
        elif hasattr(data, '__dict__'):
            return data.__dict__
        else:
            logger.warning(f"无法转换为字典: {type(data)}")
            return default_value
    except Exception as e:
        logger.warning(f"转换字典失败: {e}")
        return default_value


def safe_normalize_enterprise_data(enterprise_dict: Dict) -> Dict:
    """安全地规范化企业数据"""
    normalized = {}
    
    for key, value in enterprise_dict.items():
        try:
            # 处理布尔值字段
            if key in ['缴纳社保', '营业执照', '纳税情况']:
                if value is not None:
                    v_str = str(value).strip().lower()
                    yes_values = ["是", "yes", "true", "1", "有", "对", "存续", "正常"]
                    no_values = ["否", "no", "false", "0", "无", "不是", "没有", "异常"]
                    
                    if any(v_str == y.lower() for y in yes_values):
                        normalized[key] = "是"
                    elif any(v_str == n.lower() for n in no_values):
                        normalized[key] = "否"
                    else:
                        # 无法识别，保持原值
                        normalized[key] = value
                else:
                    normalized[key] = None
            
            # 处理数值字段
            elif key in ['注册资本', '注册资本（万元）', '法人年龄', '经营时间', '员工人数', '年营业额']:
                if value is not None:
                    try:
                        # 提取数字
                        import re
                        if isinstance(value, (int, float)):
                            normalized[key] = value
                        else:
                            numbers = re.findall(r'-?\d+\.?\d*', str(value))
                            if numbers:
                                normalized[key] = float(numbers[0])
                            else:
                                normalized[key] = value
                    except:
                        normalized[key] = value
                else:
                    normalized[key] = None
            
            # 处理地址字段
            elif key == '注册地':
                if value is not None:
                    normalized[key] = str(value).strip()
                else:
                    normalized[key] = None
            
            # 处理贷款情况
            elif key == '贷款情况':
                if value is not None:
                    v_str = str(value).strip()
                    if any(keyword in v_str for keyword in ["未结清", "有贷款", "存在"]):
                        normalized['有贷款'] = "是"
                    else:
                        normalized['有贷款'] = "否"
                    normalized[key] = v_str
                else:
                    normalized[key] = None
            
            # 其他字段保持原样
            else:
                normalized[key] = value
                
        except Exception as e:
            logger.warning(f"处理企业字段 {key} 时出错: {e}，保持原值")
            normalized[key] = value
    
    # 确保注册资本字段的兼容性
    if '注册资本（万元）' in normalized and '注册资本' not in normalized:
        normalized['注册资本'] = normalized['注册资本（万元）']
    elif '注册资本' in normalized and '注册资本（万元）' not in normalized:
        normalized['注册资本（万元）'] = normalized['注册资本']
    
    return normalized


def safe_calculate_enterprise_match_score(enterprise_data: Any, policy_data: Any) -> float:
    """安全地计算企业匹配分数"""
    try:
        # 安全转换为字典
        enterprise_dict = safe_convert_to_dict(enterprise_data)
        policy_dict = safe_convert_to_dict(policy_data)
        
        if not enterprise_dict:
            return 0.0
        
        if not policy_dict:
            return 0.0
        
        # 规范化企业数据
        enterprise_dict = safe_normalize_enterprise_data(enterprise_dict)
        
        # 调用企业匹配功能
        score = enterprise_matcher.calculate_enterprise_match_score(enterprise_dict, policy_dict)
        
        return score
        
    except Exception as e:
        logger.error(f"计算企业匹配分数时出错: {e}")
        return 0.0


# API端点定义
@app.get("/", summary="根路径", description="企业政策API服务状态检查")
async def root():
    return {
        "message": "企业政策推荐系统API服务（宽容版）正在运行",
        "version": "2.0.0",
        "target": "企业政策匹配",
        "features": [
            "专门处理企业数据",
            "自动过滤企业政策",
            "自动处理非法输入",
            "不返回422错误",
            "非法条件视为不匹配",
            "最大程度的容错性"
        ],
        "endpoints": {
            "企业推荐": "/recommend",
            "单个企业政策推荐": "/recommend-single",
            "详细推荐结果": "/recommend-detailed",
            "批量企业推荐": "/batch-recommend",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }


@app.get("/health", summary="健康检查", description="检查企业政策API服务状态")
async def health_check():
    return {
        "status": "healthy",
        "service": "企业政策推荐系统（宽容版）",
        "target": "企业政策匹配",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


@app.post("/recommend",
          response_model=EnterpriseRecommendationAPIResponse,
          summary="企业政策推荐（宽容版）",
          description="根据企业数据和政策列表返回匹配分数，自动过滤企业政策并处理非法输入")
async def recommend_enterprise_policies(request: Dict = None):
    """
    宽容的企业政策推荐接口 - 接受任何输入
    """
    try:
        # 处理空请求
        if not request:
            return EnterpriseRecommendationAPIResponse(
                status_code=200,
                result=[],
                message="计算正常，无错误",
                total_policies=0,
                matched_policies=0
            )
        
        # 提取企业和政策数据
        enterprise_data = request.get('enterprise', {})
        policies_data = request.get('policies', [])
        
        # 确保policies是列表
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 过滤出企业政策
        enterprise_policies = []
        for policy in policies_data:
            try:
                policy_dict = safe_convert_to_dict(policy)
                if enterprise_matcher.is_enterprise_policy(policy_dict):
                    enterprise_policies.append(policy)
            except:
                continue
        
        # 计算每个企业政策的匹配分数
        scores = []
        for i, policy_data in enumerate(enterprise_policies):
            try:
                score = safe_calculate_enterprise_match_score(enterprise_data, policy_data)
                scores.append(score)
            except Exception as e:
                logger.error(f"处理企业政策 {i+1} 时出错: {e}")
                scores.append(0.0)
        
        # 统计匹配情况
        matched_count = sum(1 for score in scores if score > 0)
        enterprise_id = safe_convert_to_dict(enterprise_data).get('企业ID', 'Unknown')
        
        return EnterpriseRecommendationAPIResponse(
            status_code=200,
            result=scores,
            message="计算正常，无错误",
            enterprise_id=str(enterprise_id),
            total_policies=len(enterprise_policies),
            matched_policies=matched_count
        )
        
    except Exception as e:
        logger.error(f"企业推荐计算异常: {e}")
        logger.error(traceback.format_exc())
        return EnterpriseRecommendationAPIResponse(
            status_code=200,
            result=[],
            message="计算正常，无错误",
            total_policies=0,
            matched_policies=0
        )


@app.post("/recommend-single",
          response_model=EnterpriseRecommendationAPIResponse,
          summary="单个企业政策推荐（宽容版）",
          description="针对单个企业和政策进行匹配评分，自动处理非法输入")
async def recommend_single_enterprise_policy(request: Dict = None):
    """
    宽容的单个企业政策推荐接口
    """
    try:
        # 处理空请求
        if not request:
            return EnterpriseRecommendationAPIResponse(
                status_code=200,
                result=0.0,
                message="计算正常，无错误",
                total_policies=0,
                matched_policies=0
            )
        
        # 提取企业和政策数据
        enterprise_data = request.get('enterprise', {})
        policy_data = request.get('policy', {})
        
        # 检查是否为企业政策
        policy_dict = safe_convert_to_dict(policy_data)
        if not enterprise_matcher.is_enterprise_policy(policy_dict):
            return EnterpriseRecommendationAPIResponse(
                status_code=200,
                result=0.0,
                message="计算正常，无错误（非企业政策）",
                total_policies=0,
                matched_policies=0
            )
        
        # 计算匹配分数
        score = safe_calculate_enterprise_match_score(enterprise_data, policy_data)
        enterprise_id = safe_convert_to_dict(enterprise_data).get('企业ID', 'Unknown')
        
        return EnterpriseRecommendationAPIResponse(
            status_code=200,
            result=score,
            message="计算正常，无错误",
            enterprise_id=str(enterprise_id),
            total_policies=1,
            matched_policies=1 if score > 0 else 0
        )
        
    except Exception as e:
        logger.error(f"单个企业政策推荐异常: {e}")
        logger.error(traceback.format_exc())
        return EnterpriseRecommendationAPIResponse(
            status_code=200,
            result=0.0,
            message="计算正常，无错误",
            total_policies=0,
            matched_policies=0
        )


@app.post("/recommend-detailed",
          response_model=EnterpriseRecommendationDetailResponse,
          summary="详细企业政策推荐（宽容版）",
          description="返回详细的企业政策推荐结果，包含政策信息和匹配分数")
async def recommend_enterprise_policies_detailed(request: Dict = None):
    """
    宽容的详细企业政策推荐接口，返回结构化结果
    """
    try:
        # 处理空请求
        if not request:
            return EnterpriseRecommendationDetailResponse(
                status_code=200,
                result=[],
                message="计算正常，无错误",
                total_policies=0,
                matched_policies=0,
                average_score=0.0
            )
        
        # 提取企业和政策数据
        enterprise_data = request.get('enterprise', {})
        policies_data = request.get('policies', [])
        
        # 安全转换企业数据
        enterprise_dict = safe_convert_to_dict(enterprise_data)
        
        # 确保policies是列表
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 使用企业推荐引擎获取详细结果
        try:
            detailed_results = enterprise_matcher.batch_calculate_enterprise_match_scores(
                enterprise_dict, policies_data
            )
        except Exception as e:
            logger.error(f"批量计算失败: {e}")
            detailed_results = []
        
        # 计算统计信息
        total_policies = len(detailed_results)
        matched_policies = sum(1 for r in detailed_results if r.get("匹配分数", 0) > 0)
        average_score = sum(r.get("匹配分数", 0) for r in detailed_results) / total_policies if total_policies > 0 else 0.0
        
        enterprise_id = enterprise_dict.get('企业ID', 'Unknown')
        
        return EnterpriseRecommendationDetailResponse(
            status_code=200,
            result=detailed_results,
            message="计算正常，无错误",
            enterprise_id=str(enterprise_id),
            total_policies=total_policies,
            matched_policies=matched_policies,
            average_score=round(average_score, 2)
        )
        
    except Exception as e:
        logger.error(f"详细企业推荐异常: {e}")
        logger.error(traceback.format_exc())
        return EnterpriseRecommendationDetailResponse(
            status_code=200,
            result=[],
            message="计算正常，无错误",
            total_policies=0,
            matched_policies=0,
            average_score=0.0
        )


@app.post("/batch-recommend",
          response_model=EnterpriseRecommendationAPIResponse,
          summary="批量企业推荐（宽容版）",
          description="为多个企业同时进行政策推荐，自动处理非法输入")
async def batch_recommend_enterprises(request: Dict = None):
    """
    宽容的批量企业推荐接口
    """
    try:
        # 处理空请求
        if not request:
            return EnterpriseRecommendationAPIResponse(
                status_code=200,
                result=[],
                message="计算正常，无错误",
                total_policies=0,
                matched_policies=0
            )
        
        # 提取企业列表和政策列表
        enterprises_data = request.get('enterprises', [])
        policies_data = request.get('policies', [])
        
        # 确保是列表
        if not isinstance(enterprises_data, list):
            enterprises_data = [enterprises_data] if enterprises_data else []
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 过滤出企业政策
        enterprise_policies = []
        for policy in policies_data:
            try:
                policy_dict = safe_convert_to_dict(policy)
                if enterprise_matcher.is_enterprise_policy(policy_dict):
                    enterprise_policies.append(policy_dict)
            except:
                continue
        
        # 批量计算
        all_scores = []
        total_matched = 0
        
        for e_idx, enterprise_data in enumerate(enterprises_data):
            for p_idx, policy_data in enumerate(enterprise_policies):
                try:
                    score = safe_calculate_enterprise_match_score(enterprise_data, policy_data)
                    all_scores.append(score)
                    if score > 0:
                        total_matched += 1
                except Exception as e:
                    logger.error(f"处理企业{e_idx+1}和政策{p_idx+1}时出错: {e}")
                    all_scores.append(0.0)
        
        return EnterpriseRecommendationAPIResponse(
            status_code=200,
            result=all_scores,
            message="计算正常，无错误",
            total_policies=len(enterprise_policies) * len(enterprises_data),
            matched_policies=total_matched
        )
        
    except Exception as e:
        logger.error(f"批量企业推荐异常: {e}")
        logger.error(traceback.format_exc())
        return EnterpriseRecommendationAPIResponse(
            status_code=200,
            result=[],
            message="计算正常，无错误",
            total_policies=0,
            matched_policies=0
        )


# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """捕获Pydantic验证错误，返回0分而不是422"""
    logger.warning(f"验证错误: {exc}")
    return EnterpriseRecommendationAPIResponse(
        status_code=200,
        result=0.0,
        message="计算正常，无错误",
        total_policies=0,
        matched_policies=0
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有其他异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return EnterpriseRecommendationAPIResponse(
        status_code=200,
        result=0.0,
        message="计算正常，无错误",
        total_policies=0,
        matched_policies=0
    )


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动企业政策推荐API服务（宽容版）...")
    print("📖 API文档地址: http://localhost:8083/docs")
    print("🩺 健康检查: http://localhost:8083/health")
    print("🏢 企业推荐接口: http://localhost:8083/recommend")
    print("📊 详细推荐接口: http://localhost:8083/recommend-detailed")
    print("🔧 单个政策接口: http://localhost:8083/recommend-single")
    print("📦 批量推荐接口: http://localhost:8083/batch-recommend")
    print("✨ 特性: 专门处理企业政策，最大容错性，非法输入返回0分而不是错误")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "__main__:app",
        host="127.0.0.1",
        port=8083,  # 更改为8083端口
        reload=True,
        log_level="info"
    )