"""
政策预审系统FastAPI接口服务
提供RESTful API接口调用政策预审核心功能
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
import uvicorn
import logging

# 导入核心预审模块
from policy_user_audit import PolicyPreAuditEngine

# 配置日志
logging.basicConfig(level=logging.DEBUG)  # 改为DEBUG级别
logger = logging.getLogger(__name__)

# 设置预审引擎的日志级别
preaudit_logger = logging.getLogger("PolicyPreAuditEngine")
preaudit_logger.setLevel(logging.DEBUG)

# 初始化FastAPI应用
app = FastAPI(
    title="政策预审系统API",
    description="基于用户数据和政策条件进行严格规则预审的系统",
    version="1.0.0"
)

# 初始化预审引擎实例
preaudit_engine = PolicyPreAuditEngine()

def convert_logic_to_lowercase(data):
    """递归地将逻辑操作符转换为小写"""
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
    IN = "in"
    CONTAINS = "contains"

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
    操作符: OperatorEnum = Field(..., description="操作符：=, !=, >, <, >=, <=, between, in, contains")
    值: Any = Field(..., description="条件值")
    描述: Optional[str] = Field(None, description="条件描述")


class NestedCondition(BaseModel):
    """嵌套条件模型"""
    逻辑: Optional[LogicEnum] = Field(None, description="逻辑关系：AND, OR, NOT")
    规则: Optional[List[Any]] = Field(None, description="规则列表")
    字段: Optional[str] = Field(None, description="字段名")
    操作符: Optional[OperatorEnum] = Field(None, description="操作符：=, !=, >, <, >=, <=, between, in, contains")
    值: Optional[Any] = Field(None, description="值")
    描述: Optional[str] = Field(None, description="描述")

    class Config:
        extra = "allow"
        # 排除None值，避免序列化时产生混乱
        exclude_none = True


class PolicyData(BaseModel):
    """政策数据模型"""
    政策编号: str = Field(..., description="政策编号")
    标题: str = Field(..., description="政策标题")
    条件: NestedCondition = Field(..., description="政策条件")
    类型: Optional[str] = Field(None, description="政策类型")

    class Config:
        extra = "allow"


class PreAuditRequest(BaseModel):
    """预审请求模型"""
    user: UserData = Field(..., description="用户数据")
    policies: List[PolicyData] = Field(..., description="政策列表")


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


class PreAuditSummary(BaseModel):
    """预审统计摘要"""
    总用户数: int = Field(..., description="总用户数")
    总政策数: int = Field(..., description="总政策数")
    总审核数: int = Field(..., description="总审核数")
    总通过数: int = Field(..., description="总通过数")
    总通过率: float = Field(..., description="总通过率")
    用户通过统计: List[Dict] = Field(..., description="用户通过统计")
    政策通过统计: List[Dict] = Field(..., description="政策通过统计")


# API端点定义
@app.get("/", summary="根路径", description="API服务状态检查")
async def root():
    return {
        "message": "政策预审系统API服务正在运行",
        "version": "1.0.0",
        "features": [
            "严格规则预审 (0或1结果)",
            "支持复杂逻辑运算 (AND/OR/NOT)",
            "递归规则评估",
            "短路评估优化",
            "增强类型安全性",
            "详细统计摘要"
        ],
        "endpoints": {
            "预审": "/preaudit",
            "单个政策预审": "/preaudit-single",
            "批量用户预审": "/batch-preaudit",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }


@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy", 
        "service": "政策预审系统", 
        "audit_mode": "strict",
        "result_type": "binary (0 or 1)"
    }


@app.post("/preaudit", 
          response_model=PreAuditAPIResponse,
          summary="政策预审",
          description="根据用户数据和政策列表，返回每个政策的预审结果 (0或1)")
async def preaudit_policies(request: PreAuditRequest):
    """
    政策预审接口 - 严格规则审核
    
    Args:
        request: 包含用户数据和政策列表的请求
        
    Returns:
        PreAuditAPIResponse: 包含状态码、结果列表和消息的响应
    """
    try:
        # 转换用户数据为字典
        user_dict = request.user.model_dump(exclude_none=False)
        
        # 修复枚举值转换问题
        if '就业类型' in user_dict and user_dict['就业类型'] is not None:
            if hasattr(user_dict['就业类型'], 'value'):
                user_dict['就业类型'] = user_dict['就业类型'].value
            else:
                user_dict['就业类型'] = str(user_dict['就业类型'])
        
        # 转换政策数据为字典列表，并转换逻辑操作符为小写
        policies_dict_list = []
        for policy in request.policies:
            policy_dict = policy.model_dump(exclude_none=True)  # 排除None值
            policy_dict = convert_logic_to_lowercase(policy_dict)
            policies_dict_list.append(policy_dict)
        
        # 调用核心预审功能
        results = preaudit_engine.batch_pre_audit(user_dict, policies_dict_list)
        
        return PreAuditAPIResponse(
            status_code=200,
            result=results,
            message="预审完成，无错误"
        )
        
    except Exception as e:
        logger.error(f"预审计算异常: {str(e)}")
        return PreAuditAPIResponse(
            status_code=500,
            result=[],
            message=f"预审计算出错: {str(e)}"
        )


@app.post("/preaudit-single",
          summary="单个政策预审",
          description="针对单个用户和单个政策进行预审")
async def preaudit_single_policy(user: UserData, policy: PolicyData):
    """
    单个政策预审接口
    
    Args:
        user: 用户数据
        policy: 政策数据
        
    Returns:
        Dict: 包含状态码、结果和消息
    """
    try:
        user_dict = user.model_dump(exclude_none=False)
        policy_dict = policy.model_dump(exclude_none=True)  # 排除None值
        policy_dict = convert_logic_to_lowercase(policy_dict)
        
        # 修复枚举值转换问题
        if '就业类型' in user_dict and user_dict['就业类型'] is not None:
            if hasattr(user_dict['就业类型'], 'value'):
                user_dict['就业类型'] = user_dict['就业类型'].value
            else:
                user_dict['就业类型'] = str(user_dict['就业类型'])
        
        user_id = user_dict.get("用户ID", "Unknown")
        logger.info(f"为用户 {user_id} 预审政策 {policy.政策编号}")
        
        # 添加详细调试信息
        print("=" * 80)
        print("🔍 单个政策预审调试信息")
        print("=" * 80)
        print(f"用户数据:")
        for key, value in user_dict.items():
            print(f"  {key}: {repr(value)} (类型: {type(value).__name__})")
        
        print(f"\n政策条件:")
        conditions = policy_dict.get('条件', {}).get('规则', [])
        for i, cond in enumerate(conditions):
            field = cond.get('字段')
            operator = cond.get('操作符') 
            value = cond.get('值')
            print(f"  条件{i+1}: {field} {operator} {repr(value)} (值类型: {type(value).__name__})")
        print("=" * 80)
        
        # 调用核心预审功能
        result = preaudit_engine.pre_audit_policy(user_dict, policy_dict)
        
        # 手动测试每个条件
        print("\n🧪 手动测试每个条件:")
        conditions = policy_dict.get('条件', {}).get('规则', [])
        for i, cond in enumerate(conditions):
            field = cond.get('字段')
            operator = cond.get('操作符')
            value = cond.get('值')
            
            if field in user_dict:
                user_value = user_dict[field]
                manual_result = preaudit_engine.check_condition(user_value, operator, value)
                print(f"  条件{i+1}: {field}({user_value}) {operator} {value} = {manual_result}")
            else:
                print(f"  条件{i+1}: 字段{field}不存在 = False")
        
        print("=" * 80)
        
        logger.info(f"用户 {user_id} 政策 {policy.政策编号} 预审结果: {result}")
        
        return {
            "status_code": 200,
            "result": result,
            "message": "预审完成，无错误"
        }
        
    except Exception as e:
        logger.error(f"单个政策预审异常: {str(e)}")
        return {
            "status_code": 500,
            "result": 0,  # 出错时默认不通过
            "message": f"单个政策预审出错: {str(e)}"
        }


@app.post("/batch-preaudit",
          summary="批量用户预审",
          description="为多个用户同时进行政策预审")
async def batch_preaudit(users: List[UserData], policies: List[PolicyData]):
    """
    批量预审接口
    
    Args:
        users: 用户列表
        policies: 政策列表
        
    Returns:
        Dict: 预审结果
    """
    try:
        # 转换数据格式
        users_dict_list = []
        for user in users:
            user_dict = user.model_dump(exclude_none=False)
            
            # 修复枚举值转换问题
            if '就业类型' in user_dict and user_dict['就业类型'] is not None:
                if hasattr(user_dict['就业类型'], 'value'):
                    user_dict['就业类型'] = user_dict['就业类型'].value
                else:
                    user_dict['就业类型'] = str(user_dict['就业类型'])
            
            users_dict_list.append(user_dict)
        
        policies_dict_list = []
        for policy in policies:
            policy_dict = policy.model_dump(exclude_none=True)  # 排除None值
            policy_dict = convert_logic_to_lowercase(policy_dict)
            policies_dict_list.append(policy_dict)
        
        # 调用核心预审功能
        all_results = preaudit_engine.multi_user_batch_pre_audit(users_dict_list, policies_dict_list)
        
        # 展平结果列表
        flat_results = []
        for user_results in all_results:
            flat_results.extend(user_results)
        
        return {
            "status_code": 200,
            "result": flat_results,
            "message": "批量预审完成，无错误"
        }
        
    except Exception as e:
        logger.error(f"批量预审异常: {str(e)}")
        return {
            "status_code": 500,
            "result": [],
            "message": f"批量预审出错: {str(e)}"
        }


@app.post("/preaudit-detailed",
          response_model=PreAuditResponse,
          summary="详细预审结果",
          description="返回格式化的详细预审结果")
async def preaudit_detailed(request: PreAuditRequest):
    """
    详细预审接口 - 返回格式化结果
    
    Args:
        request: 包含用户数据和政策列表的请求
        
    Returns:
        PreAuditResponse: 详细的预审结果
    """
    try:
        # 转换用户数据为字典
        user_dict = request.user.model_dump(exclude_none=False)
        
        # 修复枚举值转换问题
        if '就业类型' in user_dict and user_dict['就业类型'] is not None:
            if hasattr(user_dict['就业类型'], 'value'):
                user_dict['就业类型'] = user_dict['就业类型'].value
            else:
                user_dict['就业类型'] = str(user_dict['就业类型'])
        
        # 转换政策数据为字典列表，并转换逻辑操作符为小写
        policies_dict_list = []
        for policy in request.policies:
            policy_dict = policy.model_dump(exclude_none=True)  # 排除None值
            policy_dict = convert_logic_to_lowercase(policy_dict)
            policies_dict_list.append(policy_dict)
        
        # 调用核心预审功能
        results = preaudit_engine.batch_pre_audit(user_dict, policies_dict_list)
        
        # 构建详细结果
        audit_results = []
        for i, (policy, result) in enumerate(zip(request.policies, results)):
            audit_results.append(PolicyPreAuditResult(
                政策编号=policy.政策编号,
                标题=policy.标题,
                预审结果=result
            ))
        
        passed_count = sum(results)
        pass_rate = round(passed_count / len(results), 3) if results else 0.0
        
        return PreAuditResponse(
            audit_results=audit_results,
            total_policies=len(request.policies),
            passed_policies=passed_count,
            pass_rate=pass_rate,
            user_id=user_dict.get("用户ID")
        )
        
    except Exception as e:
        logger.error(f"详细预审异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"详细预审出错: {str(e)}")


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策预审API服务...")
    print("📖 API文档地址: http://localhost:8082/docs")
    print("🩺 健康检查: http://localhost:8082/health")
    print("🔧 主预审接口: http://localhost:8082/preaudit")
    print("✨ 特性: 严格规则预审 + 复杂逻辑运算")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "__main__:app",  # 使用导入字符串而不是app对象
        host="10.1.50.96",
        port=8082,
        reload=True,
        log_level="info"
    )