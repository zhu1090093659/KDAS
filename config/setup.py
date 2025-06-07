"""
KDAS包的安装配置文件
"""

from setuptools import setup, find_packages
import os

# 读取长描述
def read_long_description():
    readme_path = os.path.join(os.path.dirname(__file__), "..", "docs", "readme.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as fh:
            return fh.read()
    return "KDAS (Key Date Average Settlement) 智能分析系统"

# 读取requirements
def read_requirements():
    requirements = [
        "pandas>=1.3.0",
        "numpy>=1.20.0", 
        "openai>=1.0.0",
        "streamlit>=1.0.0",
        "akshare>=1.8.0",
        "asyncio-mqtt>=0.11.0"
    ]
    
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as fh:
            additional_reqs = [line.strip() for line in fh.readlines() if line.strip() and not line.startswith("#")]
            requirements.extend(additional_reqs)
    
    # 去重
    return list(set(requirements))

setup(
    name="kdas",
    version="1.0.0", 
    author="KDAS Team",
    author_email="kdas@example.com",
    description="KDAS (Key Date Average Settlement) 智能分析系统",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/example/kdas",
    packages=find_packages(where="../src"),
    package_dir={"": "../src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10", 
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "mypy>=0.800"
        ]
    },
    entry_points={
        "console_scripts": [
            "kdas-analyze=kdas.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "kdas": ["*.md", "*.txt"],
    },
    keywords="kdas, stock analysis, technical analysis, ai, finance, trading",
    project_urls={
        "Bug Reports": "https://github.com/example/kdas/issues",
        "Source": "https://github.com/example/kdas",
        "Documentation": "https://kdas.readthedocs.io/",
    }
) 