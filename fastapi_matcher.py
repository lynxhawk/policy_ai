from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import uvicorn

app = FastAPI(
    title="政策推荐系统API",
    description="基于用户数据和政策条件进行匹配评分的推荐系统",
    version="1.0.0"
)

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

class RecommendationResponse(BaseModel):
    """推荐响应模型"""
    recommendations: Dict[str, int] = Field(..., description="政策名称:匹配分数的字典")
    total_policies: int = Field(..., description="总政策数")
    user_id: Optional[str] = Field(None, description="用户ID")

# 推荐系统核心逻辑类
class RecommendationEngine:
    
    @staticmethod
    def check_condition(user_value: Any, operator: str, condition_value: Any) -> bool:
        """检查单个条件是否匹配"""
        if user_value is None:
            return False
            
        try:
            # between 操作符处理
            if operator == 'between':
                if isinstance(condition_value, list) and len(condition_value) == 2:
                    user_val = float(user_value)
                    min_val = float(condition_value[0])
                    max_val = float(condition_value[1])
                    return min_val <= user_val <= max_val
                return False
                
            # 数字比较
            elif operator in ['>', '<', '>=', '<=']:
                user_val = float(user_value)
                # 处理可能包含单位的字符串，如 "2年"
                condition_str = str(condition_value)
                condition_val = float(''.join(filter(str.isdigit, condition_str))) if condition_str else 0
                
                if operator == '>':
                    return user_val > condition_val
                elif operator == '<':
                    return user_val < condition_val
                elif operator == '>=':
                    return user_val >= condition_val
                elif operator == '<=':
                    return user_val <= condition_val
                    
            # 字符串比较
            elif operator == '=':
                return str(user_value) == str(condition_value)
            elif operator == '!=':
                return str(user_value) != str(condition_value)
                
        except (ValueError, TypeError):
            # 如果转换失败，按字符串处理
            if operator == '=':
                return str(user_value) == str(condition_value)
            elif operator == '!=':
                return str(user_value) != str(condition_value)
                
        return False
    
    @staticmethod
    def extract_all_conditions(condition_node: Dict) -> List[Dict]:
        """递归提取所有条件规则，忽略逻辑关系"""
        conditions = []
        
        # 如果有 "规则" 字段，说明是容器节点
        if "规则" in condition_node:
            rules = condition_node["规则"]
            if isinstance(rules, list):
                for rule in rules:
                    # 递归处理每个规则
                    conditions.extend(RecommendationEngine.extract_all_conditions(rule))
        else:
            # 如果包含字段、操作符、值，说明是叶子节点（实际条件）
            if all(key in condition_node for key in ["字段", "操作符", "值"]):
                conditions.append(condition_node)
        
        return conditions
    
    @staticmethod
    def calculate_match_score(user_data: Dict, policy_data: Dict) -> int:
        """计算用户与政策的匹配分数"""
        score = 0
        
        # 处理嵌套条件结构
        condition_root = policy_data.get("条件", {})
        
        # 提取所有条件规则（忽略逻辑关系）
        all_conditions = RecommendationEngine.extract_all_conditions(condition_root)
        
        for condition in all_conditions:
            field = condition.get("字段")
            operator = condition.get("操作符")
            value = condition.get("值")
            
            if field in user_data:
                user_value = user_data[field]
                
                if RecommendationEngine.check_condition(user_value, operator, value):
                    score += 1
                    
        return score

# API端点
@app.get("/", summary="根路径", description="API服务状态检查")
async def root():
    return {
        "message": "政策推荐系统API服务正在运行",
        "version": "1.0.0",
        "endpoints": {
            "推荐": "/recommend",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }

@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {"status": "healthy", "service": "政策推荐系统"}

@app.post("/recommend", 
          response_model=RecommendationResponse,
          summary="政策推荐",
          description="根据用户数据和政策列表，返回每个政策的匹配分数")
async def recommend_policies(request: RecommendationRequest):
    """
    政策推荐接口
    
    Args:
        request: 包含用户数据和政策列表的请求
        
    Returns:
        RecommendationResponse: 包含政策名称和匹配分数的响应
    """
    try:
        # 转换用户数据为字典
        user_dict = request.user.dict(exclude_none=False)
        
        # 计算每个政策的匹配分数
        recommendations = {}
        
        for policy in request.policies:
            policy_dict = policy.dict()
            score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
            policy_title = policy.标题
            recommendations[policy_title] = score
        
        # 按分数降序排序
        sorted_recommendations = dict(sorted(recommendations.items(), 
                                           key=lambda x: x[1], reverse=True))
        
        return RecommendationResponse(
            recommendations=sorted_recommendations,
            total_policies=len(request.policies),
            user_id=request.user.用户ID
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐计算出错: {str(e)}")

@app.post("/recommend-single",
          summary="单个政策推荐",
          description="针对单个用户和单个政策进行匹配评分")
async def recommend_single_policy(user: UserData, policy: PolicyData):
    """
    单个政策推荐接口
    
    Args:
        user: 用户数据
        policy: 政策数据
        
    Returns:
        Dict: 包含政策标题和匹配分数
    """
    try:
        user_dict = user.dict(exclude_none=False)
        policy_dict = policy.dict()
        
        score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
        
        return {
            "政策标题": policy.标题,
            "政策编号": policy.政策编号,
            "匹配分数": score,
            "用户ID": user.用户ID
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"单个政策推荐计算出错: {str(e)}")

@app.post("/batch-recommend",
          summary="批量用户推荐",
          description="为多个用户同时进行政策推荐")
async def batch_recommend(users: List[UserData], policies: List[PolicyData]):
    """
    批量推荐接口
    
    Args:
        users: 用户列表
        policies: 政策列表
        
    Returns:
        Dict: 每个用户的推荐结果
    """
    try:
        batch_results = {}
        
        for user in users:
            user_dict = user.dict(exclude_none=False)
            user_recommendations = {}
            
            for policy in policies:
                policy_dict = policy.dict()
                score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
                user_recommendations[policy.标题] = score
            
            # 按分数降序排序
            sorted_recs = dict(sorted(user_recommendations.items(), 
                                    key=lambda x: x[1], reverse=True))
            
            user_id = user.用户ID or f"未知用户_{len(batch_results)}"
            batch_results[user_id] = sorted_recs
        
        return {
            "批量推荐结果": batch_results,
            "处理用户数": len(users),
            "政策数": len(policies)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量推荐计算出错: {str(e)}")

if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        app,  # 直接传入app对象
        host="127.0.0.1",
        port=8081,
        reload=False,
        log_level="info"
    )