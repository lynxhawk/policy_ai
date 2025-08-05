"""
政策推荐系统FastAPI接口服务
提供RESTful API接口调用政策用户匹配核心功能
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
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

# 枚举定义
class YesNoEnum(str, Enum):
    """是否枚举"""
    YES = "是"
    NO = "否"

class EmploymentTypeEnum(str, Enum):
    """就业类型枚举"""
    EMPLOYED = "受雇就业"
    FLEXIBLE = "灵活就业"
    ENTREPRENEUR = "自主创业"
    UNEMPLOYED = "未就业"

class LogicEnum(str, Enum):
    """逻辑关系枚举"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

class OperatorEnum(str, Enum):
    """操作符枚举"""
    EQUAL = "="
    NOT_EQUAL = "!="
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    BETWEEN = "between"

# Pydantic模型定义
class UserData(BaseModel):
    """用户数据模型"""
    用户ID: Optional[str] = Field(None, description="用户ID")
    最高学历: Optional[str] = Field(None, description="最高学历")
    毕业时间: Optional[Any] = Field(None, description="毕业时间")
    籍贯: Optional[str] = Field(None, description="籍贯")
    专业: Optional[str] = Field(None, description="专业名称")
    技能等级: Optional[str] = Field(None, description="技能等级")
    
    # 是否字段 - 严格限制为"是"或"否"
    征地人员: Optional[str] = Field(None, description="是否为征地人员：是/否")
    缴纳社保: Optional[str] = Field(None, description="是否缴纳社保：是/否")
    养老保险: Optional[str] = Field(None, description="是否有养老保险：是/否")
    困难人员: Optional[str] = Field(None, description="是否为困难人员：是/否")
    
    # 就业类型 - 严格限制为四个值
    就业类型: Optional[EmploymentTypeEnum] = Field(None, description="就业类型：受雇就业/灵活就业/自主创业/未就业")
    
    # 年龄 - 限制为合理范围
    年龄: Optional[int] = Field(None, ge=0, le=120, description="年龄，0-120岁")
    
    工作经历: Optional[List[Dict]] = Field(None, description="工作经历")

    class Config:
        # 允许额外字段
        extra = "allow"
    
    @field_validator('征地人员', '缴纳社保', '养老保险', '困难人员')
    @classmethod
    def validate_yes_no_fields(cls, v):
        """验证是否字段，支持多种输入格式但统一转换为标准格式"""
        if v is None:
            return v
            
        # 支持的"是"的表示方法
        yes_values = ["是", "yes", "YES", "Yes", "true", "True", "TRUE", "1", "有", "对"]
        # 支持的"否"的表示方法  
        no_values = ["否", "no", "NO", "No", "false", "False", "FALSE", "0", "无", "不是", "没有"]
        
        v_str = str(v).strip()  # 去除空格
        
        if v_str in yes_values:
            return "是"
        elif v_str in no_values:
            return "否"
        else:
            raise ValueError(
                f'字段值必须表示"是"或"否"。'
                f'支持的"是"：{", ".join(yes_values[:5])}等；'
                f'支持的"否"：{", ".join(no_values[:5])}等。'
                f'当前值：{v}'
            )
    
    @field_validator('年龄', mode='before')
    @classmethod
    def validate_age(cls, v):
        """验证年龄字段，支持从"25岁"等格式中提取数字"""
        if v is None:
            return v
            
        # 如果已经是数字类型
        if isinstance(v, (int, float)):
            return int(v)
            
        # 字符串处理 - 提取数字
        if isinstance(v, str):
            import re
            v_str = v.strip()
            numbers = re.findall(r'\d+', v_str)
            
            if numbers:
                age = int(numbers[0])
                if age < 0 or age > 120:
                    raise ValueError('年龄必须在0-120岁之间')
                return age
            else:
                raise ValueError(f'无法从"{v}"中提取有效的年龄数字')
        
        raise ValueError(f'年龄格式不正确：{v}')
    
    @field_validator('毕业时间', mode='before')
    @classmethod
    def validate_graduation_time(cls, v):
        """验证毕业时间字段，支持多种格式并统一处理"""
        if v is None:
            return v
            
        # 如果已经是数字类型，直接返回
        if isinstance(v, (int, float)):
            return int(v)
            
        # 字符串处理
        if isinstance(v, str):
            import re
            v_str = v.strip()
            
            # 尝试提取数字（支持"2年"、"2"等格式）
            numbers = re.findall(r'\d+', v_str)
            
            if numbers:
                return int(numbers[0])
            else:
                # 如果无法提取数字，尝试直接转换
                try:
                    return int(v_str)
                except ValueError:
                    raise ValueError(f'无法从"{v}"中提取有效的毕业时间')
        
        # 其他类型尝试直接转换
        try:
            return int(v)
        except (ValueError, TypeError):
            raise ValueError(f'毕业时间格式不正确：{v}')


class ConditionRule(BaseModel):
    """条件规则模型"""
    字段: str = Field(..., description="匹配字段名")
    操作符: OperatorEnum = Field(..., description="操作符：=, !=, >, <, >=, <=, between")
    值: Any = Field(..., description="条件值")
    描述: Optional[str] = Field(None, description="条件描述")


class NestedCondition(BaseModel):
    """嵌套条件模型"""
    逻辑: Optional[LogicEnum] = Field(None, description="逻辑关系：AND, OR")
    规则: Optional[List[Any]] = Field(None, description="规则列表")
    字段: Optional[str] = Field(None, description="字段名")
    操作符: Optional[OperatorEnum] = Field(None, description="操作符：=, !=, >, <, >=, <=, between")
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


# 标准响应模型
class RecommendationAPIResponse(BaseModel):
    """推荐响应模型"""
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
            "模块化架构设计",
            "严格字段校验（是否、就业类型、年龄、逻辑、操作符）"
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
        "service": "政策推荐系统", 
        "type_safety": "enabled",
        "architecture": "modular"
    }


@app.post("/recommend", 
          response_model=RecommendationAPIResponse,
          summary="政策推荐",
          description="根据用户数据和政策列表，返回每个政策的匹配分数，增强类型安全性")
async def recommend_policies(request: RecommendationRequest):
    """
    政策推荐接口 - 增强类型安全性
    
    Args:
        request: 包含用户数据和政策列表的请求
        
    Returns:
        RecommendationAPIResponse: 包含状态码、分数列表和消息的响应
    """
    try:
        # 转换用户数据为字典
        user_dict = request.user.model_dump(exclude_none=False)
        
        # 🔧 修复枚举值转换问题
        # 确保枚举类型被正确转换为字符串值
        if '就业类型' in user_dict and user_dict['就业类型'] is not None:
            if hasattr(user_dict['就业类型'], 'value'):
                user_dict['就业类型'] = user_dict['就业类型'].value
            else:
                user_dict['就业类型'] = str(user_dict['就业类型'])
        
        # 转换政策数据为字典列表
        policies_dict_list = [policy.model_dump() for policy in request.policies]
        
        # 🔍 添加详细调试信息
        print("=" * 80)
        print("🚀 FastAPI接口调试信息")
        print("=" * 80)
        
        print("📥 接收到的用户数据:")
        for key, value in user_dict.items():
            if key in ['毕业时间', '就业类型', '养老保险']:  # 重点关注这几个字段
                print(f"  ⭐ {key}: {repr(value)} (类型: {type(value).__name__})")
            else:
                print(f"     {key}: {repr(value)} (类型: {type(value).__name__})")
        
        print(f"\n📋 政策数据 (共{len(policies_dict_list)}个):")
        for i, policy in enumerate(policies_dict_list):
            print(f"  政策{i+1}: {policy.get('政策编号')} - {policy.get('标题')}")
            
            # 显示条件详情
            conditions = policy.get('条件', {}).get('规则', [])
            print(f"    条件数量: {len(conditions)}")
            for j, cond in enumerate(conditions):
                field = cond.get('字段')
                operator = cond.get('操作符')
                value = cond.get('值')
                print(f"    条件{j+1}: {field} {operator} {repr(value)} (值类型: {type(value).__name__})")
        
        print("\n🔄 开始调用核心匹配算法...")
        print("=" * 80)
        
        # 调用核心匹配功能
        scores = matcher.batch_calculate_match_scores(user_dict, policies_dict_list)
        
        print("=" * 80)
        print(f"🎯 FastAPI接口最终结果: {scores}")
        print("=" * 80)
        
        return RecommendationAPIResponse(
            status_code=200,
            result=scores,
            message="计算正常，无错误"
        )
        
    except Exception as e:
        logger.error(f"推荐计算异常: {str(e)}")
        return RecommendationAPIResponse(
            status_code=500,
            result=[],
            message=f"推荐计算出错: {str(e)}"
        )


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
        users_dict_list = []
        for user in users:
            user_dict = user.model_dump(exclude_none=False)
            
            # 🔧 修复枚举值转换问题
            if '就业类型' in user_dict and user_dict['就业类型'] is not None:
                if hasattr(user_dict['就业类型'], 'value'):
                    user_dict['就业类型'] = user_dict['就业类型'].value
                else:
                    user_dict['就业类型'] = str(user_dict['就业类型'])
            
            users_dict_list.append(user_dict)
        
        policies_dict_list = [policy.model_dump() for policy in policies]
        
        # 🔍 添加批量调试信息
        print("=" * 80)
        print("🚀 批量推荐接口调试信息")
        print("=" * 80)
        
        print(f"📥 接收到 {len(users_dict_list)} 个用户:")
        for i, user_dict in enumerate(users_dict_list):
            user_id = user_dict.get('用户ID', f'User_{i}')
            print(f"  用户{i+1} ({user_id}):")
            for key, value in user_dict.items():
                if key in ['毕业时间', '就业类型', '养老保险']:
                    print(f"    ⭐ {key}: {repr(value)} (类型: {type(value).__name__})")
        
        print(f"\n📋 政策数据 (共{len(policies_dict_list)}个):")
        for i, policy in enumerate(policies_dict_list):
            print(f"  政策{i+1}: {policy.get('政策编号')}")
            conditions = policy.get('条件', {}).get('规则', [])
            for j, cond in enumerate(conditions):
                field = cond.get('字段')
                operator = cond.get('操作符')
                value = cond.get('值')
                print(f"    条件{j+1}: {field} {operator} {repr(value)}")
        
        print("\n🔄 开始批量匹配计算...")
        print("=" * 80)
        
        # 调用核心匹配功能
        all_scores = matcher.multi_user_batch_calculate(users_dict_list, policies_dict_list)
        
        print("=" * 80)
        print(f"🎯 批量推荐最终结果: {all_scores}")
        print(f"📊 结果解释:")
        for i, score in enumerate(all_scores):
            user_idx = i // len(policies_dict_list)
            policy_idx = i % len(policies_dict_list)
            user_id = users_dict_list[user_idx].get('用户ID', f'User_{user_idx}')
            policy_id = policies_dict_list[policy_idx].get('政策编号', f'Policy_{policy_idx}')
            print(f"  用户{user_id} vs 政策{policy_id}: {score}")
        print("=" * 80)
        
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
    print("🔧 主推荐接口: http://localhost:8081/recommend")
    print("✨ 新特性: 模块化架构 + 增强类型安全性")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "__main__:app",  # 使用导入字符串而不是app对象
        host="10.1.50.96",
        port=8081,
        reload=True,
        log_level="info"
    )