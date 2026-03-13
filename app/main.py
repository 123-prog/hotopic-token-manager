from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
from app.config import Config
from app.token_manager import TokenManager

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Token Manager Service")

# 加载配置
try:
    config = Config()
    token_manager = TokenManager(
        auth_url=config.auth_url,
        account=config.account,
        password=config.password,
        client_id=config.client_id
    )
except (ValueError, FileNotFoundError) as e:
    logging.error(f"Failed to initialize: {e}")
    raise


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "Bearer"


class CacheInfoResponse(BaseModel):
    """缓存信息响应模型"""
    cached: bool
    expires_at: str = None
    expires_in_seconds: int = None


@app.get("/token", response_model=TokenResponse)
async def get_token():
    """获取token接口

    返回有效的token，如果缓存中有则返回缓存，否则从认证接口获取
    """
    try:
        token = await token_manager.get_token()
        return TokenResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")


@app.get("/token/refresh", response_model=TokenResponse)
async def refresh_token():
    """刷新token接口

    强制从认证接口获取新的token，忽略缓存
    """
    try:
        token = await token_manager.refresh_token()
        return TokenResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")


@app.get("/cache/info", response_model=CacheInfoResponse)
async def get_cache_info():
    """获取缓存信息接口

    返回当前缓存的状态和过期时间
    """
    return await token_manager.get_cache_info()


@app.post("/cache/clear")
async def clear_cache():
    """清除缓存接口"""
    await token_manager.cache.clear()
    return {"message": "Cache cleared"}


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
