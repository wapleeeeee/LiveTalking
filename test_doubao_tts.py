#!/usr/bin/env python3
"""
豆包 TTS 测试脚本
用于测试豆包 TTS API 的连接和基本功能
"""

import asyncio
import websockets
import json
import gzip
import uuid
import wave
import os
import time
from typing import AsyncIterator

class DoubaoTTSClient:
    def __init__(self):
        # 豆包 TTS 配置
        self.appid = "7082366049"
        self.token = "1fE0k8y_gCudCL8b9CLK4YXaFANOWrcH"
        self.cluster = 'volcano_tts'
        self.host = "openspeech.bytedance.com"
        self.api_url = f"wss://{self.host}/api/v1/tts/ws_binary"
        
        # 可用的语音类型（需要根据豆包文档更新）
        self.voice_types = [
            "zh_male_beijingxiaoye_emo_v2_mars_bigtts",  # 北京小爷（已验证可用）
            "zh_female_yaoyao_luna_bigtts",  # 中文女声-瑶瑶
            "zh_male_jingqiang_moon_bigtts",  # 中文男声-京腔
            "zh_female_shuangkuaisisi_moon_bigtts",  # 中文女声-思思
            "zh_male_wennuan_moon_bigtts",  # 中文男声-温暖
            "BV001_streaming",  # 通用女声
            "BV002_streaming",  # 通用男声
        ]
        
    def create_request(self, text: str, voice_type: str) -> bytes:
        """创建请求数据包"""
        request_json = {
            "app": {
                "appid": self.appid,
                "token": "access_token",
                "cluster": self.cluster
            },
            "user": {
                "uid": "test_user_" + str(uuid.uuid4())[:8]
            },
            "audio": {
                "voice_type": voice_type,
                "encoding": "pcm",
                "rate": 16000,  # 采样率
                "speed_ratio": 1.0,  # 语速
                "volume_ratio": 1.0,  # 音量
                "pitch_ratio": 1.0,  # 音调
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "submit"
            }
        }
        
        # 构建二进制请求
        default_header = bytearray(b'\x11\x10\x11\x00')
        payload_bytes = str.encode(json.dumps(request_json))
        payload_bytes = gzip.compress(payload_bytes)
        
        full_request = bytearray(default_header)
        full_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        full_request.extend(payload_bytes)
        
        return bytes(full_request)
    
    async def synthesize(self, text: str, voice_type: str) -> AsyncIterator[bytes]:
        """合成语音"""
        print(f"开始合成: {text}")
        print(f"使用语音: {voice_type}")
        
        request_data = self.create_request(text, voice_type)
        header = {"Authorization": f"Bearer; {self.token}"}
        
        try:
            start_time = time.time()
            first_chunk = True
            
            async with websockets.connect(
                self.api_url, 
                extra_headers=header, 
                ping_interval=None
            ) as ws:
                print("WebSocket 连接成功")
                await ws.send(request_data)
                print("请求已发送")
                
                while True:
                    res = await ws.recv()
                    
                    # 解析响应头
                    header_size = res[0] & 0x0f
                    message_type = res[1] >> 4
                    message_type_specific_flags = res[1] & 0x0f
                    payload = res[header_size * 4:]
                    
                    if message_type == 0xb:  # 音频数据
                        if message_type_specific_flags == 0:
                            continue
                        else:
                            if first_chunk:
                                elapsed = time.time() - start_time
                                print(f"收到第一个音频块，耗时: {elapsed:.3f}秒")
                                first_chunk = False
                            
                            # 提取音频数据
                            sequence_number = int.from_bytes(payload[:4], "big", signed=True)
                            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
                            audio_data = payload[8:]
                            
                            yield audio_data
                            
                            # 检查是否结束
                            if sequence_number < 0:
                                print("音频流结束")
                                break
                    elif message_type == 0xf:  # 错误消息
                        error_payload = gzip.decompress(payload)
                        error_msg = json.loads(error_payload.decode('utf-8'))
                        print(f"错误: {error_msg}")
                        break
                    else:
                        print(f"未知消息类型: {message_type}")
                        break
                        
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket 错误: {e}")
            raise
        except Exception as e:
            print(f"未知错误: {e}")
            raise
    
    async def test_voice_type(self, text: str, voice_type: str, output_file: str):
        """测试单个语音类型"""
        print(f"\n{'='*50}")
        print(f"测试语音类型: {voice_type}")
        print(f"输出文件: {output_file}")
        
        try:
            # 收集所有音频数据
            audio_chunks = []
            async for chunk in self.synthesize(text, voice_type):
                audio_chunks.append(chunk)
            
            if not audio_chunks:
                print("未收到音频数据")
                return False
            
            # 合并音频数据
            audio_data = b''.join(audio_chunks)
            print(f"总共收到 {len(audio_data)} 字节音频数据")
            
            # 保存为 WAV 文件
            with wave.open(output_file, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16 位
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)
            
            print(f"音频已保存到: {output_file}")
            return True
            
        except Exception as e:
            print(f"测试失败: {e}")
            return False
    
    async def test_all_voices(self):
        """测试所有语音类型"""
        test_text = "你好，这是豆包语音合成测试。今天天气真不错。"
        success_count = 0
        failed_voices = []
        
        # 创建输出目录
        output_dir = "doubao_tts_test_output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录: {output_dir}")
        
        # 测试每个语音类型
        for i, voice_type in enumerate(self.voice_types, 1):
            output_file = os.path.join(output_dir, f"{voice_type}.wav")
            success = await self.test_voice_type(test_text, voice_type, output_file)
            
            if success:
                success_count += 1
            else:
                failed_voices.append(voice_type)
            
            # 避免请求过快
            if i < len(self.voice_types):
                await asyncio.sleep(1)
        
        # 打印测试结果
        print(f"\n{'='*50}")
        print("测试结果总结:")
        print(f"成功: {success_count}/{len(self.voice_types)}")
        
        if failed_voices:
            print(f"失败的语音类型: {', '.join(failed_voices)}")
        
        if success_count > 0:
            print(f"\n音频文件保存在: {output_dir}/")
            print("你可以播放这些文件来检查音质")
    
    async def simple_test(self):
        """简单测试 - 只测试一个语音"""
        test_text = "你好，我是数字人助手。这是一个豆包语音合成的测试。"
        voice_type = "zh_male_beijingxiaoye_emo_v2_mars_bigtts"  # 使用已验证的语音
        output_file = "doubao_test.wav"
        
        print("开始简单测试...")
        success = await self.test_voice_type(test_text, voice_type, output_file)
        
        if success:
            print(f"\n✅ 测试成功！音频文件: {output_file}")
            print("你可以使用以下命令播放音频:")
            print(f"  macOS: afplay {output_file}")
            print(f"  Linux: aplay {output_file}")
            print(f"  或使用任何音频播放器打开")
        else:
            print("\n❌ 测试失败，请检查错误信息")

async def main():
    """主函数"""
    client = DoubaoTTSClient()
    
    print("豆包 TTS 测试工具")
    print("=" * 50)
    print("配置信息:")
    print(f"  APP ID: {client.appid}")
    print(f"  Token: {client.token[:20]}...")
    print(f"  API URL: {client.api_url}")
    print()
    
    # 选择测试模式
    print("请选择测试模式:")
    print("1. 简单测试（测试一个语音）")
    print("2. 完整测试（测试所有语音类型）")
    print("3. 自定义测试（输入自定义文本）")
    
    choice = input("请输入选择 (1/2/3，默认为1): ").strip() or "1"
    
    if choice == "1":
        await client.simple_test()
    elif choice == "2":
        await client.test_all_voices()
    elif choice == "3":
        text = input("请输入要合成的文本: ").strip()
        if not text:
            text = "这是一个测试"
        
        print("\n可用的语音类型:")
        for i, voice in enumerate(client.voice_types, 1):
            print(f"{i}. {voice}")
        
        voice_idx = input("请选择语音类型编号 (默认为1): ").strip()
        try:
            idx = int(voice_idx) - 1 if voice_idx else 0
            voice_type = client.voice_types[idx]
        except (ValueError, IndexError):
            voice_type = client.voice_types[0]
        
        output_file = f"custom_test_{int(time.time())}.wav"
        success = await client.test_voice_type(text, voice_type, output_file)
        
        if success:
            print(f"\n✅ 合成成功！音频文件: {output_file}")
    else:
        print("无效的选择")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试中断")
    except Exception as e:
        print(f"错误: {e}")
