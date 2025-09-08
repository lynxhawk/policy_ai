"""
政策匹配系统FastAPI接口服务
提供RESTful API接口调用政策匹配核心功能
即使输入数据不合法也不会返回错误，而是将非法条件当作不匹配处理
"""

from fastapi import FastAPI, Request
from typing import Dict, List, Any, Optional, Union
import uvicorn
import logging
import traceback

# 导入核心匹配模块和数据处理工具
from policy_user_match import PolicyMatchEngine
from data_processor import DataProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI应用
app = FastAPI(
    title="政策匹配系统API",
    description="基于用户数据和政策条件进行严格规则匹配的系统，自动处理非法输入",
    version="2.0.0"
)

# 初始化核心组件
match_engine = PolicyMatchEngine()
data_processor = DataProcessor()


# API端点定义
@app.get("/health", summary="健康检查", description="检查API服务状态")
async def health_check():
    return {
        "status": "healthy", 
        "service": "政策匹配系统", 
        "match_mode": "strict",
        "result_type": "binary (0 or 1)",
        "tolerance": "maximum",
        "error_handling": "graceful"
    }


@app.post("/recommend-single",
          summary="单个政策匹配",
          description="针对单个用户和单个政策进行匹配，自动处理非法输入")
async def recommend_single_policy(request: Request):
    """
    单个政策匹配接口
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)
        
        # 提取用户和政策数据
        user_data = request_data.get('user', {})
        policy_data = request_data.get('policy', {})
        
        # 处理数据
        user_dict = data_processor.process_user_data(user_data)
        policy_dict = data_processor.process_policy_data(policy_data)
        
        # 验证并匹配
        if data_processor.validate_match_input(user_dict, policy_dict):
            result = match_engine.match_policy(user_dict, policy_dict)
            result = 1 if result else 0
        else:
            result = 0
        
        return {
            "status_code": 200,
            "result": result,
            "message": "匹配完成"
        }
        
    except Exception as e:
        logger.error(f"单个政策匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "result": 0,
            "message": "匹配完成"
        }


@app.post("/batch-recommend",
          summary="批量用户匹配",
          description="多个用户与单个政策进行匹配，自动处理非法输入")
async def batch_recommend(request: Request):
    """
    批量用户匹配接口 - 多个用户与单个政策匹配
    """
    try:
        # 解析请求
        request_data = await data_processor.parse_request_safely(request)
        
        # 提取用户列表和政策数据
        users_data = request_data.get('users', [])
        policy_data = request_data.get('policy', {})
        
        # 确保users是列表
        if not isinstance(users_data, list):
            users_data = [users_data] if users_data else []
        
        # 处理政策数据（只需要处理一次）
        policy_dict = data_processor.process_policy_data(policy_data)
        
        results = []
        for user_data in users_data:
            try:
                # 处理用户数据
                user_dict = data_processor.process_user_data(user_data)
                
                # 验证并匹配
                if data_processor.validate_match_input(user_dict, policy_dict):
                    result = match_engine.match_policy(user_dict, policy_dict)
                    results.append(1 if result else 0)
                else:
                    results.append(0)
                    
            except Exception as e:
                logger.error(f"处理用户时出错: {e}")
                results.append(0)
        
        return {
            "status_code": 200,
            "results": results,
            "message": "批量匹配完成"
        }
        
    except Exception as e:
        logger.error(f"批量匹配异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "status_code": 200,
            "results": [],
            "message": "批量匹配完成"
        }


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """捕获所有异常"""
    logger.error(f"全局异常: {exc}")
    logger.error(traceback.format_exc())
    return {
        "status_code": 200,
        "result": 0,
        "message": "匹配完成"
    }


if __name__ == "__main__":
    # 启动服务器
    print("🚀 正在启动政策匹配API服务...")
    print("📖 API文档地址: http://localhost:8081/docs")
    print("🩺 健康检查: http://localhost:8081/health")
    print("🔧 单个匹配接口: http://localhost:8081/recommend-single")
    print("📊 批量匹配接口: http://localhost:8081/batch-recommend")
    print("✨ 特性: 严格0或1结果 + 最大容错性，非法输入返回0而不是错误")
    print("按 Ctrl+C 停止服务")
    
    uvicorn.run(
        "fastapi_policy_user_match:app",
        host="127.0.0.1",
        port=8081,
        reload=True,
        log_level="info"
    )