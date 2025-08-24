#!/usr/bin/env python3
"""
简化版音频文件上传测试脚本
无需复杂的WebRTC连接，直接使用已有的session上传音频

使用方法：
    1. 先在浏览器打开 http://localhost:8010/webrtcapi.html
    2. 点击 Start 建立连接，获取 Session ID（6位数字）
    3. 运行: python test_audio_upload_simple.py --audio test.mp3 --session 123456
"""

import asyncio
import aiohttp
import argparse
import json
import os
import sys
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleAudioUploader:
    def __init__(self, base_url="http://localhost:8010"):
        self.base_url = base_url
        self.session_id = None
        
    async def upload_audio_file(self, audio_path: str, session_id: int):
        """上传音频文件到服务器"""
        if not os.path.exists(audio_path):
            logger.error(f"❌ 音频文件不存在: {audio_path}")
            return False
        
        # 检查文件格式
        file_ext = os.path.splitext(audio_path)[1].lower()
        if file_ext == '.mp3':
            logger.warning("⚠️ 检测到 MP3 格式")
            logger.warning("服务端不支持 MP3，请先转换为 WAV 格式：")
            logger.warning(f"运行: python convert_to_wav.py {audio_path}")
            logger.warning("然后使用转换后的 .wav 文件")
            logger.info("\n是否继续尝试上传？（可能会失败）")
            
        try:
            logger.info(f"正在上传音频文件: {audio_path}")
            logger.info(f"使用 Session ID: {session_id}")
            
            # 确定正确的 content_type
            content_type_map = {
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.flac': 'audio/flac',
                '.ogg': 'audio/ogg',
                '.m4a': 'audio/mp4'
            }
            content_type = content_type_map.get(file_ext, 'application/octet-stream')
            logger.info(f"文件类型: {content_type}")
            
            async with aiohttp.ClientSession() as session:
                # 先读取文件内容到内存
                with open(audio_path, 'rb') as f:
                    file_data = f.read()
                
                logger.info(f"文件大小: {len(file_data) / 1024:.2f} KB")
                
                # 准备文件数据
                data = aiohttp.FormData()
                data.add_field('sessionid', str(session_id))
                data.add_field('file', file_data, 
                             filename=os.path.basename(audio_path),
                             content_type=content_type)
                
                # 发送请求
                async with session.post(f"{self.base_url}/humanaudio", data=data) as resp:
                        if resp.status != 200:
                            logger.error(f"❌ 上传失败，HTTP状态码: {resp.status}")
                            response_text = await resp.text()
                            logger.error(f"服务器响应: {response_text}")
                            return False
                            
                        result = await resp.json()
                        
                        if result.get("code") == 0:
                            logger.info(f"✅ 音频文件上传成功！")
                            return True
                        else:
                            logger.error(f"❌ 上传失败: {result.get('msg')}")
                            return False
                            
        except Exception as e:
            logger.error(f"❌ 上传音频文件时出错: {e}")
            return False
    
    async def check_speaking_status(self, session_id: int):
        """检查数字人说话状态"""
        try:
            async with aiohttp.ClientSession() as session:
                data = {"sessionid": session_id}
                async with session.post(f"{self.base_url}/is_speaking", json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("data", False)
        except:
            pass
        return False
    
    async def wait_for_completion(self, session_id: int, timeout=60):
        """等待音频播放完成"""
        logger.info("等待数字人播放音频...")
        start_time = time.time()
        was_speaking = False
        
        while time.time() - start_time < timeout:
            is_speaking = await self.check_speaking_status(session_id)
            
            if is_speaking and not was_speaking:
                logger.info("🔊 数字人开始播放音频...")
                was_speaking = True
            elif not is_speaking and was_speaking:
                logger.info("✅ 音频播放完成！")
                return True
                
            await asyncio.sleep(0.5)
        
        if not was_speaking:
            logger.warning("⚠️ 数字人可能没有开始播放，请检查连接状态")
        else:
            logger.warning("⏱️ 等待播放完成超时")
        return False
    
    async def test_connection(self, session_id: int):
        """测试连接是否有效"""
        try:
            logger.info(f"测试 Session {session_id} 连接...")
            async with aiohttp.ClientSession() as session:
                data = {"sessionid": session_id}
                async with session.post(f"{self.base_url}/is_speaking", json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("code") == 0:
                            logger.info("✅ 连接有效")
                            return True
                        else:
                            logger.error(f"❌ 连接无效: {result.get('msg', '未知错误')}")
                            return False
            logger.error("❌ 无法连接到服务器")
            return False
        except Exception as e:
            logger.error(f"❌ 测试连接失败: {e}")
            return False

async def test_single_audio(audio_path: str, session_id: int, base_url: str = "http://localhost:8010"):
    """测试单个音频文件上传"""
    uploader = SimpleAudioUploader(base_url)
    
    # 测试连接
    if not await uploader.test_connection(session_id):
        logger.error("请先在浏览器中建立连接")
        return False
    
    # 上传音频文件
    success = await uploader.upload_audio_file(audio_path, session_id)
    if not success:
        return False
    
    # 等待播放完成
    await uploader.wait_for_completion(session_id)
    
    return True

async def test_loop_audio(audio_path: str, session_id: int, base_url: str = "http://localhost:8010", interval: int = 2):
    """循环测试音频文件上传"""
    uploader = SimpleAudioUploader(base_url)
    
    # 测试连接
    if not await uploader.test_connection(session_id):
        logger.error("请先在浏览器中建立连接")
        return
    
    loop_count = 0
    logger.info("开始循环播放测试（按Ctrl+C停止）...")
    
    try:
        while True:
            loop_count += 1
            logger.info(f"\n--- 第 {loop_count} 次播放 ---")
            
            # 上传音频文件
            success = await uploader.upload_audio_file(audio_path, session_id)
            if success:
                # 等待播放完成
                await uploader.wait_for_completion(session_id)
            
            # 间隔
            logger.info(f"等待 {interval} 秒后继续...")
            await asyncio.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("\n停止循环播放")

async def get_session_from_browser():
    """引导用户从浏览器获取session"""
    print("\n" + "="*60)
    print("📝 请按以下步骤获取 Session ID：")
    print("="*60)
    print("1. 打开浏览器访问: http://localhost:8010/webrtcapi.html")
    print("2. 点击 'Start' 按钮建立连接")
    print("3. 连接成功后，页面会显示 Session ID（6位数字）")
    print("4. 复制这个 Session ID")
    print("="*60)
    
    while True:
        session_input = input("\n请输入 Session ID (6位数字，输入 q 退出): ").strip()
        
        if session_input.lower() == 'q':
            return None
            
        if session_input.isdigit() and len(session_input) == 6:
            return int(session_input)
        else:
            print("❌ 无效的 Session ID，请输入6位数字")

async def main():
    parser = argparse.ArgumentParser(
        description="简化版音频上传测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用步骤：
  1. 在浏览器打开 http://localhost:8010/webrtcapi.html
  2. 点击 Start 建立连接，记下 Session ID
  3. 运行本脚本，提供音频文件和 Session ID

示例：
  python test_audio_upload_simple.py --audio test.mp3 --session 123456
  python test_audio_upload_simple.py --audio test.mp3  # 交互式输入session
        """
    )
    
    parser.add_argument(
        "--audio", 
        type=str, 
        required=True,
        help="音频文件路径（支持MP3、WAV等格式）"
    )
    parser.add_argument(
        "--session", 
        type=int,
        help="Session ID（6位数字），如不提供则交互式输入"
    )
    parser.add_argument(
        "--url", 
        type=str, 
        default="http://localhost:8010",
        help="服务器地址（默认: http://localhost:8010）"
    )
    parser.add_argument(
        "--loop", 
        action="store_true",
        help="循环播放模式"
    )
    parser.add_argument(
        "--interval", 
        type=int,
        default=2,
        help="循环播放间隔（秒，默认: 2）"
    )
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.audio):
        logger.error(f"❌ 音频文件不存在: {args.audio}")
        sys.exit(1)
    
    # 获取 Session ID
    session_id = args.session
    if not session_id:
        session_id = await get_session_from_browser()
        if not session_id:
            logger.info("已退出")
            return
    
    # 显示测试信息
    logger.info("=" * 60)
    logger.info("🎵 简化版音频上传测试工具")
    logger.info("=" * 60)
    logger.info(f"服务器地址: {args.url}")
    logger.info(f"音频文件: {args.audio}")
    logger.info(f"文件大小: {os.path.getsize(args.audio) / 1024:.2f} KB")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"播放模式: {'循环' if args.loop else '单次'}")
    logger.info("=" * 60)
    
    # 执行测试
    if args.loop:
        await test_loop_audio(args.audio, session_id, args.url, args.interval)
    else:
        success = await test_single_audio(args.audio, session_id, args.url)
        if success:
            logger.info("\n✅ 测试成功完成！")
        else:
            logger.error("\n❌ 测试失败")
            sys.exit(1)

if __name__ == "__main__":
    try:
        # 在 Windows 上设置事件循环策略，避免警告
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n测试已中断")
    except Exception as e:
        logger.error(f"测试出错: {e}")
        sys.exit(1)
