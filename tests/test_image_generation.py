"""
测试图片生成接口 - 查看返回参数

成功生成图片时，返回的最后一个chunk格式：
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion.chunk",
  "created": xxx,
  "model": "flow2api",
  "choices": [{
    "index": 0,
    "delta": {
      "content": "![Generated Image](http://图片URL)"
    },
    "finish_reason": "stop"
  }]
}

图片URL格式：
- 如果启用缓存: http://127.0.0.1:8000/tmp/文件名
- 如果未启用缓存: Flow API返回的原始URL
"""
import asyncio
import json
import sys
import io
from typing import Optional, Dict, Any
import httpx

# 修复Windows终端编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# 配置
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "han1234"


async def test_image_generation_stream():
    """测试图片生成接口（流式模式）"""
    print("=" * 80)
    print("测试图片生成接口（流式模式）")
    print("=" * 80)
    print()
    
    # 使用一个简单的图片生成模型
    model = "gemini-2.5-flash-image-landscape"
    prompt = "A beautiful sunset over the ocean with mountains in the background"
    
    print(f"模型: {model}")
    print(f"提示词: {prompt}")
    print()
    print("发送请求...")
    print("-" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 图片生成可能需要较长时间
            async with client.stream(
                method="POST",
                url=f"{BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": True
                }
            ) as response:
                print(f"状态码: {response.status_code}")
                print(f"响应头: {dict(response.headers)}")
                print()
                print("流式响应内容:")
                print("=" * 80)
                
                chunk_count = 0
                all_chunks = []
                reasoning_content = ""
                content_parts = []
                
                async for line in response.aiter_lines():
                    if line:
                        # 处理可能的多个JSON对象在同一行的情况
                        if "data: [DONE]" in line:
                            print("\n[最后一行]")
                            print(f"原始行: {line}")
                            print("✓ 收到结束标记 [DONE]")
                            break
                        
                        # 处理SSE格式 (data: {...})
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                print("\n[最后一行]")
                                print("✓ 收到结束标记 [DONE]")
                                break
                            
                            chunk_count += 1
                            print(f"\n[Chunk {chunk_count}]")
                            print(f"原始行: {line[:150]}...")
                            
                            try:
                                data = json.loads(data_str)
                                all_chunks.append(data)
                                
                                print("\n📦 解析后的JSON结构:")
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                                
                                # 提取关键字段
                                print("\n🔍 关键字段分析:")
                                if "id" in data:
                                    print(f"  - id: {data['id']}")
                                if "object" in data:
                                    print(f"  - object: {data['object']}")
                                if "created" in data:
                                    print(f"  - created: {data['created']}")
                                if "model" in data:
                                    print(f"  - model: {data['model']}")
                                
                                if "choices" in data and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    print(f"  - choices[0].index: {choice.get('index')}")
                                    
                                    if "delta" in choice:
                                        delta = choice["delta"]
                                        print(f"  - choices[0].delta 字段:")
                                        
                                        if "role" in delta:
                                            print(f"    - role: {delta['role']}")
                                        if "reasoning_content" in delta:
                                            reasoning = delta["reasoning_content"]
                                            reasoning_content += reasoning
                                            print(f"    - reasoning_content: {reasoning[:100]}...")
                                        if "content" in delta:
                                            content = delta["content"]
                                            content_parts.append(content)
                                            print(f"    - content: {content[:200]}...")
                                            
                                            # 尝试从Markdown格式中提取图片URL
                                            import re
                                            img_match = re.search(r'!\[.*?\]\((.*?)\)', content)
                                            if img_match:
                                                image_url = img_match.group(1)
                                                print(f"    - 🖼️ 提取的图片URL: {image_url}")
                                    
                                    if "finish_reason" in choice:
                                        finish_reason = choice.get("finish_reason")
                                        print(f"  - choices[0].finish_reason: {finish_reason}")
                                        if finish_reason == "stop":
                                            print(f"    - ✅ 生成完成!")
                                
                                if "error" in data:
                                    print(f"  - ⚠️ error: {data['error']}")
                                
                            except json.JSONDecodeError as e:
                                print(f"❌ JSON解析错误: {e}")
                                print(f"原始数据: {data_str[:200]}")
                        else:
                            # 处理可能的错误JSON对象
                            try:
                                data = json.loads(line)
                                if "error" in data:
                                    print(f"\n❌ 错误响应:")
                                    print(json.dumps(data, indent=2, ensure_ascii=False))
                            except:
                                if line.strip() and not line.startswith("data: [DONE]"):
                                    print(f"\n⚠️ 非标准行: {line[:200]}")
                
                print()
                print("=" * 80)
                print("📊 总结:")
                print(f"  - 总共收到 {chunk_count} 个chunks")
                print(f"  - reasoning_content 总长度: {len(reasoning_content)} 字符")
                print(f"  - content 片段数量: {len(content_parts)}")
                print()
                
                if reasoning_content:
                    print("完整 reasoning_content:")
                    print("-" * 80)
                    print(reasoning_content)
                    print()
                
                if content_parts:
                    full_content = "".join(content_parts)
                    print("完整 content (拼接):")
                    print("-" * 80)
                    print(full_content)
                    
                    # 提取图片URL
                    import re
                    img_matches = re.findall(r'!\[.*?\]\((.*?)\)', full_content)
                    if img_matches:
                        print()
                        print("🖼️ 提取到的图片URL:")
                        for idx, url in enumerate(img_matches, 1):
                            print(f"  {idx}. {url}")
                    else:
                        print("\n⚠️ 未找到图片URL（可能生成失败）")
                
                print()
                print("所有chunks的数据结构示例:")
                print("-" * 80)
                if all_chunks:
                    print(json.dumps(all_chunks[0], indent=2, ensure_ascii=False))
                
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_image_generation_non_stream():
    """测试图片生成接口（非流式模式）"""
    print("\n" + "=" * 80)
    print("测试图片生成接口（非流式模式）")
    print("=" * 80)
    print()
    
    model = "gemini-2.5-flash-image-landscape"
    prompt = "A beautiful sunset over the ocean with mountains in the background"
    
    print(f"模型: {model}")
    print(f"提示词: {prompt}")
    print()
    print("发送请求...")
    print("-" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url=f"{BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": False
                }
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print()
            print("响应内容:")
            print("=" * 80)
            
            try:
                data = response.json()
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                print(response.text)
                
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    # 先测试非流式（会返回提示信息）
    await test_image_generation_non_stream()
    
    # 再测试流式（实际生成）
    await test_image_generation_stream()


if __name__ == "__main__":
    asyncio.run(main())

