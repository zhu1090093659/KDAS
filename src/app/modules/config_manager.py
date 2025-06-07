"""
KDAS证券分析工具 - 配置管理模块

负责处理所有配置相关的功能：
- 用户配置的保存、加载和验证
- API密钥管理
- 全局设置管理
- 多图看板配置管理
- 配置文件的验证和清理

作者：KDAS团队
版本：2.0 (模块化重构版本)
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List


class ConfigManager:
    """配置管理器类，负责所有配置相关的操作"""
    
    def __init__(self, config_file_path: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_file_path is None:
            self.config_file = os.path.join(os.path.dirname(__file__), '..', 'user_configs.json')
        else:
            self.config_file = config_file_path
    
    # ==================== 基础配置操作 ====================
    
    def load_user_configs(self) -> Dict[str, Any]:
        """加载用户保存的配置，包含改进的错误处理"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                    # 验证配置文件格式
                    if not isinstance(configs, dict):
                        print(f"配置文件格式错误，将重置为默认配置")
                        return {}
                    return configs
            except json.JSONDecodeError as e:
                print(f"配置文件JSON格式错误: {e}")
                # 备份损坏的配置文件
                backup_name = f"{self.config_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    os.rename(self.config_file, backup_name)
                    print(f"已将损坏的配置文件备份为: {backup_name}")
                except Exception:
                    pass
                return {}
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return {}
        return {}
    
    def save_user_configs(self, configs: Dict[str, Any]) -> Tuple[bool, str]:
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
            print(f"📂 配置文件路径: {self.config_file}")
            print(f"📊 配置数量: {len(configs)} 个")
            
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.'
            try:
                os.makedirs(config_dir, exist_ok=True)
                print(f"📁 配置目录检查完成: {config_dir}")
            except Exception as e:
                print(f"❌ 创建配置目录失败: {e}")
                return False, f"无法创建配置目录: {e}"
            
            # 检查磁盘空间
            try:
                total, used, free = shutil.disk_usage(config_dir)
                free_mb = free // (1024*1024)
                if free_mb < 1:  # 至少1MB空闲空间
                    print(f"❌ 磁盘空间不足: 仅 {free_mb} MB 可用")
                    return False, f"磁盘空间不足，仅剩余 {free_mb} MB"
            except Exception as e:
                print(f"⚠️ 无法检查磁盘空间: {e}")
            
            # 先保存到临时文件，然后原子性地重命名
            temp_file = f"{self.config_file}.tmp"
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
                os.replace(temp_file, self.config_file)
                print(f"✅ 配置文件更新成功: {self.config_file}")
                
                # 最终验证
                if os.path.exists(self.config_file):
                    file_size = os.path.getsize(self.config_file)
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
            temp_file = f"{self.config_file}.tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"🗑️ 已清理临时文件")
                except Exception:
                    pass
            return False, f"保存过程异常: {e}"
    
    def get_config_with_validation(self, config_key: str, default_value: Any = None, config_type: type = None) -> Any:
        """通用的配置获取函数，包含类型验证"""
        configs = self.load_user_configs()
        
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
    
    # ==================== 证券配置管理 ====================
    
    def save_current_config(self, symbol: str, security_type: str, input_date: Dict[str, str], security_name: str) -> Tuple[bool, str]:
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
            configs = self.load_user_configs()
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
            save_success, save_message = self.save_user_configs(configs)
            
            if save_success:
                print(f"✅ 配置保存成功: {config_key}")
                print(f"📂 配置文件路径: {self.config_file}")
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
    
    def get_saved_config(self, symbol: str, security_type: str) -> Optional[Dict[str, Any]]:
        """获取指定证券的保存配置"""
        configs = self.load_user_configs()
        config_key = f"{security_type}_{symbol}"
        return configs.get(config_key, None)
    
    def delete_saved_config(self, symbol: str, security_type: str) -> bool:
        """删除指定证券的保存配置"""
        configs = self.load_user_configs()
        config_key = f"{security_type}_{symbol}"
        if config_key in configs:
            del configs[config_key]
            success, message = self.save_user_configs(configs)
            return success
        return False
    
    # ==================== 全局设置管理 ====================
    
    def _ensure_global_settings(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """确保配置中存在全局设置部分（内部辅助函数）"""
        if 'global_settings' not in configs:
            configs['global_settings'] = {}
        return configs
    
    def _update_save_time(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置的保存时间（内部辅助函数）"""
        configs['global_settings']['save_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return configs
    
    def save_api_key(self, api_key: str, model_name: str) -> bool:
        """保存API密钥到配置文件"""
        configs = self.load_user_configs()
        configs = self._ensure_global_settings(configs)
        
        # 保存API密钥和默认模型
        configs['global_settings']['api_key'] = api_key
        configs['global_settings']['default_model'] = model_name
        configs = self._update_save_time(configs)
        
        success, message = self.save_user_configs(configs)
        return success
    
    def load_api_key(self) -> Tuple[str, str]:
        """从配置文件加载API密钥"""
        api_key = self.get_config_with_validation('global_settings.api_key', '', str)
        default_model = self.get_config_with_validation('global_settings.default_model', 'deepseek-r1', str)
        return api_key, default_model
    
    def delete_api_key(self) -> bool:
        """删除保存的API密钥"""
        configs = self.load_user_configs()
        if 'global_settings' in configs:
            # 批量删除相关设置
            keys_to_delete = ['api_key', 'default_model', 'ai_analysis_enabled', 'ai_date_recommendation_enabled']
            for key in keys_to_delete:
                configs['global_settings'].pop(key, None)
            
            # 如果global_settings为空，则删除整个section
            if not configs['global_settings']:
                del configs['global_settings']
            success, message = self.save_user_configs(configs)
            return success
        return False
    
    def save_ai_analysis_setting(self, enabled: bool) -> bool:
        """保存AI分析开关设置"""
        configs = self.load_user_configs()
        configs = self._ensure_global_settings(configs)
        
        # 保存AI分析开关设置
        configs['global_settings']['ai_analysis_enabled'] = enabled
        configs = self._update_save_time(configs)
        
        success, message = self.save_user_configs(configs)
        return success
    
    def load_ai_analysis_setting(self) -> bool:
        """加载AI分析开关设置"""
        return self.get_config_with_validation('global_settings.ai_analysis_enabled', False, bool)
    
    def save_ai_date_recommendation_setting(self, enabled: bool) -> Tuple[bool, str]:
        """保存AI日期推荐开关设置"""
        configs = self.load_user_configs()
        configs = self._ensure_global_settings(configs)
        
        # 保存AI日期推荐开关设置
        configs['global_settings']['ai_date_recommendation_enabled'] = enabled
        configs = self._update_save_time(configs)
        
        return self.save_user_configs(configs)
    
    def load_ai_date_recommendation_setting(self) -> bool:
        """加载AI日期推荐开关设置"""
        return self.get_config_with_validation('global_settings.ai_date_recommendation_enabled', True, bool)
    
    # ==================== 多图看板配置管理 ====================
    
    def save_multi_chart_config(self, global_dates: List, securities: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """保存多图看板配置"""
        configs = self.load_user_configs()
        configs = self._ensure_global_settings(configs)
        
        # 保存多图看板配置
        configs['global_settings']['multi_chart_config'] = {
            'global_dates': [date.isoformat() for date in global_dates],
            'securities': securities,
            'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return self.save_user_configs(configs)
    
    def load_multi_chart_config(self) -> Tuple[List, List[Dict[str, Any]]]:
        """加载多图看板配置，使用改进的配置获取"""
        multi_config = self.get_config_with_validation('global_settings.multi_chart_config', None, dict)
        
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
        return self.get_default_multi_chart_config()
    
    def get_default_multi_chart_config(self) -> Tuple[List, List[Dict[str, Any]]]:
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
    
    # ==================== 配置验证和清理 ====================
    
    def validate_and_cleanup_config(self) -> Dict[str, Any]:
        """验证并清理配置文件，移除无效或过期的配置项"""
        configs = self.load_user_configs()
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
            self.save_user_configs(configs)
            print("配置文件已验证并清理")
        
        return configs
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要，用于调试和监控"""
        configs = self.load_user_configs()
        
        summary = {
            'total_configs': len(configs),
            'has_global_settings': 'global_settings' in configs,
            'securities_count': len([k for k in configs.keys() if k != 'global_settings']),
            'has_api_key': bool(self.get_config_with_validation('global_settings.api_key', '', str)),
            'ai_analysis_enabled': self.get_config_with_validation('global_settings.ai_analysis_enabled', False, bool),
            'ai_date_recommendation_enabled': self.get_config_with_validation('global_settings.ai_date_recommendation_enabled', True, bool),
            'has_multi_chart_config': self.get_config_with_validation('global_settings.multi_chart_config', None) is not None
        }
        
        return summary


# ==================== 全局实例和兼容性函数 ====================

# 创建全局配置管理器实例
_config_manager = ConfigManager()

# 为了保持与原代码的兼容性，提供全局函数接口
def load_user_configs():
    """兼容性函数：加载用户配置"""
    return _config_manager.load_user_configs()

def save_user_configs(configs):
    """兼容性函数：保存用户配置"""
    return _config_manager.save_user_configs(configs)

def get_config_with_validation(config_key, default_value=None, config_type=None):
    """兼容性函数：获取配置并验证"""
    return _config_manager.get_config_with_validation(config_key, default_value, config_type)

def save_current_config(symbol, security_type, input_date, security_name):
    """兼容性函数：保存当前配置"""
    return _config_manager.save_current_config(symbol, security_type, input_date, security_name)

def get_saved_config(symbol, security_type):
    """兼容性函数：获取保存的配置"""
    return _config_manager.get_saved_config(symbol, security_type)

def delete_saved_config(symbol, security_type):
    """兼容性函数：删除保存的配置"""
    return _config_manager.delete_saved_config(symbol, security_type)

def save_api_key(api_key, model_name):
    """兼容性函数：保存API密钥"""
    return _config_manager.save_api_key(api_key, model_name)

def load_api_key():
    """兼容性函数：加载API密钥"""
    return _config_manager.load_api_key()

def delete_api_key():
    """兼容性函数：删除API密钥"""
    return _config_manager.delete_api_key()

def save_ai_analysis_setting(enabled):
    """兼容性函数：保存AI分析设置"""
    return _config_manager.save_ai_analysis_setting(enabled)

def load_ai_analysis_setting():
    """兼容性函数：加载AI分析设置"""
    return _config_manager.load_ai_analysis_setting()

def save_ai_date_recommendation_setting(enabled):
    """兼容性函数：保存AI日期推荐设置"""
    return _config_manager.save_ai_date_recommendation_setting(enabled)

def load_ai_date_recommendation_setting():
    """兼容性函数：加载AI日期推荐设置"""
    return _config_manager.load_ai_date_recommendation_setting()

def save_multi_chart_config(global_dates, securities):
    """兼容性函数：保存多图看板配置"""
    return _config_manager.save_multi_chart_config(global_dates, securities)

def load_multi_chart_config():
    """兼容性函数：加载多图看板配置"""
    return _config_manager.load_multi_chart_config()

def get_default_multi_chart_config():
    """兼容性函数：获取默认多图看板配置"""
    return _config_manager.get_default_multi_chart_config()

def reset_multi_chart_to_default():
    """
    兼容性函数：重置多图看板配置为默认值
    
    Returns:
        重置是否成功
    """
    try:
        import streamlit as st
        default_dates, default_securities = get_default_multi_chart_config()
        st.session_state.multi_chart_global_dates = default_dates
        st.session_state.multi_securities = default_securities
        
        return save_multi_chart_config(default_dates, default_securities)[0]
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"重置配置失败: {e}")
        except:
            print(f"重置配置失败: {e}")
        return False

def validate_and_cleanup_config():
    """兼容性函数：验证和清理配置"""
    return _config_manager.validate_and_cleanup_config()

def get_config_summary():
    """兼容性函数：获取配置摘要"""
    return _config_manager.get_config_summary() 