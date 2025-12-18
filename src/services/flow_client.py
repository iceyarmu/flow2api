"""Flow API Client for VideoFX (Veo)"""
import time
import uuid
import random
import base64
import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncIterator
from contextlib import asynccontextmanager
from curl_cffi.requests import AsyncSession
from ..core.logger import debug_logger
from ..core.config import config


class FlowAPIError(Exception):
    """Flow API请求异常"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class RecaptchaTokenError(FlowAPIError):
    """reCAPTCHA token获取失败异常"""
    def __init__(self, message: str):
        super().__init__(message, status_code=403)


class FlowClient:
    """VideoFX API客户端"""

    def __init__(self, proxy_manager):
        self.proxy_manager = proxy_manager
        self.labs_base_url = config.flow_labs_base_url  # https://labs.google/fx/api
        self.api_base_url = config.flow_api_base_url    # https://aisandbox-pa.googleapis.com/v1
        self.timeout = config.flow_timeout
        self._session: Optional[AsyncSession] = None
        self._session_lock = asyncio.Lock()

    @asynccontextmanager
    async def _get_session(self, clear_cookies: bool = False) -> AsyncIterator[AsyncSession]:
        """获取或创建HTTP session，支持连接重用
        
        Args:
            clear_cookies: 如果为True，清除session的cookie jar（用于ST认证，避免cookie污染）
        """
        async with self._session_lock:
            if self._session is None:
                self._session = AsyncSession()
            try:
                if clear_cookies:
                    # 清除session的cookie jar，避免不同ST之间的cookie污染
                    if hasattr(self._session, 'cookies'):
                        self._session.cookies.clear()
                yield self._session
            except Exception:
                # 如果session出现问题，在下一次使用时重新创建
                if self._session:
                    try:
                        await self._session.close()
                    except Exception:
                        pass
                    self._session = None
                raise

    async def close(self):
        """关闭HTTP session（用于清理）"""
        async with self._session_lock:
            if self._session:
                try:
                    await self._session.close()
                except Exception:
                    pass
                self._session = None

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        use_st: bool = False,
        st_token: Optional[str] = None,
        use_at: bool = False,
        at_token: Optional[str] = None,
        need_recaptcha: bool = False,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """统一HTTP请求处理

        Args:
            method: HTTP方法 (GET/POST)
            url: 完整URL
            headers: 请求头
            json_data: JSON请求体
            use_st: 是否使用ST认证 (Cookie方式)
            st_token: Session Token
            use_at: 是否使用AT认证 (Bearer方式)
            at_token: Access Token
            need_recaptcha: 是否需要添加reCAPTCHA token
            project_id: 项目ID（当need_recaptcha=True时必需）
        """
        proxy_url = await self.proxy_manager.get_proxy_url()

        if headers is None:
            headers = {}

        # ST认证 - 使用Cookie
        if use_st and st_token:
            headers["Cookie"] = f"__Secure-next-auth.session-token={st_token}"

        # AT认证 - 使用Bearer
        if use_at and at_token:
            headers["authorization"] = f"Bearer {at_token}"

        # 通用请求头
        headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # 统一拦截：为需要reCAPTCHA token的请求自动添加token
        if need_recaptcha and project_id and json_data:
            try:
                recaptcha_token = await self._get_recaptcha_token(project_id)
                if not recaptcha_token:
                    # 如果没有获取到token，抛出403错误
                    raise RecaptchaTokenError("reCAPTCHA token获取失败: 返回的token为空")
                debug_logger.log_info(f"[reCAPTCHA] 已获取 token，准备添加到请求中 (project_id: {project_id})")
            except RecaptchaTokenError:
                # 如果是 RecaptchaTokenError，直接重新抛出
                raise
            except Exception as e:
                # 捕获其他token获取异常，转换为RecaptchaTokenError
                error_msg = str(e)
                debug_logger.log_error(f"[reCAPTCHA] 无法获取token，请求将被拒绝: {error_msg}")
                # 转换为 RecaptchaTokenError 异常（使用模块级别的类）
                raise RecaptchaTokenError(f"reCAPTCHA token获取失败: {error_msg}") from e
            
            # 递归函数：在嵌套的JSON结构中查找并添加recaptchaToken
            def add_recaptcha_token(data: Any) -> Any:
                """递归添加recaptchaToken到clientContext中
                
                Args:
                    data: 要处理的数据（dict, list或其他类型）
                    
                Returns:
                    处理后的数据，clientContext中包含recaptchaToken
                """
                if isinstance(data, dict):
                    # 创建新字典，避免修改原始数据
                    result: Dict[str, Any] = {}
                    for key, value in data.items():
                        if key == "clientContext" and isinstance(value, dict):
                            # 如果当前层级有clientContext，添加recaptchaToken
                            result[key] = {**value, "recaptchaToken": recaptcha_token}
                            debug_logger.log_info(f"[reCAPTCHA] 已为 clientContext 添加 token")
                        else:
                            # 递归处理嵌套的字典和列表
                            result[key] = add_recaptcha_token(value)
                    return result
                elif isinstance(data, list):
                    # 递归处理列表中的每个元素
                    return [add_recaptcha_token(item) for item in data]
                else:
                    # 其他类型直接返回
                    return data
            
            # 应用递归函数
            json_data = add_recaptcha_token(json_data)

        # 辅助函数：更新json_data中的recaptchaToken
        def update_recaptcha_token_in_data(data: Any, new_token: str) -> Any:
            """递归更新recaptchaToken
            
            Args:
                data: 要处理的数据（dict, list或其他类型）
                new_token: 新的recaptcha token
                
            Returns:
                更新后的数据
            """
            if isinstance(data, dict):
                result: Dict[str, Any] = {}
                for key, value in data.items():
                    if key == "clientContext" and isinstance(value, dict):
                        result[key] = {**value, "recaptchaToken": new_token}
                        debug_logger.log_info(f"[reCAPTCHA] 已更新 clientContext 中的 token")
                    else:
                        result[key] = update_recaptcha_token_in_data(value, new_token)
                return result
            elif isinstance(data, list):
                return [update_recaptcha_token_in_data(item, new_token) for item in data]
            return data

        async def _handle_recaptcha_retry(
            response_text: str,
            project_id: str,
            retry_count: int,
            max_retries: int
        ) -> Optional[str]:
            """处理reCAPTCHA token重试逻辑
            
            Args:
                response_text: 响应文本（小写）
                project_id: 项目ID
                retry_count: 当前重试次数
                max_retries: 最大重试次数
                
            Returns:
                新的token（如果成功），None（如果不需要重试或重试失败）
            """
            if retry_count >= max_retries:
                return None
                
            if "recaptcha" not in response_text and "captcha" not in response_text:
                return None
                
            debug_logger.log_warning(
                f"[reCAPTCHA] 检测到403错误，可能是token失效，尝试重新获取token并重试 "
                f"(重试 {retry_count + 1}/{max_retries})"
            )
            
            try:
                new_token = await self._get_recaptcha_token(project_id)
                if new_token:
                    return new_token
                else:
                    debug_logger.log_error("[reCAPTCHA] 重新获取token失败，无法重试")
                    return None
            except Exception as e:
                debug_logger.log_error(f"[reCAPTCHA] 重新获取token异常: {str(e)}")
                return None

        # Log request
        if config.debug_enabled:
            debug_logger.log_request(
                method=method,
                url=url,
                headers=headers,
                body=json_data,
                proxy=proxy_url
            )

        start_time = time.time()

        # 重试标志：检测到reCAPTCHA失效时自动重试一次
        max_retries = 1 if need_recaptcha and project_id else 0

        for retry_count in range(max_retries + 1):
            try:
                # 如果使用ST认证，清除cookie避免不同token之间的污染
                clear_cookies = use_st and st_token
                async with self._get_session(clear_cookies=clear_cookies) as session:
                    if method.upper() == "GET":
                        response = await session.get(
                            url,
                            headers=headers,
                            proxy=proxy_url,
                            timeout=self.timeout,
                            impersonate="chrome110"
                        )
                    else:  # POST
                        response = await session.post(
                            url,
                            headers=headers,
                            json=json_data,
                            proxy=proxy_url,
                            timeout=self.timeout,
                            impersonate="chrome110"
                        )

                    duration_ms = (time.time() - start_time) * 1000

                    # 获取响应文本（缓存以避免多次读取，特别是在调试模式下）
                    response_text = ""
                    response_text_lower = ""
                    if need_recaptcha or config.debug_enabled:
                        response_text = response.text
                        response_text_lower = response_text.lower()
                    
                    # Log response
                    if config.debug_enabled:
                        debug_logger.log_response(
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            body=response_text,
                            duration_ms=duration_ms
                        )

                    # 检查是否是reCAPTCHA相关的403错误并处理重试
                    if response.status_code == 403 and need_recaptcha and project_id:
                        new_token = await _handle_recaptcha_retry(
                            response_text_lower,
                            project_id,
                            retry_count,
                            max_retries
                        )
                        if new_token:
                            json_data = update_recaptcha_token_in_data(json_data, new_token)
                            continue  # 重试请求

                    response.raise_for_status()
                    return response.json()

            except RecaptchaTokenError:
                # reCAPTCHA token获取失败，直接重新抛出
                raise
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                # 检查是否是 reCAPTCHA token 获取失败导致的错误（自定义异常）
                if isinstance(e, RecaptchaTokenError):
                    if config.debug_enabled:
                        debug_logger.log_error(
                            error_message=error_msg,
                            status_code=403,
                            response_text=""
                        )
                    raise  # 重新抛出，让调用者处理403错误

                # 检查是否是HTTP错误（从curl_cffi的响应异常中提取信息）
                status_code = getattr(e, 'status_code', None)
                response_text = ""
                if hasattr(e, 'response_text'):
                    response_text = e.response_text.lower()
                elif hasattr(e, 'response') and hasattr(e.response, 'text'):
                    try:
                        response_text = e.response.text.lower()
                    except Exception:
                        pass
                
                # 检查是否是reCAPTCHA相关的403错误，且可以重试
                if status_code == 403 and need_recaptcha and project_id:
                    new_token = await _handle_recaptcha_retry(
                        response_text,
                        project_id,
                        retry_count,
                        max_retries
                    )
                    if new_token:
                        json_data = update_recaptcha_token_in_data(json_data, new_token)
                        continue  # 重试请求

                if config.debug_enabled:
                    debug_logger.log_error(
                        error_message=error_msg,
                        status_code=status_code,
                        response_text=response_text
                    )

                # 如果是最后一次重试，抛出异常
                if retry_count >= max_retries:
                    raise FlowAPIError(f"Flow API request failed: {error_msg}", status_code=status_code)
        
        # 理论上不应该到达这里
        raise FlowAPIError("Flow API request failed: Unexpected error")

    # ========== 认证相关 (使用ST) ==========

    async def st_to_at(self, st: str) -> dict:
        """ST转AT

        Args:
            st: Session Token

        Returns:
            {
                "access_token": "AT",
                "expires": "2025-11-15T04:46:04.000Z",
                "user": {...}
            }
        """
        url = f"{self.labs_base_url}/auth/session"
        result = await self._make_request(
            method="GET",
            url=url,
            use_st=True,
            st_token=st
        )
        return result

    # ========== 项目管理 (使用ST) ==========

    async def create_project(self, st: str, title: str) -> str:
        """创建项目,返回project_id

        Args:
            st: Session Token
            title: 项目标题

        Returns:
            project_id (UUID)
        """
        url = f"{self.labs_base_url}/trpc/project.createProject"
        json_data = {
            "json": {
                "projectTitle": title,
                "toolName": "PINHOLE"
            }
        }

        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_st=True,
            st_token=st
        )

        # 解析返回的project_id
        project_id = result["result"]["data"]["json"]["result"]["projectId"]
        return project_id

    async def delete_project(self, st: str, project_id: str):
        """删除项目

        Args:
            st: Session Token
            project_id: 项目ID
        """
        url = f"{self.labs_base_url}/trpc/project.deleteProject"
        json_data = {
            "json": {
                "projectToDeleteId": project_id
            }
        }

        await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_st=True,
            st_token=st
        )

    # ========== 余额查询 (使用AT) ==========

    async def get_credits(self, at: str) -> dict:
        """查询余额

        Args:
            at: Access Token

        Returns:
            {
                "credits": 920,
                "userPaygateTier": "PAYGATE_TIER_ONE"
            }
        """
        url = f"{self.api_base_url}/credits"
        result = await self._make_request(
            method="GET",
            url=url,
            use_at=True,
            at_token=at
        )
        return result

    # ========== 图片上传 (使用AT) ==========

    async def upload_image(
        self,
        at: str,
        image_bytes: bytes,
        aspect_ratio: str = "IMAGE_ASPECT_RATIO_LANDSCAPE"
    ) -> str:
        """上传图片,返回mediaGenerationId

        Args:
            at: Access Token
            image_bytes: 图片字节数据
            aspect_ratio: 图片或视频宽高比（会自动转换为图片格式）

        Returns:
            mediaGenerationId (CAM...)
        """
        # 转换视频aspect_ratio为图片aspect_ratio
        # VIDEO_ASPECT_RATIO_LANDSCAPE -> IMAGE_ASPECT_RATIO_LANDSCAPE
        # VIDEO_ASPECT_RATIO_PORTRAIT -> IMAGE_ASPECT_RATIO_PORTRAIT
        if aspect_ratio.startswith("VIDEO_"):
            aspect_ratio = aspect_ratio.replace("VIDEO_", "IMAGE_")

        # 编码为base64 (去掉前缀)
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        url = f"{self.api_base_url}:uploadUserImage"
        json_data = {
            "imageInput": {
                "rawImageBytes": image_base64,
                "mimeType": "image/jpeg",
                "isUserUploaded": True,
                "aspectRatio": aspect_ratio
            },
            "clientContext": {
                "sessionId": self._generate_session_id(),
                "tool": "ASSET_MANAGER"
            }
        }

        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at
        )

        # 返回mediaGenerationId
        media_id = result["mediaGenerationId"]["mediaGenerationId"]
        return media_id

    # ========== reCAPTCHA Token获取 ==========

    async def _get_recaptcha_token(self, project_id: str) -> Optional[str]:
        """获取reCAPTCHA v3 token（使用内部集成的 RecaptchaService）

        Args:
            project_id: Flow项目ID

        Returns:
            reCAPTCHA token字符串，如果获取失败抛出异常

        Raises:
            Exception: 如果 token 获取失败
        """
        # 验证 project_id
        if not project_id or not project_id.strip():
            raise RecaptchaTokenError("reCAPTCHA token获取失败: project_id 为空")
        
        try:
            from .recaptcha_service import get_recaptcha_service
            debug_logger.log_info("[reCAPTCHA] 使用内部 reCAPTCHA 服务...")
            recaptcha_service = await get_recaptcha_service()
            
            if not recaptcha_service:
                raise RecaptchaTokenError("reCAPTCHA token获取失败: 内部服务未初始化（可能 Playwright 未安装）")
            
            if not recaptcha_service._initialized:
                raise RecaptchaTokenError("reCAPTCHA token获取失败: 内部服务未就绪")
            
            debug_logger.log_info(f"[reCAPTCHA] 开始获取 token, project_id: {project_id[:20]}...（可能需要 10-20 秒，请耐心等待）...")
            
            # 使用 asyncio.wait_for 确保有足够的超时时间（60 秒）
            token, error_detail = await asyncio.wait_for(
                recaptcha_service.get_token(project_id.strip()),
                timeout=60.0
            )
            
            if token:
                debug_logger.log_info("[reCAPTCHA] ✅ Token 获取成功")
                return token
            else:
                raise RecaptchaTokenError(f"reCAPTCHA token获取失败: {error_detail}")
                
        except asyncio.TimeoutError:
            error_msg = "reCAPTCHA token获取超时（60秒），请检查网络连接或reCAPTCHA服务状态"
            debug_logger.log_error(f"[reCAPTCHA] ❌ {error_msg}")
            raise RecaptchaTokenError(error_msg)
        except ImportError as e:
            error_msg = f"reCAPTCHA token获取失败: Playwright 未安装 - {str(e)}"
            debug_logger.log_error(f"[reCAPTCHA] ❌ {error_msg}")
            raise RecaptchaTokenError(error_msg)
        except RecaptchaTokenError:
            # 如果已经是我们抛出的异常，直接重新抛出
            raise
        except Exception as e:
            error_msg = f"reCAPTCHA token获取失败: {str(e)}"
            debug_logger.log_error(f"[reCAPTCHA] ❌ {error_msg}")
            import traceback
            debug_logger.log_error(f"[reCAPTCHA] 异常详情: {traceback.format_exc()}")
            raise RecaptchaTokenError(error_msg)

    # ========== 图片生成 (使用AT) - 同步返回 ==========

    async def generate_image(
        self,
        at: str,
        project_id: str,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        image_inputs: Optional[List[Dict]] = None
    ) -> dict:
        """生成图片(同步返回)
        Args:
            at: Access Token
            project_id: 项目ID
            prompt: 提示词
            model_name: GEM_PIX, GEM_PIX_2 或 IMAGEN_3_5
            aspect_ratio: 图片宽高比
            image_inputs: 参考图片列表(图生图时使用)
        Returns:
            {
                "media": [{
                    "image": {
                        "generatedImage": {
                            "fifeUrl": "图片URL",
                            ...
                        }
                    }
                }]
            }
        """
        url = f"{self.api_base_url}/projects/{project_id}/flowMedia:batchGenerateImages"
        session_id = self._generate_session_id()
        # 构建请求（reCAPTCHA token将通过统一拦截自动添加）
        request_data = {
            "clientContext": {
                "projectId": project_id,
                "sessionId": session_id,
                "tool": "PINHOLE"
            },
            "seed": random.randint(1, 99999),
            "imageModelName": model_name,
            "imageAspectRatio": aspect_ratio,
            "prompt": prompt,
            "imageInputs": image_inputs or []
        }
        # 外层clientContext也会通过统一拦截自动添加token
        json_data = {
            "clientContext": {
                "sessionId": session_id
            },
            "requests": [request_data]
        }
        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at,
            need_recaptcha=True,
            project_id=project_id
        )
        return result

    # ========== 视频生成 (使用AT) - 异步返回 ==========
    async def generate_video_text(
        self,
        at: str,
        project_id: str,
        prompt: str,
        model_key: str,
        aspect_ratio: str,
        user_paygate_tier: str = "PAYGATE_TIER_ONE"
    ) -> dict:
        """文生视频,返回task_id
        Args:
            at: Access Token
            project_id: 项目ID
            prompt: 提示词
            model_key: veo_3_1_t2v_fast 等
            aspect_ratio: 视频宽高比
            user_paygate_tier: 用户等级
        Returns:
            {
                "operations": [{
                    "operation": {"name": "task_id"},
                    "sceneId": "uuid",
                    "status": "MEDIA_GENERATION_STATUS_PENDING"
                }],
                "remainingCredits": 900
            }
        """
        url = f"{self.api_base_url}/video:batchAsyncGenerateVideoText"
        scene_id = str(uuid.uuid4())
        json_data = {
            "clientContext": {
                "sessionId": self._generate_session_id(),
                "projectId": project_id,
                "tool": "PINHOLE",
                "userPaygateTier": user_paygate_tier
            },
            "requests": [{
                "aspectRatio": aspect_ratio,
                "seed": random.randint(1, 99999),
                "textInput": {
                    "prompt": prompt
                },
                "videoModelKey": model_key,
                "metadata": {
                    "sceneId": scene_id
                }
            }]
        }
        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at,
            need_recaptcha=True,
            project_id=project_id
        )
        return result

    async def generate_video_reference_images(
        self,
        at: str,
        project_id: str,
        prompt: str,
        model_key: str,
        aspect_ratio: str,
        reference_images: List[Dict],
        user_paygate_tier: str = "PAYGATE_TIER_ONE"
    ) -> dict:
        """图生视频,返回task_id
        Args:
            at: Access Token
            project_id: 项目ID
            prompt: 提示词
            model_key: veo_3_0_r2v_fast
            aspect_ratio: 视频宽高比
            reference_images: 参考图片列表 [{"imageUsageType": "IMAGE_USAGE_TYPE_ASSET", "mediaId": "..."}]
            user_paygate_tier: 用户等级
        Returns:
            同 generate_video_text
        """
        url = f"{self.api_base_url}/video:batchAsyncGenerateVideoReferenceImages"
        scene_id = str(uuid.uuid4())
        json_data = {
            "clientContext": {
                "sessionId": self._generate_session_id(),
                "projectId": project_id,
                "tool": "PINHOLE",
                "userPaygateTier": user_paygate_tier
            },
            "requests": [{
                "aspectRatio": aspect_ratio,
                "seed": random.randint(1, 99999),
                "textInput": {
                    "prompt": prompt
                },
                "videoModelKey": model_key,
                "referenceImages": reference_images,
                "metadata": {
                    "sceneId": scene_id
                }
            }]
        }
        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at,
            need_recaptcha=True,
            project_id=project_id
        )
        return result

    async def generate_video_start_end(
        self,
        at: str,
        project_id: str,
        prompt: str,
        model_key: str,
        aspect_ratio: str,
        start_media_id: str,
        end_media_id: str,
        user_paygate_tier: str = "PAYGATE_TIER_ONE"
    ) -> dict:
        """收尾帧生成视频,返回task_id
        Args:
            at: Access Token
            project_id: 项目ID
            prompt: 提示词
            model_key: veo_3_1_i2v_s_fast_fl
            aspect_ratio: 视频宽高比
            start_media_id: 起始帧mediaId
            end_media_id: 结束帧mediaId
            user_paygate_tier: 用户等级
        Returns:
            同 generate_video_text
        """
        url = f"{self.api_base_url}/video:batchAsyncGenerateVideoStartAndEndImage"
        scene_id = str(uuid.uuid4())
        json_data = {
            "clientContext": {
                "sessionId": self._generate_session_id(),
                "projectId": project_id,
                "tool": "PINHOLE",
                "userPaygateTier": user_paygate_tier
            },
            "requests": [{
                "aspectRatio": aspect_ratio,
                "seed": random.randint(1, 99999),
                "textInput": {
                    "prompt": prompt
                },
                "videoModelKey": model_key,
                "startImage": {
                    "mediaId": start_media_id
                },
                "endImage": {
                    "mediaId": end_media_id
                },
                "metadata": {
                    "sceneId": scene_id
                }
            }]
        }
        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at,
            need_recaptcha=True,
            project_id=project_id
        )
        return result

    async def generate_video_start_image(
        self,
        at: str,
        project_id: str,
        prompt: str,
        model_key: str,
        aspect_ratio: str,
        start_media_id: str,
        user_paygate_tier: str = "PAYGATE_TIER_ONE"
    ) -> dict:
        """仅首帧生成视频,返回task_id
        Args:
            at: Access Token
            project_id: 项目ID
            prompt: 提示词
            model_key: veo_3_1_i2v_s_fast_fl等
            aspect_ratio: 视频宽高比
            start_media_id: 起始帧mediaId
            user_paygate_tier: 用户等级
        Returns:
            同 generate_video_text
        """
        url = f"{self.api_base_url}/video:batchAsyncGenerateVideoStartAndEndImage"
        scene_id = str(uuid.uuid4())
        json_data = {
            "clientContext": {
                "sessionId": self._generate_session_id(),
                "projectId": project_id,
                "tool": "PINHOLE",
                "userPaygateTier": user_paygate_tier
            },
            "requests": [{
                "aspectRatio": aspect_ratio,
                "seed": random.randint(1, 99999),
                "textInput": {
                    "prompt": prompt
                },
                "videoModelKey": model_key,
                "startImage": {
                    "mediaId": start_media_id
                },
                # 注意: 没有endImage字段,只用首帧
                "metadata": {
                    "sceneId": scene_id
                }
            }]
        }
        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at,
            need_recaptcha=True,
            project_id=project_id
        )
        return result
    # ========== 任务轮询 (使用AT) ==========
    async def check_video_status(self, at: str, operations: List[Dict]) -> dict:
        """查询视频生成状态
        Args:
            at: Access Token
            operations: 操作列表 [{"operation": {"name": "task_id"}, "sceneId": "...", "status": "..."}]
        Returns:
            {
                "operations": [{
                    "operation": {
                        "name": "task_id",
                        "metadata": {...}  # 完成时包含视频信息
                    },
                    "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL"
                }]
            }
        """
        url = f"{self.api_base_url}/video:batchCheckAsyncVideoGenerationStatus"
        json_data = {
            "operations": operations
        }
        result = await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_at=True,
            at_token=at
        )
        return result

    # ========== 媒体删除 (使用ST) ==========
    async def delete_media(self, st: str, media_names: List[str]):
        """删除媒体
        Args:
            st: Session Token
            media_names: 媒体ID列表
        """
        url = f"{self.labs_base_url}/trpc/media.deleteMedia"
        json_data = {
            "json": {
                "names": media_names
            }
        }
        await self._make_request(
            method="POST",
            url=url,
            json_data=json_data,
            use_st=True,
            st_token=st
        )

    # ========== 辅助方法 ==========
    def _generate_session_id(self) -> str:
        """生成sessionId: ;timestamp"""
        return f";{int(time.time() * 1000)}"

    def _generate_scene_id(self) -> str:
        """生成sceneId: UUID"""
        return str(uuid.uuid4())
