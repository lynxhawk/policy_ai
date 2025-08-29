#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的API测试脚本
测试所有端口的 recommend-single 接口
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
            8081: {"name": "policy_user_match", "user_folder": "user_dataset", "policy_folder": "policy_new", "endpoint": "recommend-single"},
            8082: {"name": "policy_user_audit", "user_folder": "user_dataset", "policy_folder": "policy_new", "endpoint": "preaudit-single"},
            8083: {"name": "policy_enterprise_match", "user_folder": "enterprise_dataset", "policy_folder": "policy_new", "endpoint": "recommend-single"},
            8084: {"name": "policy_enterprise_audit", "user_folder": "enterprise_dataset", "policy_folder": "policy_new", "endpoint": "preaudit-single"}
        }
        
        self.base_url = "http://127.0.0.1"
        self.stats = {port: {"success": 0, "error": 0, "total": 0} for port in self.services.keys()}
        
    def load_test_data(self, port):
        """为指定端口加载测试数据"""
        service = self.services[port]
        users = []
        policies = []
        
        # 加载政策数据
        policy_folder = service["policy_folder"]
        if os.path.exists(policy_folder):
            for file in os.listdir(policy_folder):
                if file.endswith('.json'):
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
                        print(f"端口 {port} - 加载用户文件 {file} 失败: {e}")
        
        print(f"端口 {port} ({service['name']}) - 加载数据: 政策 {len(policies)}, 用户 {len(users)}")
        return users, policies
    
    def send_request(self, port, user, policy):
        """发送单个请求到指定端口"""
        try:
            service = self.services[port]
            endpoint = f"{self.base_url}:{port}/{service['endpoint']}"
            payload = {
                "user": user,
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
                score = result.get('result', 0)
                print(f"✅ 端口 {port} ({service['endpoint']}) - 请求 {self.stats[port]['total']}: 匹配度 {score:.4f}")
                return True
            else:
                self.stats[port]["error"] += 1
                print(f"❌ 端口 {port} ({service['endpoint']}) - 请求 {self.stats[port]['total']}: 状态码 {response.status_code}")
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
        print(f"🚀 测试端口 {port} ({self.services[port]['name']})")
        
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
        print("\n" + "=" * 60)
        print("📊 测试结果统计")
        print("=" * 60)
        
        total_requests = 0
        total_success = 0
        total_errors = 0
        
        for port, stats in self.stats.items():
            service_name = self.services[port]['name']
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            print(f"端口 {port} ({service_name}):")
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

def quick_test(requests_per_port=10, interval=0.1):
    """快速测试所有端口"""
    tester = SimpleAPITester()
    tester.test_all_ports_concurrent(requests_per_port, interval)

# 使用示例
if __name__ == "__main__":
    print("🎯 API快速测试脚本")
    print("=" * 40)
    
    # 获取用户输入
    requests_per_port = int(input("每个端口发送多少个请求? (默认10): ") or "10")
    interval = float(input("请求间隔秒数? (默认0.1): ") or "0.1")
    
    print(f"\n🚀 开始测试 - 每端口 {requests_per_port} 个请求，间隔 {interval} 秒")
    
    # 执行测试
    quick_test(requests_per_port, interval)
    
    print("\n✅ 测试完成!")

# 一行代码启动测试的例子：
# quick_test(20, 0.2)  # 每端口20个请求，间隔0.2秒