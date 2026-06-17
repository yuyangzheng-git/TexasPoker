"""
DeepSeek API 客户端
使用 DeepSeek V4 模型 (兼容 OpenAI API)
"""
import os
from openai import AsyncOpenAI, OpenAI

class DeepSeekClient:
    """DeepSeek LLM 客户端包装器"""

    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment")
        
        # 同步客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 异步客户端
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def call_sync(self, messages, model="deepseek-chat", temperature=0.7, max_tokens=400):
        """同步调用 DeepSeek API"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def call_async(self, messages, model="deepseek-chat", temperature=0.7, max_tokens=400):
        """异步调用 DeepSeek API"""
        response = await self.async_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def stream_sync(self, messages, model="deepseek-chat", temperature=0.7, max_tokens=400):
        """流式同步调用"""
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def stream_async(self, messages, model="deepseek-chat", temperature=0.7, max_tokens=400):
        """流式异步调用"""
        stream = await self.async_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# 全局客户端实例
_client = None

def get_deepseek_client():
    """获取全局 DeepSeek 客户端"""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client
