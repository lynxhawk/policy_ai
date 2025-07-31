import json
import os
import random
from pathlib import Path

def process_user_data(folder_path="user_dataset"):
    """
    处理user_dataset文件夹下的JSON文件，为每个用户添加年龄和性别字段
    年龄计算公式：22 + 毕业时间
    性别随机分配：男/女
    字段顺序：毕业时间 -> 年龄 -> 性别
    """
    
    # 确保文件夹存在
    if not os.path.exists(folder_path):
        print(f"错误：文件夹 '{folder_path}' 不存在")
        return
    
    # 获取文件夹下所有JSON文件
    json_files = list(Path(folder_path).glob("*.json"))
    
    if not json_files:
        print(f"在文件夹 '{folder_path}' 中没有找到JSON文件")
        return
    
    processed_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            print(f"正在处理文件: {json_file.name}")
            
            # 读取JSON文件
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否包含毕业时间字段
            if "毕业时间" in data:
                graduation_years = data["毕业时间"]
                
                # 计算年龄：22 + 毕业时间
                age = 22 + graduation_years
                
                # 随机生成性别
                gender = random.choice(["男", "女"])
                
                # 重新构建有序字典，确保字段顺序：毕业时间 -> 年龄 -> 性别
                ordered_data = {}
                for key, value in data.items():
                    ordered_data[key] = value
                    # 在毕业时间字段后立即插入年龄和性别字段
                    if key == "毕业时间":
                        ordered_data["年龄"] = age
                        ordered_data["性别"] = gender
                
                print(f"  用户ID: {data.get('用户ID', 'Unknown')}")
                print(f"  毕业时间: {graduation_years}年")
                print(f"  计算年龄: {age}岁")
                print(f"  随机性别: {gender}")
                
                # 将更新后的数据写回文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(ordered_data, f, ensure_ascii=False, indent=2)
                
                processed_count += 1
                print(f"  ✓ 文件已更新\n")
                
            else:
                print(f"  ⚠️ 警告：文件中没有找到'毕业时间'字段\n")
                error_count += 1
                
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON解析错误: {e}\n")
            error_count += 1
        except Exception as e:
            print(f"  ❌ 处理文件时出错: {e}\n")
            error_count += 1
    
    # 输出处理结果统计
    print("=" * 50)
    print("处理完成！")
    print(f"成功处理文件数: {processed_count}")
    print(f"错误文件数: {error_count}")
    print(f"总文件数: {len(json_files)}")

def preview_changes(folder_path="user_dataset"):
    """
    预览将要进行的修改，不实际修改文件
    """
    print("预览模式 - 不会修改文件")
    print("=" * 50)
    
    if not os.path.exists(folder_path):
        print(f"错误：文件夹 '{folder_path}' 不存在")
        return
    
    json_files = list(Path(folder_path).glob("*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "毕业时间" in data:
                graduation_years = data["毕业时间"]
                age = 22 + graduation_years
                gender = random.choice(["男", "女"])
                
                print(f"文件: {json_file.name}")
                print(f"  用户ID: {data.get('用户ID', 'Unknown')}")
                print(f"  当前毕业时间: {graduation_years}年")
                print(f"  将添加年龄: {age}岁")
                print(f"  将添加性别: {gender}")
                print(f"  是否已有年龄字段: {'是' if '年龄' in data else '否'}")
                print(f"  是否已有性别字段: {'是' if '性别' in data else '否'}")
                print()
                
        except Exception as e:
            print(f"读取文件 {json_file.name} 时出错: {e}\n")

if __name__ == "__main__":
    print("用户数据处理脚本")
    print("功能：为JSON文件添加年龄字段（年龄 = 22 + 毕业时间）和性别字段（随机男/女）")
    print()
    
    # 询问用户操作
    choice = input("请选择操作：\n1. 预览修改\n2. 执行修改\n请输入数字 (1或2): ").strip()
    
    if choice == "1":
        preview_changes()
    elif choice == "2":
        confirm = input("确认要修改文件吗？(y/n): ").strip().lower()
        if confirm in ['y', 'yes', '是']:
            process_user_data()
        else:
            print("操作已取消")
    else:
        print("无效选择，程序退出")