import pandas as pd
import numpy as np
from typing import Any


def safe_json_convert(obj: Any) -> Any:
    """
    安全地转换数据类型以支持JSON序列化
    
    Args:
        obj: 需要转换的对象
        
    Returns:
        可以JSON序列化的对象
    """
    if isinstance(obj, dict):
        return {k: safe_json_convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_convert(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj 