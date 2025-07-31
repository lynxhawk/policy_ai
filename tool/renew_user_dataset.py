import os
import json
import re

def rename_and_update_json_files(directory_path):
    """
    批量重命名JSON文件并更新文件内容中的用户ID
    从 U001.json -> U0001.json 格式
    """
    # 检查目录是否存在
    if not os.path.exists(directory_path):
        print(f"错误: 目录 '{directory_path}' 不存在")
        return
    
    # 获取所有匹配模式的JSON文件
    files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
    pattern = re.compile(r'^U(\d{3})\.json$')  # 匹配 U001.json 格式
    
    matching_files = []
    for file in files:
        match = pattern.match(file)
        if match:
            matching_files.append((file, match.group(1)))
    
    if not matching_files:
        print("未找到符合 U001.json 格式的文件")
        return
    
    print(f"找到 {len(matching_files)} 个需要处理的文件:")
    
    for old_filename, number in matching_files:
        old_path = os.path.join(directory_path, old_filename)
        new_filename = f"U{number.zfill(4)}.json"  # 补零到4位
        new_path = os.path.join(directory_path, new_filename)
        
        try:
            # 读取原文件内容
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 更新用户ID
            old_user_id = f"U{number}"
            new_user_id = f"U{number.zfill(4)}"
            
            if "用户ID" in data:
                data["用户ID"] = new_user_id
                print(f"✓ 更新用户ID: {old_user_id} -> {new_user_id}")
            
            # 写入新文件
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 删除原文件
            os.remove(old_path)
            
            print(f"✓ 文件重命名: {old_filename} -> {new_filename}")
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON解析错误 {old_filename}: {e}")
        except Exception as e:
            print(f"✗ 处理文件 {old_filename} 时出错: {e}")
    
    print("\n处理完成!")

def preview_changes(directory_path):
    """
    预览将要进行的更改，不实际执行
    """
    if not os.path.exists(directory_path):
        print(f"错误: 目录 '{directory_path}' 不存在")
        return
    
    files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
    pattern = re.compile(r'^U(\d{3})\.json$')
    
    print("预览模式 - 将要进行的更改:")
    print("-" * 50)
    
    for file in files:
        match = pattern.match(file)
        if match:
            number = match.group(1)
            old_filename = file
            new_filename = f"U{number.zfill(4)}.json"
            old_user_id = f"U{number}"
            new_user_id = f"U{number.zfill(4)}"
            
            print(f"文件名: {old_filename} -> {new_filename}")
            print(f"用户ID: {old_user_id} -> {new_user_id}")
            print()

if __name__ == "__main__":
    # 设置包含JSON文件的目录路径
    directory_path = "user_dataset"  # 修改为你的目录路径
    
    print("JSON文件批量重命名工具")
    print("=" * 40)
    
    # 首先预览更改
    preview_changes(directory_path)
    
    # 询问是否继续
    response = input("是否继续执行更改? (y/n): ").lower().strip()
    
    if response == 'y' or response == 'yes':
        rename_and_update_json_files(directory_path)
    else:
        print("操作已取消")