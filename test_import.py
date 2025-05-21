#!/usr/bin/env python
# coding: utf-8

"""
测试导入应用包
"""

import os
import sys

def main():
    """测试是否可以导入应用模块"""
    try:
        # 尝试导入config模块
        from app.core import config
        print(f"成功导入配置模块，环境: {config.ENV}")
        
        # 尝试导入蓝图
        from app.core.routes import main_bp
        print(f"成功导入主页蓝图: {main_bp.name}")
        
        from app.core.document_routes import document_bp
        print(f"成功导入文档蓝图: {document_bp.name}")
        
        from app.core.search_routes import search_bp
        print(f"成功导入搜索蓝图: {search_bp.name}")
        
        # 尝试导入工具类
        from app.utils import document_parser
        print(f"成功导入文档解析器模块")
        
        from app.utils import search_engine
        print(f"成功导入搜索引擎模块")
        
        from app.utils import storage
        print(f"成功导入存储模块")
        
        print("\n目录结构测试成功，应用模块导入正常。")
    except Exception as e:
        print(f"导入测试失败: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 