#!/usr/bin/env python3
"""
政策推荐系统完整数据集测试
测试所有8个政策 × 50个用户 = 400个匹配组合
"""

import requests
import json
import time
import os
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FullDatasetTester:
    """完整数据集测试类"""
    
    def __init__(self, base_url="http://127.0.0.1:8081"):
        self.base_url = base_url
        self.policies = []
        self.users = []
        self.test_results = {
            'batch_results': [],  # 批量推荐结果
            'individual_results': [],  # 单个推荐结果
            'performance_metrics': [],
            'error_logs': []
        }
    
    def load_all_data(self):
        """加载所有政策和用户数据"""
        logger.info("🔄 开始加载完整数据集...")
        
        # 加载所有政策数据
        policy_folder = "policy_new"
        if os.path.exists(policy_folder):
            policy_files = sorted([f for f in os.listdir(policy_folder) if f.endswith('.json')])
            logger.info(f"发现 {len(policy_files)} 个政策文件")
            
            for file in policy_files:
                try:
                    with open(os.path.join(policy_folder, file), 'r', encoding='utf-8') as f:
                        policy_data = json.load(f)
                        self.policies.append(policy_data)
                        logger.info(f"  ✅ 加载政策: {policy_data.get('政策编号', file)}")
                except Exception as e:
                    logger.error(f"  ❌ 加载政策文件 {file} 失败: {e}")
        else:
            logger.warning(f"政策文件夹 {policy_folder} 不存在，使用示例数据")
            self._create_sample_policies()
        
        # 加载所有用户数据
        user_folder = "user_dataset"
        if os.path.exists(user_folder):
            user_files = sorted([f for f in os.listdir(user_folder) if f.endswith('.json')])
            logger.info(f"发现 {len(user_files)} 个用户文件")
            
            for file in user_files:
                try:
                    with open(os.path.join(user_folder, file), 'r', encoding='utf-8') as f:
                        user_data = json.load(f)
                        self.users.append(user_data)
                        logger.info(f"  ✅ 加载用户: {user_data.get('用户ID', file)}")
                except Exception as e:
                    logger.error(f"  ❌ 加载用户文件 {file} 失败: {e}")
        else:
            logger.warning(f"用户文件夹 {user_folder} 不存在，使用示例数据")
            self._create_sample_users()
        
        logger.info(f"📊 数据加载完成 - 政策: {len(self.policies)} 个, 用户: {len(self.users)} 个")
        logger.info(f"🎯 预计测试组合数: {len(self.policies)} × {len(self.users)} = {len(self.policies) * len(self.users)} 个")
        
        return len(self.policies), len(self.users)
    
    def _create_sample_policies(self):
        """创建示例政策数据"""
        sample_policies = [
            {
                "政策编号": "POL0001",
                "标题": "高校毕业生社保补贴（灵活就业）",
                "条件": {
                    "逻辑": "AND",
                    "规则": [
                        {"字段": "毕业时间", "操作符": "<=", "值": 2, "描述": "2年以内"},
                        {"字段": "就业类型", "操作符": "=", "值": "灵活就业", "描述": "灵活就业"},
                        {"字段": "养老保险", "操作符": "=", "值": "是", "描述": "养老保险"}
                    ]
                }
            },
            {
                "政策编号": "POL0002",
                "标题": "创业担保贷款",
                "条件": {
                    "逻辑": "AND",
                    "规则": [
                        {"字段": "就业类型", "操作符": "=", "值": "自主创业", "描述": "自主创业"},
                        {"字段": "年龄", "操作符": "<=", "值": 45, "描述": "45岁以下"}
                    ]
                }
            }
        ]
        self.policies = sample_policies
    
    def _create_sample_users(self):
        """创建示例用户数据"""
        base_user = {
            "最高学历": "本科",
            "毕业时间": 2,
            "年龄": 25,
            "籍贯": "浙江省",
            "专业": "计算机科学",
            "征地人员": "否",
            "缴纳社保": "是",
            "养老保险": "是",
            "困难人员": "否"
        }
        
        job_types = ["受雇就业", "灵活就业", "自主创业", "未就业"]
        sample_users = []
        
        for i in range(10):  # 创建10个示例用户
            user = base_user.copy()
            user["用户ID"] = f"U{i+1:04d}"
            user["就业类型"] = job_types[i % len(job_types)]
            user["年龄"] = 23 + (i % 20)
            user["毕业时间"] = (i % 5) + 1
            sample_users.append(user)
        
        self.users = sample_users
    
    def test_all_users_all_policies_batch(self):
        """测试每个用户对所有政策的批量推荐"""
        logger.info("📊 开始批量推荐测试 - 每个用户对所有政策")
        
        total_users = len(self.users)
        batch_results = []
        
        for i, user in enumerate(self.users):
            user_id = user.get('用户ID', f'User_{i}')
            logger.info(f"🔄 测试用户 {user_id} ({i+1}/{total_users})")
            
            start_time = time.time()
            
            try:
                payload = {
                    "user": user,
                    "policies": self.policies
                }
                
                response = requests.post(
                    f"{self.base_url}/recommend",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    result_data = response.json()
                    scores = result_data.get('result', [])
                    
                    # 记录详细结果
                    user_result = {
                        'user_id': user_id,
                        'user_data': user,
                        'scores': scores,
                        'response_time': response_time,
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # 创建用户-政策匹配详情
                    policy_matches = []
                    for j, score in enumerate(scores):
                        if j < len(self.policies):
                            policy_match = {
                                'user_id': user_id,
                                'policy_id': self.policies[j].get('政策编号', f'Policy_{j}'),
                                'policy_title': self.policies[j].get('标题', ''),
                                'match_score': score,
                                'user_age': user.get('年龄'),
                                'user_education': user.get('最高学历'),
                                'user_job_type': user.get('就业类型'),
                                'user_graduation_time': user.get('毕业时间')
                            }
                            policy_matches.append(policy_match)
                    
                    user_result['policy_matches'] = policy_matches
                    batch_results.append(user_result)
                    
                    # 显示匹配结果摘要
                    avg_score = np.mean(scores) if scores else 0
                    max_score = max(scores) if scores else 0
                    logger.info(f"  ✅ 用户 {user_id}: 平均分 {avg_score:.1f}, 最高分 {max_score}, 响应时间 {response_time:.1f}ms")
                    
                else:
                    error_result = {
                        'user_id': user_id,
                        'success': False,
                        'error': f"HTTP {response.status_code}: {response.text}",
                        'response_time': response_time,
                        'timestamp': datetime.now().isoformat()
                    }
                    batch_results.append(error_result)
                    logger.error(f"  ❌ 用户 {user_id} 测试失败: {response.status_code}")
                
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                error_result = {
                    'user_id': user_id,
                    'success': False,
                    'error': str(e),
                    'response_time': response_time,
                    'timestamp': datetime.now().isoformat()
                }
                batch_results.append(error_result)
                logger.error(f"  ❌ 用户 {user_id} 测试异常: {e}")
            
            # 短暂休息，避免过于频繁的请求
            time.sleep(0.1)
        
        self.test_results['batch_results'] = batch_results
        
        # 生成批量测试统计
        successful_tests = [r for r in batch_results if r.get('success', False)]
        failed_tests = [r for r in batch_results if not r.get('success', False)]
        
        logger.info("📊 批量测试统计:")
        logger.info(f"  成功用户数: {len(successful_tests)}/{len(self.users)}")
        logger.info(f"  失败用户数: {len(failed_tests)}")
        logger.info(f"  成功率: {len(successful_tests)/len(self.users)*100:.1f}%")
        
        if successful_tests:
            avg_response_time = np.mean([r['response_time'] for r in successful_tests])
            logger.info(f"  平均响应时间: {avg_response_time:.1f}ms")
        
        return batch_results
    
    def test_multi_user_batch_recommendation(self):
        """测试多用户批量推荐接口"""
        logger.info("👥 开始多用户批量推荐测试")
        
        start_time = time.time()
        
        try:
            payload = {
                "users": self.users,
                "policies": self.policies
            }
            
            response = requests.post(
                f"{self.base_url}/batch-recommend",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=180  # 增加超时时间
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                result_data = response.json()
                scores = result_data.get('result', [])
                
                expected_count = len(self.users) * len(self.policies)
                actual_count = len(scores)
                
                logger.info(f"✅ 多用户批量推荐成功:")
                logger.info(f"  用户数: {len(self.users)}")
                logger.info(f"  政策数: {len(self.policies)}")
                logger.info(f"  预期结果数: {expected_count}")
                logger.info(f"  实际结果数: {actual_count}")
                logger.info(f"  结果完整性: {'✅ 完整' if actual_count == expected_count else '❌ 不完整'}")
                logger.info(f"  响应时间: {response_time:.1f}ms")
                
                if scores:
                    avg_score = np.mean(scores)
                    logger.info(f"  平均匹配分数: {avg_score:.2f}")
                
                # 保存多用户批量结果
                multi_batch_result = {
                    'test_type': 'multi_user_batch',
                    'user_count': len(self.users),
                    'policy_count': len(self.policies),
                    'expected_results': expected_count,
                    'actual_results': actual_count,
                    'complete': actual_count == expected_count,
                    'scores': scores,
                    'response_time': response_time,
                    'success': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.test_results['performance_metrics'].append(multi_batch_result)
                return multi_batch_result
                
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ 多用户批量推荐失败: {error_msg}")
                
                error_result = {
                    'test_type': 'multi_user_batch',
                    'success': False,
                    'error': error_msg,
                    'response_time': response_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.test_results['error_logs'].append(error_result)
                return error_result
                
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            logger.error(f"❌ 多用户批量推荐异常: {e}")
            
            error_result = {
                'test_type': 'multi_user_batch',
                'success': False,
                'error': str(e),
                'response_time': response_time,
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results['error_logs'].append(error_result)
            return error_result
    
    def generate_match_matrix(self):
        """生成用户-政策匹配矩阵"""
        logger.info("📊 生成匹配矩阵分析...")
        
        batch_results = self.test_results.get('batch_results', [])
        successful_results = [r for r in batch_results if r.get('success', False)]
        
        if not successful_results:
            logger.warning("⚠️  无成功的批量测试结果，无法生成匹配矩阵")
            return None
        
        # 创建匹配矩阵
        user_ids = [r['user_id'] for r in successful_results]
        policy_ids = [p.get('政策编号', f'Policy_{i}') for i, p in enumerate(self.policies)]
        
        match_matrix = []
        user_summaries = []
        
        for result in successful_results:
            user_id = result['user_id']
            scores = result.get('scores', [])
            user_data = result.get('user_data', {})
            
            # 用户匹配行
            match_row = {
                'user_id': user_id,
                'age': user_data.get('年龄', 'N/A'),
                'education': user_data.get('最高学历', 'N/A'),
                'job_type': user_data.get('就业类型', 'N/A'),
                'graduation_time': user_data.get('毕业时间', 'N/A')
            }
            
            for i, score in enumerate(scores):
                if i < len(policy_ids):
                    match_row[policy_ids[i]] = score
            
            match_matrix.append(match_row)
            
            # 用户统计摘要
            user_summary = {
                'user_id': user_id,
                'total_policies': len(scores),
                'avg_score': np.mean(scores) if scores else 0,
                'max_score': max(scores) if scores else 0,
                'min_score': min(scores) if scores else 0,
                'high_score_count': len([s for s in scores if s >= 80]),
                'zero_score_count': len([s for s in scores if s == 0])
            }
            user_summaries.append(user_summary)
        
        # 政策统计摘要
        policy_summaries = []
        for i, policy in enumerate(self.policies):
            policy_id = policy.get('政策编号', f'Policy_{i}')
            policy_scores = []
            
            for result in successful_results:
                scores = result.get('scores', [])
                if i < len(scores):
                    policy_scores.append(scores[i])
            
            if policy_scores:
                policy_summary = {
                    'policy_id': policy_id,
                    'policy_title': policy.get('标题', ''),
                    'total_users': len(policy_scores),
                    'avg_score': np.mean(policy_scores),
                    'max_score': max(policy_scores),
                    'min_score': min(policy_scores),
                    'match_rate': len([s for s in policy_scores if s > 0]) / len(policy_scores) * 100,
                    'high_match_rate': len([s for s in policy_scores if s >= 80]) / len(policy_scores) * 100
                }
                policy_summaries.append(policy_summary)
        
        # 保存矩阵分析结果
        matrix_analysis = {
            'match_matrix': match_matrix,
            'user_summaries': user_summaries,
            'policy_summaries': policy_summaries,
            'total_combinations': len(successful_results) * len(self.policies),
            'generation_time': datetime.now().isoformat()
        }
        
        return matrix_analysis
    
    def save_detailed_results(self, filename='full_dataset_test_results.json'):
        """保存详细测试结果"""
        logger.info(f"💾 保存详细测试结果到: {filename}")
        
        # 生成匹配矩阵
        matrix_analysis = self.generate_match_matrix()
        
        # 综合测试报告
        full_report = {
            'test_summary': {
                'test_time': datetime.now().isoformat(),
                'total_policies': len(self.policies),
                'total_users': len(self.users),
                'expected_combinations': len(self.policies) * len(self.users),
                'policy_list': [p.get('政策编号', '') for p in self.policies],
                'user_count_by_job_type': self._analyze_user_distribution()
            },
            'test_results': self.test_results,
            'matrix_analysis': matrix_analysis
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 测试结果已保存")
        return filename
    
    def _analyze_user_distribution(self):
        """分析用户分布"""
        job_type_count = {}
        for user in self.users:
            job_type = user.get('就业类型', '未知')
            job_type_count[job_type] = job_type_count.get(job_type, 0) + 1
        return job_type_count
    
    def generate_summary_report(self):
        """生成测试摘要报告"""
        logger.info("📋 生成测试摘要报告...")
        
        batch_results = self.test_results.get('batch_results', [])
        successful_tests = [r for r in batch_results if r.get('success', False)]
        failed_tests = [r for r in batch_results if not r.get('success', False)]
        
        print("\n" + "="*80)
        print("🎯 完整数据集测试摘要报告")
        print("="*80)
        
        print(f"📊 测试数据规模:")
        print(f"  政策数量: {len(self.policies)}")
        print(f"  用户数量: {len(self.users)}")
        print(f"  预期测试组合: {len(self.policies)} × {len(self.users)} = {len(self.policies) * len(self.users)}")
        
        print(f"\n✅ 批量推荐测试结果:")
        print(f"  成功用户数: {len(successful_tests)}")
        print(f"  失败用户数: {len(failed_tests)}")
        print(f"  成功率: {len(successful_tests)/len(self.users)*100:.1f}%")
        
        if successful_tests:
            all_scores = []
            for result in successful_tests:
                all_scores.extend(result.get('scores', []))
            
            if all_scores:
                print(f"\n📈 匹配分数统计:")
                print(f"  总匹配组合数: {len(all_scores)}")
                print(f"  平均匹配分数: {np.mean(all_scores):.2f}")
                print(f"  最高匹配分数: {max(all_scores)}")
                print(f"  最低匹配分数: {min(all_scores)}")
                print(f"  高分匹配 (≥80): {len([s for s in all_scores if s >= 80])} ({len([s for s in all_scores if s >= 80])/len(all_scores)*100:.1f}%)")
                print(f"  零分匹配: {len([s for s in all_scores if s == 0])} ({len([s for s in all_scores if s == 0])/len(all_scores)*100:.1f}%)")
        
        # 性能统计
        if successful_tests:
            response_times = [r['response_time'] for r in successful_tests]
            print(f"\n⚡ 性能统计:")
            print(f"  平均响应时间: {np.mean(response_times):.1f}ms")
            print(f"  最快响应时间: {min(response_times):.1f}ms")
            print(f"  最慢响应时间: {max(response_times):.1f}ms")
        
        # 用户分布统计
        user_distribution = self._analyze_user_distribution()
        print(f"\n👥 用户分布统计:")
        for job_type, count in user_distribution.items():
            print(f"  {job_type}: {count} 人")
        
        print("\n" + "="*80)
        print("✅ 测试完成！所有数据已全部测试。")
        print("="*80)

def main():
    """主函数"""
    print("🚀 政策推荐系统完整数据集测试")
    print("📋 测试目标: 8个政策 × 50个用户 = 400个匹配组合")
    print("="*80)
    
    # 创建测试器
    tester = FullDatasetTester()
    
    # 加载完整数据集
    policy_count, user_count = tester.load_all_data()
    
    if policy_count == 0 or user_count == 0:
        print("❌ 数据加载失败，无法进行测试")
        return
    
    # 开始测试
    test_start_time = time.time()
    
    # 1. 批量推荐测试 - 每个用户对所有政策
    print("\n🎯 开始批量推荐测试...")
    batch_results = tester.test_all_users_all_policies_batch()
    
    # 2. 多用户批量推荐测试
    print("\n👥 开始多用户批量推荐测试...")
    multi_batch_result = tester.test_multi_user_batch_recommendation()
    
    test_end_time = time.time()
    total_test_time = test_end_time - test_start_time
    
    # 保存详细结果
    result_file = tester.save_detailed_results()
    
    # 生成摘要报告
    tester.generate_summary_report()
    
    print(f"\n📄 详细测试结果已保存到: {result_file}")
    print(f"⏱️  总测试时间: {total_test_time:.1f} 秒")

if __name__ == "__main__":
    main()