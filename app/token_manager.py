import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class TokenCache:
    """Token缓存管理器"""

    def __init__(self):
        self.token: Optional[str] = None
        self.expires_at: Optional[float] = None
        self.lock = asyncio.Lock()

    def is_expired(self) -> bool:
        """检查token是否过期"""
        if self.token is None or self.expires_at is None:
            return True
        return time.time() >= self.expires_at

    async def get_token(self) -> Optional[str]:
        """获取缓存的token"""
        async with self.lock:
            if not self.is_expired():
                return self.token
            return None

    async def set_token(self, token: str, expires_in: int):
        """设置token和过期时间（秒）"""
        async with self.lock:
            self.token = token
            self.expires_at = time.time() + expires_in

    async def clear(self):
        """清除缓存"""
        async with self.lock:
            self.token = None
            self.expires_at = None


class TokenManager:
    """Token管理器"""

    def __init__(
        self,
        auth_url: str,
        account: str,
        password: str,
        client_id: str,
        expires_in: int = 3600
    ):
        """
        初始化Token管理器

        Args:
            auth_url: 认证接口URL
            account: 账户名
            password: 密码
            client_id: 客户端ID
            expires_in: token过期时间（秒）
        """
        self.auth_url = auth_url
        self.account = account
        self.password = password
        self.client_id = client_id
        self.expires_in = expires_in
        self.cache = TokenCache()

    async def fetch_token_from_auth(self) -> dict:
        """从认证接口获取token"""
        async with httpx.AsyncClient() as client:
            # 构建请求头
            headers = {
                "Referer": "https://id.datastat.osinfra.cn/"
            }

            # 构建请求体
            payload = {
                "permission": "sigRead",
                "account": self.account,
                "client_id": self.client_id,
                "accept_term": 0,
                "password": self.password,
            }

            response = await client.post(
                self.auth_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            # 从cookies中提取token（_U_T_字段）
            token = response.cookies.get("_U_T_")
            if token:
                logger.info("从cookies中提取token: _U_T_")
                return {
                    "access_token": token,
                    "expires_in": self.expires_in,
                    "cookies": dict(response.cookies)
                }

            # 如果cookies中没有，尝试从JSON响应中提取
            response_data = response.json()
            token = response_data.get("access_token")
            expires_in = response_data.get("expires_in", self.expires_in)

            return {
                "access_token": token,
                "expires_in": expires_in,
                "response_data": response_data
            }

    async def get_token(self) -> str:
        """获取token，如果缓存有效则返回缓存，否则重新获取"""
        # 尝试从缓存获取
        cached_token = await self.cache.get_token()
        if cached_token:
            return cached_token

        # 从认证接口获取新token
        token_data = await self.fetch_token_from_auth()
        token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        # 存入缓存
        await self.cache.set_token(token, expires_in)
        return token

    async def refresh_token(self) -> str:
        """强制刷新token"""
        await self.cache.clear()
        return await self.get_token()

    async def get_cache_info(self) -> dict:
        """获取缓存信息"""
        async with self.cache.lock:
            if self.cache.token is None:
                return {"cached": False, "expires_at": None}

            expires_at = self.cache.expires_at
            expires_in = max(0, expires_at - time.time())

            return {
                "cached": True,
                "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
                "expires_in_seconds": int(expires_in)
            }
