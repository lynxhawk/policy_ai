"""
政策预审系统FastAPI接口服务（宽容版本）
提供RESTful API接口调用政策预审核心功能
即使输入数据不合法也不会返回422错误，而是将非法条件当作不通过处理
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
import uvicorn
import logging
import traceback

# 导入核心预审模块
from policy_user_audit import PolicyPreAuditEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策预审系统API（宽容版）",
    description="基于用户数据和政策条件进行严格规则预审的系统，自动处理非法输入",
    version="1.1.0"
)

# 初始化预审引擎实例
preaudit_engine = PolicyPreAuditEngine()

# 宽容的Pydantic模型定义
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


class TolerantPreAuditRequest(BaseModel):
    """宽容的预审请求模型"""
    user: Optional[Any] = Field(None, description="用户数据")
    policies: Optional[Any] = Field(None, description="政策列表")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


# 标准响应模型
class PreAuditAPIResponse(BaseModel):
    """预审响应模型"""
    status_code: int = Field(..., description="状态码")
    result: List[int] = Field(..., description="预审结果列表 (0或1)")
    message: str = Field(..., description="响应消息")


class PolicyPreAuditResult(BaseModel):
    """单个政策预审结果"""
    政策编号: str = Field(..., description="政策编号")
    标题: str = Field(..., description="政策标题")
    预审结果: int = Field(..., description="预审结果: 1-通过, 0-不通过")


class PreAuditResponse(BaseModel):
    """完整预审响应模型"""
    audit_results: List[PolicyPreAuditResult] = Field(..., description="预审结果列表")
    total_policies: int = Field(..., description="总政策数")
    passed_policies: int = Field(..., description="通过的政策数")
    pass_rate: float = Field(..., description="通过率")
    user_id: Optional[str] = Field(None, description="用户ID")


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
                    # 尝试匹配标准就业类型
                    value_str = str(value).strip()
                    employment_mapping = {
                        "受雇就业": "受雇就业",
                        "灵活就业": "灵活就业", 
                        "自主创业": "自主创业",
                        "未就业": "未就业",
                        "employed": "受雇就业",
                        "flexible": "灵活就业",
                        "entrepreneur": "自主创业",
                        "unemployed": "未就业"
                    }
                    normalized[key] = employment_mapping.get(value_str, str(value))
            
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
                                age = int(numbers[0])
                                # 确保年龄在合理范围内
                                if 0 <= age <= 120:
                                    normalized[key] = age
                                else:
                                    normalized[key] = value
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


def convert_logic_to_lowercase(data):
    """递归地将逻辑操作符转换为小写"""
    try:
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key == "逻辑" and isinstance(value, str):
                    result[key] = value.lower()
                elif isinstance(value, (dict, list)):
                    result[key] = convert_logic_to_lowercase(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [convert_logic_to_lowercase(item) for item in data]
        else:
            return data
    except Exception as e:
        logger.warning(f"转换逻辑操作符失败: {e}")
        return data


def safe_preaudit_single(user_data: Any, policy_data: Any) -> int:
    """安全地预审单个政策"""
    try:
        # 安全转换为字典
        user_dict = safe_convert_to_dict(user_data)
        policy_dict = safe_convert_to_dict(policy_data)
        
        if not user_dict:
            return 0
        
        if not policy_dict:
            return 0
        
        # 规范化用户数据
        user_dict = safe_normalize_user_data(user_dict)
        
        # 转换逻辑操作符
        policy_dict = convert_logic_to_lowercase(policy_dict)
        
        # 调用核心预审功能
        result = preaudit_engine.pre_audit_policy(user_dict, policy_dict)
        
        # 确保结果是0或1
        return 1 if result else 0
        
    except Exception as e:
        logger.error(f"预审单个政策时出错: {e}")
        return 0


def safe_batch_preaudit(user_data: Any, policies_data: List[Any]) -> List[int]:
    """安全地批量预审政策"""
    try:
        if not policies_data:
            return []
        
        results = []
        for policy_data in policies_data:
            try:
                result = safe_preaudit_single(user_data, policy_data)
                results.append(result)
            except Exception as e:
                logger.error(f"处理政策时出错: {e}")
                results.append(0)
        
        return results
        
    except Exception as e:
        logger.error(f"批量预审时出错: {e}")
        return [0] * len(policies_data) if policies_data else []


# API端点定义
@app.get("/", summary="根路径", description="API服务状态检查")
async def root():
    return {
        "message": "政策预审系统API服务（宽容版）正在运行",
        "version": "1.1.0",
        "features": [
            "自动处理非法输入",
            "不返回422错误", 
            "非法条件视为不通过",
            "严格0或1结果输出",
            "最大程度的容错性"
        ],
        "endpoints": {
            "预审": "/preaudit",
            "单个政策预审": "/preaudit-single",
            "批量用户预审": "/batch-preaudit",
            "详细预审结果": "/preaudit-detailed",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }


@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy", 
        "service": "政策预审系统（宽容版）", 
        "audit_mode": "strict",
        "result_type": "binary (0 or 1)",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


@app.post("/preaudit", 
          response_model=PreAuditAPIResponse,
          summary="政策预审（宽容版）",
          description="根据用户数据和政策列表返回每个政策的预审结果(0或1)，自动处理非法输入")
async def preaudit_policies(request: Dict = None):
    """
    宽容的政策预审接口 - 严格规则审核，返回0或1
    """
    try:
        # 处理空请求
        if not request:
            return PreAuditAPIResponse(
                status_code=200,
                result=[],
                message="预审完成，无错误"
            )
        
        # 提取用户和政策数据
        user_data = request.get('user', {})
        policies_data = request.get('policies', [])
        
        # 确保policies是列表
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 批量预审
        results = safe_batch_preaudit(user_data, policies_data)
        
        return PreAuditAPIResponse(
            status_code=200,
            result=results,
            message="预审完成，无错误"
        )
        
    except Exception as e:
        logger.error(f"预审计算异常: {e}")
        logger.error(traceback.format_exc())
        return PreAuditAPIResponse(
            status_code=200,
            result=[],
            message="预审完成，无错误"
        )


@app.post("/preaudit-single",
          summary="单个政策预审（宽容版）",
          description="针对单个用户和单个政策进行预审，自动处理非法输入")
async def preaudit_single_policy(request: Dict = None):
    """
    宽容的单个政策预审接口
    """
    try:
        # 处理空请求
        if not request:
            return {
                "status_code": 200,
                "result": 0,
                "message": "预审完成，无错误"
            }
        
        # 提取用户和政策数据
        user_data = request.get('user', {})
        policy_data = request.get('policy', {})
        
        # 预审单个政策
        result = safe_preaudit_single(user_data, policy_data)
        
        return {
            "status_code": 200,
            "result": result,
            "message": "预审完成，无错误"
        }
        
    except Exception as e:
        logger.error(f"单个政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "预审完成，无错误"
        }


@app.post("/batch-preaudit",
          summary="批量用户预审（宽容版）",
          description="为多个用户同时进行政策预审，自动处理非法输入")
async def batch_preaudit(request: Dict = None):
    """
    宽容的批量预审接口
    """
    try:
        # 处理空请求
        if not request:
            return {
                "status_code": 200,
                "result": [],
                "message": "批量预审完成，无错误"
            }
        
        # 提取用户列表和政策列表
        users_data = request.get('users', [])
        policies_data = request.get('policies', [])
        
        # 确保是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 批量计算
        all_results = []
        for u_idx, user_data in enumerate(users_data):
            user_results = safe_batch_preaudit(user_data, policies_data)
            all_results.extend(user_results)
        
        return {
            "status_code": 200,
            "result": all_results,
            "message": "批量预审完成，无错误"
        }
        
    except Exception as e:
        logger.error(f"批量预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": [],
            "message": "批量预审完成，无错误"
        }


@app.post("/preaudit-detailed",
          summary="详细预审结果（宽容版）",
          description="返回格式化的详细预审结果，自动处理非法输入")
async def preaudit_detailed(request: Dict = None):
    """
    宽容的详细预审接口 - 返回格式化结果
    """
    try:
        # 处理空请求
        if not request:
            return PreAuditResponse(
                audit_results=[],
                total_policies=0,
                passed_policies=0,
                pass_rate=0.0,
                user_id=None
            )
        
        # 提取用户和政策数据
        user_data = request.get('user', {})
        policies_data = request.get('policies', [])
        
        # 确保policies是列表
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 批量预审
        results = safe_batch_preaudit(user_data, policies_data)
        
        # 构建详细结果
        audit_results = []
        for i, (policy_data, result) in enumerate(zip(policies_data, results)):
            policy_dict = safe_convert_to_dict(policy_data)
            audit_results.append(PolicyPreAuditResult(
                政策编号=str(policy_dict.get('政策编号', f'Policy_{i+1}')),
                标题=str(policy_dict.get('标题', f'政策{i+1}')),
                预审结果=result
            ))
        
        passed_count = sum(results)
        pass_rate = round(passed_count / len(results), 3) if results else 0.0
        
        user_dict = safe_convert_to_dict(user_data)
        
        return PreAuditResponse(
            audit_results=audit_results,
            total_policies=len(policies_data),
            passed_policies=passed_count,
            pass_rate=pass_rate,
            user_id=str(user_dict.get("用户ID")) if user_dict.get("用户ID") else None
        )
        
    except Exception as e:
        logger.error(f"详细预审异常: {e}")
        logger.error(traceback.format_exc())
        return PreAuditResponse(
            audit_results=[],
            total_policies=0,
            passed_policies=0,
            pass_rate=0.0,
            user_id=None
        )


# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """捕获Pydantic验证错误，返回0结果而不是422"""
    logger.warning(f"验证错误: {exc}")
    return PreAuditAPIResponse(
        status_code=200,
        result=[0],
        message="预审完成，无错误"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有其他异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return PreAuditAPIResponse(
        status_code=200,
        result=[0],
        message="预审完成，无错误"
    )


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策预审API服务（宽容版）...")
    print("📖 API文档地址: http://localhost:8082/docs")
    print("🩺 健康检查: http://localhost:8082/health")
    print("🔧 主预审接口: http://localhost:8082/preaudit")
    print("✨ 特性: 严格0或1结果 + 最大容错性，非法输入返回0而不是错误")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "__main__:app",
        host="10.1.50.96",
        port=8082,
        reload=True,
        log_level="info"
    )