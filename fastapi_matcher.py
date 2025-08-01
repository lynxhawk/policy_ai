from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Union
import uvicorn
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# 推荐系统核心逻辑类
class RecommendationEngine:
    
    @staticmethod
    def safe_type_conversion(value: Any, target_type: str = "auto") -> Any:
        """
        安全的类型转换，失败时返回None
        
        Args:
            value: 需要转换的值
            target_type: 目标类型 ("int", "float", "str", "auto")
            
        Returns:
            转换后的值，失败时返回None
        """
        if value is None:
            return None
            
        try:
            if target_type == "int":
                return int(float(str(value)))
            elif target_type == "float":
                return float(str(value))
            elif target_type == "str":
                return str(value)
            else:  # auto
                # 尝试自动推断类型
                str_value = str(value).strip()
                
                # 尝试转换为数字
                if str_value.replace('.', '').replace('-', '').isdigit():
                    if '.' in str_value:
                        return float(str_value)
                    else:
                        return int(str_value)
                
                return str_value
                
        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(f"类型转换失败: {value} -> {target_type}, 错误: {e}")
            return None
    
    @staticmethod
    def extract_numeric_value(value: Any) -> Optional[float]:
        """
        从值中提取数字，支持带单位的字符串如"2年"、"25岁"等
        
        Args:
            value: 输入值
            
        Returns:
            提取的数字，失败时返回None
        """
        if value is None:
            return None
            
        try:
            # 如果已经是数字类型
            if isinstance(value, (int, float)):
                return float(value)
                
            # 字符串处理
            str_value = str(value).strip()
            
            # 提取数字部分
            import re
            numbers = re.findall(r'-?\d+\.?\d*', str_value)
            
            if numbers:
                return float(numbers[0])
            
            return None
            
        except (ValueError, TypeError) as e:
            logger.warning(f"数字提取失败: {value}, 错误: {e}")
            return None
    
    @staticmethod
    def check_condition(user_value: Any, operator: str, condition_value: Any) -> bool:
        """
        检查单个条件是否匹配，增强类型安全性
        
        Args:
            user_value: 用户数据值
            operator: 操作符
            condition_value: 条件值
            
        Returns:
            是否匹配，类型不匹配时返回False
        """
        # 如果用户值为None或空，直接返回False
        if user_value is None or user_value == "":
            logger.debug(f"用户值为空: {user_value}")
            return False
            
        try:
            # between 操作符处理
            if operator == 'between':
                if isinstance(condition_value, list) and len(condition_value) == 2:
                    user_val = RecommendationEngine.extract_numeric_value(user_value)
                    min_val = RecommendationEngine.extract_numeric_value(condition_value[0])
                    max_val = RecommendationEngine.extract_numeric_value(condition_value[1])
                    
                    if user_val is None or min_val is None or max_val is None:
                        logger.warning(f"between操作符类型转换失败: user={user_value}, range={condition_value}")
                        return False
                        
                    return min_val <= user_val <= max_val
                else:
                    logger.warning(f"between操作符条件值格式错误: {condition_value}")
                    return False
                    
            # 数字比较操作符
            elif operator in ['>', '<', '>=', '<=']:
                user_val = RecommendationEngine.extract_numeric_value(user_value)
                condition_val = RecommendationEngine.extract_numeric_value(condition_value)
                
                if user_val is None or condition_val is None:
                    logger.warning(f"数字比较类型转换失败: user={user_value}, condition={condition_value}")
                    return False
                
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
                # 安全的字符串转换
                user_str = RecommendationEngine.safe_type_conversion(user_value, "str")
                condition_str = RecommendationEngine.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    logger.warning(f"字符串比较转换失败: user={user_value}, condition={condition_value}")
                    return False
                    
                return user_str == condition_str
                
            elif operator == '!=':
                # 安全的字符串转换
                user_str = RecommendationEngine.safe_type_conversion(user_value, "str")
                condition_str = RecommendationEngine.safe_type_conversion(condition_value, "str")
                
                if user_str is None or condition_str is None:
                    logger.warning(f"字符串比较转换失败: user={user_value}, condition={condition_value}")
                    return False
                    
                return user_str != condition_str
            
            else:
                logger.warning(f"不支持的操作符: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"条件检查异常: user={user_value}, operator={operator}, condition={condition_value}, 错误: {e}")
            return False
    
    @staticmethod
    def extract_all_conditions(condition_node: Dict) -> List[Dict]:
        """递归提取所有条件规则，忽略逻辑关系"""
        conditions = []
        
        try:
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
                    
        except Exception as e:
            logger.error(f"提取条件规则异常: {condition_node}, 错误: {e}")
        
        return conditions
    
    @staticmethod
    def calculate_match_score(user_data: Dict, policy_data: Dict) -> float:
        """
        计算用户与政策的匹配分数，返回0-1之间的匹配率
        增强类型安全性，类型不匹配时返回0
        
        Args:
            user_data: 用户数据字典
            policy_data: 政策数据字典
            
        Returns:
            匹配分数 (0.0-1.0)，出错时返回0.0
        """
        try:
            matched_conditions = 0
            total_conditions = 0
            
            # 处理嵌套条件结构
            condition_root = policy_data.get("条件", {})
            
            # 提取所有条件规则（忽略逻辑关系）
            all_conditions = RecommendationEngine.extract_all_conditions(condition_root)
            total_conditions = len(all_conditions)
            
            if total_conditions == 0:
                logger.warning(f"政策 {policy_data.get('政策编号', 'Unknown')} 没有条件规则")
                return 0.0
            
            for condition in all_conditions:
                try:
                    field = condition.get("字段")
                    operator = condition.get("操作符")
                    value = condition.get("值")
                    
                    if not field or not operator:
                        logger.warning(f"条件缺少必要字段: {condition}")
                        continue
                    
                    if field in user_data:
                        user_value = user_data[field]
                        
                        if RecommendationEngine.check_condition(user_value, operator, value):
                            matched_conditions += 1
                    else:
                        logger.debug(f"用户数据中缺少字段: {field}")
                        
                except Exception as e:
                    logger.error(f"处理单个条件异常: {condition}, 错误: {e}")
                    continue
            
            # 返回匹配率（0-1之间的浮点数）
            score = matched_conditions / total_conditions
            return round(score, 1)
            
        except Exception as e:
            logger.error(f"计算匹配分数异常: 用户={user_data.get('用户ID', 'Unknown')}, 政策={policy_data.get('政策编号', 'Unknown')}, 错误: {e}")
            return 0.0

# API端点
@app.get("/", summary="根路径", description="API服务状态检查")
async def root():
    return {
        "message": "政策推荐系统API服务正在运行",
        "version": "1.0.0",
        "features": [
            "增强类型安全性",
            "自动处理类型不匹配",
            "详细错误日志记录",
            "数字提取支持（如：25岁、2年经验）"
        ],
        "endpoints": {
            "推荐": "/recommend",
            "简化推荐": "/recommend-simple",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }

@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {"status": "healthy", "service": "政策推荐系统", "type_safety": "enabled"}

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
        
        # 记录用户ID用于调试
        user_id = user_dict.get("用户ID", "Unknown")
        logger.info(f"开始为用户 {user_id} 计算 {len(request.policies)} 个政策的匹配分数")
        
        # 计算每个政策的匹配分数（按输入顺序）
        scores = []
        
        for i, policy in enumerate(request.policies):
            try:
                policy_dict = policy.model_dump()
                score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
                scores.append(score)
                
                logger.debug(f"政策 {policy.政策编号} 匹配分数: {score}")
                
            except Exception as e:
                logger.error(f"计算第 {i+1} 个政策匹配分数失败: {e}")
                scores.append(0.0)  # 出错时默认返回0分
        
        logger.info(f"用户 {user_id} 匹配计算完成，平均分数: {sum(scores)/len(scores):.2f}")
        
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
        
        # 记录用户ID用于调试
        user_id = user_dict.get("用户ID", "Unknown")
        logger.info(f"开始为用户 {user_id} 计算 {len(request.policies)} 个政策的匹配分数")
        
        # 计算每个政策的匹配分数（按输入顺序）
        scores = []
        
        for i, policy in enumerate(request.policies):
            try:
                policy_dict = policy.model_dump()
                score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
                scores.append(score)
                
                logger.debug(f"政策 {policy.政策编号} 匹配分数: {score}")
                
            except Exception as e:
                logger.error(f"计算第 {i+1} 个政策匹配分数失败: {e}")
                scores.append(0.0)  # 出错时默认返回0分
        
        logger.info(f"用户 {user_id} 匹配计算完成，平均分数: {sum(scores)/len(scores):.2f}")
        
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
        
        score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
        
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
        all_scores = []
        
        logger.info(f"开始批量推荐：{len(users)} 个用户，{len(policies)} 个政策")
        
        for user_idx, user in enumerate(users):
            try:
                user_dict = user.model_dump(exclude_none=False)
                user_id = user_dict.get("用户ID", f"User_{user_idx}")
                
                # 计算每个政策的匹配分数
                for policy_idx, policy in enumerate(policies):
                    try:
                        policy_dict = policy.model_dump()
                        score = RecommendationEngine.calculate_match_score(user_dict, policy_dict)
                        all_scores.append(score)
                        
                    except Exception as e:
                        logger.error(f"用户 {user_id} 计算政策 {policy_idx} 失败: {e}")
                        all_scores.append(0.0)  # 出错时默认返回0分
                        
            except Exception as e:
                logger.error(f"处理第 {user_idx} 个用户失败: {e}")
                # 为该用户的所有政策添加0分
                all_scores.extend([0.0] * len(policies))
        
        logger.info(f"批量推荐完成，生成 {len(all_scores)} 个分数")
        
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
    print("✨ 新特性: 增强类型安全性，自动处理类型不匹配")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8081,
        reload=False,
        log_level="info"
    )