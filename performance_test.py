#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策推荐系统 recommend-single 接口专项性能测试
专门测试单个政策推荐接口的并发性能
"""

import requests
import time
import threading
import json
import psutil
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import os
import logging
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'single_api_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RecommendSingleTester:
    """recommend-single接口专项性能测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8081"):
        self.base_url = base_url
        self.endpoint = "recommend-single"
        self.test_results = []
        self.system_metrics = []
        
    def check_service_health(self) -> bool:
        """检查服务是否正常运行"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ 服务健康检查通过")
                return True
            else:
                logger.error(f"❌ 服务健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到服务: {e}")
            return False
    
    def load_test_data(self, policy_folder: str = "policy_new", user_folder: str = "user_dataset", 
                       policy_limit: int = 8, user_limit: int = 50):
        """加载测试数据"""
        logger.info(f"📁 加载测试数据 - 政策限制:{policy_limit}, 用户限制:{user_limit}")
        
        # 加载政策数据
        policies = []
        if os.path.exists(policy_folder):
            policy_files = sorted([f for f in os.listdir(policy_folder) if f.endswith('.json')])[:policy_limit]
            for file in policy_files:
                try:
                    with open(os.path.join(policy_folder, file), 'r', encoding='utf-8') as f:
                        policy_data = json.load(f)
                        policies.append(policy_data)
                        logger.info(f"✅ 加载政策: {policy_data.get('政策编号', file)}")
                except Exception as e:
                    logger.warning(f"加载政策文件 {file} 失败: {e}")
        
        # 加载用户数据
        users = []
        if os.path.exists(user_folder):
            user_files = sorted([f for f in os.listdir(user_folder) if f.endswith('.json')])[:user_limit]
            for file in user_files:
                try:
                    with open(os.path.join(user_folder, file), 'r', encoding='utf-8') as f:
                        user_data = json.load(f)
                        users.append(user_data)
                        logger.info(f"✅ 加载用户: {user_data.get('用户ID', file)}")
                except Exception as e:
                    logger.warning(f"加载用户文件 {file} 失败: {e}")
        
        logger.info(f"✅ 数据加载完成 - 政策:{len(policies)}, 用户:{len(users)}")
        return policies, users
    
    def monitor_system_resources(self, duration: float, interval: float = 1.0):
        """监控系统资源使用情况"""
        logger.info(f"📊 开始监控系统资源 - 持续时间:{duration}s")
        
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            try:
                # CPU和内存使用率
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                metric = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
                
                self.system_metrics.append(metric)
                
            except Exception as e:
                logger.warning(f"系统监控异常: {e}")
            
            time.sleep(interval)
        
        logger.info("📊 系统资源监控完成")
    
    def single_recommend_request(self, user: Dict, policy: Dict, timeout: int = 30) -> Dict:
        """执行单次recommend-single请求"""
        start_time = time.time()
        thread_id = threading.current_thread().ident
        
        try:
            payload = {
                "user": user,
                "policy": policy
            }
            
            response = requests.post(
                f"{self.base_url}/{self.endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            end_time = time.time()
            
            result = {
                'thread_id': thread_id,
                'user_id': user.get('用户ID', 'unknown'),
                'policy_id': policy.get('政策编号', 'unknown'),
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': (end_time - start_time) * 1000,  # ms
                'request_size': len(json.dumps(payload).encode('utf-8')),  # bytes
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
                'start_time': start_time,
                'end_time': end_time,
                'timestamp': datetime.now().isoformat()
            }
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    match_score = response_data.get('result', 0)
                    result['match_score'] = match_score
                    result['response_data'] = response_data
                except:
                    result['match_score'] = 0
            
            return result
            
        except requests.exceptions.Timeout:
            end_time = time.time()
            return {
                'thread_id': thread_id,
                'user_id': user.get('用户ID', 'unknown'),
                'policy_id': policy.get('政策编号', 'unknown'),
                'success': False,
                'status_code': 408,
                'response_time': (end_time - start_time) * 1000,
                'error': 'Request timeout',
                'start_time': start_time,
                'end_time': end_time,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            end_time = time.time()
            return {
                'thread_id': thread_id,
                'user_id': user.get('用户ID', 'unknown'),
                'policy_id': policy.get('政策编号', 'unknown'),
                'success': False,
                'status_code': 0,
                'response_time': (end_time - start_time) * 1000,
                'error': str(e),
                'start_time': start_time,
                'end_time': end_time,
                'timestamp': datetime.now().isoformat()
            }
    
    def concurrent_test(self, users: List[Dict], policies: List[Dict], 
                       concurrent_requests: int = 10, test_duration: int = 60):
        """并发测试recommend-single接口"""
        logger.info(f"🚀 开始recommend-single并发测试")
        logger.info(f"  并发请求数: {concurrent_requests}")
        logger.info(f"  测试持续时间: {test_duration}s")
        logger.info(f"  用户数: {len(users)}, 政策数: {len(policies)}")
        
        test_results = []
        test_start_time = time.time()
        test_end_time = test_start_time + test_duration
        
        # 启动系统监控线程
        monitor_thread = threading.Thread(
            target=self.monitor_system_resources,
            args=(test_duration + 5,),
            daemon=True
        )
        monitor_thread.start()
        
        def generate_random_pair():
            """随机生成用户-政策对"""
            user = random.choice(users)
            policy = random.choice(policies)
            return user, policy
        
        def worker():
            """工作线程函数"""
            thread_results = []
            request_count = 0
            
            while time.time() < test_end_time:
                user, policy = generate_random_pair()
                result = self.single_recommend_request(user, policy)
                thread_results.append(result)
                request_count += 1
                
                # 短暂休息避免过度请求
                time.sleep(0.01)  # 10ms间隔
            
            logger.info(f"线程 {threading.current_thread().ident} 完成 {request_count} 个请求")
            return thread_results
        
        # 启动并发测试
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_requests)]
            
            for future in as_completed(futures):
                try:
                    thread_results = future.result()
                    test_results.extend(thread_results)
                except Exception as e:
                    logger.error(f"工作线程异常: {e}")
        
        total_test_time = time.time() - test_start_time
        
        # 分析结果
        return self._analyze_test_results(test_results, total_test_time, {
            'concurrent_requests': concurrent_requests,
            'test_duration': test_duration,
            'users_count': len(users),
            'policies_count': len(policies)
        })
    
    def _analyze_test_results(self, test_results: List[Dict], total_test_time: float, test_config: Dict):
        """分析测试结果"""
        successful_requests = [r for r in test_results if r['success']]
        failed_requests = [r for r in test_results if not r['success']]
        
        if not successful_requests:
            return {
                'test_name': 'recommend-single并发测试',
                'test_config': test_config,
                'error': '所有请求都失败了',
                'failed_requests': len(failed_requests),
                'error_analysis': self._analyze_errors(failed_requests),
                'timestamp': datetime.now().isoformat()
            }
        
        # 响应时间统计
        response_times = [r['response_time'] for r in successful_requests]
        match_scores = [r.get('match_score', 0) for r in successful_requests if 'match_score' in r]
        
        # 用户-政策组合统计
        user_policy_stats = {}
        for r in successful_requests:
            key = f"{r.get('user_id', 'unknown')}-{r.get('policy_id', 'unknown')}"
            if key not in user_policy_stats:
                user_policy_stats[key] = {
                    'count': 0,
                    'avg_response_time': 0,
                    'match_scores': []
                }
            user_policy_stats[key]['count'] += 1
            user_policy_stats[key]['match_scores'].append(r.get('match_score', 0))
        
        # 计算平均响应时间
        for key, stats in user_policy_stats.items():
            related_requests = [r for r in successful_requests 
                              if f"{r.get('user_id', 'unknown')}-{r.get('policy_id', 'unknown')}" == key]
            stats['avg_response_time'] = np.mean([r['response_time'] for r in related_requests])
        
        performance_stats = {
            'test_name': 'recommend-single并发测试',
            'test_config': test_config,
            'request_stats': {
                'total_requests': len(test_results),
                'successful_requests': len(successful_requests),
                'failed_requests': len(failed_requests),
                'success_rate': len(successful_requests) / len(test_results) * 100,
                'requests_per_second': len(test_results) / total_test_time,
                'unique_user_policy_combinations': len(user_policy_stats)
            },
            'response_time_stats': {
                'avg_response_time': np.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': np.median(response_times),
                'p90_response_time': np.percentile(response_times, 90),
                'p95_response_time': np.percentile(response_times, 95),
                'p99_response_time': np.percentile(response_times, 99),
                'std_response_time': np.std(response_times)
            },
            'match_score_stats': {
                'avg_match_score': np.mean(match_scores) if match_scores else 0,
                'min_match_score': min(match_scores) if match_scores else 0,
                'max_match_score': max(match_scores) if match_scores else 0,
                'high_match_rate': len([s for s in match_scores if s > 0.5]) / len(match_scores) * 100 if match_scores else 0
            },
            'data_transfer_stats': {
                'avg_request_size': np.mean([r.get('request_size', 0) for r in successful_requests]),
                'avg_response_size': np.mean([r.get('response_size', 0) for r in successful_requests]),
                'total_data_mb': sum([r.get('request_size', 0) + r.get('response_size', 0) for r in successful_requests]) / (1024*1024)
            },
            'user_policy_combinations': user_policy_stats,
            'error_analysis': self._analyze_errors(failed_requests),
            'system_metrics': self._analyze_system_metrics(test_results[0]['start_time'] if test_results else 0, 
                                                         test_results[-1]['end_time'] if test_results else 0),
            'timestamp': datetime.now().isoformat(),
            'raw_results': test_results
        }
        
        return performance_stats
    
    def _analyze_errors(self, failed_requests: List[Dict]) -> Dict:
        """分析错误统计"""
        if not failed_requests:
            return {'no_errors': True}
        
        error_types = {}
        status_codes = {}
        user_errors = {}
        policy_errors = {}
        
        for req in failed_requests:
            error = req.get('error', 'Unknown error')
            status_code = req.get('status_code', 0)
            user_id = req.get('user_id', 'unknown')
            policy_id = req.get('policy_id', 'unknown')
            
            error_types[error] = error_types.get(error, 0) + 1
            status_codes[str(status_code)] = status_codes.get(str(status_code), 0) + 1
            user_errors[user_id] = user_errors.get(user_id, 0) + 1
            policy_errors[policy_id] = policy_errors.get(policy_id, 0) + 1
        
        return {
            'total_errors': len(failed_requests),
            'error_types': error_types,
            'status_codes': status_codes,
            'user_error_distribution': user_errors,
            'policy_error_distribution': policy_errors,
            'error_rate': len(failed_requests)
        }
    
    def _analyze_system_metrics(self, start_time: float, end_time: float) -> Dict:
        """分析系统性能指标"""
        relevant_metrics = [
            m for m in self.system_metrics 
            if start_time <= m['timestamp'] <= end_time
        ]
        
        if not relevant_metrics:
            return {'no_data': True}
        
        cpu_values = [m['cpu_percent'] for m in relevant_metrics]
        memory_values = [m['memory_percent'] for m in relevant_metrics]
        
        return {
            'cpu_stats': {
                'avg_cpu': np.mean(cpu_values),
                'max_cpu': max(cpu_values),
                'min_cpu': min(cpu_values)
            },
            'memory_stats': {
                'avg_memory': np.mean(memory_values),
                'max_memory': max(memory_values),
                'min_memory': min(memory_values)
            },
            'sample_count': len(relevant_metrics)
        }
    
    def gradual_load_test(self, users: List[Dict], policies: List[Dict],
                         max_concurrent: int = 50, step_size: int = 5, step_duration: int = 30):
        """渐进式负载测试"""
        logger.info(f"📈 开始recommend-single渐进式负载测试")
        logger.info(f"  最大并发数: {max_concurrent}")
        logger.info(f"  步长: {step_size}")
        logger.info(f"  每步持续时间: {step_duration}s")
        
        gradual_results = []
        
        for concurrent_requests in range(step_size, max_concurrent + 1, step_size):
            logger.info(f"🔄 测试并发请求数: {concurrent_requests}")
            
            # 执行当前并发级别的测试
            result = self.concurrent_test(
                users, policies, 
                concurrent_requests=concurrent_requests, 
                test_duration=step_duration
            )
            
            result['concurrent_level'] = concurrent_requests
            gradual_results.append(result)
            
            # 短暂休息让系统恢复
            time.sleep(3)
            
            # 检查是否出现严重问题（成功率过低）
            success_rate = result.get('request_stats', {}).get('success_rate', 0)
            if success_rate < 50:
                logger.warning(f"⚠️  成功率过低 ({success_rate:.1f}%)，提前结束测试")
                break
        
        # 分析渐进测试结果
        gradual_analysis = self._analyze_gradual_results(gradual_results)
        
        logger.info(f"✅ 渐进式负载测试完成")
        logger.info(f"  最高稳定并发: {gradual_analysis.get('max_stable_concurrent', 0)}")
        logger.info(f"  峰值QPS: {gradual_analysis.get('peak_qps', 0):.2f}")
        
        return {
            'test_name': 'recommend-single渐进式负载测试',
            'test_results': gradual_results,
            'analysis': gradual_analysis,
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_gradual_results(self, results: List[Dict]) -> Dict:
        """分析渐进测试结果"""
        if not results:
            return {}
        
        qps_values = []
        response_times = []
        success_rates = []
        concurrent_levels = []
        
        for result in results:
            if 'request_stats' in result and 'response_time_stats' in result:
                concurrent_levels.append(result['concurrent_level'])
                qps_values.append(result['request_stats']['requests_per_second'])
                response_times.append(result['response_time_stats']['avg_response_time'])
                success_rates.append(result['request_stats']['success_rate'])
        
        # 找到最佳性能点
        stable_results = [
            (i, qps, rt, sr) for i, (qps, rt, sr) in 
            enumerate(zip(qps_values, response_times, success_rates))
            if sr >= 95  # 成功率大于95%
        ]
        
        max_stable_concurrent = 0
        peak_qps = 0
        optimal_response_time = float('inf')
        
        if stable_results:
            max_qps_idx, max_qps, _, _ = max(stable_results, key=lambda x: x[1])
            max_stable_concurrent = concurrent_levels[max_qps_idx]
            peak_qps = max_qps
            optimal_response_time = response_times[max_qps_idx]
        
        return {
            'max_stable_concurrent': max_stable_concurrent,
            'peak_qps': peak_qps,
            'optimal_response_time': optimal_response_time,
            'performance_curve': list(zip(concurrent_levels, qps_values, response_times, success_rates)),
            'total_test_levels': len(results)
        }
    
    def generate_performance_charts(self, test_results: List[Dict], output_dir: str):
        """生成性能图表"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 查找渐进测试结果
        gradual_test = None
        for result in test_results:
            if 'recommend-single渐进式负载测试' in result.get('test_name', ''):
                gradual_test = result
                break
        
        if gradual_test and 'test_results' in gradual_test:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('recommend-single接口性能测试报告', fontsize=16, fontweight='bold')
            
            gradual_data = gradual_test['test_results']
            concurrent_levels = [r['concurrent_level'] for r in gradual_data if 'request_stats' in r]
            qps_values = [r['request_stats']['requests_per_second'] for r in gradual_data if 'request_stats' in r]
            response_times = [r['response_time_stats']['avg_response_time'] for r in gradual_data if 'response_time_stats' in r]
            success_rates = [r['request_stats']['success_rate'] for r in gradual_data if 'request_stats' in r]
            
            # QPS vs 并发数
            axes[0, 0].plot(concurrent_levels, qps_values, 'b-o', linewidth=2, markersize=6)
            axes[0, 0].set_xlabel('并发请求数')
            axes[0, 0].set_ylabel('QPS (请求/秒)')
            axes[0, 0].set_title('QPS vs 并发请求数')
            axes[0, 0].grid(True, alpha=0.3)
            
            # 响应时间 vs 并发数
            axes[0, 1].plot(concurrent_levels, response_times, 'r-s', linewidth=2, markersize=6)
            axes[0, 1].set_xlabel('并发请求数')
            axes[0, 1].set_ylabel('平均响应时间 (ms)')
            axes[0, 1].set_title('响应时间 vs 并发请求数')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 成功率 vs 并发数
            axes[1, 0].plot(concurrent_levels, success_rates, 'g-^', linewidth=2, markersize=6)
            axes[1, 0].set_xlabel('并发请求数')
            axes[1, 0].set_ylabel('成功率 (%)')
            axes[1, 0].set_title('成功率 vs 并发请求数')
            axes[1, 0].set_ylim(0, 105)
            axes[1, 0].grid(True, alpha=0.3)
            
            # 响应时间分布
            all_response_times = []
            for result in test_results:
                if 'raw_results' in result:
                    response_times_raw = [r['response_time'] for r in result['raw_results'] if r.get('success', False)]
                    all_response_times.extend(response_times_raw)
            
            if all_response_times:
                axes[1, 1].hist(all_response_times, bins=50, alpha=0.7, color='purple', edgecolor='black')
                axes[1, 1].set_xlabel('响应时间 (ms)')
                axes[1, 1].set_ylabel('请求数量')
                axes[1, 1].set_title('响应时间分布')
                axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存图表
            chart_filename = os.path.join(output_dir, f"recommend_single_performance_{timestamp}.png")
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📈 性能图表已保存到: {chart_filename}")
            return chart_filename
        
        return None
    
    def generate_performance_report(self, test_results: List[Dict], output_dir: str = "performance_reports"):
        """生成性能测试报告"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON报告
        json_report = {
            'test_summary': {
                'test_time': datetime.now().isoformat(),
                'total_tests': len(test_results),
                'test_endpoint': 'recommend-single',
                'test_types': list(set([r.get('test_name', 'Unknown') for r in test_results]))
            },
            'test_results': test_results,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3)
            }
        }
        
        json_filename = os.path.join(output_dir, f"recommend_single_report_{timestamp}.json")
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        # 生成图表
        chart_file = self.generate_performance_charts(test_results, output_dir)
        
        logger.info(f"📊 性能报告已生成:")
        logger.info(f"  JSON报告: {json_filename}")
        if chart_file:
            logger.info(f"  图表文件: {chart_file}")
        
        return json_filename
    
    def run_comprehensive_test(self):
        """运行recommend-single接口综合性能测试"""
        logger.info("🎯 开始recommend-single接口综合性能测试")
        
        # 检查服务状态
        if not self.check_service_health():
            logger.error("❌ 服务不可用，无法进行测试")
            return None
        
        # 加载测试数据
        policies, users = self.load_test_data()
        
        if not policies or not users:
            logger.error("❌ 测试数据加载失败")
            return None
        
        all_test_results = []
        
        # 1. 基础并发测试
        logger.info("\n" + "="*60)
        logger.info("1. 基础并发测试 (10并发, 60秒)")
        logger.info("="*60)
        basic_test = self.concurrent_test(users, policies, concurrent_requests=10, test_duration=60)
        all_test_results.append(basic_test)
        
        # 2. 渐进式负载测试
        if basic_test.get('request_stats', {}).get('success_rate', 0) > 80:
            logger.info("\n" + "="*60)
            logger.info("2. 渐进式负载测试")
            logger.info("="*60)
            gradual_test = self.gradual_load_test(users, policies, max_concurrent=40, step_size=5, step_duration=30)
            all_test_results.append(gradual_test)
        else:
            logger.warning("⚠️  基础测试成功率较低，跳过渐进式测试")
        
        # 3. 高并发压力测试
        if basic_test.get('request_stats', {}).get('success_rate', 0) > 90:
            logger.info("\n" + "="*60)
            logger.info("3. 高并发压力测试 (30并发, 180秒)")
            logger.info("="*60)
            stress_test = self.concurrent_test(users, policies, concurrent_requests=30, test_duration=180)
            all_test_results.append(stress_test)
        
        # 生成报告
        report_file = self.generate_performance_report(all_test_results)
        
        logger.info("✅ recommend-single接口综合性能测试完成！")
        logger.info(f"📄 详细报告: {report_file}")
        
        return all_test_results

def main():
    """主函数"""
    print("🚀 recommend-single接口专项性能测试")
    print("=" * 80)
    
    # 创建测试器
    tester = RecommendSingleTester()
    
    # 运行综合测试
    results = tester.run_comprehensive_test()
    
    if results:
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            test_name = result.get('test_name', f'测试 {i}')
            print(f"\n{i}. {test_name}:")
            
            if 'request_stats' in result:
                stats = result['request_stats']
                print(f"   总请求数: {stats.get('total_requests', 0)}")
                print(f"   成功请求数: {stats.get('successful_requests', 0)}")
                print(f"   成功率: {stats.get('success_rate', 0):.2f}%")
                print(f"   QPS: {stats.get('requests_per_second', 0):.2f}")
                print(f"   用户-政策组合数: {stats.get('unique_user_policy_combinations', 0)}")
            
            if 'response_time_stats' in result:
                rt_stats = result['response_time_stats']
                print(f"   平均响应时间: {rt_stats.get('avg_response_time', 0):.2f}ms")
                print(f"   95%响应时间: {rt_stats.get('p95_response_time', 0):.2f}ms")
                print(f"   99%响应时间: {rt_stats.get('p99_response_time', 0):.2f}ms")
            
            if 'match_score_stats' in result:
                match_stats = result['match_score_stats']
                print(f"   平均匹配度: {match_stats.get('avg_match_score', 0):.4f}")
                print(f"   高匹配率(>0.5): {match_stats.get('high_match_rate', 0):.1f}%")
            
            if 'analysis' in result:
                analysis = result['analysis']
                print(f"   最大稳定并发: {analysis.get('max_stable_concurrent', 0)}")
                print(f"   峰值QPS: {analysis.get('peak_qps', 0):.2f}")
                print(f"   最优响应时间: {analysis.get('optimal_response_time', 0):.2f}ms")
        
        print("\n" + "=" * 80)
        print("📈 性能指标说明:")
        print("  - QPS: 每秒处理请求数，越高越好")
        print("  - 响应时间: 单次请求处理时间，越低越好")
        print("  - 成功率: 请求成功百分比，应接近100%")
        print("  - 匹配度: 用户与政策的匹配分数，0-1之间")
        print("  - P95/P99: 95%/99%的请求在此时间内完成")
        
        print("\n🎉 recommend-single接口性能测试完成！")
        print("📊 请查看生成的报告文件和图表获取详细分析。")
    else:
        print("❌ 性能测试失败")

if __name__ == "__main__":
    main()