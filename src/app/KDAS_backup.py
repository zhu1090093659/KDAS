"""
KDAS证券分析工具 - 主程序文件

这是一个基于Streamlit的证券技术分析工具，集成了KDAS（累积成交量加权平均价格）指标分析。

主要功能模块：
- 配置管理：用户配置的保存、加载和验证
- AI分析文本格式化：智能分析结果的格式化展示
- 数据获取和处理：证券数据的获取、缓存和KDAS计算
- AI分析功能：集成kdas包的AI智能分析能力
- 图表生成：交互式K线图和KDAS指标图表
- 分析功能：单图精细分析和多图概览看板
- UI渲染：用户界面的渲染和交互处理

技术栈：
- Streamlit: Web界面框架
- Plotly: 交互式图表库
- akshare: 证券数据获取
- kdas: 专业KDAS分析包
- pandas: 数据处理

作者：KDAS团队
版本：2.0 (重构版本，集成kdas包)
"""

# === 标准库导入 ===
import os
import json
import re
import asyncio
from datetime import datetime, date, timedelta

# === 第三方库导入 ===
import akshare as ak
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# === KDAS包导入与初始化 ===
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from kdas import DataHandler, KDASAIAdvisor, KDASAnalyzer, get_ai_advisor, AIRecommendationEngine
    AI_ADVISOR_AVAILABLE = True
    # 初始化全局数据处理器
    data_handler = DataHandler()
except ImportError:
    AI_ADVISOR_AVAILABLE = False
    data_handler = None
    st.warning("⚠️ AI智能推荐功能需要安装openai库和kdas包: pip install openai")

# === 全局常量和配置 ===
# 数据目录路径（相对于项目根目录）
data_root = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
os.makedirs(os.path.join(data_root, 'shares'), exist_ok=True)
os.makedirs(os.path.join(data_root, 'etfs'), exist_ok=True)
os.makedirs(os.path.join(data_root, 'stocks'), exist_ok=True)

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'user_configs.json')

def load_user_configs():
    """加载用户保存的配置，包含改进的错误处理"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                configs = json.load(f)
                # 验证配置文件格式
                if not isinstance(configs, dict):
                    print(f"配置文件格式错误，将重置为默认配置")
                    return {}
                return configs
        except json.JSONDecodeError as e:
            print(f"配置文件JSON格式错误: {e}")
            # 备份损坏的配置文件
            backup_name = f"{CONFIG_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                os.rename(CONFIG_FILE, backup_name)
                print(f"已将损坏的配置文件备份为: {backup_name}")
            except Exception:
                pass
            return {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    return {}

def save_user_configs(configs):
    """保存用户配置，包含改进的错误处理和详细调试信息"""
    try:
        # 参数验证
        if configs is None:
            print("❌ 保存配置失败: 配置对象为None")
            return False, "配置对象为空"
        
        if not isinstance(configs, dict):
            print(f"❌ 保存配置失败: 配置对象类型错误，期望dict，实际{type(configs)}")
            return False, f"配置对象类型错误: {type(configs).__name__}"
        
        # 调试信息
        print(f"📂 配置文件路径: {CONFIG_FILE}")
        print(f"📊 配置数量: {len(configs)} 个")
        
        # 确保目录存在
        config_dir = os.path.dirname(CONFIG_FILE) if os.path.dirname(CONFIG_FILE) else '.'
        try:
            os.makedirs(config_dir, exist_ok=True)
            print(f"📁 配置目录检查完成: {config_dir}")
        except Exception as e:
            print(f"❌ 创建配置目录失败: {e}")
            return False, f"无法创建配置目录: {e}"
        
        # 检查磁盘空间
        try:
            import shutil
            total, used, free = shutil.disk_usage(config_dir)
            free_mb = free // (1024*1024)
            if free_mb < 1:  # 至少1MB空闲空间
                print(f"❌ 磁盘空间不足: 仅 {free_mb} MB 可用")
                return False, f"磁盘空间不足，仅剩余 {free_mb} MB"
        except Exception as e:
            print(f"⚠️ 无法检查磁盘空间: {e}")
        
        # 先保存到临时文件，然后原子性地重命名
        temp_file = f"{CONFIG_FILE}.tmp"
        print(f"💾 开始写入临时文件: {temp_file}")
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            print(f"✅ 临时文件写入成功")
        except PermissionError as e:
            print(f"❌ 临时文件写入失败: 权限不足 - {e}")
            return False, "权限不足，无法写入配置文件"
        except OSError as e:
            print(f"❌ 临时文件写入失败: 系统错误 - {e}")
            return False, f"系统错误: {e}"
        except Exception as e:
            print(f"❌ 临时文件写入失败: {e}")
            return False, f"写入失败: {e}"
        
        # 验证临时文件
        try:
            with open(temp_file, 'r', encoding='utf-8') as f:
                loaded_configs = json.load(f)
            print(f"✅ 临时文件验证成功，包含 {len(loaded_configs)} 个配置")
        except Exception as e:
            print(f"❌ 临时文件验证失败: {e}")
            # 清理无效的临时文件
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"🗑️ 已清理无效临时文件")
                except Exception:
                    pass
            return False, f"配置文件验证失败: {e}"
        
        # 原子性地替换原文件
        try:
            os.replace(temp_file, CONFIG_FILE)
            print(f"✅ 配置文件更新成功: {CONFIG_FILE}")
            
            # 最终验证
            if os.path.exists(CONFIG_FILE):
                file_size = os.path.getsize(CONFIG_FILE)
                print(f"📏 配置文件大小: {file_size} 字节")
                return True, "配置保存成功"
            else:
                print(f"❌ 配置文件替换后不存在")
                return False, "配置文件替换失败"
                
        except PermissionError as e:
            print(f"❌ 配置文件替换失败: 权限不足 - {e}")
            return False, "权限不足，无法更新配置文件"
        except Exception as e:
            print(f"❌ 配置文件替换失败: {e}")
            return False, f"文件替换失败: {e}"
        
    except Exception as e:
        print(f"❌ 保存配置文件过程中发生异常: {e}")
        import traceback
        print(f"📋 详细错误信息: {traceback.format_exc()}")
        
        # 清理临时文件
        temp_file = f"{CONFIG_FILE}.tmp"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print(f"🗑️ 已清理临时文件")
            except Exception:
                pass
        return False, f"保存过程异常: {e}"

def get_config_with_validation(config_key, default_value=None, config_type=None):
    """通用的配置获取函数，包含类型验证"""
    configs = load_user_configs()
    
    # 支持嵌套键，如 'global_settings.api_key'
    keys = config_key.split('.')
    current_value = configs
    
    try:
        for key in keys:
            current_value = current_value[key]
        
        # 类型验证
        if config_type is not None and not isinstance(current_value, config_type):
            print(f"配置项 {config_key} 类型错误，期望 {config_type.__name__}，实际 {type(current_value).__name__}")
            return default_value
            
        return current_value
    except (KeyError, TypeError):
        return default_value

def save_current_config(symbol, security_type, input_date, security_name):
    """保存当前的配置 - 增强版本，包含详细的错误处理和调试信息"""
    try:
        # 参数验证
        if not symbol or not symbol.strip():
            print(f"❌ 保存配置失败: 证券代码为空")
            return False, "证券代码不能为空"
        
        if not security_type or not security_type.strip():
            print(f"❌ 保存配置失败: 证券类型为空")
            return False, "证券类型不能为空"
        
        if not input_date or not isinstance(input_date, dict):
            print(f"❌ 保存配置失败: 日期配置无效")
            return False, "日期配置格式无效"
        
        if not security_name or not security_name.strip():
            print(f"❌ 保存配置失败: 证券名称为空")
            return False, "证券名称不能为空"
        
        # 调试信息
        print(f"📝 开始保存配置: {security_type} {symbol} ({security_name})")
        print(f"📅 日期配置: {input_date}")
        
        # 加载现有配置
        configs = load_user_configs()
        config_key = f"{security_type}_{symbol}"
        
        # 构建新配置
        new_config = {
            'symbol': symbol.strip(),
            'security_type': security_type.strip(),
            'security_name': security_name.strip(),
            'dates': input_date,
            'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 保存配置
        configs[config_key] = new_config
        
        # 尝试保存到文件
        save_success, save_message = save_user_configs(configs)
        
        if save_success:
            print(f"✅ 配置保存成功: {config_key}")
            print(f"📂 配置文件路径: {CONFIG_FILE}")
            return True, "配置保存成功"
        else:
            print(f"❌ 配置保存失败: {save_message}")
            return False, save_message
            
    except Exception as e:
        error_msg = f"保存配置时发生异常: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"📋 详细错误信息: {traceback.format_exc()}")
        return False, error_msg

def get_saved_config(symbol, security_type):
    """获取指定证券的保存配置"""
    configs = load_user_configs()
    config_key = f"{security_type}_{symbol}"
    return configs.get(config_key, None)

def delete_saved_config(symbol, security_type):
    """删除指定证券的保存配置"""
    configs = load_user_configs()
    config_key = f"{security_type}_{symbol}"
    if config_key in configs:
        del configs[config_key]
        success, message = save_user_configs(configs)
        return success
    return False

def _ensure_global_settings(configs):
    """确保配置中存在全局设置部分（内部辅助函数）"""
    if 'global_settings' not in configs:
        configs['global_settings'] = {}
    return configs

def _update_save_time(configs):
    """更新配置的保存时间（内部辅助函数）"""
    configs['global_settings']['save_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return configs

def save_api_key(api_key, model_name):
    """保存API密钥到配置文件"""
    configs = load_user_configs()
    configs = _ensure_global_settings(configs)
    
    # 保存API密钥和默认模型
    configs['global_settings']['api_key'] = api_key
    configs['global_settings']['default_model'] = model_name
    configs = _update_save_time(configs)
    
    success, message = save_user_configs(configs)
    return success

def save_ai_analysis_setting(enabled):
    """保存AI分析开关设置"""
    configs = load_user_configs()
    configs = _ensure_global_settings(configs)
    
    # 保存AI分析开关设置
    configs['global_settings']['ai_analysis_enabled'] = enabled
    configs = _update_save_time(configs)
    
    success, message = save_user_configs(configs)
    return success

def load_ai_analysis_setting():
    """加载AI分析开关设置"""
    return get_config_with_validation('global_settings.ai_analysis_enabled', False, bool)

def save_ai_date_recommendation_setting(enabled):
    """保存AI日期推荐开关设置"""
    configs = load_user_configs()
    configs = _ensure_global_settings(configs)
    
    # 保存AI日期推荐开关设置
    configs['global_settings']['ai_date_recommendation_enabled'] = enabled
    configs = _update_save_time(configs)
    
    return save_user_configs(configs)

def load_ai_date_recommendation_setting():
    """加载AI日期推荐开关设置"""
    return get_config_with_validation('global_settings.ai_date_recommendation_enabled', True, bool)

def load_api_key():
    """从配置文件加载API密钥"""
    api_key = get_config_with_validation('global_settings.api_key', '', str)
    default_model = get_config_with_validation('global_settings.default_model', 'deepseek-r1', str)
    return api_key, default_model

def delete_api_key():
    """删除保存的API密钥"""
    configs = load_user_configs()
    if 'global_settings' in configs:
        # 批量删除相关设置
        keys_to_delete = ['api_key', 'default_model', 'ai_analysis_enabled', 'ai_date_recommendation_enabled']
        for key in keys_to_delete:
            configs['global_settings'].pop(key, None)
        
        # 如果global_settings为空，则删除整个section
        if not configs['global_settings']:
            del configs['global_settings']
        return save_user_configs(configs)
    return False

# ==================== AI分析文本格式化模块 ====================

def format_analysis_text(analysis_text):
    """统一的分析文本格式化函数，整合原有的多个格式化函数"""
    if not analysis_text or not analysis_text.strip():
        return "暂无分析内容"
    
    # 尝试从文本中提取JSON部分
    json_data = _extract_json_from_text(analysis_text)
    
    if json_data:
        # 如果成功提取并解析JSON，则格式化展示
        return _format_json_analysis(json_data)
    else:
        # 如果不是JSON格式，使用原有的文本格式化方法
        return _format_plain_text_analysis(analysis_text)

def _extract_json_from_text(text):
    """从文本中提取JSON部分并解析为字典"""
    import re
    import json
    
    try:
        # 方法1：尝试找到被```json包围的JSON
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
        
        # 方法2：尝试找到大括号包围的JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group().strip()
            return json.loads(json_str)
        
        # 方法3：尝试直接解析整个文本
        return json.loads(text.strip())
        
    except (json.JSONDecodeError, AttributeError):
        return None

def _format_json_analysis(json_data):
    """格式化JSON格式的分析结果"""
    if not isinstance(json_data, dict):
        return "分析结果格式错误"
    
    formatted_content = []
    
    # 定义字段映射和图标
    field_mapping = {
        '状态': ('📊', 'KDAS状态分析'),
        '多空力量分析': ('⚖️', '多空力量对比'),
        '趋势方向判断': ('📈', '趋势方向判断'),
        '交易建议': ('💡', '交易策略建议'),
        '风险提示': ('⚠️', '风险评估提示'),
        '置信度': ('🎯', '分析置信度')
    }
    
    # 按预定义顺序展示字段
    for field_key, (icon, title) in field_mapping.items():
        if field_key in json_data:
            content = json_data[field_key]
            if content and str(content).strip():
                # 格式化内容
                formatted_content.append(f"#### {icon} {title}")
                formatted_content.append("")
                
                # 应用文本样式
                styled_content = _apply_text_styling(str(content))
                formatted_content.append(styled_content)
                formatted_content.append("")  # 添加空行分隔
    
    # 处理其他未映射的字段
    for key, value in json_data.items():
        if key not in field_mapping and value and str(value).strip():
            formatted_content.append(f"#### 🔸 {key}")
            formatted_content.append("")
            styled_content = _apply_text_styling(str(value))
            formatted_content.append(styled_content)
            formatted_content.append("")
    
    return '\n'.join(formatted_content)

def _format_plain_text_analysis(analysis_text):
    """格式化普通文本格式的分析结果（保留原有逻辑）"""
    import re
    
    # 首先处理整体结构
    formatted_content = []
    
    # 按行分割并重新组织
    lines = analysis_text.split('\n')
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_section:
                # 处理当前积累的段落
                section_text = ' '.join(current_section).strip()
                if section_text:
                    formatted_content.append(_format_paragraph(section_text))
                current_section = []
            continue
        
        current_section.append(line)
    
    # 处理最后一个段落
    if current_section:
        section_text = ' '.join(current_section).strip()
        if section_text:
            formatted_content.append(_format_paragraph(section_text))
    
    # 合并所有内容
    result = '\n\n'.join(formatted_content)
    
    # 全局样式优化
    result = _apply_text_styling(result)
    
    return result

def _format_paragraph(text):
    """格式化单个段落"""
    import re
    
    if not text.strip():
        return ""
    
    # 处理主要章节标题（如：1. **当前KDAS状态判断**）
    main_section_match = re.match(r'^(\d+)\.\s*\*\*(.*?)\*\*[:：]?(.*)', text)
    
    if main_section_match:
        num = main_section_match.group(1)
        title = main_section_match.group(2).strip()
        content = main_section_match.group(3).strip()
        
        icons = {
            '1': '📊', '2': '⚖️', '3': '📈', 
            '4': '💡', '5': '🎯', '6': '⚠️'
        }
        icon = icons.get(num, '🔸')
        
        result = f"#### {icon} {num}. {title}\n"
        if content:
            result += f"\n{content}"
        return result
    
    # 处理子标题（如：**多空力量分析**）
    subtitle_match = re.match(r'^\*\*(.*?)\*\*[:：]?(.*)', text)
    if subtitle_match:
        title = subtitle_match.group(1).strip()
        content = subtitle_match.group(2).strip()
        result = f"**🔸 {title}**"
        if content:
            result += f"\n\n{content}"
        return result
    
    # 处理引用内容
    if text.startswith('"') and text.endswith('"'):
        return f"> {text[1:-1]}"
    
    # 处理列表项
    if text.startswith('- '):
        return f"• {text[2:]}"
    
    # 处理普通段落
    return text

def _apply_text_styling(text):
    """应用文本样式优化"""
    
    # 关键词高亮
    styling_rules = [
        ('多头', '🟢 **多头**'),
        ('空头', '🔴 **空头**'),
        ('支撑位', '🟢 **支撑位**'),
        ('压力位', '🔴 **压力位**'),
        ('阻力位', '🔴 **阻力位**'),
        ('突破', '⚡ **突破**'),
        ('趋势确认', '✅ **趋势确认**'),
        ('趋势反转', '🔄 **趋势反转**'),
        ('情绪宣泄', '😱 **情绪宣泄**'),
        ('震荡', '📊 **震荡**'),
        ('整理', '⏸️ **整理**'),
        ('风险', '⚠️ **风险**'),
        ('建议', '💡 **建议**'),
        ('策略', '🎯 **策略**'),
        ('关键位', '🔑 **关键位**'),
        ('收敛', '📐 **收敛**'),
        ('发散', '📏 **发散**'),
        ('观望', '👀 **观望**'),
        ('入场', '🚀 **入场**'),
        ('止损', '🛑 **止损**'),
        ('止盈', '✨ **止盈**'),
        ('KDAS', '📊 **KDAS**'),
        ('均线', '📈 **均线**'),
        ('多空力量', '⚖️ **多空力量**'),
        ('趋势行进', '📈 **趋势行进**'),
        ('趋势衰竭', '📉 **趋势衰竭**'),
        ('市场一致性', '🎯 **市场一致性**'),
        ('情绪积累', '📊 **情绪积累**'),
        ('盘整', '📊 **盘整**'),
        ('强势', '💪 **强势**'),
        ('弱势', '📉 **弱势**'),
        ('高位', '⬆️ **高位**'),
        ('低位', '⬇️ **低位**')
    ]
    
    for old, new in styling_rules:
        # 只替换独立的词，避免重复替换
        text = re.sub(f'(?<!\\*){re.escape(old)}(?!\\*)', new, text)
    
    return text

def save_multi_chart_config(global_dates, securities):
    """保存多图看板配置"""
    configs = load_user_configs()
    configs = _ensure_global_settings(configs)
    
    # 保存多图看板配置
    configs['global_settings']['multi_chart_config'] = {
        'global_dates': [date.isoformat() for date in global_dates],
        'securities': securities,
        'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return save_user_configs(configs)

def load_multi_chart_config():
    """加载多图看板配置，使用改进的配置获取"""
    multi_config = get_config_with_validation('global_settings.multi_chart_config', None, dict)
    
    if multi_config:
        try:
            # 转换日期格式
            global_dates = [datetime.fromisoformat(date_str).date() for date_str in multi_config['global_dates']]
            securities = multi_config['securities']
            return global_dates, securities
        except Exception as e:
            print(f"加载多图看板配置失败: {e}")
            # 继续执行，返回默认配置
    
    # 返回默认配置
    return get_default_multi_chart_config()

# ==================== 数据获取和处理模块 ====================

def get_default_multi_chart_config():
    """
    获取多图看板的默认配置
    
    Returns:
        (default_dates, default_securities) 元组
    """
    default_dates = [
        datetime(2024, 9, 24).date(),
        datetime(2024, 11, 7).date(),
        datetime(2024, 12, 17).date(),
        datetime(2025, 4, 7).date(),
        datetime(2025, 4, 23).date()
    ]
    
    default_securities = [
        {'type': '股票', 'symbol': '001215', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': 'ETF', 'symbol': '159915', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': '指数', 'symbol': '000001', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': '股票', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': 'ETF', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
        {'type': '指数', 'symbol': '', 'use_global_dates': True, 'dates': None, 'config_key': None},
    ]
    
    return default_dates, default_securities

def reset_multi_chart_to_default():
    """
    重置多图看板配置为默认值
    
    Returns:
        重置是否成功
    """
    try:
        default_dates, default_securities = get_default_multi_chart_config()
        st.session_state.multi_chart_global_dates = default_dates
        st.session_state.multi_securities = default_securities
        
        return save_multi_chart_config(default_dates, default_securities)
    except Exception as e:
        st.error(f"重置配置失败: {e}")
        return False

@st.cache_data
def load_stock_info():
    """缓存加载股票信息 - 使用kdas.DataHandler"""
    if data_handler is None:
        # 备用方案：直接使用akshare
        stock_file_path_backup = os.path.join(data_root, 'shares', 'A股全部股票代码.csv')
        if os.path.exists(stock_file_path_backup):
            stock_info_df = pd.read_csv(stock_file_path_backup, dtype={0: str})
            if '股票代码' in stock_info_df.columns and '股票名称' in stock_info_df.columns:
                stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
        else:
            stock_info_df = ak.stock_info_a_code_name()
            stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
            stock_info_df.to_csv(stock_file_path_backup, index=False)
        return stock_info_df
    
    # 使用kdas.DataHandler的逻辑
    stock_file_path = os.path.join(data_root, 'shares', 'A股全部股票代码.csv')
    if os.path.exists(stock_file_path):
        stock_info_df = pd.read_csv(stock_file_path, dtype={0: str})
        if '股票代码' in stock_info_df.columns and '股票名称' in stock_info_df.columns:
            stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
    else:
        stock_info_df = ak.stock_info_a_code_name()
        stock_info_df = stock_info_df.rename(columns={"股票代码": "code", "股票名称": "name"})
        stock_info_df.to_csv(stock_file_path, index=False)
    return stock_info_df

@st.cache_data
def load_etf_info():
    """缓存加载ETF信息 - 使用kdas.DataHandler"""
    etf_file_path = os.path.join(data_root, 'etfs', 'A股全部ETF代码.csv')
    if os.path.exists(etf_file_path):
        etf_info_df = pd.read_csv(etf_file_path, dtype={0: str})
    else:
        etf_info_df = ak.fund_etf_spot_em()  # 东财A股全部ETF
        etf_info_df = etf_info_df[['代码', '名称']].drop_duplicates().rename(columns={"代码": "code", "名称": "name"})
        etf_info_df.to_csv(etf_file_path, index=False)
    return etf_info_df

@st.cache_data
def load_index_info():
    """缓存加载指数信息 - 使用kdas.DataHandler"""
    index_file_path = os.path.join(data_root, 'stocks', 'A股全部指数代码.csv')
    if os.path.exists(index_file_path):
        index_info_df = pd.read_csv(index_file_path, dtype={0: str})
    else:
        categories = ("沪深重要指数", "上证系列指数", "深证系列指数", "指数成份", "中证系列指数")
        index_dfs = []
        for category in categories:
            df = ak.stock_zh_index_spot_em(symbol=category)
            index_dfs.append(df)
        # 合并数据并去重
        index_info_df = pd.concat(index_dfs).drop_duplicates(subset=["代码"])
        index_info_df = index_info_df[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
        index_info_df.to_csv(index_file_path, index=False)
    return index_info_df

# 获取历史数据（股票、ETF、指数） - 使用kdas.DataHandler
@st.cache_data
def get_security_data(symbol, input_date, security_type="股票"):
    """使用kdas.DataHandler获取证券数据，保持与原API兼容"""
    if data_handler is None:
        # 备用方案：使用原始实现
        try:
            symbol = symbol.split('.')[0]
            start_date = min(input_date.values())
            today = datetime.now().strftime('%Y%m%d')
            
            if security_type == "股票":
                folder = 'shares'
                api_func = lambda: ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
                api_func_update = lambda last_date: ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=last_date, adjust="qfq")
            elif security_type == "ETF":
                folder = 'etfs'
                api_func = lambda: ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
                api_func_update = lambda last_date: ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=last_date, adjust="qfq")
            elif security_type == "指数":
                folder = 'stocks'
                api_func = lambda: ak.stock_zh_index_daily(symbol=symbol, start_date=start_date)
                api_func_update = lambda last_date: ak.stock_zh_index_daily(symbol=symbol, start_date=last_date)
            else:
                raise ValueError(f"不支持的证券类型: {security_type}")
            
            file_path = os.path.join(data_root, folder, f'{symbol}.csv')
            
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['日期'] = pd.to_datetime(df['日期'])
                
                start_date_ts = pd.to_datetime(start_date)
                if not (df['日期'] == start_date_ts).any():
                    df = api_func()
                    if not df.empty:
                        df['日期'] = pd.to_datetime(df['日期'])
                        df.to_csv(file_path, index=False)
                else:
                    last_date_in_df = df['日期'].iloc[-1]
                    today_ts = pd.to_datetime(today)
                    if last_date_in_df < today_ts:
                        df_add = api_func_update(last_date_in_df.strftime('%Y%m%d'))
                        if not df_add.empty:
                            df_add['日期'] = pd.to_datetime(df_add['日期'])
                            df.drop(index=df.index[-1], inplace=True)
                            df = pd.concat([df, df_add], ignore_index=True)
                            df = df.drop_duplicates(subset=['日期']).sort_values('日期').reset_index(drop=True)
                            df.to_csv(file_path, index=False)
            else:
                df = api_func()
                if not df.empty:
                    df['日期'] = pd.to_datetime(df['日期'])
                    df.to_csv(file_path, index=False)
            
            if df.empty:
                return df
                
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期').reset_index(drop=True)
            
            if security_type == "指数" and '股票代码' not in df.columns:
                df['股票代码'] = symbol
            
            return df
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise Exception(f"get_security_data函数执行失败: {str(e)}\n详细错误:\n{error_details}")
    
    # 使用kdas.DataHandler
    try:
        return data_handler.get_security_data(symbol, input_date, security_type)
    except Exception as e:
        raise Exception(f"kdas.DataHandler获取数据失败: {str(e)}")

@st.cache_data
def get_trade_calendar():
    """获取中国股市官方交易日历数据"""
    try:
        # 使用akshare获取交易日历
        trade_calendar_df = ak.tool_trade_date_hist_sina()
        # 转换为日期格式
        trade_calendar_df['trade_date'] = pd.to_datetime(trade_calendar_df['trade_date'])
        return trade_calendar_df['trade_date'].dt.date.tolist()
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        # 如果获取失败，返回空列表，后续会使用备用方案
        return []

def get_non_trading_dates(start_date, end_date):
    """获取指定日期范围内的非交易日"""
    trade_dates = get_trade_calendar()
    
    if not trade_dates:
        # 如果获取交易日历失败，使用备用方案（基本节假日）
        return get_basic_holidays()
    
    # 转换日期范围
    start_dt = pd.to_datetime(start_date).date() if isinstance(start_date, str) else start_date
    end_dt = pd.to_datetime(end_date).date() if isinstance(end_date, str) else end_date
    
    # 获取所有日期
    all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
    trade_dates_set = set(trade_dates)
    
    # 找出非交易日（排除周末，因为rangebreaks会单独处理周末）
    non_trading_dates = []
    for date in all_dates:
        if date.weekday() < 5:  # 只考虑工作日
            if date.date() not in trade_dates_set:
                non_trading_dates.append(date.strftime('%Y-%m-%d'))
    
    return non_trading_dates

def get_basic_holidays():
    """备用方案：基本节假日列表（当无法获取官方交易日历时使用）"""
    return [
        # 只保留主要节假日作为备用
        "2024-01-01", "2024-02-10", "2024-02-11", "2024-02-12", "2024-02-13", 
        "2024-02-14", "2024-02-15", "2024-02-16", "2024-02-17", "2024-04-04", 
        "2024-04-05", "2024-04-06", "2024-05-01", "2024-05-02", "2024-05-03", 
        "2024-06-10", "2024-09-15", "2024-09-16", "2024-09-17", "2024-10-01", 
        "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-07",
        "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
        "2025-02-01", "2025-02-02", "2025-02-03", "2025-02-04", "2025-04-05", 
        "2025-04-06", "2025-04-07", "2025-05-01", "2025-05-02", "2025-05-03", 
        "2025-05-31", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-06", 
        "2025-10-07", "2025-10-08"
    ]

# KDAS计算 - 使用kdas.DataHandler
def calculate_cumulative_vwap(df, input_date):
    """
    使用kdas.DataHandler计算KDAS，保持与原API兼容
    
    Args:
        df: 证券数据DataFrame
        input_date: 输入日期字典，格式为 {'day1': 'YYYYMMDD', ...}
        
    Returns:
        包含KDAS计算结果的DataFrame
    """
    if data_handler is None:
        # 备用方案：使用原始实现
        df = df.copy()  # 避免修改原始数据
        df['日期'] = pd.to_datetime(df['日期'])
        for key, value in input_date.items():
            target_date = datetime.strptime(value, "%Y%m%d").date()
            start_idx = df[df['日期'].dt.date == target_date].index
            if len(start_idx) > 0:
                start_idx = start_idx[0]
                # 初始化列为NaN
                df[f'累计成交额{value}'] = pd.Series(dtype=float)
                df[f'累计成交量{value}'] = pd.Series(dtype=float)
                df[f'KDAS{value}'] = pd.Series(dtype=float)
                
                # 只对从start_idx开始的行进行累计计算
                df.loc[start_idx:, f'累计成交额{value}'] = df.loc[start_idx:, '成交额'].cumsum()
                df.loc[start_idx:, f'累计成交量{value}'] = df.loc[start_idx:, '成交量'].cumsum()
                df.loc[start_idx:, f'KDAS{value}'] = (df.loc[start_idx:, f'累计成交额{value}'] / df.loc[start_idx:, f'累计成交量{value}'] / 100).round(3)
        return df
    
    # 使用kdas.DataHandler - 高效且经过优化的实现
    try:
        return data_handler.calculate_cumulative_vwap(df, input_date)
    except Exception as e:
        # 如果kdas包出现问题，回退到备用方案
        st.warning(f"kdas包计算KDAS时出现问题，使用备用方案: {str(e)}")
        df = df.copy()
        df['日期'] = pd.to_datetime(df['日期'])
        for key, value in input_date.items():
            target_date = datetime.strptime(value, "%Y%m%d").date()
            start_idx = df[df['日期'].dt.date == target_date].index
            if len(start_idx) > 0:
                start_idx = start_idx[0]
                df[f'累计成交额{value}'] = pd.Series(dtype=float)
                df[f'累计成交量{value}'] = pd.Series(dtype=float)
                df[f'KDAS{value}'] = pd.Series(dtype=float)
                
                df.loc[start_idx:, f'累计成交额{value}'] = df.loc[start_idx:, '成交额'].cumsum()
                df.loc[start_idx:, f'累计成交量{value}'] = df.loc[start_idx:, '成交量'].cumsum()
                df.loc[start_idx:, f'KDAS{value}'] = (df.loc[start_idx:, f'累计成交额{value}'] / df.loc[start_idx:, f'累计成交量{value}'] / 100).round(3)
        return df

def get_security_name(symbol, security_type):
    """获取证券名称 - 使用kdas.DataHandler"""
    if data_handler is None:
        # 备用方案：查找对应的info_df
        if security_type == "股票":
            info_df = load_stock_info()
        elif security_type == "ETF":
            info_df = load_etf_info()
        elif security_type == "指数":
            info_df = load_index_info()
        else:
            return f"未知{security_type}"
        
        symbol = str(symbol).split('.')[0]
        security_name = info_df[info_df["code"] == symbol]["name"].values
        return security_name[0] if len(security_name) > 0 else f"未知{security_type}"
    
    # 使用kdas.DataHandler
    return data_handler.get_security_name(symbol, security_type)

# ==================== AI分析功能模块 ====================

def get_ai_advisor_instance(api_key, model):
    """获取AI顾问实例 - 使用kdas包"""
    if AI_ADVISOR_AVAILABLE:
        try:
            # 使用kdas包的get_ai_advisor函数
            advisor = get_ai_advisor(api_key, model)
            return advisor
        except Exception as e:
            st.warning(f"创建AI顾问实例失败: {str(e)}")
            return None
    return None

def generate_ai_recommendation(symbol, security_type, api_key, model):
    """生成AI日期推荐 - 使用kdas包"""
    try:
        # 获取证券名称
        security_name = get_security_name(symbol, security_type)
        
        # 生成临时日期用于数据获取
        temp_dates = {f'day{i+1}': (datetime.now() - timedelta(days=30*i)).strftime('%Y%m%d') for i in range(5)}
        
        # 获取分析数据
        analysis_data = get_security_data(symbol, temp_dates, security_type)
        
        if analysis_data.empty:
            return {
                'success': False,
                'error': f'未找到该{security_type}的数据，请检查{security_type}代码是否正确'
            }
        
        ai_engine = AIRecommendationEngine(api_key, model)
        result = ai_engine.generate_kdas_recommendation(
            analysis_data, symbol, security_name, security_type
        )
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'AI推荐过程出现错误: {str(e)}'
        }

def analyze_kdas_state_with_ai(processed_data, input_date, symbol, security_type, api_key, model):
    """使用AI分析KDAS状态 - 使用kdas包"""
    try:
        # 获取证券名称
        security_name = get_security_name(symbol, security_type)
        
        analyzer = KDASAnalyzer(api_key, model)
        analysis_result = analyzer.analyze_kdas_state(
            processed_data, input_date, symbol, security_name, security_type
        )
        
        return analysis_result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'AI分析过程出现错误: {str(e)}',
            'analysis': f'分析失败: {str(e)}'
        }

# ==================== 图表生成模块 ====================

def create_interactive_chart(df, input_date, info_df, security_type="股票", symbol_code=None):
    """创建交互式图表"""
    # 创建子图：上方K线图+KDAS，下方成交量
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=('K线图与KDAS指标', '成交量'),
        row_heights=[0.75, 0.25]  # 上图占75%，下图占25%
    )
    
    # 确保数据按日期排序并过滤掉无效数据
    df = df.sort_values('日期').reset_index(drop=True)
    
    # 更严格的数据过滤逻辑，确保数据质量
    df = df.dropna(subset=['开盘', '收盘', '最高', '最低', '成交量', '成交额'])
    df = df[df['成交量'] > 0].reset_index(drop=True)
    df = df[df['成交额'] > 0].reset_index(drop=True)
    
    # 过滤掉明显异常的数据（如价格为0的情况）
    df = df[(df['开盘'] > 0) & (df['收盘'] > 0) & (df['最高'] > 0) & (df['最低'] > 0)].reset_index(drop=True)
    
    # 确保高价≥低价，开盘和收盘在高低价之间（基本的数据一致性检查）
    df = df[df['最高'] >= df['最低']].reset_index(drop=True)
    df = df[(df['开盘'] >= df['最低']) & (df['开盘'] <= df['最高'])].reset_index(drop=True)
    df = df[(df['收盘'] >= df['最低']) & (df['收盘'] <= df['最高'])].reset_index(drop=True)
    
    # 获取证券名称用于图例
    if symbol_code is None:
        # 如果没有传入symbol_code，尝试从数据中获取
        if '股票代码' in df.columns:
            symbol_code = df['股票代码'].iloc[0]
        else:
            # 对于某些数据源，可能需要从其他列获取代码
            symbol_code = df.iloc[0, 0] if len(df.columns) > 0 else "未知代码"
    
    # 确保symbol_code是字符串格式，并去掉可能的后缀（如.SZ）
    symbol_code = str(symbol_code).split('.')[0]
    
    # 查找证券名称
    # 调试：检查info_df的结构
    # print(f"Debug - symbol_code: {symbol_code}")
    # print(f"Debug - info_df columns: {info_df.columns.tolist()}")
    # print(f"Debug - info_df first few rows:")
    # print(info_df.head())
    
    security_name = info_df[info_df["code"] == symbol_code]["name"].values
    security_name = security_name[0] if len(security_name) > 0 else f"未知{security_type}"
    
    # print(f"Debug - found security_name: {security_name}")  # 调试信息
    
    # 添加K线图到第一行
    fig.add_trace(go.Candlestick(
        x=df['日期'],
        open=df['开盘'],
        high=df['最高'],
        low=df['最低'],
        close=df['收盘'],
        name=f'{security_name}',
        increasing_line_color='#FF4444',
        decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF4444',
        decreasing_fillcolor='#00AA00',
        showlegend=False
    ), row=1, col=1)
    
    # KDAS线条颜色配置
    kdas_colors = {
        'day1': "#FF0000",   # 红色
        'day2': "#0000FF",   # 蓝色  
        'day3': "#00FF00",   # 绿色
        'day4': "#FF00FF",   # 紫色
        'day5': "#FFA500",   # 橙色
    }
    
    # 添加KDAS线条到第一行（与股价共享同一个Y轴）
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            # 过滤掉NaN值
            mask = df[f'KDAS{value}'].notna()
            fig.add_trace(go.Scatter(
                x=df.loc[mask, '日期'],
                y=df.loc[mask, f'KDAS{value}'],
                mode='lines',
                name=f'D{key[-1]}',
                line=dict(color=kdas_colors.get(key, "#000000"), width=2, dash='solid'),
                opacity=0.8
            ), row=1, col=1)
    
    # 添加成交量柱状图到第二行
    volume_colors = ['#FF4444' if close >= open else '#00AA00' 
                    for close, open in zip(df['收盘'], df['开盘'])]
    
    fig.add_trace(go.Bar(
        x=df['日期'],
        y=df['成交量'],
        name='成交量',
        marker_color=volume_colors,
        opacity=0.7,
        showlegend=False
    ), row=2, col=1)
    
    # 设置Y轴标题
    fig.update_yaxes(title_text="价格/KDAS (元)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)
    
    # 计算当前支撑位和压力位
    current_price = df['收盘'].iloc[-1]
    support_levels = []  # 支撑位（价格下方的KDAS值）
    resistance_levels = []  # 压力位（价格上方的KDAS值）
    
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            # 获取最新的KDAS值
            kdas_series = df[f'KDAS{value}'].dropna()
            if not kdas_series.empty:
                latest_kdas = kdas_series.iloc[-1]
                if latest_kdas < current_price:
                    support_levels.append((latest_kdas, f"支撑位: ¥{latest_kdas:.3f}"))
                elif latest_kdas > current_price:
                    resistance_levels.append((latest_kdas, f"压力位: ¥{latest_kdas:.3f}"))
    
    # 对支撑位和压力位进行排序
    support_levels.sort(key=lambda x: x[0], reverse=True)  # 支撑位从高到低排序
    resistance_levels.sort(key=lambda x: x[0])  # 压力位从低到高排序
    
    # 创建图例文本
    legend_text = []
    legend_text.append(f"📊 当前价格: ¥{current_price:.3f}")
    legend_text.append("━━━━━━━━━━━━━━━━")
    
    if resistance_levels:
        legend_text.append("🔴 压力位:")
        for _, text in resistance_levels:
            legend_text.append(f"  {text}")
    
    if support_levels:
        legend_text.append("🟢 支撑位:")
        for _, text in support_levels:
            legend_text.append(f"  {text}")
    
    if not resistance_levels and not support_levels:
        legend_text.append("暂无明显支撑/压力位")
    
    # 更新整体布局
    fig.update_layout(
        title={
            'text': f"{security_name} ({symbol_code}) - K线走势图与KDAS指标分析",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        height=800,
        xaxis_rangeslider_visible=False,  # 隐藏K线图下方的范围滑块
        showlegend=False,  # 隐藏默认图例
        hovermode='x unified',  # 统一悬停模式
        template='plotly_white',  # 使用白色主题
        annotations=[
            dict(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text="<br>".join(legend_text),
                showarrow=False,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='rgba(0, 0, 0, 0.3)',
                borderwidth=1,
                font=dict(size=11, family="monospace"),
                align="left",
                xanchor="left",
                yanchor="top"
            )
        ]
    )
    
    # 使用官方交易日历配置X轴，精确跳过非交易日
    # 基础配置：隐藏周末
    rangebreaks_config = [
        dict(bounds=["sat", "mon"])  # 隐藏周末
    ]
    
    # 获取数据的日期范围
    start_date = df['日期'].min().date()
    end_date = df['日期'].max().date()
    
    # 使用官方交易日历获取非交易日
    non_trading_dates = get_non_trading_dates(start_date, end_date)
    
    if non_trading_dates:
        rangebreaks_config.append(dict(values=non_trading_dates))
        print(f"🗓️ 应用了 {len(non_trading_dates)} 个非交易日的rangebreaks配置")
    else:
        print("⚠️ 未获取到非交易日数据，仅应用周末配置")
    
    # 应用配置到两个子图
    fig.update_xaxes(rangebreaks=rangebreaks_config, row=1, col=1)
    fig.update_xaxes(rangebreaks=rangebreaks_config, row=2, col=1)
    
    # 设置价格和KDAS的综合Y轴范围
    # 获取价格范围
    price_min = df[['开盘', '收盘', '最高', '最低']].min().min()
    price_max = df[['开盘', '收盘', '最高', '最低']].max().max()
    
    # 获取KDAS范围
    kdas_values = []
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            kdas_values.extend(df[f'KDAS{value}'].dropna().tolist())
    
    # 计算综合范围
    if kdas_values:
        kdas_min, kdas_max = min(kdas_values), max(kdas_values)
        combined_min = min(price_min, kdas_min)
        combined_max = max(price_max, kdas_max)
    else:
        combined_min = price_min
        combined_max = price_max
    
    # 设置Y轴范围，留出10%的余量
    range_span = combined_max - combined_min
    fig.update_yaxes(
        range=[combined_min - range_span * 0.1, combined_max + range_span * 0.1],
        row=1, col=1
    )
    
    return fig

def create_mini_chart(df, input_date, info_df, security_type="股票", symbol_code=None):
    """创建紧凑型交互式图表，用于多图看板"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=(None, None), # No subplot titles
        row_heights=[0.7, 0.3]
    )
    
    df = df.sort_values('日期').reset_index(drop=True)
    df = df.dropna(subset=['开盘', '收盘', '最高', '最低', '成交量', '成交额'])
    df = df[df['成交量'] > 0].reset_index(drop=True)
    df = df[(df['开盘'] > 0) & (df['收盘'] > 0) & (df['最高'] > 0) & (df['最低'] > 0)].reset_index(drop=True)
    df = df[df['最高'] >= df['最低']].reset_index(drop=True)

    symbol_code = str(symbol_code).split('.')[0]
    security_name_series = info_df[info_df["code"] == symbol_code]["name"]
    security_name = security_name_series.values[0] if len(security_name_series) > 0 else f"未知{security_type}"
    
    fig.add_trace(go.Candlestick(
        x=df['日期'],
        open=df['开盘'],
        high=df['最高'],
        low=df['最低'],
        close=df['收盘'],
        name=f'{security_name}',
        increasing_line_color='#FF4444',
        decreasing_line_color='#00AA00',
        increasing_fillcolor='#FF4444',
        decreasing_fillcolor='#00AA00',
        showlegend=False
    ), row=1, col=1)
    
    kdas_colors = {
        'day1': "#FF0000", 'day2': "#0000FF", 'day3': "#00FF00",
        'day4': "#FF00FF", 'day5': "#FFA500",
    }
    
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            mask = df[f'KDAS{value}'].notna()
            fig.add_trace(go.Scatter(
                x=df.loc[mask, '日期'],
                y=df.loc[mask, f'KDAS{value}'],
                mode='lines',
                name=f'D{key[-1]}',
                line=dict(color=kdas_colors.get(key, "#000000"), width=2, dash='solid'),
                opacity=0.8
            ), row=1, col=1)
    
    # 计算当前支撑位和压力位
    current_price = df['收盘'].iloc[-1]
    support_levels = []  # 支撑位（价格下方的KDAS值）
    resistance_levels = []  # 压力位（价格上方的KDAS值）
    
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            # 获取最新的KDAS值
            kdas_series = df[f'KDAS{value}'].dropna()
            if not kdas_series.empty:
                latest_kdas = kdas_series.iloc[-1]
                if latest_kdas < current_price:
                    support_levels.append((latest_kdas, f"支撑位: ¥{latest_kdas:.3f}"))
                elif latest_kdas > current_price:
                    resistance_levels.append((latest_kdas, f"压力位: ¥{latest_kdas:.3f}"))
    
    # 对支撑位和压力位进行排序
    support_levels.sort(key=lambda x: x[0], reverse=True)  # 支撑位从高到低排序
    resistance_levels.sort(key=lambda x: x[0])  # 压力位从低到高排序
    
    # 创建图例文本
    legend_text = []
    legend_text.append(f"📊 当前价格: ¥{current_price:.3f}")
    legend_text.append("━━━━━━━━━━━━━━━━")
    
    if resistance_levels:
        legend_text.append("🔴 压力位:")
        for _, text in resistance_levels:
            legend_text.append(f"  {text}")
    
    if support_levels:
        legend_text.append("🟢 支撑位:")
        for _, text in support_levels:
            legend_text.append(f"  {text}")
    
    if not resistance_levels and not support_levels:
        legend_text.append("暂无明显支撑/压力位")
    
    fig.update_layout(
        title={
            'text': f"{security_name} ({symbol_code})",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 14}
        },
        height=400,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=40, r=20, t=70, b=40),
        annotations=[
            dict(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text="<br>".join(legend_text),
                showarrow=False,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='rgba(0, 0, 0, 0.3)',
                borderwidth=1,
                font=dict(size=9, family="monospace"),  # 使用更小的字体以适应小图
                align="left",
                xanchor="left",
                yanchor="top"
            )
        ]
    )
    
    start_date, end_date = df['日期'].min().date(), df['日期'].max().date()
    non_trading_dates = get_non_trading_dates(start_date, end_date)
    
    rangebreaks_config = [dict(bounds=["sat", "mon"])]
    if non_trading_dates:
        rangebreaks_config.append(dict(values=non_trading_dates))
    
    fig.update_xaxes(rangebreaks=rangebreaks_config)
    fig.update_yaxes(title_text=None, row=1, col=1)
    fig.update_yaxes(title_text=None, row=2, col=1)
    
    # 设置价格和KDAS的综合Y轴范围
    # 获取价格范围
    price_min = df[['开盘', '收盘', '最高', '最低']].min().min()
    price_max = df[['开盘', '收盘', '最高', '最低']].max().max()
    
    # 获取KDAS范围
    kdas_values = []
    for key, value in input_date.items():
        if f'KDAS{value}' in df.columns:
            kdas_values.extend(df[f'KDAS{value}'].dropna().tolist())
    
    # 计算综合范围
    if kdas_values:
        kdas_min, kdas_max = min(kdas_values), max(kdas_values)
        combined_min = min(price_min, kdas_min)
        combined_max = max(price_max, kdas_max)
    else:
        combined_min = price_min
        combined_max = price_max
    
    # 设置Y轴范围，留出10%的余量
    range_span = combined_max - combined_min
    fig.update_yaxes(
        range=[combined_min - range_span * 0.1, combined_max + range_span * 0.1],
        row=1, col=1
    )
    
    return fig

def validate_and_cleanup_config():
    """验证并清理配置文件，移除无效或过期的配置项"""
    configs = load_user_configs()
    cleaned = False
    
    # 清理空的或无效的证券配置
    keys_to_remove = []
    for key, value in configs.items():
        if key == 'global_settings':
            continue
            
        # 检查证券配置的有效性
        if not isinstance(value, dict):
            keys_to_remove.append(key)
            cleaned = True
            continue
            
        required_fields = ['symbol', 'security_type', 'security_name', 'dates']
        if not all(field in value for field in required_fields):
            keys_to_remove.append(key)
            cleaned = True
            continue
            
        # 检查是否有空的或无效的symbol
        if not value.get('symbol') or not value.get('symbol').strip():
            keys_to_remove.append(key)
            cleaned = True
    
    # 移除无效配置
    for key in keys_to_remove:
        del configs[key]
        print(f"已清理无效配置: {key}")
    
    # 验证全局设置
    if 'global_settings' in configs:
        global_settings = configs['global_settings']
        
        # 清理空的API密钥
        if 'api_key' in global_settings and not global_settings['api_key'].strip():
            del global_settings['api_key']
            cleaned = True
            
        # 验证模型名称
        valid_models = ['deepseek-r1', 'deepseek-v3', 'gpt-4', 'gpt-3.5-turbo']
        if 'default_model' in global_settings:
            if global_settings['default_model'] not in valid_models:
                global_settings['default_model'] = 'deepseek-r1'
                cleaned = True
                
        # 清理空的全局设置
        if not global_settings:
            del configs['global_settings']
            cleaned = True
    
    # 如果有清理操作，保存配置
    if cleaned:
        save_user_configs(configs)
        print("配置文件已验证并清理")
    
    return configs

def get_config_summary():
    """获取配置摘要，用于调试和监控"""
    configs = load_user_configs()
    
    summary = {
        'total_configs': len(configs),
        'has_global_settings': 'global_settings' in configs,
        'securities_count': len([k for k in configs.keys() if k != 'global_settings']),
        'has_api_key': bool(get_config_with_validation('global_settings.api_key', '', str)),
        'ai_analysis_enabled': get_config_with_validation('global_settings.ai_analysis_enabled', False, bool),
        'ai_date_recommendation_enabled': get_config_with_validation('global_settings.ai_date_recommendation_enabled', True, bool),
        'has_multi_chart_config': get_config_with_validation('global_settings.multi_chart_config', None) is not None
    }
    
    return summary

# ==================== 分析功能模块 ====================

def run_single_chart_analysis_with_kdas(security_type, symbol, api_key=None, model="deepseek-r1", manual_dates=None):
    """
    使用kdas包的集成功能进行单图精细分析
    
    Args:
        security_type: 证券类型
        symbol: 证券代码
        api_key: AI API密钥
        model: AI模型名称
        manual_dates: 手动指定的日期字典，如果提供则不使用AI推荐
    
    Returns:
        分析结果字典
    """
    try:
        # 1. 获取证券名称
        security_name = get_security_name(symbol, security_type)
        
        # 2. 判断是使用AI推荐还是手动日期
        if manual_dates and not any(st.session_state.get('using_ai_dates', False) for _ in [True]):
            # 使用手动日期
            input_date = manual_dates
            df = get_security_data(symbol, input_date, security_type)
            if df.empty:
                return {
                    'success': False,
                    'error': f'未找到该{security_type}的数据，请检查{security_type}代码是否正确。',
                    'data': None,
                    'processed_data': None,
                    'security_name': security_name,
                    'recommendation_result': None,
                    'ai_analysis_result': None
                }
            
            # 计算KDAS
            processed_data = calculate_cumulative_vwap(df, input_date)
            
            # 如果有API密钥，进行AI状态分析
            ai_analysis_result = None
            if api_key and load_ai_analysis_setting():
                ai_analysis_result = analyze_kdas_state_with_ai(
                    processed_data, input_date, symbol, security_type, api_key, model
                )
            
            return {
                'success': True,
                'data': df,
                'processed_data': processed_data,
                'security_name': security_name,
                'input_dates': input_date,
                'recommendation_result': None,
                'ai_analysis_result': ai_analysis_result,
                'mode': 'manual'
            }
        
        elif api_key and AI_ADVISOR_AVAILABLE:
            # 使用kdas包的完整集成分析
            try:
                # 使用kdas包的集成功能
                advisor = get_ai_advisor_instance(api_key, model)
                if advisor is None:
                    raise Exception("无法创建AI顾问实例")
                
                # 异步调用需要在同步函数中处理
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    kdas_result = loop.run_until_complete(
                        advisor.analyze_all_async(security_type, symbol, api_key, model)
                    )
                finally:
                    loop.close()
                
                if not kdas_result.get('success', False):
                    # 如果AI分析失败，回退到手动模式
                    if manual_dates:
                        return run_single_chart_analysis_with_kdas(
                            security_type, symbol, api_key, model, manual_dates
                        )
                    else:
                        return {
                            'success': False,
                            'error': f'AI分析失败: {kdas_result.get("error", "未知错误")}',
                            'data': None,
                            'processed_data': None,
                            'security_name': security_name,
                            'recommendation_result': kdas_result.get('recommendation'),
                            'ai_analysis_result': kdas_result.get('analysis')
                        }
                
                # 成功获得AI推荐，使用推荐的日期重新获取数据和计算KDAS
                recommended_dates_dict = kdas_result.get('input_dates', {})
                df = get_security_data(symbol, recommended_dates_dict, security_type)
                processed_data = calculate_cumulative_vwap(df, recommended_dates_dict)
                
                return {
                    'success': True,
                    'data': df,
                    'processed_data': processed_data,
                    'security_name': security_name,
                    'input_dates': recommended_dates_dict,
                    'recommendation_result': kdas_result.get('recommendation'),
                    'ai_analysis_result': kdas_result.get('analysis'),
                    'mode': 'ai_integrated',
                    'recommended_dates': kdas_result.get('recommended_dates', [])
                }
                
            except Exception as e:
                # AI分析出错，如果有手动日期则回退
                if manual_dates:
                    return run_single_chart_analysis_with_kdas(
                        security_type, symbol, api_key, model, manual_dates
                    )
                else:
                    return {
                        'success': False,
                        'error': f'AI集成分析失败: {str(e)}',
                        'data': None,
                        'processed_data': None,
                        'security_name': security_name,
                        'recommendation_result': None,
                        'ai_analysis_result': None
                    }
        
        else:
            # 没有API密钥或AI不可用，必须使用手动日期
            if not manual_dates:
                return {
                    'success': False,
                    'error': '没有配置AI API密钥，请手动选择日期或配置API密钥',
                    'data': None,
                    'processed_data': None,
                    'security_name': security_name,
                    'recommendation_result': None,
                    'ai_analysis_result': None
                }
            
            return run_single_chart_analysis_with_kdas(
                security_type, symbol, api_key, model, manual_dates
            )
    
    except Exception as e:
        return {
            'success': False,
            'error': f'分析过程中出现错误: {str(e)}',
            'data': None,
            'processed_data': None,
            'security_name': get_security_name(symbol, security_type) if symbol else "未知",
            'recommendation_result': None,
            'ai_analysis_result': None
        }

def run_multi_chart_analysis_with_kdas(securities_config, global_dates):
    """
    使用kdas包优化多图看板分析功能
    
    Args:
        securities_config: 证券配置列表
        global_dates: 全局日期配置
    
    Returns:
        分析结果列表
    """
    results = []
    
    # 预加载数据源映射
    info_sources = {
        "股票": load_stock_info(),
        "ETF": load_etf_info(), 
        "指数": load_index_info()
    }
    
    for i, config in enumerate(securities_config):
        symbol = config.get('symbol', '').strip()
        sec_type = config.get('type', '股票')
        
        # 跳过空的配置
        if not symbol:
            results.append({
                'success': False,
                'index': i,
                'symbol': '',
                'type': sec_type,
                'error': '未配置证券代码',
                'data': None,
                'processed_data': None,
                'fig': None
            })
            continue
        
        try:
            # 确定使用的日期
            if config.get('use_global_dates', True):
                dates_to_use = global_dates
            elif config.get('dates'):
                dates_to_use = config['dates']
            else:
                dates_to_use = global_dates
            
            # 使用已优化的数据获取函数
            data = get_security_data(symbol, dates_to_use, sec_type)
            
            if data.empty:
                results.append({
                    'success': False,
                    'index': i,
                    'symbol': symbol,
                    'type': sec_type,
                    'error': f'未找到{sec_type}数据',
                    'data': None,
                    'processed_data': None,
                    'fig': None
                })
                continue
            
            # 计算KDAS
            processed_data = calculate_cumulative_vwap(data, dates_to_use)
            
            # 创建图表
            info_df = info_sources[sec_type]
            fig = create_mini_chart(processed_data, dates_to_use, info_df, sec_type, symbol)
            
            results.append({
                'success': True,
                'index': i,
                'symbol': symbol,
                'type': sec_type,
                'data': data,
                'processed_data': processed_data,
                'fig': fig,
                'dates_used': dates_to_use
            })
            
        except Exception as e:
            results.append({
                'success': False,
                'index': i,
                'symbol': symbol,
                'type': sec_type,
                'error': str(e),
                'data': None,
                'processed_data': None,
                'fig': None
            })
    
    return results

def render_multi_chart_dashboard(analysis_results):
    """
    渲染多图看板的结果展示
    
    Args:
        analysis_results: 分析结果列表
    """
    # 创建3x2的网格布局
    col_defs = [1, 1, 1]
    row1 = st.columns(col_defs)
    row2 = st.columns(col_defs)
    plot_positions = row1 + row2
    
    for i, pos in enumerate(plot_positions):
        with pos:
            if i < len(analysis_results):
                result = analysis_results[i]
                
                if result['success']:
                    # 显示成功的图表
                    st.plotly_chart(result['fig'], use_container_width=True)
                else:
                    # 显示错误信息
                    if result['symbol']:
                        error_msg = f"图表 {i+1}: {result['symbol']}<br>❌ {result['error']}"
                    else:
                        error_msg = f"图表 {i+1}<br>未配置"
                    
                    st.markdown(
                        f"<div style='height: 400px; display: flex; align-items: center; "
                        f"justify-content: center; background-color: #ffebee; border: 1px solid #f44336; "
                        f"border-radius: 10px; text-align: center; color: #d32f2f;'>{error_msg}</div>", 
                        unsafe_allow_html=True
                    )
            else:
                # 显示空白占位符
                st.markdown(
                    f"<div style='height: 400px; display: flex; align-items: center; "
                    f"justify-content: center; background-color: #f0f2f6; border-radius: 10px; "
                    f"text-align: center; color: grey;'>图表 {i+1}<br>未配置</div>", 
                    unsafe_allow_html=True
                )

def get_multi_chart_summary(analysis_results):
    """
    获取多图看板分析的汇总信息
    
    Args:
        analysis_results: 分析结果列表
    
    Returns:
        汇总信息字典
    """
    total_charts = len(analysis_results)
    successful_charts = sum(1 for r in analysis_results if r['success'])
    failed_charts = total_charts - successful_charts
    
    # 按类型统计
    type_stats = {}
    for result in analysis_results:
        if result['success']:
            sec_type = result['type']
            type_stats[sec_type] = type_stats.get(sec_type, 0) + 1
    
    # 获取失败的证券列表
    failed_securities = [
        f"{r['symbol']} ({r['type']})" 
        for r in analysis_results 
        if not r['success'] and r['symbol']
    ]
    
    return {
        'total_charts': total_charts,
        'successful_charts': successful_charts,
        'failed_charts': failed_charts,
        'type_statistics': type_stats,
        'failed_securities': failed_securities,
        'success_rate': successful_charts / total_charts if total_charts > 0 else 0
    }

# ==================== UI渲染模块 ====================

def render_waiting_dashboard():
    """
    渲染等待状态的多图看板
    """
    col_defs = [1, 1, 1]
    row1 = st.columns(col_defs)
    row2 = st.columns(col_defs)
    plot_positions = row1 + row2
    
    for i, pos in enumerate(plot_positions):
        with pos:
            st.markdown(
                f"<div style='height: 400px; display: flex; align-items: center; "
                f"justify-content: center; background-color: #f0f2f6; border-radius: 10px; "
                f"text-align: center; color: grey;'>图表 {i+1}<br>等待分析...</div>", 
                unsafe_allow_html=True
            )

# ==================== 主程序入口 ====================

def main():
    st.set_page_config(page_title="KDAS证券分析工具", layout="wide")
    
    # 应用启动时验证和清理配置文件
    if 'config_validated' not in st.session_state:
        try:
            validate_and_cleanup_config()
            st.session_state.config_validated = True
        except Exception as e:
            st.warning(f"配置文件验证时出现问题: {e}")
    
    st.title("📈 KDAS证券分析工具")
    st.markdown("---")
    
    with st.sidebar:
        st.header("模式选择")
        app_mode = st.radio(
            "选择分析模式",
            ("单图精细分析", "多图概览看板"),
            key='app_mode_selection',
            horizontal=True,
        )
        st.markdown("---")

    if app_mode == "单图精细分析":
        # 检查是否需要加载完整配置
        load_full_config = st.session_state.get('load_full_config', None)
        if load_full_config:
            st.success(f"✅ 已加载完整配置: {load_full_config['symbol']}")
            # 将配置信息设置到session_state中，用于组件显示
            st.session_state.current_security_type = load_full_config['security_type']
            st.session_state.current_symbol = load_full_config['symbol']
            st.session_state.current_dates = load_full_config['dates']
            # 清除load_full_config标志
            st.session_state.load_full_config = None
        
        # 侧边栏配置
        with st.sidebar:
            st.header("📊 配置参数")
            
            # 证券类型选择 - 如果有当前配置，则使用配置中的类型
            current_security_type = st.session_state.get('current_security_type', None)
            if current_security_type:
                security_type_options = ["股票", "ETF", "指数"]
                default_type_index = security_type_options.index(current_security_type)
            else:
                default_type_index = 0
                
            security_type = st.selectbox(
                "证券类型",
                ["股票", "ETF", "指数"],
                index=default_type_index,
                help="选择要分析的证券类型"
            )
            
            # 根据证券类型加载对应的信息
            if security_type == "股票":
                info_df = load_stock_info()
                default_symbol = "001215"
                help_text = "请输入6位股票代码"
            elif security_type == "ETF":
                info_df = load_etf_info()
                default_symbol = "159915"
                help_text = "请输入6位ETF代码"
            else:  # 指数
                info_df = load_index_info()
                default_symbol = "000001"
                help_text = "请输入6位指数代码"
            
            # 如果有当前配置，使用配置中的代码
            current_symbol = st.session_state.get('current_symbol', None)
            if current_symbol:
                default_symbol = current_symbol
            
            # 证券代码选择
            symbol = st.text_input(f"{security_type}代码", value=default_symbol, help=help_text)
            
            # 检查是否有保存的配置
            saved_config = None
            if symbol:
                saved_config = get_saved_config(symbol, security_type)
                if saved_config:
                    st.success(f"💾 找到保存的配置: {saved_config['security_name']}")
                    if st.button("🔄 加载保存的日期配置", use_container_width=True):
                        st.session_state.load_saved_config = True
                        st.rerun()
            
            st.subheader("KDAS计算起始日期")
            
            # AI智能推荐功能
            if AI_ADVISOR_AVAILABLE and symbol:
                st.markdown("#### 🤖 AI智能推荐")
                
                # 加载保存的API密钥和模型配置
                saved_api_key, saved_model = load_api_key()
                
                # AI日期推荐开关（新增，放在最上方）
                ai_date_recommendation_enabled = load_ai_date_recommendation_setting()
                ai_date_enabled_checkbox = st.checkbox(
                    "📅 启用AI日期推荐", 
                    value=ai_date_recommendation_enabled,
                    help="开启后分析时将自动使用AI推荐的最佳关键日期"
                )
                
                # 保存AI日期推荐开关设置
                if ai_date_enabled_checkbox != ai_date_recommendation_enabled:
                    save_ai_date_recommendation_setting(ai_date_enabled_checkbox)
                
                # AI分析开关
                ai_analysis_enabled = load_ai_analysis_setting()
                ai_enabled_checkbox = st.checkbox(
                    "🔮 启用AI智能分析", 
                    value=ai_analysis_enabled,
                    help="开启后将在右侧显示AI分析报告"
                )
                
                # 保存AI分析开关设置
                if ai_enabled_checkbox != ai_analysis_enabled:
                    save_ai_analysis_setting(ai_enabled_checkbox)
                
                # 根据AI选项组合显示相应提示
                if not ai_date_enabled_checkbox and not ai_enabled_checkbox:
                    st.info("💡 可勾选上方AI选项以启用智能功能：日期推荐 + 状态分析")
                elif ai_date_enabled_checkbox and not ai_enabled_checkbox:
                    st.info("💡 当前将使用AI推荐日期，可额外勾选「🔮 启用AI智能分析」获得分析报告")
                elif not ai_date_enabled_checkbox and ai_enabled_checkbox:
                    st.info("💡 当前将分析手动选择的日期，可额外勾选「📅 启用AI日期推荐」自动推荐最佳日期")
                else:
                    # 两个AI功能都启用时的提示
                    if not saved_api_key:
                        st.warning("⚠️ 已启用AI功能，但需要配置API密钥才能使用")
                    else:
                        st.success("✅ AI完整功能已启用：智能日期推荐 + 状态分析")
                
                # 加载保存的API密钥和模型配置
                api_key_input = st.text_input(
                    "AI API密钥", 
                    value=saved_api_key,  # 使用保存的API密钥作为默认值
                    type="password", 
                    help="输入您的AI API密钥以使用AI功能（日期推荐和智能分析）",
                    placeholder="sk-..."
                )
                
                # 获取当前模型列表并确定默认选择
                model_options = ["deepseek-r1", "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-03-25"]
                default_model_index = 0
                if saved_model in model_options:
                    default_model_index = model_options.index(saved_model)
                
                # AI模型选择
                ai_model = st.selectbox(
                    "AI模型选择",
                    model_options,
                    index=default_model_index,
                    help="选择要使用的AI模型"
                )
                
                # API密钥保存/删除按钮
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 保存配置", help="保存API密钥和模型选择，下次无需重新输入"):
                        if api_key_input.strip():
                            if save_api_key(api_key_input.strip(), ai_model):
                                st.success("✅ 配置已保存！")
                            else:
                                st.error("❌ 保存失败，请重试")
                        else:
                            st.warning("⚠️ 请先输入API密钥")
                
                with col2:
                    if saved_api_key and st.button("🗑️ 清除配置", help="删除保存的API密钥"):
                        if delete_api_key():
                            st.success("✅ 配置已清除！")
                            st.rerun()  # 刷新页面以清除输入框
                        else:
                            st.error("❌ 清除失败，请重试")
                
                if api_key_input:
                    os.environ['OPENAI_API_KEY'] = api_key_input

                st.markdown("---")
            
            # 使用日期选择器
            default_dates = [
                datetime(2024, 9, 24).date(),
                datetime(2024, 11, 7).date(),
                datetime(2024, 12, 17).date(),
                datetime(2025, 4, 7).date(),
                datetime(2025, 4, 23).date()
            ]
            
            # 如果有当前配置，使用配置中的日期
            if st.session_state.get('current_dates'):
                current_dates = st.session_state.current_dates
                try:
                    for i, (key, date_str) in enumerate(current_dates.items()):
                        if i < len(default_dates):  # 确保不超出范围
                            date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                            # 直接设置到session_state中
                            st.session_state[f"date_{i+1}"] = date_obj
                except Exception as e:
                    st.warning(f"加载完整配置的日期失败: {e}")
            
            # 如果有保存的配置且用户选择加载，则使用保存的日期
            elif (saved_config and 
                hasattr(st.session_state, 'load_saved_config') and 
                st.session_state.load_saved_config):
                try:
                    for i, (key, date_str) in enumerate(saved_config['dates'].items()):
                        date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                        # 直接设置到session_state中
                        st.session_state[f"date_{i+1}"] = date_obj
                    st.session_state.load_saved_config = False  # 重置标志
                    st.success("✅ 已加载保存的日期配置！")
                except Exception as e:
                    st.warning(f"加载保存的日期配置失败: {e}")
            
            input_date = {}
            colors = ["🔴", "🔵", "🟢", "🟣", "🟡"]
            
            for i in range(5):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"{colors[i]} Day{i+1}")
                with col2:
                    # 使用session_state中的值，如果不存在则使用默认值
                    date_key = f"date_{i+1}"
                    if date_key not in st.session_state:
                        st.session_state[date_key] = default_dates[i]
                    
                    selected_date = st.date_input(
                        f"日期{i+1}",
                        key=f"date_{i+1}"
                    )
                    
                    input_date[f'day{i+1}'] = selected_date.strftime('%Y%m%d')
            
            # 分析按钮
            analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)
            
            # 如果当前有加载的配置或分析状态，显示清除按钮
            has_current_config = (st.session_state.get('current_security_type') or 
                                st.session_state.get('current_symbol') or 
                                st.session_state.get('current_dates'))
            has_analysis_state = st.session_state.get('current_analysis')
            
            if has_current_config or has_analysis_state:
                if st.button("🔄 清除当前配置", use_container_width=True):
                    # 清除当前配置
                    keys_to_clear = [
                        'current_security_type', 'current_symbol', 'current_dates', 'current_analysis'
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    # 清除所有分析状态
                    analysis_keys = [k for k in st.session_state.keys() if k.startswith('analysis_')]
                    for key in analysis_keys:
                        del st.session_state[key]
                    
                    # 同时清除日期选择器的session_state值，让它们回到默认状态
                    for i in range(5):
                        date_key = f"date_{i+1}"
                        if date_key in st.session_state:
                            del st.session_state[date_key]
                            
                    st.rerun()
            
            # 配置管理
            st.markdown("---")
            st.subheader("💾 配置管理")
            
            # 配置诊断功能
            with st.expander("🔧 配置诊断", expanded=False):
                st.markdown("**系统配置状态检查**")
                
                # 检查配置文件状态
                config_file_exists = os.path.exists(CONFIG_FILE)
                if config_file_exists:
                    try:
                        file_size = os.path.getsize(CONFIG_FILE)
                        st.success(f"✅ 配置文件存在: {CONFIG_FILE} ({file_size} 字节)")
                        
                        # 检查文件权限
                        if os.access(CONFIG_FILE, os.R_OK):
                            st.success("✅ 配置文件可读")
                        else:
                            st.error("❌ 配置文件不可读")
                            
                        if os.access(CONFIG_FILE, os.W_OK):
                            st.success("✅ 配置文件可写")
                        else:
                            st.error("❌ 配置文件不可写 - 这可能导致保存失败")
                            
                    except Exception as e:
                        st.error(f"❌ 检查配置文件时出错: {e}")
                else:
                    st.warning("⚠️ 配置文件不存在，将在首次保存时创建")
                
                # 检查配置目录权限
                config_dir = os.path.dirname(CONFIG_FILE) if os.path.dirname(CONFIG_FILE) else '.'
                if os.path.exists(config_dir):
                    if os.access(config_dir, os.W_OK):
                        st.success(f"✅ 配置目录可写: {config_dir}")
                    else:
                        st.error(f"❌ 配置目录不可写: {config_dir}")
                else:
                    st.warning(f"⚠️ 配置目录不存在: {config_dir}")
                
                # 检查磁盘空间
                try:
                    import shutil
                    total, used, free = shutil.disk_usage(config_dir)
                    free_mb = free // (1024*1024)
                    if free_mb > 10:  # 至少10MB空闲空间
                        st.success(f"✅ 磁盘空间充足: {free_mb} MB 可用")
                    else:
                        st.error(f"❌ 磁盘空间不足: 仅 {free_mb} MB 可用")
                except Exception as e:
                    st.warning(f"⚠️ 无法检查磁盘空间: {e}")
                
                # 配置文件内容验证
                if config_file_exists:
                    try:
                        configs = load_user_configs()
                        st.success(f"✅ 配置文件格式正确，包含 {len(configs)} 个配置项")
                        
                        # 检查配置完整性
                        issues = []
                        for key, config in configs.items():
                            if key == 'global_settings':
                                continue
                            if not isinstance(config, dict):
                                issues.append(f"配置项 {key} 格式错误")
                            else:
                                required_fields = ['symbol', 'security_type', 'security_name', 'dates']
                                missing_fields = [f for f in required_fields if f not in config]
                                if missing_fields:
                                    issues.append(f"配置项 {key} 缺少字段: {missing_fields}")
                        
                        if issues:
                            st.warning("⚠️ 发现配置问题:")
                            for issue in issues:
                                st.write(f"  - {issue}")
                        else:
                            st.success("✅ 所有配置项格式正确")
                            
                    except Exception as e:
                        st.error(f"❌ 配置文件解析失败: {e}")
                
                # 测试保存功能
                if st.button("🧪 测试配置保存功能"):
                    test_config = {
                        'test_key': {
                            'symbol': 'TEST01',
                            'security_type': '测试',
                            'security_name': '测试证券',
                            'dates': {'day1': '20240101'},
                            'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'test_flag': True
                        }
                    }
                    
                    try:
                        # 加载现有配置
                        existing_configs = load_user_configs()
                        # 添加测试配置
                        existing_configs.update(test_config)
                        # 尝试保存
                        if save_user_configs(existing_configs):
                            st.success("✅ 配置保存测试成功")
                            # 清理测试配置
                            del existing_configs['test_key']
                            save_user_configs(existing_configs)
                            st.info("🧹 测试配置已清理")
                        else:
                            st.error("❌ 配置保存测试失败")
                    except Exception as e:
                        st.error(f"❌ 配置保存测试异常: {e}")
            
            # 显示全局设置状态
            configs = load_user_configs()
            global_settings = configs.get('global_settings', {})
            if global_settings:
                with st.expander("⚙️ 全局设置"):
                    if 'ai_date_recommendation_enabled' in global_settings:
                        enabled_status = "✅ 已启用" if global_settings['ai_date_recommendation_enabled'] else "❌ 已禁用"
                        st.write(f"**AI日期推荐**: {enabled_status}")
                    if 'ai_analysis_enabled' in global_settings:
                        enabled_status = "✅ 已启用" if global_settings['ai_analysis_enabled'] else "❌ 已禁用"
                        st.write(f"**AI智能分析**: {enabled_status}")
                    if 'api_key' in global_settings:
                        masked_key = global_settings['api_key'][:8] + "..." + global_settings['api_key'][-4:] if len(global_settings['api_key']) > 12 else "***"
                        st.write(f"**API密钥**: {masked_key}")
                    if 'default_model' in global_settings:
                        st.write(f"**默认AI模型**: {global_settings['default_model']}")
                    if 'save_time' in global_settings:
                        st.write(f"**保存时间**: {global_settings['save_time']}")
            
            # 显示已保存的配置
            security_configs = {k: v for k, v in configs.items() if k != 'global_settings'}
            if security_configs:
                st.write(f"已保存 {len(security_configs)} 个证券配置:")
                
                for config_key, config in security_configs.items():
                    with st.expander(f"{config['security_name']} ({config['symbol']})"):
                        st.write(f"**类型**: {config['security_type']}")
                        st.write(f"**保存时间**: {config['save_time']}")
                        st.write("**日期配置**:")
                        for day_key, date_str in config['dates'].items():
                            try:
                                date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                                st.write(f"  - {day_key}: {date_obj}")
                            except:
                                st.write(f"  - {day_key}: {date_str}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"📋 加载完整配置", key=f"load_full_{config_key}"):
                                # 清除之前的配置状态
                                keys_to_clear = ['current_security_type', 'current_symbol', 'current_dates', 'load_saved_config']
                                for key in keys_to_clear:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                
                                # 清除日期选择器的session_state值
                                for i in range(5):
                                    date_key = f"date_{i+1}"
                                    if date_key in st.session_state:
                                        del st.session_state[date_key]
                                
                                # 设置加载标志，在页面重新渲染时会被处理
                                st.session_state.load_full_config = {
                                    'security_type': config['security_type'],
                                    'symbol': config['symbol'],
                                    'dates': config['dates']
                                }
                                st.rerun()
                        
                        with col2:
                            if st.button(f"🗑️ 删除配置", key=f"delete_{config_key}"):
                                if delete_saved_config(config['symbol'], config['security_type']):
                                    st.success("配置已删除！")
                                    st.rerun()
                                else:
                                    st.error("删除配置失败！")
            else:
                st.info("暂无保存的证券配置")
        
        # 主要内容区域
        
        # 检查是否有保存的分析状态，如果有则直接显示，避免重复分析
        current_analysis_key = f"analysis_{security_type}_{symbol}"
        has_saved_analysis = (current_analysis_key in st.session_state and 
                             st.session_state.get('current_analysis') == current_analysis_key)
        
        if analyze_button or has_saved_analysis:
            # 预检查：验证输入参数
            if not symbol or len(symbol.strip()) != 6:
                st.error("❌ 请输入正确的6位证券代码")
                st.stop()
            
            # 检查AI功能配置
            saved_api_key, saved_model = load_api_key()
            ai_date_recommendation_enabled = load_ai_date_recommendation_setting()
            ai_analysis_enabled = load_ai_analysis_setting()
            
            # 如果启用了AI功能但没有API密钥，给出提示
            if (ai_date_recommendation_enabled or ai_analysis_enabled) and not saved_api_key:
                st.warning("⚠️ 您已启用AI功能，但未配置API密钥。将使用手动模式进行分析。")
                st.info("💡 如需使用AI功能，请在左侧边栏配置API密钥")
            
            try:
                # 检查是否可以使用保存的分析状态
                if has_saved_analysis and not analyze_button:
                    # 使用保存的分析状态
                    saved_state = st.session_state[current_analysis_key]
                    data = saved_state['data']
                    processed_data = saved_state['processed_data']
                    analysis_dates = saved_state['analysis_dates']
                    security_name = saved_state['security_name']
                    use_ai_date_recommendation = saved_state['use_ai_date_recommendation']
                    use_ai_analysis = saved_state['use_ai_analysis']
                    saved_api_key = saved_state['saved_api_key']
                    saved_model = saved_state['saved_model']
                    info_df = saved_state['info_df']
                    
                    st.info(f"💾 正在显示已保存的分析结果 (生成时间: {saved_state['analysis_timestamp']})")
                    
                else:
                    # 执行新的分析
                    # 步骤1: 检查AI选项状态
                    
                    # 确定分析模式
                    use_ai_date_recommendation = (ai_date_recommendation_enabled and saved_api_key and AI_ADVISOR_AVAILABLE)
                    use_ai_analysis = (ai_analysis_enabled and saved_api_key and AI_ADVISOR_AVAILABLE)
                    
                    analysis_dates = input_date  # 默认使用手动日期
                    
                    # 步骤2: 根据配置决定是否调用AI推荐日期
                    if use_ai_date_recommendation:
                        with st.spinner(f"📅 AI正在为{security_type}推荐最佳关键日期..."):
                            recommendation_result = generate_ai_recommendation(symbol, security_type, saved_api_key, saved_model)
                            
                            if recommendation_result['success']:
                                # 转换AI推荐的日期格式
                                recommended_dates = recommendation_result['dates']
                                analysis_dates = {}
                                for i, date_str in enumerate(recommended_dates[:5]):
                                    analysis_dates[f'day{i+1}'] = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d')
                                
                                st.success("✅ AI日期推荐完成")
                                
                                # 显示推荐日期信息
                                with st.expander("📅 AI推荐的关键日期", expanded=False):
                                    for i, date_str in enumerate(recommended_dates[:5]):
                                        st.write(f"Day{i+1}: {date_str}")
                            else:
                                st.warning(f"⚠️ AI日期推荐失败: {recommendation_result['error']}")
                                st.info("💡 将使用手动选择的日期进行分析")
                                
                                # 提供故障排除建议
                                with st.expander("🔧 故障排除建议"):
                                    st.markdown("""
                                    **可能的原因和解决方案：**
                                    - **API密钥问题**: 请检查API密钥是否正确且有效
                                    - **网络连接**: 请检查网络连接是否正常
                                    - **模型限制**: 尝试切换到其他AI模型
                                    - **证券代码**: 确认证券代码是否正确
                                    - **服务限制**: API服务可能暂时不可用，请稍后重试
                                    """)
                    
                    # 获取证券数据并计算KDAS
                    with st.spinner(f"📊 正在获取{security_type}数据并计算KDAS指标..."):
                        data = get_security_data(symbol, analysis_dates, security_type)
                        if data.empty:
                            st.error(f'未找到该{security_type}的数据，请检查{security_type}代码是否正确。')
                            return
                        
                        processed_data = calculate_cumulative_vwap(data, analysis_dates)
                        security_name = get_security_name(symbol, security_type)
                    
                    # 保存分析状态到session_state，防止按钮点击后内容消失
                    analysis_state_key = f"analysis_{security_type}_{symbol}"
                    st.session_state[analysis_state_key] = {
                        'data': data,
                        'processed_data': processed_data,
                        'analysis_dates': analysis_dates,
                        'security_name': security_name,
                        'security_type': security_type,
                        'symbol': symbol,
                        'use_ai_date_recommendation': use_ai_date_recommendation,
                        'use_ai_analysis': use_ai_analysis,
                        'saved_api_key': saved_api_key,
                        'saved_model': saved_model,
                        'info_df': info_df,
                        'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    # 设置当前活跃的分析状态
                    st.session_state['current_analysis'] = analysis_state_key
                
                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(f"{security_type}名称", security_name)
                with col2:
                    st.metric(f"{security_type}代码", symbol)
                with col3:
                    latest_price = processed_data['收盘'].iloc[-1]
                    st.metric("最新收盘价", f"¥{latest_price:.3f}")
                with col4:
                    if len(processed_data) > 1:
                        price_change = processed_data['收盘'].iloc[-1] - processed_data['收盘'].iloc[-2]
                        st.metric("涨跌", f"¥{price_change:.3f}", delta=f"{(price_change/processed_data['收盘'].iloc[-2]*100):.3f}%")
                    else:
                        st.metric("涨跌", "暂无数据")
                
                st.markdown("---")
                
                # 步骤3: 显示图表和步骤4: 根据配置决定是否调用AI分析
                col_chart, col_analysis = st.columns([3, 2])
                
                with col_chart:
                    # 创建并显示图表
                    fig = create_interactive_chart(processed_data, analysis_dates, info_df, security_type, symbol)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_analysis:
                    st.subheader("🤖 KDAS智能分析")
                    
                    # 步骤4: 根据配置决定是否调用AI分析
                    if use_ai_analysis:
                        with st.spinner("🤖 AI正在分析KDAS状态..."):
                            ai_analysis_result = analyze_kdas_state_with_ai(
                                processed_data, analysis_dates, symbol, security_type, saved_api_key, saved_model
                            )
                        
                        # 步骤5: 显示AI分析结果
                        if ai_analysis_result and ai_analysis_result.get('success', False):
                            st.success("✅ AI状态分析完成")
                            
                            # 格式化分析结果
                            analysis_text = ai_analysis_result.get('analysis', '')
                            if analysis_text:
                                formatted_analysis = format_analysis_text(analysis_text)
                                with st.expander("📈 查看详细分析报告", expanded=True):
                                    st.markdown(formatted_analysis, unsafe_allow_html=True)
                        else:
                            error_msg = ai_analysis_result.get('error', '未知错误') if ai_analysis_result else '未知错误'
                            st.error(f"❌ AI状态分析失败: {error_msg}")
                            
                            # 提供故障排除建议
                            with st.expander("🔧 故障排除建议"):
                                st.markdown("""
                                **可能的原因和解决方案：**
                                - **API密钥问题**: 请检查API密钥是否正确且有效
                                - **数据问题**: 确保证券数据已正确加载
                                - **网络连接**: 请检查网络连接是否正常
                                - **模型限制**: 尝试切换到其他AI模型
                                - **服务限制**: API服务可能暂时不可用，请稍后重试
                                
                                **建议操作：**
                                1. 检查左侧边栏的API密钥配置
                                2. 尝试切换AI模型
                                3. 稍后重新点击"开始分析"按钮
                                """)
                    else:
                        # 显示AI配置提示
                        if not ai_analysis_enabled:
                            st.info("💡 **启用KDAS智能分析**")
                            st.markdown("勾选左侧边栏「🔮 启用AI智能分析」选项，此处将自动显示专业的KDAS状态分析报告")
                        elif not saved_api_key:
                            st.info("💡 **配置AI API密钥**")
                            st.markdown("您已启用AI智能分析，但还需要配置API密钥才能使用")
                            st.warning("⚠️ 需要先在左侧边栏的AI智能推荐区域配置API密钥")
                        elif not AI_ADVISOR_AVAILABLE:
                            st.warning("⚠️ AI功能不可用，请检查kdas包是否正确安装")
                
                # 保存配置逻辑
                st.markdown("---")
                if use_ai_date_recommendation:
                    # 使用AI推荐日期时的手动保存选项
                    col_save1, col_save2 = st.columns(2)
                    with col_save1:
                        st.info("💡 当前使用AI推荐日期")
                    with col_save2:
                        if st.button("💾 保存AI推荐配置", help="将当前的AI推荐日期保存为配置"):
                            save_success, save_message = save_current_config(symbol, security_type, analysis_dates, security_name)
                            if save_success:
                                st.success("✅ AI推荐配置已保存！")
                                st.info("💡 下次分析该证券时可在左侧边栏快速加载此配置")
                                # 显示保存的详细信息
                                with st.expander("📋 保存详情", expanded=False):
                                    st.write(f"**证券代码**: {symbol}")
                                    st.write(f"**证券名称**: {security_name}")
                                    st.write(f"**证券类型**: {security_type}")
                                    st.write("**AI推荐日期**:")
                                    for key, value in analysis_dates.items():
                                        date_obj = datetime.strptime(value, '%Y%m%d').date()
                                        st.write(f"  - {key}: {date_obj}")
                            else:
                                st.error(f"❌ 保存失败: {save_message}")
                                with st.expander("🔧 故障排除建议", expanded=False):
                                    st.markdown("""
                                    **常见问题和解决方案：**
                                    - **权限问题**: 检查应用是否有写入文件的权限
                                    - **磁盘空间**: 确保磁盘有足够的可用空间
                                    - **路径问题**: 确认配置文件路径可访问
                                    - **文件占用**: 关闭其他可能占用配置文件的程序
                                    
                                    **详细错误信息**: {save_message}
                                    """.format(save_message=save_message))
                else:
                    # 手动日期模式的自动保存
                    save_success, save_message = save_current_config(symbol, security_type, analysis_dates, security_name)
                    if save_success:
                        st.success("✅ 当前配置已自动保存，下次可直接加载！")
                        st.info("💡 可在左侧边栏的配置管理区域查看和管理所有保存的配置")
                    else:
                        st.warning(f"⚠️ 配置自动保存失败: {save_message}")
                        st.info("💡 分析结果仍然有效，但配置未能保存。您可以稍后手动保存配置。")
                
                # 分析完成提示
                with st.expander("📋 分析完成 - 下一步操作建议"):
                    st.markdown("""
                    **🎉 分析已完成！您可以：**
                    
                    **📊 深入分析：**
                    - 仔细查看K线图和KDAS指标的走势关系
                    - 关注KDAS线与价格的交叉点和背离情况
                    - 观察成交量与价格变化的配合情况
                    
                    **🤖 AI分析报告：**
                    - 展开右侧的"查看详细分析报告"了解专业解读
                    - 重点关注趋势判断和交易策略建议
                    - 注意风险提示和关键位分析
                    
                    **⚙️ 配置管理：**
                    - 当前配置已自动保存，下次可快速加载
                    - 可在左侧边栏管理多个证券的配置
                    - 尝试不同的AI模型获得多角度分析
                    
                    **🔄 继续分析：**
                    - 修改日期配置重新分析
                    - 切换到其他证券进行对比分析
                    - 使用多图看板功能进行批量分析
                    """)

            except Exception as e:
                st.error(f"分析过程中出现错误: {str(e)}")
                st.info("请检查股票代码是否正确，或稍后重试。")
        
        else:
            # 显示使用说明
            st.info("👈 请在左侧边栏配置参数并点击「开始分析」按钮")
            
            with st.expander("📖 使用说明"):
                st.markdown("""
                ### KDAS指标说明
                KDAS（Key Date Average Settlement）是基于关键日期的累计成交量加权平均价格指标。作者： 叙市 （全网同名）
                
                ### 使用步骤
                1. 选择证券类型（股票、ETF、指数）
                2. 输入对应的6位证券代码
                   - 股票：如 000001、300001、001215等
                   - ETF：如 159915、159919、510300等
                   - 指数：如 000001（上证指数）、399001（深证成指）等
                3. **(可选)** 配置AI功能：
                   - 勾选「📅 启用AI日期推荐」自动推荐最佳关键日期
                   - 勾选「🔮 启用AI智能分析」获得专业的KDAS状态分析
                   - 配置API密钥以使用AI功能
                4. 手动选择5个关键的分析日期（如未启用AI日期推荐）
                5. 点击「开始分析」按钮
                6. 查看K线图、KDAS指标走势和AI分析报告
                
                ### 🤖 AI智能功能（全新升级）
                
                #### 📅 智能日期推荐
                - **多模型支持**: 支持DeepSeek-R1、Gemini-2.5等多种先进AI模型
                - **智能分析**: 基于大语言模型分析证券的技术指标、价格趋势、成交量等数据
                - **专业推荐**: 遵循KDAS交易体系原理，推荐最佳的关键日期
                - **技术依据**: 识别重要的价格突破点、趋势转折点、异常成交量日期等
                - **降低门槛**: 新手用户无需深入了解技术分析，即可获得专业的日期配置
                
                #### 📊 KDAS状态智能分析（新增）
                - **实时分析**: 基于KDAS交易体系自动分析当前市场状态
                - **四种状态识别**: 趋势行进、趋势衰竭、震荡状态、整理状态的智能判断
                - **多空力量分析**: 分析当前多空力量对比和价格与KDAS系统的位置关系
                - **趋势方向判断**: 基于KDAS系统判断当前趋势方向和强度
                - **交易策略建议**: 根据KDAS体系给出具体的交易策略建议
                - **关键位识别**: 智能识别当前的关键支撑和压力位
                - **风险提示**: 基于当前状态的风险评估和注意事项
                - **专业解读**: 用易懂的语言解释复杂的技术分析结果
                
                #### 🔧 配置管理
                - **📅 AI日期推荐开关**: 可选择性启用/禁用AI日期推荐功能，默认开启
                - **🔮 AI分析开关**: 可选择性启用/禁用AI智能分析功能，默认关闭
                - **API配置**: 需要配置AI API密钥（sk-开头的密钥）
                - **模型选择**: 可根据需求选择不同的AI模型进行分析
                - **智能组合**: 支持4种AI功能组合，满足不同使用需求
                - **备用方案**: 当AI推荐失败时，自动回退到手动日期模式
                - **💾 配置记忆**: 点击"保存配置"按钮可保存API密钥和模型选择，刷新页面不会丢失
                - **🔒 本地存储**: 所有配置安全保存在本地配置文件中，仅您可以访问
                
                ### 🔧 支持的AI模型
                - **deepseek-r1**: DeepSeek推理模型，逻辑推理能力强
                - **gemini-2.5-flash-preview-05-20**: Google Gemini快速版本，响应速度快
                - **gemini-2.5-pro-preview-03-25**: Google Gemini专业版本，分析更深入
                
                ### 💾 记忆功能（新增）
                - **自动保存**: 每次分析后会自动保存当前证券代码及其对应的日期配置
                - **智能识别**: 输入之前分析过的证券代码时，会自动提示有保存的配置
                - **部分加载**: 点击"加载保存的日期配置"按钮仅恢复日期设置
                - **完整加载**: 点击"📋 加载完整配置"按钮一键切换证券类型、代码和所有日期
                - **配置重置**: 加载配置后可点击"🔄 清除当前配置"按钮恢复默认状态
                - **配置管理**: 在侧边栏底部可以查看和删除已保存的所有配置
                - **数据持久化**: 配置信息保存在本地文件中，重启应用也不会丢失
                
                ### 图表说明
                - **K线图**: 显示证券的开高低收价格走势
                - **KDAS线**: 不同颜色表示从不同日期开始计算的KDAS值
                - **成交量**: 显示每日的成交量情况
                - **图例**: 位于图表左上角，可以点击控制显示/隐藏
                - **时间轴优化**: 使用新浪财经官方交易日历数据，精确跳过非交易日，确保x轴连续显示
                - **智能分析面板**: 右侧显示AI实时分析的KDAS状态和交易建议
                - **布局优化**: 左侧图表占2/3，右侧分析面板占1/3，信息展示更高效
                
                ### 支持的证券类型
                - **股票**: A股上市公司股票
                - **ETF**: 交易型开放式指数基金
                - **指数**: 沪深各类股票指数
                """)
    
    else: # 多图概览看板
        with st.sidebar:
            st.header("📊 多图看板配置")
            st.subheader("全局KDAS计算起始日期")

            # 定义全局日期和证券配置 - 从保存的配置中加载
            if 'multi_chart_global_dates' not in st.session_state or 'multi_securities' not in st.session_state:
                # 加载保存的配置
                saved_dates, saved_securities = load_multi_chart_config()
                st.session_state.multi_chart_global_dates = saved_dates
                st.session_state.multi_securities = saved_securities

            global_input_dates = {}
            colors = ["🔴", "🔵", "🟢", "🟣", "🟡"]
            dates_changed = False
            
            for i in range(5):
                selected_date = st.date_input(
                    f"{colors[i]} 日期 {i+1}", 
                    value=st.session_state.multi_chart_global_dates[i], 
                    key=f"multi_global_date_{i+1}"
                )
                global_input_dates[f'day{i+1}'] = selected_date.strftime('%Y%m%d')
                
                # 检查日期是否发生变化
                if st.session_state.multi_chart_global_dates[i] != selected_date:
                    dates_changed = True
                    st.session_state.multi_chart_global_dates[i] = selected_date

            st.markdown("---")
            st.subheader("证券配置 (最多6个)")

            # 初始化每个图表的配置（已在上面从保存的配置中加载）
            
            # 加载所有已保存的配置用于下拉菜单
            configs = load_user_configs()
            security_configs = {k: v for k, v in configs.items() if k != 'global_settings'}
            config_options = {k: f"{v['security_name']} ({v['symbol']})" for k, v in security_configs.items()}
            options_list = [None] + list(config_options.keys())
            format_func = lambda k: "选择一个配置..." if k is None else config_options[k]
            
            securities_changed = False
            
            for i in range(6):
                with st.expander(f"图表 {i+1}", expanded=(i<3 or st.session_state.multi_securities[i]['symbol'] != '')):
                    
                    # 加载配置的下拉菜单
                    selected_config_key = st.selectbox(
                        "加载已存配置",
                        options=options_list,
                        format_func=format_func,
                        index=options_list.index(st.session_state.multi_securities[i]['config_key']) if st.session_state.multi_securities[i]['config_key'] in options_list else 0,
                        key=f'multi_load_{i}',
                    )

                    # 当用户从下拉菜单选择新配置时，更新状态
                    if selected_config_key != st.session_state.multi_securities[i]['config_key']:
                        securities_changed = True
                        if selected_config_key:
                            config = security_configs[selected_config_key]
                            st.session_state.multi_securities[i].update({
                                'type': config['security_type'],
                                'symbol': config['symbol'],
                                'dates': config['dates'],
                                'use_global_dates': False,
                                'config_key': selected_config_key
                            })
                        else:  # 用户选择 "None"
                            st.session_state.multi_securities[i].update({
                                'use_global_dates': True,
                                'config_key': None
                            })
                        # 立即保存配置
                        save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities)
                        st.rerun()

                    # 证券类型和代码输入
                    sec_type = st.selectbox(
                        f"证券类型", ["股票", "ETF", "指数"],
                        index=["股票", "ETF", "指数"].index(st.session_state.multi_securities[i]['type']),
                        key=f"multi_type_{i}"
                    )
                    symbol = st.text_input(
                        f"证券代码", 
                        value=st.session_state.multi_securities[i]['symbol'], 
                        key=f"multi_symbol_{i}"
                    ).strip()

                    # 是否使用全局日期的复选框
                    use_global = st.checkbox(
                        "使用全局日期",
                        value=st.session_state.multi_securities[i]['use_global_dates'],
                        key=f'multi_global_date_cb_{i}'
                    )
                    
                    # 检查配置是否发生变化并更新状态（来自手动输入）
                    if (st.session_state.multi_securities[i]['type'] != sec_type or 
                        st.session_state.multi_securities[i]['symbol'] != symbol or 
                        st.session_state.multi_securities[i]['use_global_dates'] != use_global):
                        securities_changed = True
                    
                    st.session_state.multi_securities[i]['type'] = sec_type
                    st.session_state.multi_securities[i]['symbol'] = symbol
                    st.session_state.multi_securities[i]['use_global_dates'] = use_global
                    
                    # 如果使用特定日期，则显示提示
                    if not st.session_state.multi_securities[i]['use_global_dates'] and st.session_state.multi_securities[i]['dates']:
                        dates_str = ", ".join([d.replace("2024", "24").replace("2025", "25") for d in st.session_state.multi_securities[i]['dates'].values()])
                        st.info(f"特定日期: {dates_str}", icon="🗓️")


            # 自动保存配置（如果有变化）
            if dates_changed or securities_changed:
                save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities)
                # 只在底部显示一个小的状态指示器，不显示成功消息以避免干扰用户体验

            st.markdown("---")
            
            # 手动保存和重置按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存配置", use_container_width=True):
                    if save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities):
                        st.success("✅ 配置保存成功")
                    else:
                        st.error("❌ 配置保存失败")
            
            with col2:
                if st.button("🔄 重置为默认", use_container_width=True):
                    # 重置为默认配置
                    default_dates, default_securities = get_default_multi_chart_config()
                    # 获取默认配置（重新调用函数但不使用保存的配置）
                    st.session_state.multi_chart_global_dates = default_dates
                    st.session_state.multi_securities = default_securities
                    if save_multi_chart_config(st.session_state.multi_chart_global_dates, st.session_state.multi_securities):
                        st.success("✅ 已重置为默认配置")
                        st.rerun()
                    else:
                        st.error("❌ 重置失败")

            analyze_button = st.button("🔍 更新看板", type="primary", use_container_width=True)
            
            # 显示最后保存时间
            configs = load_user_configs()
            if 'global_settings' in configs and 'multi_chart_config' in configs['global_settings']:
                save_time = configs['global_settings']['multi_chart_config'].get('save_time', '未知')
                st.caption(f"💾 最后保存: {save_time}")

        st.header("多图概览看板")
        st.info('在左侧配置需要同时监控的证券（最多6个），所有图表将使用相同的KDAS日期。配置完成后，点击"更新看板"以加载图表。')
        st.success('💾 配置自动保存：您的多图看板配置会自动保存，重启或刷新后自动恢复到上次的设置。', icon="✨")
        
        if 'charts_generated' not in st.session_state:
            st.session_state.charts_generated = False

        if analyze_button:
            st.session_state.charts_generated = True

        if st.session_state.charts_generated:
            # 使用优化的多图分析函数
            with st.spinner("🔄 正在生成多图看板..."):
                analysis_results = run_multi_chart_analysis_with_kdas(
                    st.session_state.multi_securities, 
                    global_input_dates
                )
            
            # 显示分析汇总
            summary = get_multi_chart_summary(analysis_results)
            
            # 创建状态指示器
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("成功图表", summary['successful_charts'], f"共 {summary['total_charts']} 个")
            with col_info2:
                success_rate_pct = summary['success_rate'] * 100
                delta_color = "normal" if success_rate_pct >= 80 else "inverse"
                st.metric("成功率", f"{success_rate_pct:.1f}%", delta=None)
            with col_info3:
                if summary['type_statistics']:
                    type_info = ", ".join([f"{k}:{v}" for k, v in summary['type_statistics'].items()])
                    st.metric("证券类型", type_info)
                else:
                    st.metric("证券类型", "无数据")
            
            # 显示失败的证券（如果有）
            if summary['failed_securities']:
                with st.expander(f"⚠️ 失败的证券 ({len(summary['failed_securities'])}个)", expanded=False):
                    for failed_sec in summary['failed_securities']:
                        st.warning(failed_sec)
            
            st.markdown("---")
            
            # 渲染图表看板
            render_multi_chart_dashboard(analysis_results)
        else:
            # 显示等待状态的看板
            render_waiting_dashboard()


if __name__ == "__main__":
    # 检测是否通过streamlit运行
    try:
        import streamlit.runtime.scriptrunner.script_run_context as ctx
        if ctx.get_script_run_ctx() is None:
            # 不是通过streamlit运行
            print("❌ 请使用以下命令之一来运行应用：")
            print()
            print("方法一（推荐）：")
            print("   python run_app.py")
            print()
            print("方法二：")
            print("   streamlit run KDAS.py")
            print()
            print("⚠️  不要直接使用 'python KDAS.py' 运行！")
            exit(1)
    except ImportError:
        pass
    
    main()