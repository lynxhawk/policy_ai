"""
政策推荐系统FastAPI接口服务
提供RESTful API接口调用政策用户匹配核心功能
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Union
import uvicorn
import logging

# 导入核心匹配模块
from policy_user_match import PolicyUserMatcher, RecommendationEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策推荐系统API",
    description="基于用户数据和政策条件进行匹配评分的推荐系统",
    version="1.0.0"
)

# 初始化匹配器实例
matcher = PolicyUserMatcher()

# Pydantic模型定义
class UserData(BaseModel):
    """用户数据模型"""
    用户ID: Optional[str] = Field(None, description="用户ID")
    最高学历: Optional[str] = Field(None, description="最高学历")
    毕业时间: Optional[Any] = Field(None, description="毕业时间")
    籍贯: Optional[str] = Field(None, description="籍贯")
    专业: Optional[str] = Field(None, description="专业")
    技能等级: Optional[str] = Field(None, description="技能等级")
    征地人员: Optional[str] = Field(None, description="征地人员")
    缴纳社保: Optional[str] = Field(None, description="缴纳社保")
    养老保险: Optional[str] = Field(None, description="养老保险")
    困难人员: Optional[str] = Field(None, description="困难人员")
    就业类型: Optional[str] = Field(None, description="就业类型")
    年龄: Optional[Any] = Field(None, description="年龄")
    工作经历: Optional[List[Dict]] = Field(None, description="工作经历")

    class Config:
        # 允许额外字段
        extra = "allow"


class ConditionRule(BaseModel):
    """条件规则模型"""
    字段: str = Field(..., description="匹配字段")
    操作符: str = Field(..., description="操作符: =, !=, >, <, >=, <=, between")
    值: Any = Field(..., description="条件值")
    描述: Optional[str] = Field(None, description="条件描述")


class NestedCondition(BaseModel):
    """嵌套条件模型"""
    逻辑: Optional[str] = Field(None, description="逻辑关系: AND, OR")
    规则: Optional[List[Any]] = Field(None, description="规则列表")
    字段: Optional[str] = Field(None, description="字段名")
    操作符: Optional[str] = Field(None, description="操作符")
    值: Optional[Any] = Field(None, description="值")
    描述: Optional[str] = Field(None, description="描述")

    class Config:
        extra = "allow"


class PolicyData(BaseModel):
    """政策数据模型"""
    政策编号: str = Field(..., description="政策编号")
    标题: str = Field(..., description="政策标题")
    条件: NestedCondition = Field(..., description="政策条件")
    类型: Optional[str] = Field(None, description="政策类型")

    class Config:
        extra = "allow"


class RecommendationRequest(BaseModel):
    """推荐请求模型"""
    user: UserData = Field(..., description="用户数据")
    policies: List[PolicyData] = Field(..., description="政策列表")


# 简化的响应模型 - 只包含三个字段
class SimpleRecommendationResponse(BaseModel):
    """简化的推荐响应模型"""
    status_code: int = Field(..., description="状态码")
    result: List[float] = Field(..., description="匹配分数列表")
    message: str = Field(..., description="响应消息")


class PolicyRecommendation(BaseModel):
    """单个政策推荐结果"""
    政策编号: str = Field(..., description="政策编号")
    政策标题: str = Field(..., description="政策标题")
    匹配分数: int = Field(..., description="匹配分数")


class RecommendationResponse(BaseModel):
    """完整推荐响应模型"""
    recommendations: List[PolicyRecommendation] = Field(..., description="推荐政策列表，按分数和编号排序")
    total_policies: int = Field(..., description="总政策数")
    user_id: Optional[str] = Field(None, description="用户ID")


# API端点定义
@app.get("/", summary="根路径", description="API服务状态检查")
async def root():
    return {
        "message": "政策推荐系统API服务正在运行",
        "version": "1.0.0",
        "features": [
            "增强类型安全性",
            "自动处理类型不匹配",
            "详细错误日志记录",
            "数字提取支持（如：25岁、2年经验）",
            "模块化架构设计"
        ],
        "endpoints": {
            "推荐": "/recommend",
            "简化推荐": "/recommend-simple",
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
        "service": "政策推荐系统", 
        "type_safety": "enabled",
        "architecture": "modular"
    }


@app.post("/recommend-simple", 
          response_model=SimpleRecommendationResponse,
          summary="简化政策推荐",
          description="返回简化格式的政策匹配分数，类型不匹配时自动返回0分")
async def recommend_policies_simple(request: RecommendationRequest):
    """
    简化政策推荐接口 - 增强类型安全性
    
    Args:
        request: 包含用户数据和政策列表的请求
        
    Returns:
        SimpleRecommendationResponse: 包含状态码、分数列表和消息的简化响应
    """
    try:
        # 转换用户数据为字典
        user_dict = request.user.model_dump(exclude_none=False)
        
        # 转换政策数据为字典列表
        policies_dict_list = [policy.model_dump() for policy in request.policies]
        
        # 调用核心匹配功能
        scores = matcher.batch_calculate_match_scores(user_dict, policies_dict_list)
        
        return SimpleRecommendationResponse(
            status_code=200,
            result=scores,
            message="计算正常，无错误"
        )
        
    except Exception as e:
        logger.error(f"推荐计算异常: {str(e)}")
        return SimpleRecommendationResponse(
            status_code=500,
            result=[],
            message=f"计算出错: {str(e)}"
        )


@app.post("/recommend", 
          summary="政策推荐",
          description="根据用户数据和政策列表，返回每个政策的匹配分数，增强类型安全性")
async def recommend_policies(request: RecommendationRequest):
    """
    政策推荐接口 - 增强类型安全性
    
    Args:
        request: 包含用户数据和政策列表的请求
        
    Returns:
        Dict: 包含状态码、结果和消息
    """
    try:
        # 转换用户数据为字典
        user_dict = request.user.model_dump(exclude_none=False)
        
        # 转换政策数据为字典列表
        policies_dict_list = [policy.model_dump() for policy in request.policies]
        
        # 调用核心匹配功能
        scores = matcher.batch_calculate_match_scores(user_dict, policies_dict_list)
        
        return {
            "status_code": 200,
            "result": scores,
            "message": "计算正常，无错误"
        }
        
    except Exception as e:
        logger.error(f"推荐计算异常: {str(e)}")
        return {
            "status_code": 500,
            "result": [],
            "message": f"推荐计算出错: {str(e)}"
        }


@app.post("/recommend-single",
          summary="单个政策推荐",
          description="针对单个用户和单个政策进行匹配评分，增强类型安全性")
async def recommend_single_policy(user: UserData, policy: PolicyData):
    """
    单个政策推荐接口 - 增强类型安全性
    
    Args:
        user: 用户数据
        policy: 政策数据
        
    Returns:
        Dict: 包含状态码、结果和消息
    """
    try:
        user_dict = user.model_dump(exclude_none=False)
        policy_dict = policy.model_dump()
        
        user_id = user_dict.get("用户ID", "Unknown")
        logger.info(f"为用户 {user_id} 计算政策 {policy.政策编号} 的匹配分数")
        
        # 调用核心匹配功能
        score = matcher.calculate_match_score(user_dict, policy_dict)
        
        logger.info(f"用户 {user_id} 与政策 {policy.政策编号} 匹配分数: {score}")
        
        return {
            "status_code": 200,
            "result": score,
            "message": "计算正常，无错误"
        }
        
    except Exception as e:
        logger.error(f"单个政策推荐计算异常: {str(e)}")
        return {
            "status_code": 500,
            "result": 0.0,  # 出错时默认返回0分
            "message": f"单个政策推荐计算出错: {str(e)}"
        }


@app.post("/batch-recommend",
          summary="批量用户推荐",
          description="为多个用户同时进行政策推荐，增强类型安全性")
async def batch_recommend(users: List[UserData], policies: List[PolicyData]):
    """
    批量推荐接口 - 增强类型安全性
    
    Args:
        users: 用户列表
        policies: 政策列表
        
    Returns:
        Dict: 推荐结果
    """
    try:
        # 转换数据格式
        users_dict_list = [user.model_dump(exclude_none=False) for user in users]
        policies_dict_list = [policy.model_dump() for policy in policies]
        
        # 调用核心匹配功能
        all_scores = matcher.multi_user_batch_calculate(users_dict_list, policies_dict_list)
        
        return {
            "status_code": 200,
            "result": all_scores,
            "message": "计算正常，无错误"
        }
        
    except Exception as e:
        logger.error(f"批量推荐计算异常: {str(e)}")
        return {
            "status_code": 500,
            "result": [],
            "message": f"批量推荐计算出错: {str(e)}"
        }


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策推荐API服务...")
    print("📖 API文档地址: http://localhost:8081/docs")
    print("🩺 健康检查: http://localhost:8081/health")
    print("🔧 简化推荐接口: http://localhost:8081/recommend-simple")
    print("✨ 新特性: 模块化架构 + 增强类型安全性")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        app,
        host="10.1.50.96",
        port=8081,
        reload=False,
        log_level="info"
    )