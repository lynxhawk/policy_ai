"""
企业政策预审系统FastAPI接口服务（宽容版本）
提供RESTful API接口调用企业政策预审核心功能
即使输入数据不合法也不会返回422错误，而是将非法条件当作不通过处理
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
import uvicorn
import logging
import traceback

# 导入企业预审模块
from enterprise_policy_preaudit import EnterprisePreAuditEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="企业政策预审系统API（宽容版）",
    description="基于企业数据和企业政策条件进行严格规则预审的系统，自动处理非法输入",
    version="1.1.0"
)

# 初始化企业预审引擎实例
enterprise_preaudit_engine = EnterprisePreAuditEngine()

# 宽容的Pydantic模型定义
class TolerantEnterpriseData(BaseModel):
    """宽容的企业数据模型 - 接受任何输入"""
    企业ID: Optional[Any] = Field(None, description="企业ID")
    企业名称: Optional[Any] = Field(None, description="企业名称")
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

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


class TolerantEnterprisePreAuditRequest(BaseModel):
    """宽容的企业预审请求模型"""
    enterprise: Optional[Any] = Field(None, description="企业数据")
    policies: Optional[Any] = Field(None, description="政策列表")

    class Config:
        extra = "allow"
        validate_assignment = False
        arbitrary_types_allowed = True


# 标准响应模型
class EnterprisePreAuditAPIResponse(BaseModel):
    """企业预审响应模型"""
    status_code: int = Field(..., description="状态码")
    result: List[int] = Field(..., description="预审结果列表 (0或1)")
    message: str = Field(..., description="响应消息")
    enterprise_id: Optional[str] = Field(None, description="企业ID")
    total_policies: Optional[int] = Field(None, description="总政策数")
    enterprise_policies: Optional[int] = Field(None, description="企业政策数")
    passed_policies: Optional[int] = Field(None, description="通过的政策数")


class EnterprisePolicyPreAuditResult(BaseModel):
    """单个企业政策预审结果"""
    政策编号: str = Field(..., description="政策编号")
    标题: str = Field(..., description="政策标题")
    政策类型: str = Field(..., description="政策类型")
    预审结果: int = Field(..., description="预审结果: 1-通过, 0-不通过")
    预审状态: str = Field(..., description="预审状态描述")


class EnterprisePreAuditResponse(BaseModel):
    """完整企业预审响应模型"""
    audit_results: List[EnterprisePolicyPreAuditResult] = Field(..., description="预审结果列表")
    total_policies: int = Field(..., description="总政策数")
    enterprise_policies: int = Field(..., description="企业政策数")
    passed_policies: int = Field(..., description="通过的政策数")
    pass_rate: float = Field(..., description="通过率")
    enterprise_id: Optional[str] = Field(None, description="企业ID")
    enterprise_name: Optional[str] = Field(None, description="企业名称")


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
                    no_values = ["否", "no", "false", "0", "无", "不是", "没有", "异常", "吊销", "注销"]
                    
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
                                num_val = float(numbers[0])
                                # 对特定字段进行合理性检查
                                if key == '法人年龄' and not (0 <= num_val <= 120):
                                    normalized[key] = value  # 保持原值
                                elif key == '经营时间' and not (0 <= num_val <= 100):
                                    normalized[key] = value  # 保持原值
                                else:
                                    normalized[key] = num_val
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
                    if any(keyword in v_str for keyword in ["未结清", "有贷款", "存在", "在贷"]):
                        normalized['有贷款'] = "是"
                    else:
                        normalized['有贷款'] = "否"
                    normalized[key] = v_str
                else:
                    normalized[key] = None
            
            # 处理企业规模标准化
            elif key == '企业规模':
                if value is not None:
                    v_str = str(value).strip()
                    size_mapping = {
                        "小型": "小型企业",
                        "小微": "小型企业", 
                        "中型": "中型企业",
                        "大型": "大型企业",
                        "微型": "微型企业"
                    }
                    for size_key, size_value in size_mapping.items():
                        if size_key in v_str:
                            normalized[key] = size_value
                            break
                    else:
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


def convert_logic_to_lowercase(data):
    """递归地将逻辑操作符转换为小写"""
    try:
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ["逻辑", "逻辑关系"] and isinstance(value, str):
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


def safe_enterprise_preaudit_single(enterprise_data: Any, policy_data: Any) -> int:
    """安全地预审单个企业政策"""
    try:
        # 安全转换为字典
        enterprise_dict = safe_convert_to_dict(enterprise_data)
        policy_dict = safe_convert_to_dict(policy_data)
        
        if not enterprise_dict:
            return 0
        
        if not policy_dict:
            return 0
        
        # 检查是否为企业政策
        if not enterprise_preaudit_engine.is_enterprise_policy(policy_dict):
            logger.debug(f"政策 {policy_dict.get('政策编号', 'Unknown')} 不是企业政策")
            return 0
        
        # 规范化企业数据
        enterprise_dict = safe_normalize_enterprise_data(enterprise_dict)
        
        # 转换逻辑操作符
        policy_dict = convert_logic_to_lowercase(policy_dict)
        
        # 调用核心企业预审功能
        result = enterprise_preaudit_engine.pre_audit_enterprise_policy(enterprise_dict, policy_dict)
        
        # 确保结果是0或1
        return 1 if result else 0
        
    except Exception as e:
        logger.error(f"企业预审单个政策时出错: {e}")
        return 0


def safe_batch_enterprise_preaudit(enterprise_data: Any, policies_data: List[Any]) -> List[int]:
    """安全地批量预审企业政策"""
    try:
        if not policies_data:
            return []
        
        # 过滤出企业政策
        enterprise_policies = []
        for policy_data in policies_data:
            policy_dict = safe_convert_to_dict(policy_data)
            if enterprise_preaudit_engine.is_enterprise_policy(policy_dict):
                enterprise_policies.append(policy_data)
        
        results = []
        for policy_data in enterprise_policies:
            try:
                result = safe_enterprise_preaudit_single(enterprise_data, policy_data)
                results.append(result)
            except Exception as e:
                logger.error(f"处理企业政策时出错: {e}")
                results.append(0)
        
        return results
        
    except Exception as e:
        logger.error(f"批量企业预审时出错: {e}")
        return [0] * len(policies_data) if policies_data else []


# API端点定义
@app.get("/", summary="根路径", description="企业政策预审API服务状态检查")
async def root():
    return {
        "message": "企业政策预审系统API服务（宽容版）正在运行",
        "version": "1.1.0",
        "target": "企业政策预审",
        "features": [
            "专门处理企业数据",
            "自动过滤企业政策",
            "自动处理非法输入",
            "不返回422错误", 
            "非法条件视为不通过",
            "严格0或1结果输出",
            "最大程度的容错性"
        ],
        "endpoints": {
            "企业预审": "/preaudit",
            "单个企业政策预审": "/preaudit-single",
            "批量企业预审": "/batch-preaudit",
            "详细预审结果": "/preaudit-detailed",
            "健康检查": "/health",
            "API文档": "/docs"
        }
    }


@app.get("/health", summary="健康检查", description="检查企业政策预审API服务状态")
async def health_check():
    return {
        "status": "healthy", 
        "service": "企业政策预审系统（宽容版）", 
        "target": "企业政策预审",
        "audit_mode": "strict",
        "result_type": "binary (0 or 1)",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


@app.post("/preaudit", 
          response_model=EnterprisePreAuditAPIResponse,
          summary="企业政策预审（宽容版）",
          description="根据企业数据和政策列表返回每个企业政策的预审结果(0或1)，自动处理非法输入")
async def preaudit_enterprise_policies(request: Dict = None):
    """
    宽容的企业政策预审接口 - 严格规则审核，返回0或1
    """
    try:
        # 处理空请求
        if not request:
            return EnterprisePreAuditAPIResponse(
                status_code=200,
                result=[],
                message="企业预审完成，无错误",
                total_policies=0,
                enterprise_policies=0,
                passed_policies=0
            )
        
        # 提取企业和政策数据
        enterprise_data = request.get('enterprise', {})
        policies_data = request.get('policies', [])
        
        # 确保policies是列表
        if not isinstance(policies_data, list):
            policies_data = [policies_data] if policies_data else []
        
        # 统计企业政策数量
        enterprise_policy_count = sum(1 for policy in policies_data 
                                    if enterprise_preaudit_engine.is_enterprise_policy(safe_convert_to_dict(policy)))
        
        # 批量预审
        results = safe_batch_enterprise_preaudit(enterprise_data, policies_data)
        
        # 统计通过数量
        passed_count = sum(results)
        enterprise_dict = safe_convert_to_dict(enterprise_data)
        enterprise_id = enterprise_dict.get('企业ID', 'Unknown')
        
        return EnterprisePreAuditAPIResponse(
            status_code=200,
            result=results,
            message="企业预审完成，无错误",
            enterprise_id=str(enterprise_id),
            total_policies=len(policies_data),
            enterprise_policies=enterprise_policy_count,
            passed_policies=passed_count
        )
        
    except Exception as e:
        logger.error(f"企业预审计算异常: {e}")
        logger.error(traceback.format_exc())
        return EnterprisePreAuditAPIResponse(
            status_code=200,
            result=[],
            message="企业预审完成，无错误",
            total_policies=0,
            enterprise_policies=0,
            passed_policies=0
        )


@app.post("/preaudit-single",
          summary="单个企业政策预审（宽容版）",
          description="针对单个企业和单个政策进行预审，自动处理非法输入")
async def preaudit_single_enterprise_policy(request: Dict = None):
    """
    宽容的单个企业政策预审接口
    """
    try:
        # 处理空请求
        if not request:
            return {
                "status_code": 200,
                "result": 0,
                "message": "企业预审完成，无错误",
                "is_enterprise_policy": False
            }
        
        # 提取企业和政策数据
        enterprise_data = request.get('enterprise', {})
        policy_data = request.get('policy', {})
        
        # 检查是否为企业政策
        policy_dict = safe_convert_to_dict(policy_data)
        is_enterprise_policy = enterprise_preaudit_engine.is_enterprise_policy(policy_dict)
        
        # 预审单个政策
        result = safe_enterprise_preaudit_single(enterprise_data, policy_data)
        
        enterprise_dict = safe_convert_to_dict(enterprise_data)
        enterprise_id = enterprise_dict.get('企业ID', 'Unknown')
        
        return {
            "status_code": 200,
            "result": result,
            "message": "企业预审完成，无错误",
            "enterprise_id": str(enterprise_id),
            "is_enterprise_policy": is_enterprise_policy
        }
        
    except Exception as e:
        logger.error(f"单个企业政策预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "企业预审完成，无错误",
            "is_enterprise_policy": False
        }


@app.post("/batch-preaudit",
          summary="批量企业预审（宽容版）",
          description="为多个企业同时进行政策预审，自动处理非法输入")
async def batch_enterprise_preaudit(request: Dict = None):
    """
    宽容的批量企业预审接口
    """
    try:
        # 处理空请求
        if not request:
            return {
                "status_code": 200,
                "result": [],
                "message": "批量企业预审完成，无错误"
            }
        
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
            policy_dict = safe_convert_to_dict(policy)
            if enterprise_preaudit_engine.is_enterprise_policy(policy_dict):
                enterprise_policies.append(policy)
        
        # 批量计算
        all_results = []
        total_passed = 0
        
        for e_idx, enterprise_data in enumerate(enterprises_data):
            enterprise_results = safe_batch_enterprise_preaudit(enterprise_data, enterprise_policies)
            all_results.extend(enterprise_results)
            total_passed += sum(enterprise_results)
        
        return {
            "status_code": 200,
            "result": all_results,
            "message": "批量企业预审完成，无错误",
            "total_enterprises": len(enterprises_data),
            "enterprise_policies": len(enterprise_policies),
            "total_audits": len(all_results),
            "total_passed": total_passed
        }
        
    except Exception as e:
        logger.error(f"批量企业预审异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": [],
            "message": "批量企业预审完成，无错误"
        }


@app.post("/preaudit-detailed",
          summary="详细企业预审结果（宽容版）",
          description="返回格式化的详细企业预审结果，自动处理非法输入")
async def preaudit_enterprise_detailed(request: Dict = None):
    """
    宽容的详细企业预审接口 - 返回格式化结果
    """
    try:
        # 处理空请求
        if not request:
            return EnterprisePreAuditResponse(
                audit_results=[],
                total_policies=0,
                enterprise_policies=0,
                passed_policies=0,
                pass_rate=0.0,
                enterprise_id=None,
                enterprise_name=None
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
            policy_dict = safe_convert_to_dict(policy)
            if enterprise_preaudit_engine.is_enterprise_policy(policy_dict):
                enterprise_policies.append(policy)
        
        # 批量预审
        results = safe_batch_enterprise_preaudit(enterprise_data, enterprise_policies)
        
        # 构建详细结果
        audit_results = []
        for i, (policy_data, result) in enumerate(zip(enterprise_policies, results)):
            policy_dict = safe_convert_to_dict(policy_data)
            
            audit_results.append(EnterprisePolicyPreAuditResult(
                政策编号=str(policy_dict.get('政策编号', f'Enterprise_Policy_{i+1}')),
                标题=str(policy_dict.get('标题', policy_dict.get('政策名称', f'企业政策{i+1}'))),
                政策类型=str(policy_dict.get('政策类型', policy_dict.get('类型', '企业'))),
                预审结果=result,
                预审状态="通过" if result == 1 else "不通过"
            ))
        
        passed_count = sum(results)
        pass_rate = round(passed_count / len(results), 3) if results else 0.0
        
        enterprise_dict = safe_convert_to_dict(enterprise_data)
        
        return EnterprisePreAuditResponse(
            audit_results=audit_results,
            total_policies=len(policies_data),
            enterprise_policies=len(enterprise_policies),
            passed_policies=passed_count,
            pass_rate=pass_rate,
            enterprise_id=str(enterprise_dict.get("企业ID")) if enterprise_dict.get("企业ID") else None,
            enterprise_name=str(enterprise_dict.get("企业名称")) if enterprise_dict.get("企业名称") else None
        )
        
    except Exception as e:
        logger.error(f"详细企业预审异常: {e}")
        logger.error(traceback.format_exc())
        return EnterprisePreAuditResponse(
            audit_results=[],
            total_policies=0,
            enterprise_policies=0,
            passed_policies=0,
            pass_rate=0.0,
            enterprise_id=None,
            enterprise_name=None
        )


# 全局异常处理器
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """捕获Pydantic验证错误，返回0结果而不是422"""
    logger.warning(f"验证错误: {exc}")
    return EnterprisePreAuditAPIResponse(
        status_code=200,
        result=[0],
        message="企业预审完成，无错误",
        total_policies=0,
        enterprise_policies=0,
        passed_policies=0
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有其他异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return EnterprisePreAuditAPIResponse(
        status_code=200,
        result=[0],
        message="企业预审完成，无错误",
        total_policies=0,
        enterprise_policies=0,
        passed_policies=0
    )


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动企业政策预审API服务（宽容版）...")
    print("📖 API文档地址: http://localhost:8084/docs")
    print("🩺 健康检查: http://localhost:8084/health")
    print("🏢 企业预审接口: http://localhost:8084/preaudit")
    print("📊 详细预审接口: http://localhost:8084/preaudit-detailed")
    print("🔧 单个政策预审接口: http://localhost:8084/preaudit-single")
    print("📦 批量预审接口: http://localhost:8084/batch-preaudit")
    print("✨ 特性: 专门处理企业政策预审 + 严格0或1结果 + 最大容错性")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "__main__:app",
        host="127.0.0.1",
        port=8084,
        reload=True,
        log_level="info"
    )