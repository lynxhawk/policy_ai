import os
import json
import re
from typing import List

class PolicyConverter:
    """政策文本转JSON转换器"""
    
    def __init__(self, input_dir="policy_txt", output_dir="policy_dataset"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
    def convert_single_file(self, txt_file_path: str) -> dict:
        """转换单个txt文件为政策JSON"""
        
        # 从文件名提取政策编号
        filename = os.path.basename(txt_file_path)
        policy_id = os.path.splitext(filename)[0]  # 去掉.txt扩展名
        
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                raise ValueError("文件为空")
            
            # 第一行是标题
            title = lines[0].strip()
            
            # 第二行及后面是内容
            content_text = ""
            if len(lines) > 1:
                content_text = "".join(lines[1:]).strip()
            
            # 将内容分割为数组
            content_array = self._split_content_to_array(content_text)
             
            # 构建政策JSON
            policy_json = {
                "政策编号": policy_id,
                "标题": title,
                "内容": content_array
            }
            
            return policy_json
            
        except Exception as e:
            print(f"❌ 转换文件 {txt_file_path} 时出错: {e}")
            return None
    
    def _split_content_to_array(self, content: str) -> List[str]:
        """将长文本内容分割为数组"""
        if not content.strip():
            return []
        
        paragraphs = []
        
        # 按多种标识符分割内容
        # 匹配：一、二、三、 或者 1. 2. 3. 或者 （一）（二） 等
        section_pattern = r'([一二三四五六七八九十百]+、|[0-9]+\.|第[一二三四五六七八九十百]+[章节条款]|（[一二三四五六七八九十百]+）|[0-9]+\s*[\.\)、])'
        
        # 先按段落分割（双换行）
        raw_paragraphs = re.split(r'\n\s*\n', content)
        
        for raw_para in raw_paragraphs:
            if not raw_para.strip():
                continue
                
            # 进一步按章节标识分割
            sections = re.split(section_pattern, raw_para)
            
            current_section = ""
            for i, section in enumerate(sections):
                section = section.strip()
                if not section:
                    continue
                
                # 如果是章节标识符
                if re.match(section_pattern, section):
                    # 保存之前的内容
                    if current_section.strip():
                        sub_paras = self._split_long_paragraph(current_section.strip())
                        paragraphs.extend(sub_paras)
                    # 开始新的章节
                    current_section = section
                else:
                    current_section += section
            
            # 处理最后一个section
            if current_section.strip():
                sub_paras = self._split_long_paragraph(current_section.strip())
                paragraphs.extend(sub_paras)
        
        # 如果没有章节标识，直接按句子分割
        if not paragraphs:
            paragraphs = self._split_long_paragraph(content)
        
        # 清理并返回
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_long_paragraph(self, text: str, max_length: int = 300) -> List[str]:
        """分割过长的段落"""
        if len(text) <= max_length:
            return [text]
        
        paragraphs = []
        
        # 按句子分割（句号、感叹号、问号、分号）
        sentences = re.split(r'([。！？；])', text)
        current_para = ""
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            
            # 如果下一个是标点符号，合并
            if i + 1 < len(sentences) and sentences[i + 1] in '。！？；':
                sentence += sentences[i + 1]
                i += 2
            else:
                i += 1
            
            # 检查长度
            if len(current_para + sentence) > max_length and current_para:
                paragraphs.append(current_para.strip())
                current_para = sentence
            else:
                current_para += sentence
        
        # 添加最后一段
        if current_para.strip():
            paragraphs.append(current_para.strip())
        
        return paragraphs
    
    def convert_all_files(self):
        """转换所有txt文件"""
        if not os.path.exists(self.input_dir):
            print(f"❌ 输入目录不存在: {self.input_dir}")
            return
        
        # 创建输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"📁 创建输出目录: {self.output_dir}")
        
        # 获取所有txt文件
        txt_files = [f for f in os.listdir(self.input_dir) if f.endswith('.txt')]
        
        if not txt_files:
            print(f"❌ 在 {self.input_dir} 中没有找到txt文件")
            return
        
        print(f"📝 找到 {len(txt_files)} 个txt文件，开始转换...")
        
        success_count = 0
        
        for txt_file in txt_files:
            txt_path = os.path.join(self.input_dir, txt_file)
            print(f"\n🔄 正在转换: {txt_file}")
            
            # 转换文件
            policy_json = self.convert_single_file(txt_path)
            
            if policy_json:
                # 保存JSON文件
                policy_id = policy_json["政策编号"]
                json_filename = f"{policy_id}.json"
                json_path = os.path.join(self.output_dir, json_filename)
                
                try:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(policy_json, f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ 转换成功: {json_filename}")
                    print(f"   标题: {policy_json['标题']}")
                    print(f"   内容段落数: {len(policy_json['内容'])}")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ 保存文件 {json_filename} 时出错: {e}")
            else:
                print(f"❌ 转换失败: {txt_file}")
        
        print(f"\n🎉 转换完成！成功转换 {success_count}/{len(txt_files)} 个文件")
        
        if success_count > 0:
            print(f"📂 输出目录: {self.output_dir}")
    
    def preview_conversion(self, txt_file_path: str):
        """预览转换结果"""
        print(f"🔍 预览转换: {txt_file_path}")
        print("=" * 60)
        
        policy_json = self.convert_single_file(txt_file_path)
        
        if policy_json:
            print(f"政策编号: {policy_json['政策编号']}")
            print(f"标题: {policy_json['标题']}")
            print(f"内容段落数: {len(policy_json['内容'])}")
            print("\n前5个段落:")
            
            for i, para in enumerate(policy_json['内容'][:5], 1):
                print(f"{i:2d}. {para}")
                if len(para) > 100:
                    print(f"    [长度: {len(para)}字符]")
            
            if len(policy_json['内容']) > 5:
                print(f"... 还有 {len(policy_json['内容']) - 5} 个段落")
            
            return policy_json
        else:
            print("❌ 转换失败")
            return None

def create_sample_files():
    """创建示例文件"""
    sample_dir = "policy_txt"
    if not os.path.exists(sample_dir):
        os.makedirs(sample_dir)
    
    # 示例文件1
    sample1_content = """关于调整平湖市灵活就业人员社会保险补贴标准的通知
各镇人民政府、街道办事处，平湖经济技术开发区管委会、独山港经济开发区管委会，市级机关各部门，市属各单位：

为减轻灵活就业人员参加社会保险的负担，根据《嘉兴市人民政府关于做好当前和今后一段时期就业创业工作的实施意见》（嘉政发〔2018〕29号）精神，就业困难人员实现灵活就业并依法缴纳社会保险费的，按当年最低社会保险缴费基数缴费额（基本养老、基本医疗保险）的50%给予社保补贴，期限不超过3年。

其中对初次核定享受补贴政策时距离法定退休年龄不足5年的人员，延长至退休。补贴政策自2018年1月1日起实施。

一、适用对象
就业困难人员实现灵活就业的人员。

二、申请条件
1. 依法缴纳社会保险费
2. 属于就业困难人员
3. 实现灵活就业

三、补贴标准
按当年最低社会保险缴费基数缴费额（基本养老、基本医疗保险）的50%给予社保补贴。

四、享受期限
期限不超过3年，距离法定退休年龄不足5年的人员延长至退休。"""
    
    with open(os.path.join(sample_dir, "POL0001.txt"), 'w', encoding='utf-8') as f:
        f.write(sample1_content)
    
    # 示例文件2
    sample2_content = """关于《平湖市人才公寓管理暂行办法》政策解读
一、政策依据

根据《平湖市关于加强和改进新时代人才工作的若干意见》（平委发〔2022〕28号）文件精神，为规范人才公寓管理，充分发挥人才公寓周转服务作用，努力改善人才居住环境，故出台该文件。

二、政策出台背景

人才公寓作为招才引智的重要载体，我市高度重视、积极谋划部署，精心筑巢引凤。近年来，随着各镇街道陆续开工建设多批人才公寓，相关管理办法亟需规范完善。

三、适用对象

人才公寓租住对象为全市各类人才，其中申请资金补助对象应同时符合以下条件：
（一）2021年10月1日后，在我市首次缴纳社保、公积金、个人所得税其中之一。
（二）申请时未取得房产网签备案或不动产权证。
（三）拥有G类及以上的人才码（归属管理权限在平湖市内）。

四、补贴标准

（一）人才码E类及以上人才，每月每人不超过2000元。
（二）人才码F类人才，每月每人不超过1200元。
（三）人才码G类人才，每月每人不超过600元。"""
    
    with open(os.path.join(sample_dir, "POL0002.txt"), 'w', encoding='utf-8') as f:
        f.write(sample2_content)
    
    print(f"✅ 已创建示例文件到 {sample_dir} 目录")
    print("📁 文件列表:")
    print("  - POL0001.txt (灵活就业补贴政策)")
    print("  - POL0002.txt (人才公寓政策)")

def main():
    """主函数"""
    print("🚀 TXT转政策JSON转换工具")
    print("=" * 60)
    
    # 创建转换器
    converter = PolicyConverter()
    
    # 检查输入目录
    if not os.path.exists(converter.input_dir):
        print(f"❓ 输入目录 {converter.input_dir} 不存在")
        create_sample = input("是否创建示例文件？(y/n): ").lower().strip()
        
        if create_sample == 'y':
            create_sample_files()
            print("\n现在可以运行转换了！")
        else:
            print("请创建目录并放入txt文件后再运行")
            return
    
    # 显示使用说明
    print(f"\n📋 使用说明:")
    print(f"1. 将txt文件放入 {converter.input_dir} 目录")
    print(f"2. 文件名作为政策编号（如：POL0001.txt）")
    print(f"3. 第一行为政策标题")
    print(f"4. 第二行开始为政策内容")
    print(f"5. 转换后的JSON文件将保存到 {converter.output_dir} 目录")
    
    # 执行转换
    print(f"\n开始转换...")
    converter.convert_all_files()

def preview_mode():
    """预览模式"""
    print("🔍 预览模式")
    print("=" * 40)
    
    converter = PolicyConverter()
    
    txt_file = input("请输入要预览的txt文件路径: ").strip()
    
    if os.path.exists(txt_file):
        result = converter.preview_conversion(txt_file)
        
        if result:
            save = input("\n是否保存此转换结果？(y/n): ").lower().strip()
            if save == 'y':
                if not os.path.exists(converter.output_dir):
                    os.makedirs(converter.output_dir)
                
                json_path = os.path.join(converter.output_dir, f"{result['政策编号']}.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✅ 已保存到: {json_path}")
    else:
        print("❌ 文件不存在")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview_mode()
    else:
        main()