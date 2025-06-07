#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KDAS股票分析工具启动脚本
运行命令: python run_app.py
"""

import subprocess
import sys
import os

def run_streamlit_app():
    """启动Streamlit应用"""
    try:
        # 检查是否安装了streamlit
        import streamlit
        print("✅ Streamlit已安装")
    except ImportError:
        print("❌ 未安装Streamlit，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("✅ Streamlit安装完成")
    
    # 检查KDAS.py文件是否存在
    kdas_file = os.path.join(os.path.dirname(__file__), 'KDAS.py')
    if not os.path.exists(kdas_file):
        print("❌ 未找到KDAS.py文件")
        return
    
    print("🚀 启动KDAS股票分析工具...")
    print("📱 应用将在浏览器中自动打开")
    print("🔄 如需停止应用，请按 Ctrl+C")
    
    # 启动streamlit应用
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", kdas_file,
            "--server.address", "localhost",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 应用已停止")

if __name__ == "__main__":
    run_streamlit_app() 