"""
KDAS智能分析系统 - 兼容性接口

这个文件保持原有的API接口，但内部使用新的模块化KDAS包。
这样可以保证现有代码的兼容性，同时享受模块化带来的好处。

为了更好的代码组织，建议使用新的导入方式：
from kdas import analyze_security_kdas, batch_analyze_securities, KDASAIAdvisor

快速开始：

# 单个证券分析
from kdas_ai_advisor import analyze_security_kdas
import asyncio

async def main():
    result = await analyze_security_kdas(
        security_type="股票",  # 或 "ETF"
        symbol="000001",      # 证券代码
        api_key="your-api-key",
        model="deepseek-r1"   # 可选，默认为deepseek-r1
    )
    
    if result['success']:
        print("推荐日期:", result['recommended_dates'])
        print("分析结果:", result['analysis']['analysis'])
    else:
        print("分析失败:", result['error'])

asyncio.run(main())

注意：此接口已被弃用，请使用新的kdas包。
"""

import warnings
from typing import List, Dict, Optional

# 从新的kdas包导入所有功能
from kdas import (
    analyze_security_kdas,
    batch_analyze_securities, 
    get_ai_advisor,
    KDASAIAdvisor,
    TechnicalAnalyzer,
    AIRecommendationEngine,
    KDASAnalyzer,
    DataHandler,
    safe_json_convert
)

# 发出弃用警告
warnings.warn(
    "直接导入kdas_ai_advisor模块已弃用，请使用 'from kdas import ...' 代替。"
    "更多信息请参考新的kdas包文档。",
    DeprecationWarning,
    stacklevel=2
)

# 为了保持兼容性，重新导出所有功能
__all__ = [
    "analyze_security_kdas",
    "batch_analyze_securities", 
    "get_ai_advisor",
    "KDASAIAdvisor",
    "TechnicalAnalyzer",
    "AIRecommendationEngine",
    "KDASAnalyzer",
    "DataHandler",
    "safe_json_convert"
]