"""Configuration management for Flow2API"""
import tomli
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Application configuration"""

    def __init__(self):
        self._config = self._load_config()
        self._admin_username: Optional[str] = None
        self._admin_password: Optional[str] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from setting.toml"""
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        with open(config_path, "rb") as f:
            return tomli.load(f)

    def reload_config(self):
        """Reload configuration from file"""
        self._config = self._load_config()

    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration dictionary"""
        return self._config

    @property
    def admin_username(self) -> str:
        # If admin_username is set from database, use it; otherwise fall back to config file
        if self._admin_username is not None:
            return self._admin_username
        return self._config["global"]["admin_username"]

    @admin_username.setter
    def admin_username(self, value: str):
        self._admin_username = value
        self._config["global"]["admin_username"] = value

    def set_admin_username_from_db(self, username: str):
        """Set admin username from database"""
        self._admin_username = username

    # Flow2API specific properties
    @property
    def flow_labs_base_url(self) -> str:
        """Google Labs base URL for project management"""
        return self._config["flow"]["labs_base_url"]

    @property
    def flow_api_base_url(self) -> str:
        """Google AI Sandbox API base URL for generation"""
        return self._config["flow"]["api_base_url"]

    @property
    def flow_timeout(self) -> int:
        return self._config["flow"]["timeout"]

    @property
    def flow_max_retries(self) -> int:
        return self._config["flow"]["max_retries"]

    @property
    def poll_interval(self) -> float:
        return self._config["flow"]["poll_interval"]

    @property
    def max_poll_attempts(self) -> int:
        return self._config["flow"]["max_poll_attempts"]

    @property
    def server_host(self) -> str:
        return self._config["server"]["host"]

    @property
    def server_port(self) -> int:
        return self._config["server"]["port"]

    @property
    def debug_enabled(self) -> bool:
        return self._config.get("debug", {}).get("enabled", False)

    @property
    def debug_log_requests(self) -> bool:
        return self._config.get("debug", {}).get("log_requests", True)

    @property
    def debug_log_responses(self) -> bool:
        return self._config.get("debug", {}).get("log_responses", True)

    @property
    def debug_mask_token(self) -> bool:
        return self._config.get("debug", {}).get("mask_token", True)

    # Mutable properties for runtime updates
    @property
    def api_key(self) -> str:
        return self._config["global"]["api_key"]

    @api_key.setter
    def api_key(self, value: str):
        self._config["global"]["api_key"] = value

    @property
    def admin_password(self) -> str:
        # If admin_password is set from database, use it; otherwise fall back to config file
        if self._admin_password is not None:
            return self._admin_password
        return self._config["global"]["admin_password"]

    @admin_password.setter
    def admin_password(self, value: str):
        self._admin_password = value
        self._config["global"]["admin_password"] = value

    def set_admin_password_from_db(self, password: str):
        """Set admin password from database"""
        self._admin_password = password

    def set_debug_enabled(self, enabled: bool):
        """Set debug mode enabled/disabled"""
        if "debug" not in self._config:
            self._config["debug"] = {}
        self._config["debug"]["enabled"] = enabled

    @property
    def image_timeout(self) -> int:
        """Get image generation timeout in seconds"""
        return self._config.get("generation", {}).get("image_timeout", 300)

    def set_image_timeout(self, timeout: int):
        """Set image generation timeout in seconds"""
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["image_timeout"] = timeout

    @property
    def video_timeout(self) -> int:
        """Get video generation timeout in seconds"""
        return self._config.get("generation", {}).get("video_timeout", 1500)

    def set_video_timeout(self, timeout: int):
        """Set video generation timeout in seconds"""
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["video_timeout"] = timeout

    # Cache configuration
    @property
    def cache_enabled(self) -> bool:
        """Get cache enabled status"""
        return self._config.get("cache", {}).get("enabled", False)

    def set_cache_enabled(self, enabled: bool):
        """Set cache enabled status"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["enabled"] = enabled

    @property
    def cache_timeout(self) -> int:
        """Get cache timeout in seconds"""
        return self._config.get("cache", {}).get("timeout", 7200)

    def set_cache_timeout(self, timeout: int):
        """Set cache timeout in seconds"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["timeout"] = timeout

    @property
    def cache_base_url(self) -> str:
        """Get cache base URL"""
        return self._config.get("cache", {}).get("base_url", "")

    def set_cache_base_url(self, base_url: str):
        """Set cache base URL"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["base_url"] = base_url

    # Yescaptcha configuration
    @property
    def yescaptcha_enabled(self) -> bool:
        """Get yescaptcha enabled status"""
        return self._config.get("yescaptcha", {}).get("enabled", False)

    @property
    def yescaptcha_client_key(self) -> str:
        """Get yescaptcha client key"""
        return self._config.get("yescaptcha", {}).get("client_key", "")

    def set_yescaptcha_config(self, enabled: bool, client_key: str):
        """Set yescaptcha configuration"""
        if "yescaptcha" not in self._config:
            self._config["yescaptcha"] = {}
        self._config["yescaptcha"]["enabled"] = enabled
        self._config["yescaptcha"]["client_key"] = client_key
        self._write_yescaptcha_config_to_file(enabled, client_key)

    def _write_yescaptcha_config_to_file(self, enabled: bool, client_key: str):
        """Write yescaptcha configuration to setting.toml file"""
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        try:
            # Read current file
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Find and update the yescaptcha section
            in_yescaptcha_section = False
            enabled_updated = False
            client_key_updated = False
            enabled_line_idx = -1
            client_key_line_idx = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith("[yescaptcha]"):
                    in_yescaptcha_section = True
                elif line.strip().startswith("[") and not line.strip().startswith("[yescaptcha]"):
                    # Entered a new section
                    in_yescaptcha_section = False
                elif in_yescaptcha_section:
                    if line.strip().startswith("enabled"):
                        lines[i] = f'enabled = {str(enabled).lower()}  # 是否启用yescaptcha获取reCAPTCHA token\n'
                        enabled_updated = True
                        enabled_line_idx = i
                    elif line.strip().startswith("client_key"):
                        lines[i] = f'client_key = "{client_key}"  # yescaptcha平台的API key，从 https://yescaptcha.com/ 获取\n'
                        client_key_updated = True
                        client_key_line_idx = i
            
            # If we're still in yescaptcha section and didn't update, append at end of section
            if in_yescaptcha_section:
                if not enabled_updated:
                    # Find the position to insert (after [yescaptcha] or after existing lines)
                    insert_pos = -1
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i].strip().startswith("[yescaptcha]"):
                            insert_pos = i + 1
                            break
                        elif lines[i].strip().startswith("[") and not lines[i].strip().startswith("[yescaptcha]"):
                            break
                    if insert_pos >= 0:
                        lines.insert(insert_pos, f'enabled = {str(enabled).lower()}  # 是否启用yescaptcha获取reCAPTCHA token\n')
                        enabled_updated = True
                
                if not client_key_updated:
                    # Find the position to insert (after enabled line or at end of section)
                    insert_pos = enabled_line_idx + 1 if enabled_line_idx >= 0 else -1
                    if insert_pos < 0:
                        for i in range(len(lines) - 1, -1, -1):
                            if lines[i].strip().startswith("[yescaptcha]"):
                                insert_pos = i + 1
                                break
                            elif lines[i].strip().startswith("[") and not lines[i].strip().startswith("[yescaptcha]"):
                                break
                    if insert_pos >= 0:
                        lines.insert(insert_pos, f'client_key = "{client_key}"  # yescaptcha平台的API key，从 https://yescaptcha.com/ 获取\n')
                        client_key_updated = True
            
            # If yescaptcha section doesn't exist, add it
            if not in_yescaptcha_section and (not enabled_updated or not client_key_updated):
                lines.append("\n[yescaptcha]\n")
                lines.append(f'enabled = {str(enabled).lower()}  # 是否启用yescaptcha获取reCAPTCHA token\n')
                lines.append(f'client_key = "{client_key}"  # yescaptcha平台的API key，从 https://yescaptcha.com/ 获取\n')
            
            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            # If file write fails, at least update in-memory config
            # Log error but don't raise to avoid breaking the app
            import sys
            print(f"Warning: Failed to write yescaptcha config to config file: {e}", file=sys.stderr)
    
    # Self reCAPTCHA configuration
    @property
    def self_recaptcha_enabled(self) -> bool:
        """Get self-implemented reCAPTCHA enabled status"""
        return self._config.get("recaptcha", {}).get("use_self", False)

    @property
    def recaptcha_service_url(self) -> str:
        """Get reCAPTCHA token service URL"""
        return self._config.get("recaptcha", {}).get("service_url", "")

    def set_recaptcha_service_url(self, service_url: str):
        """Set reCAPTCHA token service URL"""
        if "recaptcha" not in self._config:
            self._config["recaptcha"] = {}
        self._config["recaptcha"]["service_url"] = service_url
        self._write_recaptcha_service_url_to_file(service_url)

    def _write_recaptcha_service_url_to_file(self, service_url: str):
        """Write recaptcha_service_url to setting.toml file"""
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        try:
            # Read current file
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Find and update the service_url line in [recaptcha] section
            in_recaptcha_section = False
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith("[recaptcha]"):
                    in_recaptcha_section = True
                elif line.strip().startswith("[") and not line.strip().startswith("[recaptcha]"):
                    # Entered a new section
                    if in_recaptcha_section and not updated:
                        # Insert service_url before leaving recaptcha section
                        lines.insert(i, f'service_url = "{service_url}"  # reCAPTCHA Token服务地址\n')
                        updated = True
                    in_recaptcha_section = False
                elif in_recaptcha_section and line.strip().startswith("service_url"):
                    # Update existing service_url line
                    lines[i] = f'service_url = "{service_url}"  # reCAPTCHA Token服务地址\n'
                    updated = True
            
            # If we're still in recaptcha section and didn't update, append at end of section
            if in_recaptcha_section and not updated:
                # Find the last line of recaptcha section (before next section or end of file)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip().startswith("[recaptcha]"):
                        # Insert after the section header
                        j = i + 1
                        while j < len(lines) and (lines[j].strip().startswith("#") or lines[j].strip() == "" or not lines[j].strip().startswith("[")):
                            j += 1
                        lines.insert(j, f'service_url = "{service_url}"  # reCAPTCHA Token服务地址\n')
                        updated = True
                        break
            
            # If recaptcha section doesn't exist, add it
            if not updated:
                lines.append("\n[recaptcha]\n")
                lines.append(f'service_url = "{service_url}"  # reCAPTCHA Token服务地址\n')
            
            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            # If file write fails, at least update in-memory config
            # Log error but don't raise to avoid breaking the app
            import sys
            print(f"Warning: Failed to write recaptcha_service_url to config file: {e}", file=sys.stderr)

# Global config instance
config = Config()
