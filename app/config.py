import os
import yaml
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果为None则从SECRET_CONFIG环境变量读取
        """
        if config_path is None:
            config_path = os.getenv("SECRET_CONFIG")
            if not config_path:
                raise ValueError("SECRET_CONFIG environment variable is not set.")

        logger.info(f"Loading config from: {config_path}")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r', encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
            logger.info(f"Config loaded successfully")

            # Token管理相关配置
            self.auth_url: str = config.get("AUTH_URL")
            self.account: str = config.get("ACCOUNT")
            self.password: str = config.get("PASSWORD")
            self.client_id: str = config.get("CLIENT_ID")

            # 验证必要的配置
            if not all([self.auth_url, self.account, self.password, self.client_id]):
                raise ValueError(
                    "缺少必要的配置: AUTH_URL, ACCOUNT, PASSWORD, CLIENT_ID"
                )

            logger.info("Config validation passed")

    def to_dict(self) -> dict:
        """将配置转换为字典"""
        return {
            "auth_url": self.auth_url,
            "account": self.account,
            "password": self.password,
            "client_id": self.client_id,
        }
