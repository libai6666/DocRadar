#!/usr/bin/env python
"""
检查并修复Python文件中的空字节（null bytes）问题
"""

import os
import sys


def check_file_for_null_bytes(file_path):
    """检查文件是否包含空字节，如果有则返回True"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            return b'\x00' in content
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return False


def fix_file_with_null_bytes(file_path):
    """修复包含空字节的文件"""
    try:
        # 读取文件内容（二进制模式）
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 移除空字节
        fixed_content = content.replace(b'\x00', b'')
        
        # 写回文件
        with open(file_path, 'wb') as f:
            f.write(fixed_content)
        
        print(f"修复了文件: {file_path}")
        return True
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False


def scan_directory_for_null_bytes(directory='.'):
    """扫描目录中的Python文件，查找并可选修复包含空字节的文件"""
    problematic_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if check_file_for_null_bytes(file_path):
                    problematic_files.append(file_path)
    
    return problematic_files


def main():
    """主函数"""
    print("开始扫描Python文件中的空字节问题...")
    problematic_files = scan_directory_for_null_bytes()
    
    if not problematic_files:
        print("没有找到包含空字节的Python文件。")
        return
    
    print(f"找到 {len(problematic_files)} 个包含空字节的Python文件:")
    for file in problematic_files:
        print(f" - {file}")
    
    answer = input("是否修复这些文件? (y/n): ")
    if answer.lower() == 'y':
        fixed_count = 0
        for file in problematic_files:
            if fix_file_with_null_bytes(file):
                fixed_count += 1
        
        print(f"修复了 {fixed_count} 个文件。")
    else:
        print("未进行任何修复。")


if __name__ == '__main__':
    main() 