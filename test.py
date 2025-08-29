#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的API测试脚本
测试所有端口的 recommend-single 接口
政策1-8用于用户匹配和预审，政策9-16用于企业匹配和预审
"""

import requests
import json
import time
import random
import os
from threading import Thread

class SimpleAPITester:
    def __init__(self):
        # 定义所有服务端口和对应的数据文件夹及接口
        self.services = {
            8081: {"name": "policy_user_match", "user_folder": "user_dataset", "policy_folder": "policy_new", "endpoint": "recommend-single", "policy_range": (1, 8)},
            8082: {"name": "policy_user_audit", "user_folder": "user_dataset", "policy_folder": "policy_new", "endpoint": "preaudit-single", "policy_range": (1, 8)},
            8083: {"name": "policy_enterprise_match", "user_folder": "enterprise_dataset", "policy_folder": "policy_new", "endpoint": "recommend-single", "policy_range": (9, 16)},
            8084: {"name": "policy_enterprise_audit", "user_folder": "enterprise_dataset", "policy_folder": "policy_new", "endpoint": "preaudit-single", "policy_range": (9, 16)}
        }
        
        self.base_url = "http://127.0.0.1"
        self.stats = {port: {"success": 0, "error": 0, "total": 0} for port in self.services.keys()}
        
    def load_test_data(self, port):
        """为指定端口加载测试数据"""
        service = self.services[port]
        users = []
        policies = []
        
        # 加载政策数据 - 根据端口选择对应范围的政策
        policy_folder = service["policy_folder"]
        policy_start, policy_end = service["policy_range"]
        
        if os.path.exists(policy_folder):
            # 获取所有政策文件并排序
            policy_files = [f for f in os.listdir(policy_folder) if f.endswith('.json')]
            policy_files.sort()  # 确保顺序一致
            
            # 根据政策范围选择对应的文件
            for i, file in enumerate(policy_files):
                policy_number = i + 1  # 政策编号从1开始
                if policy_start <= policy_number <= policy_end:
                    try:
                        with open(os.path.join(policy_folder, file), 'r', encoding='utf-8') as f:
                            policy = json.load(f)
                            policies.append(policy)
                    except Exception as e:
                        print(f"端口 {port} - 加载政策文件 {file} 失败: {e}")
        
        # 加载用户/企业数据
        user_folder = service["user_folder"]
        if os.path.exists(user_folder):
            for file in os.listdir(user_folder):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(user_folder, file), 'r', encoding='utf-8') as f:
                            user = json.load(f)
                            users.append(user)
                    except Exception as e:
                        print(f"端口 {port} - 加载{'企业' if 'enterprise' in service['user_folder'] else '用户'}文件 {file} 失败: {e}")
        
        data_type = "企业" if "enterprise" in service["user_folder"] else "用户"
        print(f"端口 {port} ({service['name']}) - 加载数据: 政策 {len(policies)} (编号{policy_start}-{policy_end}), {data_type} {len(users)}")
        return users, policies
    
    def format_result(self, result, endpoint):
        """格式化返回结果"""
        if endpoint == "preaudit-single":
            # 预审结果返回0或1
            if isinstance(result, (int, float)):
                return int(round(result))  # 四舍五入转为整数
            return result
        else:
            # 匹配度保留两位小数
            if isinstance(result, (int, float)):
                return round(float(result), 2)
            return result
    
    def send_request(self, port, user, policy):
        """发送单个请求到指定端口"""
        try:
            service = self.services[port]
            endpoint = f"{self.base_url}:{port}/{service['endpoint']}"
            
            # 根据端口决定payload的key名称
            if port in [8083, 8084]:  # 企业相关接口
                payload = {
                    "enterprise": user,  # 企业接口使用enterprise字段
                    "policy": policy
                }
            else:  # 用户相关接口
                payload = {
                    "user": user,  # 用户接口使用user字段
                    "policy": policy
                }
            
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            self.stats[port]["total"] += 1
            
            if response.status_code == 200:
                self.stats[port]["success"] += 1
                result = response.json()
                raw_result = result.get('result', 0)
                formatted_result = self.format_result(raw_result, service['endpoint'])
                
                if service['endpoint'] == "preaudit-single":
                    print(f"✅ 端口 {port} ({service['endpoint']}) - 请求 {self.stats[port]['total']}: 预审结果 {formatted_result}")
                else:
                    print(f"✅ 端口 {port} ({service['endpoint']}) - 请求 {self.stats[port]['total']}: 匹配度 {formatted_result}")
                return True
            else:
                self.stats[port]["error"] += 1
                print(f"❌ 端口 {port} ({service['endpoint']}) - 请求 {self.stats[port]['total']}: 状态码 {response.status_code}")
                print(f"   响应内容: {response.text[:200]}...")
                return False
                
        except requests.exceptions.Timeout:
            self.stats[port]["total"] += 1
            self.stats[port]["error"] += 1
            print(f"⏰ 端口 {port} ({self.services[port]['endpoint']}) - 请求 {self.stats[port]['total']}: 超时")
            return False
            
        except Exception as e:
            self.stats[port]["total"] += 1
            self.stats[port]["error"] += 1
            print(f"💥 端口 {port} ({self.services[port]['endpoint']}) - 请求 {self.stats[port]['total']}: 异常 - {e}")
            return False
    
    def test_single_port(self, port, requests_count=10, interval=0.1):
        """测试单个端口"""
        service_info = self.services[port]
        policy_range = f"{service_info['policy_range'][0]}-{service_info['policy_range'][1]}"
        print(f"🚀 测试端口 {port} ({service_info['name']}) - 使用政策{policy_range}")
        
        users, policies = self.load_test_data(port)
        if not users or not policies:
            print(f"❌ 端口 {port} - 数据加载失败")
            return
        
        for i in range(requests_count):
            user = random.choice(users)
            policy = random.choice(policies)
            self.send_request(port, user, policy)
            
            if i < requests_count - 1:
                time.sleep(interval)
    
    def test_all_ports_concurrent(self, requests_per_port=10, interval=0.1):
        """并发测试所有端口"""
        print(f"🚀 并发测试所有端口，每端口 {requests_per_port} 个请求")
        print("📋 测试规则:")
        print("   - 政策1-8: 用于用户匹配和预审测试")
        print("   - 政策9-16: 用于企业匹配和预审测试")
        print("   - 用户接口payload使用'user'字段")
        print("   - 企业接口payload使用'enterprise'字段")
        print("   - 匹配度结果: 保留两位小数")
        print("   - 预审结果: 返回0或1")
        print("-" * 60)
        
        def worker_thread(port):
            self.test_single_port(port, requests_per_port, interval)
        
        # 启动所有端口的测试线程
        threads = []
        for port in self.services.keys():
            t = Thread(target=worker_thread, args=(port,), daemon=True)
            t.start()
            threads.append(t)
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 打印统计结果
        self.print_stats()
    
    def print_stats(self):
        """打印统计结果"""
        print("\n" + "=" * 70)
        print("📊 测试结果统计")
        print("=" * 70)
        
        total_requests = 0
        total_success = 0
        total_errors = 0
        
        for port, stats in self.stats.items():
            service_info = self.services[port]
            service_name = service_info['name']
            policy_range = f"{service_info['policy_range'][0]}-{service_info['policy_range'][1]}"
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            print(f"端口 {port} ({service_name}) - 政策{policy_range}:")
            print(f"  总请求: {stats['total']}")
            print(f"  成功: {stats['success']}")
            print(f"  失败: {stats['error']}")
            print(f"  成功率: {success_rate:.1f}%")
            print()
            
            total_requests += stats['total']
            total_success += stats['success']
            total_errors += stats['error']
        
        if total_requests > 0:
            overall_success_rate = (total_success / total_requests * 100)
            print(f"🎯 总体统计:")
            print(f"  总请求数: {total_requests}")
            print(f"  总成功数: {total_success}")
            print(f"  总失败数: {total_errors}")
            print(f"  总成功率: {overall_success_rate:.1f}%")
            print()
            print("📋 结果格式说明:")
            print("  - 匹配度 (recommend-single): 保留两位小数")
            print("  - 预审结果 (preaudit-single): 返回0或1")

    def test_specific_port(self, port, requests_count=10, interval=0.1):
        """测试指定端口"""
        if port not in self.services:
            print(f"❌ 端口 {port} 不在支持的服务列表中")
            print(f"支持的端口: {list(self.services.keys())}")
            return
        
        print(f"🎯 单独测试端口 {port}")
        self.test_single_port(port, requests_count, interval)
        self.print_stats()

def quick_test(requests_per_port=10, interval=0.1):
    """快速测试所有端口"""
    tester = SimpleAPITester()
    tester.test_all_ports_concurrent(requests_per_port, interval)

def test_single_service(port, requests_count=10, interval=0.1):
    """测试单个服务"""
    tester = SimpleAPITester()
    tester.test_specific_port(port, requests_count, interval)

# 使用示例
if __name__ == "__main__":
    print("🎯 API快速测试脚本 v2.0")
    print("=" * 50)
    print("支持的服务:")
    print("  8081: 用户政策匹配 (政策1-8)")
    print("  8082: 用户政策预审 (政策1-8)")
    print("  8083: 企业政策匹配 (政策9-16)")
    print("  8084: 企业政策预审 (政策9-16)")
    print()
    
    # 选择测试模式
    test_mode = input("选择测试模式 (1=全部测试, 2=单端口测试): ").strip()
    
    if test_mode == "2":
        # 单端口测试
        port = int(input("输入要测试的端口号 (8081/8082/8083/8084): "))
        requests_count = int(input("发送多少个请求? (默认10): ") or "10")
        interval = float(input("请求间隔秒数? (默认0.1): ") or "0.1")
        
        print(f"\n🚀 开始测试端口 {port} - {requests_count} 个请求，间隔 {interval} 秒")
        test_single_service(port, requests_count, interval)
    else:
        # 全部测试
        requests_per_port = int(input("每个端口发送多少个请求? (默认10): ") or "10")
        interval = float(input("请求间隔秒数? (默认0.1): ") or "0.1")
        
        print(f"\n🚀 开始测试所有端口 - 每端口 {requests_per_port} 个请求，间隔 {interval} 秒")
        quick_test(requests_per_port, interval)
    
    print("\n✅ 测试完成!")

# 快速使用示例：
# quick_test(20, 0.2)                    # 全部测试，每端口20个请求，间隔0.2秒  
# test_single_service(8081, 15, 0.1)     # 只测试8081端口，15个请求，间隔0.1秒