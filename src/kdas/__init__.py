"""
KDAS (Key Date Average Settlement) 智能分析系统

一个基于AI的证券技术分析和KDAS交易体系分析工具包。

主要功能：
- 智能推荐KDAS关键日期
- 技术指标分析
- KDAS状态分析
- 支持股票、ETF等证券类型
- 异步批量处理

基本用法：
    import asyncio
    from kdas import analyze_security_kdas, batch_analyze_securities
    
    # 单个证券分析
    async def main():
        result = await analyze_security_kdas("股票", "000001", "your-api-key")
        print(result)
    
    asyncio.run(main())

版本: 1.0.0
作者: KDAS Team
"""

from .advisor import (
    KDASAIAdvisor,
    analyze_security_kdas,
    batch_analyze_securities,
    get_ai_advisor
)

from .utils import safe_json_convert
from .technical_analysis import TechnicalAnalyzer
from .ai_recommendation import AIRecommendationEngine
from .kdas_analysis import KDASAnalyzer
from .data_handler import DataHandler

__version__ = "1.0.0"
__author__ = "KDAS Team"
__email__ = "kdas@example.com"

# 定义包的公共API
__all__ = [
    # 主要功能函数
    "analyze_security_kdas",
    "batch_analyze_securities",
    "get_ai_advisor",
    
    # 主要类
    "KDASAIAdvisor",
    "TechnicalAnalyzer", 
    "AIRecommendationEngine",
    "KDASAnalyzer",
    "DataHandler",
    
    # 工具函数
    "safe_json_convert",
    
    # 版本信息
    "__version__",
    "__author__",
    "__email__"
] 