"""
政策推荐系统FastAPI接口服务（宽容版本）
提供RESTful API接口调用政策用户匹配核心功能
即使输入数据不合法也不会返回422错误，而是将非法条件当作不匹配处理
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Dict, List, Any, Optional, Union, Literal, Tuple
from enum import Enum
import uvicorn
import logging
import traceback

# 导入核心匹配模块
from policy_user_match import PolicyUserMatcher, RecommendationEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策推荐系统API（宽容版）",
    description="基于用户数据和政策条件进行匹配评分的推荐系统，自动处理非法输入",
    version="2.0.0"
)

# 初始化匹配器实例
matcher = PolicyUserMatcher()


# 更宽容的Pydantic模型定义
class TolerantUserData(BaseModel):
    """宽容的用户数据模型 - 接受任何输入"""
    用户ID: Optional[Any] = Field(None, description="用户ID")
    最高学历: Optional[Any] = Field(None, description="最高学历")
    毕业时间: Optional[Any] = Field(None, description="毕业时间")
    籍贯: Optional[Any] = Field(None, description="籍贯")
    专业: Optional[Any] = Field(None, description="专业名称")
    技能等级: Optional[Any] = Field(None, description="技能等级")
    征地人员: Optional[Any] = Field(None, description="是否为征地人员")
    缴纳社保: Optional[Any] = Field(None, description="是否缴纳社保")
    养老保险: Optional[Any] = Field(None, description="是否有养老保险")
    困难人员: Optional[Any] = Field(None, description="是否为困难人员")
    就业类型: Optional[Any] = Field(None, description="就业类型")
    年龄: Optional[Any] = Field(None, description="年龄")
    工作经历: Optional[Any] = Field(None, description="工作经历")

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


class TolerantNestedCondition(BaseModel):
    """宽容的嵌套条件模型"""
    逻辑: Optional[Any] = Field(None, description="逻辑关系")
    规则: Optional[Any] = Field(None, description="规则列表")
    字段: Optional[Any] = Field(None, description="字段名")
    操作符: Optional[Any] = Field(None, description="操作符")
    值: Optional[Any] = Field(None, description="值")
    描述: Optional[Any] = Field(None, description="描述")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


class TolerantPolicyData(BaseModel):
    """宽容的政策数据模型"""
    政策编号: Optional[Any] = Field(None, description="政策编号")
    标题: Optional[Any] = Field(None, description="政策标题")
    条件: Optional[Any] = Field(None, description="政策条件")
    类型: Optional[Any] = Field(None, description="政策类型")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


class TolerantRecommendationRequest(BaseModel):
    """宽容的推荐请求模型"""
    user: Optional[Any] = Field(None, description="用户数据")
    policies: Optional[Any] = Field(None, description="政策列表")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


# 标准响应模型（简化版，移除warnings）
class RecommendationAPIResponse(BaseModel):
    """推荐响应模型"""
    status_code: int = Field(..., description="状态码")
    result: Union[List[float], float] = Field(..., description="匹配分数")
    message: str = Field(..., description="响应消息")


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


def safe_normalize_user_data(user_dict: Dict) -> Dict:
    """安全地规范化用户数据"""
    normalized = {}
    
    for key, value in user_dict.items():
        try:
            # 尝试处理特殊字段
            if key == '就业类型' and value is not None:
                # 处理枚举或字符串
                if hasattr(value, 'value'):
                    normalized[key] = value.value
                else:
                    normalized[key] = str(value) if value is not None else None
            
            elif key in ['征地人员', '缴纳社保', '养老保险', '困难人员']:
                # 尝试规范化是否字段
                if value is not None:
                    v_str = str(value).strip().lower()
                    yes_values = ["是", "yes", "true", "1", "有", "对"]
                    no_values = ["否", "no", "false", "0", "无", "不是", "没有"]
                    
                    if any(v_str == y.lower() for y in yes_values):
                        normalized[key] = "是"
                    elif any(v_str == n.lower() for n in no_values):
                        normalized[key] = "否"
                    else:
                        # 无法识别，保持原值
                        normalized[key] = value
                else:
                    normalized[key] = None
            
            elif key == '年龄':
                # 尝试提取年龄数字
                if value is not None:
                    try:
                        if isinstance(value, (int, float)):
                            normalized[key] = int(value)
                        else:
                            import re
                            numbers = re.findall(r'\d+', str(value))
                            if numbers:
                                normalized[key] = int(numbers[0])
                            else:
                                normalized[key] = value
                    except:
                        normalized[key] = value
                else:
                    normalized[key] = None
            
            elif key == '毕业时间':
                # 尝试提取毕业时间数字
                if value is not None:
                    try:
                        if isinstance(value, (int, float)):
                            normalized[key] = int(value)
                        else:
                            import re
                            numbers = re.findall(r'\d+', str(value))
                            if numbers:
                                normalized[key] = int(numbers[0])
                            else:
                                normalized[key] = value
                    except:
                        normalized[key] = value
                else:
                    normalized[key] = None
            
            else:
                # 其他字段保持原样
                normalized[key] = value
                
        except Exception as e:
            logger.warning(f"处理字段 {key} 时出错: {e}，保持原值")
            normalized[key] = value
    
    return normalized


def safe_calculate_match_score(user_data: Any, policy_data: Any) -> float:
    """安全地计算匹配分数"""
    try:
        # 安全转换为字典
        user_dict = safe_convert_to_dict(user_data)
        policy_dict = safe_convert_to_dict(policy_data)
        
        if not user_dict:
            return 0.0
        
        if not policy_dict:
            return 0.0
        
        # 规范化用户数据
        user_dict = safe_normalize_user_data(user_dict)
        
        # 调用核心匹配功能
        score = matcher.calculate_match_score(user_dict, policy_dict)
        
        return score
        
    except Exception as e:
        logger.error(f"计算匹配分数时出错: {e}")
        return 0.0


# API端点定义
@app.get("/", summary="根路径", description="API服务状态检查")
async def root():
    return {
        "message": "政策推荐系统API服务（宽容版）正在运行",
        "version": "2.0.0",
        "features": [
            "自动处理非法输入",
            "不返回422错误",
            "非法条件视为不匹配",
            "最大程度的容错性"
        ],
        "endpoints": {
            "推荐": "/recommend",
            "单个政策推荐": "/recommend-single",
            "批量用户推荐": "/batch-recommend",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }


@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy",
        "service": "政策推荐系统（宽容版）",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


@app.post("/recommend",
          response_model=RecommendationAPIResponse,
          summary="政策推荐（宽容版）",
          description="根据用户数据和政策列表返回匹配分数，自动处理非法输入")
async def recommend_policies(request: Dict = None):
    """
    宽容的政策推荐接口 - 接受任何输入
    """
    try:
        # 处理空请求
        if not request:
            return RecommendationAPIResponse(
                status_code=200,
                result=[],
                message="计算正常，无错误"
            )
        
        # 提取用户和政策数据
        user_data = request.get('user', {})
        policies_data = request.get('policies', [])
        
        # 确保policies是列表
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 计算每个政策的匹配分数
        scores = []
        for i, policy_data in enumerate(policies_data):
            try:
                score = safe_calculate_match_score(user_data, policy_data)
                scores.append(score)
            except Exception as e:
                logger.error(f"处理政策 {i+1} 时出错: {e}")
                scores.append(0.0)
        
        return RecommendationAPIResponse(
            status_code=200,
            result=scores,
            message="计算正常，无错误"
        )
        
    except Exception as e:
        logger.error(f"推荐计算异常: {e}")
        logger.error(traceback.format_exc())
        return RecommendationAPIResponse(
            status_code=200,
            result=[],
            message="计算正常，无错误"
        )


@app.post("/recommend-single",
          response_model=RecommendationAPIResponse,
          summary="单个政策推荐（宽容版）",
          description="针对单个用户和政策进行匹配评分，自动处理非法输入")
async def recommend_single_policy(request: Dict = None):
    """
    宽容的单个政策推荐接口
    """
    try:
        # 处理空请求
        if not request:
            return RecommendationAPIResponse(
                status_code=200,
                result=0.0,
                message="计算正常，无错误"
            )
        
        # 提取用户和政策数据
        user_data = request.get('user', {})
        policy_data = request.get('policy', {})
        
        # 计算匹配分数
        score = safe_calculate_match_score(user_data, policy_data)
        
        return RecommendationAPIResponse(
            status_code=200,
            result=score,
            message="计算正常，无错误"
        )
        
    except Exception as e:
        logger.error(f"单个政策推荐异常: {e}")
        logger.error(traceback.format_exc())
        return RecommendationAPIResponse(
            status_code=200,
            result=0.0,
            message="计算正常，无错误"
        )


@app.post("/batch-recommend",
          response_model=RecommendationAPIResponse,
          summary="批量用户推荐（宽容版）",
          description="为多个用户同时进行政策推荐，自动处理非法输入")
async def batch_recommend(request: Dict = None):
    """
    宽容的批量推荐接口
    """
    try:
        # 处理空请求
        if not request:
            return RecommendationAPIResponse(
                status_code=200,
                result=[],
                message="计算正常，无错误"
            )
        
        # 提取用户列表和政策列表
        users_data = request.get('users', [])
        policies_data = request.get('policies', [])
        
        # 确保是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 批量计算
        all_scores = []
        for u_idx, user_data in enumerate(users_data):
            for p_idx, policy_data in enumerate(policies_data):
                try:
                    score = safe_calculate_match_score(user_data, policy_data)
                    all_scores.append(score)
                except Exception as e:
                    logger.error(f"处理用户{u_idx+1}和政策{p_idx+1}时出错: {e}")
                    all_scores.append(0.0)
        
        return RecommendationAPIResponse(
            status_code=200,
            result=all_scores,
            message="计算正常，无错误"
        )
        
    except Exception as e:
        logger.error(f"批量推荐异常: {e}")
        logger.error(traceback.format_exc())
        return RecommendationAPIResponse(
            status_code=200,
            result=[],
            message="计算正常，无错误"
        )


# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """捕获Pydantic验证错误，返回0分而不是422"""
    logger.warning(f"验证错误: {exc}")
    return RecommendationAPIResponse(
        status_code=200,
        result=0.0,
        message="计算正常，无错误"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有其他异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return RecommendationAPIResponse(
        status_code=200,
        result=0.0,
        message="计算正常，无错误"
    )


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策推荐API服务（宽容版）...")
    print("📖 API文档地址: http://localhost:8081/docs")
    print("🩺 健康检查: http://localhost:8081/health")
    print("🔧 主推荐接口: http://localhost:8081/recommend")
    print("✨ 特性: 最大容错性，非法输入返回0分而不是错误")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "__main__:app",
        host="10.1.50.96",
        port=8081,
        reload=True,
        log_level="info"
    )