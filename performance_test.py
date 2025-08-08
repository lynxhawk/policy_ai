#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策推荐系统并发性能测试脚本
专门用于测试系统的并发处理能力和性能指标
"""

import subprocess
import time
import threading
import json
import psutil
import requests
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import os
import pandas as pd
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'performance_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConcurrentPerformanceTester:
    """并发性能测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8081"):
        self.base_url = base_url
        self.performance_data = []
        self.system_metrics = []
        self.test_results = {}
        
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
                       policy_limit: int = 5, user_limit: int = 10):
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
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                # 内存使用情况
                memory = psutil.virtual_memory()
                
                # 磁盘I/O
                disk_io = psutil.disk_io_counters()
                
                # 网络I/O
                net_io = psutil.net_io_counters()
                
                metric = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available / (1024**3),  # GB
                    'disk_read_mb': disk_io.read_bytes / (1024**2) if disk_io else 0,
                    'disk_write_mb': disk_io.write_bytes / (1024**2) if disk_io else 0,
                    'net_bytes_sent': net_io.bytes_sent / (1024**2) if net_io else 0,
                    'net_bytes_recv': net_io.bytes_recv / (1024**2) if net_io else 0
                }
                
                self.system_metrics.append(metric)
                
            except Exception as e:
                logger.warning(f"系统监控异常: {e}")
            
            time.sleep(interval)
        
        logger.info("📊 系统资源监控完成")
    
    def single_api_request(self, endpoint: str, payload: Dict, timeout: int = 30) -> Dict:
        """执行单个API请求"""
        start_time = time.time()
        thread_id = threading.current_thread().ident
        
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            end_time = time.time()
            
            result = {
                'thread_id': thread_id,
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': (end_time - start_time) * 1000,  # ms
                'request_size': len(json.dumps(payload).encode('utf-8')) / 1024,  # KB
                'response_size': len(response.content) / 1024 if hasattr(response, 'content') else 0,  # KB
                'start_time': start_time,
                'end_time': end_time,
                'timestamp': datetime.now().isoformat()
            }
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result['response_data'] = response_data
                    
                    # 提取匹配度分数（如果有）
                    if 'result' in response_data:
                        if isinstance(response_data['result'], list):
                            result['match_scores'] = response_data['result']
                            result['avg_match_score'] = np.mean(response_data['result'])
                        else:
                            result['match_score'] = response_data['result']
                except:
                    pass
            
            return result
            
        except requests.exceptions.Timeout:
            end_time = time.time()
            return {
                'thread_id': thread_id,
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
                'success': False,
                'status_code': 0,
                'response_time': (end_time - start_time) * 1000,
                'error': str(e),
                'start_time': start_time,
                'end_time': end_time,
                'timestamp': datetime.now().isoformat()
            }
    
    def concurrent_load_test(self, users: List[Dict], policies: List[Dict], 
                           concurrent_users: int = 10, test_duration: int = 60,
                           endpoint: str = "recommend"):
        """并发负载测试"""
        logger.info(f"🚀 开始并发负载测试")
        logger.info(f"  并发用户数: {concurrent_users}")
        logger.info(f"  测试持续时间: {test_duration}s")
        logger.info(f"  测试端点: /{endpoint}")
        
        test_results = []
        test_start_time = time.time()
        test_end_time = test_start_time + test_duration
        
        # 启动系统监控线程
        monitor_thread = threading.Thread(
            target=self.monitor_system_resources,
            args=(test_duration + 5,),  # 多监控5秒
            daemon=True
        )
        monitor_thread.start()
        
        def generate_request():
            """生成一个随机请求"""
            user = users[np.random.randint(0, len(users))]
            if endpoint == "recommend-single":
                policy = policies[np.random.randint(0, len(policies))]
                payload = {"user": user, "policy": policy}
            else:  # recommend or batch-recommend
                payload = {"user": user, "policies": policies}
            return payload
        
        def worker():
            """工作线程函数"""
            thread_results = []
            while time.time() < test_end_time:
                payload = generate_request()
                result = self.single_api_request(endpoint, payload)
                thread_results.append(result)
                
                # 短暂休息避免过度请求
                time.sleep(0.1)
            
            return thread_results
        
        # 启动并发测试
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_users)]
            
            for future in as_completed(futures):
                try:
                    thread_results = future.result()
                    test_results.extend(thread_results)
                except Exception as e:
                    logger.error(f"工作线程异常: {e}")
        
        total_test_time = time.time() - test_start_time
        
        # 分析结果
        successful_requests = [r for r in test_results if r['success']]
        failed_requests = [r for r in test_results if not r['success']]
        
        if successful_requests:
            response_times = [r['response_time'] for r in successful_requests]
            
            performance_stats = {
                'test_name': f'并发负载测试 - {endpoint}',
                'test_config': {
                    'concurrent_users': concurrent_users,
                    'test_duration': test_duration,
                    'endpoint': endpoint,
                    'users_count': len(users),
                    'policies_count': len(policies)
                },
                'request_stats': {
                    'total_requests': len(test_results),
                    'successful_requests': len(successful_requests),
                    'failed_requests': len(failed_requests),
                    'success_rate': len(successful_requests) / len(test_results) * 100,
                    'requests_per_second': len(test_results) / total_test_time
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
                'throughput_stats': {
                    'avg_request_size_kb': np.mean([r.get('request_size', 0) for r in successful_requests]),
                    'avg_response_size_kb': np.mean([r.get('response_size', 0) for r in successful_requests]),
                    'total_data_transferred_mb': sum([r.get('response_size', 0) for r in successful_requests]) / 1024
                },
                'error_analysis': self._analyze_errors(failed_requests),
                'system_metrics': self._analyze_system_metrics(test_start_time, test_start_time + total_test_time),
                'timestamp': datetime.now().isoformat(),
                'raw_results': test_results  # 保存原始数据用于详细分析
            }
        else:
            performance_stats = {
                'test_name': f'并发负载测试 - {endpoint}',
                'error': '所有请求都失败了',
                'failed_requests': len(failed_requests),
                'error_analysis': self._analyze_errors(failed_requests),
                'timestamp': datetime.now().isoformat()
            }
        
        logger.info(f"✅ 并发负载测试完成")
        logger.info(f"  总请求数: {len(test_results)}")
        logger.info(f"  成功率: {performance_stats.get('request_stats', {}).get('success_rate', 0):.2f}%")
        logger.info(f"  平均响应时间: {performance_stats.get('response_time_stats', {}).get('avg_response_time', 0):.2f}ms")
        logger.info(f"  QPS: {performance_stats.get('request_stats', {}).get('requests_per_second', 0):.2f}")
        
        return performance_stats
    
    def _analyze_errors(self, failed_requests: List[Dict]) -> Dict:
        """分析错误统计"""
        if not failed_requests:
            return {'no_errors': True}
        
        error_types = {}
        status_codes = {}
        
        for req in failed_requests:
            error = req.get('error', 'Unknown error')
            status_code = req.get('status_code', 0)
            
            error_types[error] = error_types.get(error, 0) + 1
            status_codes[str(status_code)] = status_codes.get(str(status_code), 0) + 1
        
        return {
            'total_errors': len(failed_requests),
            'error_types': error_types,
            'status_codes': status_codes,
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
        """渐进式负载测试 - 逐步增加并发用户数"""
        logger.info(f"📈 开始渐进式负载测试")
        logger.info(f"  最大并发数: {max_concurrent}")
        logger.info(f"  步长: {step_size}")
        logger.info(f"  每步持续时间: {step_duration}s")
        
        gradual_results = []
        
        for concurrent_users in range(step_size, max_concurrent + 1, step_size):
            logger.info(f"🔄 测试并发用户数: {concurrent_users}")
            
            # 执行当前并发级别的测试
            result = self.concurrent_load_test(
                users, policies, 
                concurrent_users=concurrent_users, 
                test_duration=step_duration,
                endpoint="recommend"
            )
            
            result['concurrent_level'] = concurrent_users
            gradual_results.append(result)
            
            # 短暂休息让系统恢复
            time.sleep(5)
            
            # 检查是否出现严重问题（成功率过低）
            success_rate = result.get('request_stats', {}).get('success_rate', 0)
            if success_rate < 50:
                logger.warning(f"⚠️  成功率过低 ({success_rate:.1f}%)，提前结束测试")
                break
        
        # 分析渐进测试结果
        gradual_analysis = self._analyze_gradual_results(gradual_results)
        
        logger.info(f"✅ 渐进式负载测试完成")
        logger.info(f"  最高并发: {gradual_analysis.get('max_stable_concurrent', 0)}")
        logger.info(f"  峰值QPS: {gradual_analysis.get('peak_qps', 0):.2f}")
        
        return {
            'test_name': '渐进式负载测试',
            'test_results': gradual_results,
            'analysis': gradual_analysis,
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_gradual_results(self, results: List[Dict]) -> Dict:
        """分析渐进测试结果"""
        if not results:
            return {}
        
        # 找到性能拐点
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
            # 找到QPS最高的稳定点
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
    
    def stress_test(self, users: List[Dict], policies: List[Dict], 
                   concurrent_users: int = 100, test_duration: int = 300):
        """压力测试 - 高并发长时间测试"""
        logger.info(f"💪 开始压力测试")
        logger.info(f"  并发用户数: {concurrent_users}")
        logger.info(f"  测试持续时间: {test_duration}s ({test_duration/60:.1f}分钟)")
        
        return self.concurrent_load_test(
            users, policies,
            concurrent_users=concurrent_users,
            test_duration=test_duration,
            endpoint="recommend"
        )
    
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
                'test_types': list(set([r.get('test_name', 'Unknown') for r in test_results]))
            },
            'test_results': test_results,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'python_version': os.sys.version
            }
        }
        
        json_filename = os.path.join(output_dir, f"performance_report_{timestamp}.json")
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        # 生成图表报告
        self.generate_performance_charts(test_results, output_dir, timestamp)
        
        logger.info(f"📊 性能报告已生成到目录: {output_dir}")
        return json_filename
    
    def generate_performance_charts(self, test_results: List[Dict], output_dir: str, timestamp: str):
        """生成性能图表"""
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('政策推荐系统性能测试报告', fontsize=16, fontweight='bold')
        
        # 提取渐进测试数据
        gradual_test = None
        for result in test_results:
            if result.get('test_name') == '渐进式负载测试':
                gradual_test = result
                break
        
        if gradual_test and 'test_results' in gradual_test:
            gradual_data = gradual_test['test_results']
            concurrent_levels = [r['concurrent_level'] for r in gradual_data if 'request_stats' in r]
            qps_values = [r['request_stats']['requests_per_second'] for r in gradual_data if 'request_stats' in r]
            response_times = [r['response_time_stats']['avg_response_time'] for r in gradual_data if 'response_time_stats' in r]
            success_rates = [r['request_stats']['success_rate'] for r in gradual_data if 'request_stats' in r]
            
            # QPS vs 并发数
            axes[0, 0].plot(concurrent_levels, qps_values, 'b-o', linewidth=2, markersize=6)
            axes[0, 0].set_xlabel('并发用户数')
            axes[0, 0].set_ylabel('QPS (请求/秒)')
            axes[0, 0].set_title('QPS vs 并发用户数')
            axes[0, 0].grid(True, alpha=0.3)
            
            # 响应时间 vs 并发数
            axes[0, 1].plot(concurrent_levels, response_times, 'r-s', linewidth=2, markersize=6)
            axes[0, 1].set_xlabel('并发用户数')
            axes[0, 1].set_ylabel('平均响应时间 (ms)')
            axes[0, 1].set_title('响应时间 vs 并发用户数')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 成功率 vs 并发数
            axes[1, 0].plot(concurrent_levels, success_rates, 'g-^', linewidth=2, markersize=6)
            axes[1, 0].set_xlabel('并发用户数')
            axes[1, 0].set_ylabel('成功率 (%)')
            axes[1, 0].set_title('成功率 vs 并发用户数')
            axes[1, 0].set_ylim(0, 105)
            axes[1, 0].grid(True, alpha=0.3)
        
        # 响应时间分布（从所有测试中获取）
        all_response_times = []
        for result in test_results:
            if 'raw_results' in result:
                response_times = [r['response_time'] for r in result['raw_results'] if r.get('success', False)]
                all_response_times.extend(response_times)
        
        if all_response_times:
            axes[1, 1].hist(all_response_times, bins=50, alpha=0.7, color='purple', edgecolor='black')
            axes[1, 1].set_xlabel('响应时间 (ms)')
            axes[1, 1].set_ylabel('请求数量')
            axes[1, 1].set_title('响应时间分布')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        chart_filename = os.path.join(output_dir, f"performance_charts_{timestamp}.png")
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📈 性能图表已保存到: {chart_filename}")
    
    def run_comprehensive_performance_test(self):
        """运行综合性能测试套件"""
        logger.info("🎯 开始运行综合性能测试套件")
        
        # 检查服务状态
        if not self.check_service_health():
            logger.error("❌ 服务不可用，无法进行测试")
            return None
        
        # 加载测试数据
        policies, users = self.load_test_data(policy_limit=5, user_limit=10)
        
        if not policies or not users:
            logger.error("❌ 测试数据加载失败")
            return None
        
        all_test_results = []
        
        # 1. 基础并发测试 (10个并发用户，60秒)
        logger.info("\n" + "="*60)
        logger.info("1. 基础并发测试")
        logger.info("="*60)
        basic_test = self.concurrent_load_test(users, policies, concurrent_users=10, test_duration=60)
        all_test_results.append(basic_test)
        
        # 2. 渐进式负载测试
        logger.info("\n" + "="*60)
        logger.info("2. 渐进式负载测试")
        logger.info("="*60)
        gradual_test = self.gradual_load_test(users, policies, max_concurrent=30, step_size=5, step_duration=30)
        all_test_results.append(gradual_test)
        
        # 3. 压力测试 (如果前面测试表现良好)
        if basic_test.get('request_stats', {}).get('success_rate', 0) > 90:
            logger.info("\n" + "="*60)
            logger.info("3. 压力测试")
            logger.info("="*60)
            stress_test = self.stress_test(users, policies, concurrent_users=20, test_duration=180)
            all_test_results.append(stress_test)
        else:
            logger.warning("⚠️  基础测试成功率较低，跳过压力测试")
        
        # 生成综合报告
        report_file = self.generate_performance_report(all_test_results)
        
        logger.info("✅ 综合性能测试完成！")
        logger.info(f"📄 详细报告: {report_file}")
        
        return all_test_results

def main():
    """主函数"""
    print("🚀 政策推荐系统并发性能测试")
    print("=" * 80)
    
    # 创建性能测试器
    tester = ConcurrentPerformanceTester()
    
    # 运行综合性能测试
    results = tester.run_comprehensive_performance_test()
    
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
                print(f"   成功率: {stats.get('success_rate', 0):.2f}%")
                print(f"   QPS: {stats.get('requests_per_second', 0):.2f}")
            
            if 'response_time_stats' in result:
                rt_stats = result['response_time_stats']
                print(f"   平均响应时间: {rt_stats.get('avg_response_time', 0):.2f}ms")
                print(f"   95%响应时间: {rt_stats.get('p95_response_time', 0):.2f}ms")
            
            if 'analysis' in result:
                analysis = result['analysis']
                print(f"   最大稳定并发: {analysis.get('max_stable_concurrent', 0)}")
                print(f"   峰值QPS: {analysis.get('peak_qps', 0):.2f}")
        
        print("\n🎉 性能测试完成！请查看生成的报告文件获取详细分析。")
    else:
        print("❌ 性能测试失败")

if __name__ == "__main__":
    main()