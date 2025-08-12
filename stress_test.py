#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的循环测试脚本
持续发送请求到 recommend-single 接口
"""

import requests
import json
import time
import random
import os
from threading import Thread

class SimpleAPITester:
    def __init__(self, base_url="http://127.0.0.1:8081"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/recommend-single"
        self.users = []
        self.policies = []
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
    def load_test_data(self, policy_folder="policy_new", user_folder="user_dataset"):
        """加载测试数据"""
        print("📁 加载测试数据...")
        
        # 加载政策数据
        if os.path.exists(policy_folder):
            for file in os.listdir(policy_folder):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(policy_folder, file), 'r', encoding='utf-8') as f:
                            policy = json.load(f)
                            self.policies.append(policy)
                    except Exception as e:
                        print(f"加载政策文件 {file} 失败: {e}")
        
        # 加载用户数据
        if os.path.exists(user_folder):
            for file in os.listdir(user_folder):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(user_folder, file), 'r', encoding='utf-8') as f:
                            user = json.load(f)
                            self.users.append(user)
                    except Exception as e:
                        print(f"加载用户文件 {file} 失败: {e}")
        
        print(f"✅ 加载完成 - 政策: {len(self.policies)}, 用户: {len(self.users)}")
        return len(self.policies) > 0 and len(self.users) > 0
    
    def send_single_request(self):
        """发送单个请求"""
        try:
            # 随机选择用户和政策
            user = random.choice(self.users)
            policy = random.choice(self.policies)
            
            # 构造请求数据
            payload = {
                "user": user,
                "policy": policy
            }
            
            # 发送请求
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            self.request_count += 1
            
            if response.status_code == 200:
                self.success_count += 1
                result = response.json()
                score = result.get('result', 0)
                print(f"✅ 请求 {self.request_count}: 成功 - 匹配度: {score:.4f}")
            else:
                self.error_count += 1
                print(f"❌ 请求 {self.request_count}: 失败 - 状态码: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.request_count += 1
            self.error_count += 1
            print(f"⏰ 请求 {self.request_count}: 超时")
            
        except Exception as e:
            self.request_count += 1
            self.error_count += 1
            print(f"💥 请求 {self.request_count}: 异常 - {e}")
    
    def run_continuous_test(self, interval=1.0):
        """持续循环测试"""
        print(f"🚀 开始持续测试，每 {interval} 秒发送一次请求")
        print("按 Ctrl+C 停止测试")
        print("-" * 50)
        
        try:
            while True:
                self.send_single_request()
                
                # 每100次请求显示统计
                if self.request_count % 100 == 0:
                    success_rate = (self.success_count / self.request_count) * 100
                    print(f"📊 统计: 总请求 {self.request_count}, 成功 {self.success_count}, 失败 {self.error_count}, 成功率 {success_rate:.1f}%")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 测试停止")
            print(f"📊 最终统计:")
            print(f"   总请求数: {self.request_count}")
            print(f"   成功数: {self.success_count}")
            print(f"   失败数: {self.error_count}")
            if self.request_count > 0:
                success_rate = (self.success_count / self.request_count) * 100
                print(f"   成功率: {success_rate:.1f}%")

def run_concurrent_test(base_url="http://127.0.0.1:8081", threads=5, interval=0.1):
    """多线程并发测试"""
    print(f"🚀 启动 {threads} 个线程并发测试，每线程间隔 {interval} 秒")
    
    def worker_thread(thread_id):
        tester = SimpleAPITester(base_url)
        if not tester.load_test_data():
            print(f"线程 {thread_id}: 数据加载失败")
            return
        
        print(f"线程 {thread_id} 开始工作...")
        
        try:
            while True:
                tester.send_single_request()
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"线程 {thread_id} 停止")
    
    # 启动多个线程
    threads_list = []
    for i in range(threads):
        t = Thread(target=worker_thread, args=(i+1,), daemon=True)
        t.start()
        threads_list.append(t)
    
    try:
        # 主线程等待
        for t in threads_list:
            t.join()
    except KeyboardInterrupt:
        print("\n🛑 所有线程停止")

# 使用示例
if __name__ == "__main__":
    print("🎯 简单API测试脚本")
    print("=" * 40)
    
    # 选择测试模式
    print("请选择测试模式:")
    print("1. 单线程循环测试")
    print("2. 多线程并发测试")
    print("3. 快速测试 (高频率)")
    
    choice = input("请输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        # 单线程测试
        tester = SimpleAPITester()
        if tester.load_test_data():
            interval = float(input("请输入请求间隔秒数 (默认1.0): ") or "1.0")
            tester.run_continuous_test(interval)
        else:
            print("❌ 测试数据加载失败")
    
    elif choice == "2":
        # 多线程测试
        threads = int(input("请输入线程数 (默认5): ") or "5")
        interval = float(input("请输入每线程间隔秒数 (默认0.5): ") or "0.5")
        run_concurrent_test(threads=threads, interval=interval)
    
    elif choice == "3":
        # 快速测试
        print("🚀 启动快速测试模式 (10线程, 0.1秒间隔)")
        run_concurrent_test(threads=10, interval=0.1)
    
    else:
        print("❌ 无效选择")

# 或者直接使用这些快捷函数：

def quick_test(requests_count=100, interval=0.5):
    """快速测试指定次数"""
    tester = SimpleAPITester()
    if not tester.load_test_data():
        print("❌ 数据加载失败")
        return
    
    print(f"🚀 发送 {requests_count} 个请求，间隔 {interval} 秒")
    
    for i in range(requests_count):
        tester.send_single_request()
        if i < requests_count - 1:  # 最后一次不等待
            time.sleep(interval)
    
    print("✅ 测试完成")

def stress_test(duration_seconds=60):
    """压力测试，指定时长"""
    tester = SimpleAPITester()
    if not tester.load_test_data():
        print("❌ 数据加载失败")
        return
    
    print(f"🚀 压力测试 {duration_seconds} 秒")
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        tester.send_single_request()
        time.sleep(0.01)  # 10ms间隔，高频请求
    
    print("✅ 压力测试完成")

# 一行代码启动测试的例子：
# quick_test(50, 0.2)  # 发送50个请求，间隔0.2秒
# stress_test(30)      # 压力测试30秒