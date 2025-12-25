"""API routes - OpenAI compatible endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional
import base64
import re
import json
import time
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession
from ..core.auth import verify_api_key_header
from ..core.models import ChatCompletionRequest, ImageGenerationRequest
from ..services.generation_handler import GenerationHandler, MODEL_CONFIG
from ..core.logger import debug_logger

router = APIRouter()

# Dependency injection will be set up in main.py
generation_handler: GenerationHandler = None


def set_generation_handler(handler: GenerationHandler):
    """Set generation handler instance"""
    global generation_handler
    generation_handler = handler


async def retrieve_image_data(url: str) -> Optional[bytes]:
    """
    智能获取图片数据：
    1. 优先检查是否为本地 /tmp/ 缓存文件，如果是则直接读取磁盘
    2. 如果本地不存在或是外部链接，则进行网络下载
    """
    # 优先尝试本地读取
    try:
        if "/tmp/" in url and generation_handler and generation_handler.file_cache:
            path = urlparse(url).path
            filename = path.split("/tmp/")[-1]
            local_file_path = generation_handler.file_cache.cache_dir / filename

            if local_file_path.exists() and local_file_path.is_file():
                data = local_file_path.read_bytes()
                if data:
                    return data
    except Exception as e:
        debug_logger.log_warning(f"[CONTEXT] 本地缓存读取失败: {str(e)}")

    # 回退逻辑：网络下载
    try:
        async with AsyncSession() as session:
            response = await session.get(url, timeout=30, impersonate="chrome110", verify=False)
            if response.status_code == 200:
                return response.content
            else:
                debug_logger.log_warning(f"[CONTEXT] 图片下载失败，状态码: {response.status_code}")
    except Exception as e:
        debug_logger.log_error(f"[CONTEXT] 图片下载异常: {str(e)}")

    return None


@router.get("/v1/models")
async def list_models(api_key: str = Depends(verify_api_key_header)):
    """List available models"""
    models = []

    for model_id, config in MODEL_CONFIG.items():
        description = f"{config['type'].capitalize()} generation"
        if config['type'] == 'image':
            description += f" - {config['model_name']}"
        else:
            description += f" - {config['model_key']}"

        models.append({
            "id": model_id,
            "object": "model",
            "owned_by": "flow2api",
            "description": description
        })

    return {
        "object": "list",
        "data": models
    }


@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key_header)
):
    """Create chat completion (unified endpoint for image and video generation)"""
    try:
        # Extract prompt from messages
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")

        last_message = request.messages[-1]
        content = last_message.content

        # Handle both string and array format (OpenAI multimodal)
        prompt = ""
        images: List[bytes] = []

        if isinstance(content, str):
            # Simple text format
            prompt = content
        elif isinstance(content, list):
            # Multimodal format
            for item in content:
                if item.get("type") == "text":
                    prompt = item.get("text", "")
                elif item.get("type") == "image_url":
                    # Extract base64 image
                    image_url = item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image"):
                        # Parse base64
                        match = re.search(r"base64,(.+)", image_url)
                        if match:
                            image_base64 = match.group(1)
                            image_bytes = base64.b64decode(image_base64)
                            images.append(image_bytes)

        # Fallback to deprecated image parameter
        if request.image and not images:
            if request.image.startswith("data:image"):
                match = re.search(r"base64,(.+)", request.image)
                if match:
                    image_base64 = match.group(1)
                    image_bytes = base64.b64decode(image_base64)
                    images.append(image_bytes)

        # 自动参考图：仅对图片模型生效
        model_config = MODEL_CONFIG.get(request.model)

        if model_config and model_config["type"] == "image" and not images and len(request.messages) > 1:
            debug_logger.log_info(f"[CONTEXT] 开始查找历史参考图，消息数量: {len(request.messages)}")

            # 如果当前请求没有上传图片，则尝试从历史记录中寻找最近的一张生成图
            for msg in reversed(request.messages[:-1]):
                if msg.role == "assistant" and isinstance(msg.content, str):
                    # 匹配 Markdown 图片格式: ![...](http...)
                    matches = re.findall(r"!\[.*?\]\((.*?)\)", msg.content)
                    if matches:
                        last_image_url = matches[-1]

                        if last_image_url.startswith("http"):
                            try:
                                downloaded_bytes = await retrieve_image_data(last_image_url)
                                if downloaded_bytes and len(downloaded_bytes) > 0:
                                    images.append(downloaded_bytes)
                                    debug_logger.log_info(f"[CONTEXT] ✅ 自动使用历史参考图: {last_image_url}")
                                    break
                                else:
                                    debug_logger.log_warning(f"[CONTEXT] 图片下载失败或为空，尝试下一个: {last_image_url}")
                            except Exception as e:
                                debug_logger.log_error(f"[CONTEXT] 处理参考图时出错: {str(e)}")
                                # 继续尝试下一个图片

        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        # Call generation handler
        if request.stream:
            # Streaming response
            async def generate():
                async for chunk in generation_handler.handle_generation(
                    model=request.model,
                    prompt=prompt,
                    images=images if images else None,
                    stream=True
                ):
                    yield chunk

                # Send [DONE] signal
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming response
            result = None
            async for chunk in generation_handler.handle_generation(
                model=request.model,
                prompt=prompt,
                images=images if images else None,
                stream=False
            ):
                result = chunk

            if result:
                # Parse the result JSON string
                try:
                    result_json = json.loads(result)
                    return JSONResponse(content=result_json)
                except json.JSONDecodeError:
                    # If not JSON, return as-is
                    return JSONResponse(content={"result": result})
            else:
                raise HTTPException(status_code=500, detail="Generation failed: No response from handler")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 默认模型基础名
DEFAULT_MODEL_BASE = "gemini-2.5-flash-image"


def get_model_base_name(model: str) -> str:
    """获取模型的基础名称（去除 -landscape/-portrait 后缀）"""
    if model.endswith("-landscape"):
        return model[:-10]  # 去除 "-landscape"
    elif model.endswith("-portrait"):
        return model[:-9]   # 去除 "-portrait"
    return model


def get_model_orientation_suffix(model: str) -> Optional[str]:
    """获取模型的方向后缀，如果没有则返回 None"""
    if model.endswith("-landscape"):
        return "landscape"
    elif model.endswith("-portrait"):
        return "portrait"
    return None


def parse_size_orientation(size: str) -> Optional[str]:
    """
    解析 size 字符串，根据宽高判断方向
    - 宽 > 高: landscape
    - 高 > 宽: portrait
    - 宽 == 高 或无法解析: None
    """
    if not size:
        return None
    try:
        parts = size.lower().split("x")
        if len(parts) == 2:
            width = int(parts[0])
            height = int(parts[1])
            if width > height:
                return "landscape"
            elif height > width:
                return "portrait"
    except (ValueError, IndexError):
        pass
    return None


@router.post("/v1/images/generations")
async def create_image(
    request: ImageGenerationRequest,
    api_key: str = Depends(verify_api_key_header)
):
    """Create image (OpenAI compatible endpoint)

    支持的尺寸 (自动根据宽高判断横竖屏):
    - 宽 > 高: landscape (横屏)
    - 高 > 宽: portrait (竖屏)
    - 宽 == 高: 默认 landscape

    支持的模型 (可省略 -landscape/-portrait 后缀，由 size 决定):
    - gemini-2.5-flash-image / gemini-2.5-flash-image-landscape / gemini-2.5-flash-image-portrait
    - gemini-3.0-pro-image / gemini-3.0-pro-image-landscape / gemini-3.0-pro-image-portrait
    - imagen-4.0-generate-preview / imagen-4.0-generate-preview-landscape / imagen-4.0-generate-preview-portrait
    """
    try:
        # 1. 尝试从 size 解析方向 (优先级最高)
        orientation = parse_size_orientation(request.size)

        # 2. 如果 size 无法确定方向（正方形或无效），尝试从 model 后缀获取
        if orientation is None and request.model:
            orientation = get_model_orientation_suffix(request.model)

        # 3. 如果仍无法确定，默认使用 landscape
        if orientation is None:
            orientation = "landscape"

        # 获取模型基础名称
        model_base = get_model_base_name(request.model) if request.model else DEFAULT_MODEL_BASE

        # 根据方向拼接完整模型名
        model = f"{model_base}-{orientation}"

        # 验证模型是否支持
        if model not in MODEL_CONFIG:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model: {model}. Available image models: " +
                       ", ".join([k for k, v in MODEL_CONFIG.items() if v["type"] == "image"])
            )

        # 验证模型类型是否为图片
        if MODEL_CONFIG[model]["type"] != "image":
            raise HTTPException(
                status_code=400,
                detail=f"Model {model} is not an image generation model"
            )

        # 验证生成数量 (目前仅支持1)
        if request.n and request.n != 1:
            raise HTTPException(
                status_code=400,
                detail="Currently only n=1 is supported"
            )

        # 调用生成处理器 (必须使用流式模式)
        result_url = None
        result_b64 = None
        error_message = None

        async for chunk in generation_handler.handle_generation(
            model=model,
            prompt=request.prompt,
            images=None,
            stream=True
        ):
            # 解析流式响应
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:])

                    # 检查是否有错误
                    if "error" in data:
                        error_message = data["error"].get("message", "Unknown error")
                        break

                    # 提取最终内容 (包含图片URL的Markdown)
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        finish_reason = data["choices"][0].get("finish_reason")

                        if finish_reason == "stop" and content:
                            # 从Markdown格式中提取图片URL
                            # 格式: ![Generated Image](http://...)
                            match = re.search(r"!\[.*?\]\((.*?)\)", content)
                            if match:
                                result_url = match.group(1)
                except json.JSONDecodeError:
                    continue

        # 检查是否有错误
        if error_message:
            raise HTTPException(status_code=500, detail=error_message)

        if not result_url:
            raise HTTPException(status_code=500, detail="Image generation failed: No URL returned")

        # 构建响应
        created_timestamp = int(time.time())

        if request.response_format == "b64_json":
            # 下载图片并转换为base64
            try:
                image_bytes = await retrieve_image_data(result_url)
                if image_bytes:
                    result_b64 = base64.b64encode(image_bytes).decode("utf-8")
                else:
                    raise HTTPException(status_code=500, detail="Failed to download image for b64_json response")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to convert image to base64: {str(e)}")

            return JSONResponse(content={
                "created": created_timestamp,
                "data": [
                    {
                        "b64_json": result_b64
                    }
                ]
            })
        else:
            # 默认返回URL格式
            return JSONResponse(content={
                "created": created_timestamp,
                "data": [
                    {
                        "url": result_url
                    }
                ]
            })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
