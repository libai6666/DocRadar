#!/usr/bin/env python
"""
反向数据迁移脚本 - 将数据从新目录结构迁移回旧目录结构

新结构:
  data/          -> 生产环境数据
  data_test/     -> 测试环境数据

旧结构:
  data/
    production/  -> 生产环境数据
    test/        -> 测试环境数据
"""

import os
import sys
import shutil
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 根目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 目录映射 - 反向迁移（新结构 -> 旧结构）
DIRECTORY_MAPPING = {
    # 新路径 -> 旧路径
    os.path.join(BASE_DIR, 'data'): os.path.join(BASE_DIR, 'data', 'production'),
    os.path.join(BASE_DIR, 'data_test'): os.path.join(BASE_DIR, 'data', 'test'),
}

def migrate_directory(src_dir, dest_dir):
    """将源目录内容迁移到目标目录"""
    if not os.path.exists(src_dir):
        logging.warning(f"源目录不存在，跳过迁移: {src_dir}")
        return False
    
    # 创建目标目录及父目录
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        logging.info(f"创建目标目录: {dest_dir}")
    
    # 移动所有内容
    success = True
    try:
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dest_path = os.path.join(dest_dir, item)
            
            # 如果目标已存在，备份它
            if os.path.exists(dest_path):
                backup_path = f"{dest_path}.bak"
                logging.warning(f"目标已存在，创建备份: {backup_path}")
                shutil.move(dest_path, backup_path)
            
            # 移动目录或文件
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path)
                logging.info(f"复制目录: {src_path} -> {dest_path}")
            else:
                shutil.copy2(src_path, dest_path)
                logging.info(f"复制文件: {src_path} -> {dest_path}")
    except Exception as e:
        logging.error(f"迁移出错: {str(e)}")
        success = False
    
    return success

def main():
    """主函数"""
    print("DocRadar 反向数据迁移工具")
    print("=======================")
    print("此工具将帮助您将数据从新目录结构迁移回旧目录结构。")
    print("")
    print("新结构: data/ 和 data_test/")
    print("旧结构: data/production/ 和 data/test/")
    print("")
    
    # 检查是否有需要迁移的目录
    need_migration = False
    for src_dir in DIRECTORY_MAPPING.keys():
        if os.path.exists(src_dir) and os.listdir(src_dir):
            need_migration = True
            break
    
    if not need_migration:
        print("没有发现需要迁移的数据。程序退出。")
        return
    
    # 确认操作
    confirmation = input("是否继续迁移数据？(y/n): ")
    if confirmation.lower() not in ('y', 'yes'):
        print("操作已取消。")
        return
    
    # 执行迁移
    print("\n开始迁移数据...")
    for src_dir, dest_dir in DIRECTORY_MAPPING.items():
        if os.path.exists(src_dir) and os.listdir(src_dir):
            print(f"正在迁移 {src_dir} -> {dest_dir}")
            success = migrate_directory(src_dir, dest_dir)
            if success:
                print(f"迁移成功: {src_dir} -> {dest_dir}")
            else:
                print(f"迁移失败: {src_dir} -> {dest_dir}")
    
    print("\n迁移完成。")
    print("请检查旧目录结构中的数据是否正确。")
    print("如果确认无误，可以删除新的目录结构。")
    print("要删除新目录结构，请运行: python migrate_data_reverse.py --cleanup")

def cleanup():
    """清理新目录结构"""
    print("DocRadar 新数据清理工具")
    print("======================")
    print("此工具将删除新目录结构中的数据。")
    print("确保您已经备份或迁移了重要数据！")
    print("")
    
    # 确认操作
    confirmation = input("是否删除新目录结构？此操作不可撤销! (y/n): ")
    if confirmation.lower() not in ('y', 'yes'):
        print("操作已取消。")
        return
    
    # 二次确认
    confirmation = input("再次确认删除 (yes/no): ")
    if confirmation.lower() != 'yes':
        print("操作已取消。")
        return
    
    # 删除新目录
    new_data = os.path.join(BASE_DIR, 'data')
    new_data_test = os.path.join(BASE_DIR, 'data_test')
    
    # 检查data目录是否仅包含production和test子目录
    if os.path.exists(new_data):
        data_items = os.listdir(new_data)
        if len(data_items) == 2 and 'production' in data_items and 'test' in data_items:
            print("data目录现在只包含production和test子目录，无需删除。")
        else:
            # 存在其他项目，询问是否要备份或删除
            print(f"警告: data目录包含 {data_items}，请手动检查并处理。")
            choice = input("是否继续删除？手动备份后才输入yes: ")
            if choice.lower() == 'yes':
                # 删除data目录中除了production和test之外的内容
                for item in data_items:
                    if item not in ['production', 'test']:
                        item_path = os.path.join(new_data, item)
                        try:
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                            print(f"已删除: {item_path}")
                        except Exception as e:
                            print(f"删除失败: {item_path} - {str(e)}")
            else:
                print("操作已取消。")
    
    # 删除data_test目录
    if os.path.exists(new_data_test):
        try:
            shutil.rmtree(new_data_test)
            print(f"已删除: {new_data_test}")
        except Exception as e:
            print(f"删除失败: {new_data_test} - {str(e)}")
    
    print("\n清理完成。")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
        cleanup()
    else:
        main() 