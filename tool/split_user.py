import json
import os

def split_user_info_to_files(input_file_path, output_directory="user_files"):
    """
    将包含多个用户信息的JSON文件分割为以用户ID命名的单独文件
    
    Args:
        input_file_path (str): 输入的JSON文件路径
        output_directory (str): 输出目录，默认为"user_files"
    """
    
    # 创建输出目录
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        print(f"创建输出目录: {output_directory}")
    
    try:
        # 读取原始JSON文件
        with open(input_file_path, 'r', encoding='utf-8') as file:
            users_data = json.load(file)
        
        print(f"成功读取文件: {input_file_path}")
        print(f"共找到 {len(users_data)} 个用户")
        
        # 为每个用户创建单独的JSON文件
        for user in users_data:
            user_id = user.get("用户ID", "unknown")
            
            # 生成输出文件路径
            output_file_path = os.path.join(output_directory, f"{user_id}.json")
            
            # 写入单个用户的JSON文件
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                json.dump(user, output_file, ensure_ascii=False, indent=2)
            
            print(f"已生成文件: {output_file_path}")
        
        print(f"\n转换完成！所有用户文件已保存到 {output_directory} 目录")
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file_path}")
    except json.JSONDecodeError:
        print(f"错误: {input_file_path} 不是有效的JSON文件")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    # 使用脚本
    input_file = "userinfo.json"  # 输入文件名
    output_dir = "user_dataset"     # 输出目录名
    
    split_user_info_to_files(input_file, output_dir)