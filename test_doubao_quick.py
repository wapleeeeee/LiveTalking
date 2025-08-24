#!/usr/bin/env python3
"""
豆包 TTS 快速测试脚本
快速验证豆包 TTS API 连接状态
"""

import asyncio
import websockets
import json
import gzip
import uuid
import sys

async def quick_test():
    """快速测试豆包 TTS 连接"""
    
    # 配置
    appid = "7082366049"
    token = "1fE0k8y_gCudCL8b9CLK4YXaFANOWrcH"
    api_url = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    
    print("=" * 50)
    print("豆包 TTS 快速连接测试")
    print("=" * 50)
    print(f"APP ID: {appid}")
    print(f"Token: {token[:20]}...")
    print(f"API URL: {api_url}")
    print()
    
    # 准备测试请求
    test_text = "测试连接"
    voice_type = "zh_male_beijingxiaoye_emo_v2_mars_bigtts"  # 使用有效的语音类型
    
    request_json = {
        "app": {
            "appid": appid,
            "token": "access_token",
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "test_" + str(uuid.uuid4())[:8]
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "pcm",
            "rate": 16000,
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": test_text,
            "text_type": "plain",
            "operation": "submit"
        }
    }
    
    # 构建请求
    default_header = bytearray(b'\x11\x10\x11\x00')
    payload_bytes = str.encode(json.dumps(request_json))
    payload_bytes = gzip.compress(payload_bytes)
    
    full_request = bytearray(default_header)
    full_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
    full_request.extend(payload_bytes)
    
    header = {"Authorization": f"Bearer; {token}"}
    
    print("步骤 1: 尝试建立 WebSocket 连接...")
    
    try:
        async with websockets.connect(
            api_url,
            extra_headers=header,
            ping_interval=None,
            timeout=10
        ) as ws:
            print("✅ WebSocket 连接成功！")
            
            print("\n步骤 2: 发送 TTS 请求...")
            await ws.send(full_request)
            print("✅ 请求已发送！")
            
            print("\n步骤 3: 等待响应...")
            
            # 等待第一个响应
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=5)
                print("✅ 收到响应！")
                
                # 解析响应
                header_size = res[0] & 0x0f
                message_type = res[1] >> 4
                message_type_specific_flags = res[1] & 0x0f
                payload = res[header_size * 4:]
                
                if message_type == 0xb:  # 音频数据
                    print("✅ 收到音频数据响应")
                    
                    if message_type_specific_flags != 0:
                        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
                        print(f"   音频数据大小: {payload_size} 字节")
                    
                    print("\n🎉 测试成功！豆包 TTS 服务正常工作")
                    return True
                    
                elif message_type == 0xf:  # 错误消息
                    print("❌ 收到错误响应")
                    try:
                        # 跳过序列号和大小信息
                        actual_payload = payload[8:] if len(payload) > 8 else payload
                        error_payload = gzip.decompress(actual_payload)
                        error_msg = json.loads(error_payload.decode('utf-8'))
                        print(f"   错误信息: {error_msg}")
                        
                        # 详细错误分析
                        if 'message' in error_msg:
                            msg = error_msg['message']
                            if 'token' in msg.lower() or 'auth' in msg.lower():
                                print("   问题: Token 认证失败")
                            elif 'voice' in msg.lower() or 'voice_type' in msg.lower():
                                print("   问题: 语音类型不支持")
                    except Exception as e:
                        print(f"   解析错误: {e}")
                        print(f"   原始错误数据: {payload[:100]}")
                    return False
                    
                else:
                    print(f"⚠️ 收到未知消息类型: {message_type}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ 等待响应超时（5秒）")
                return False
                
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket 连接失败 - HTTP状态码: {e.status_code}")
        if e.status_code == 401:
            print("   可能原因: Token 无效或过期")
        elif e.status_code == 403:
            print("   可能原因: 权限不足")
        return False
        
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket 错误: {e}")
        return False
        
    except ConnectionRefusedError:
        print("❌ 连接被拒绝")
        print("   可能原因: 网络问题或服务地址错误")
        return False
        
    except Exception as e:
        print(f"❌ 未知错误: {type(e).__name__}: {e}")
        return False

def print_troubleshooting():
    """打印故障排查建议"""
    print("\n" + "=" * 50)
    print("故障排查建议:")
    print("=" * 50)
    print("""
1. 检查网络连接
   - 确保能访问互联网
   - 尝试 ping openspeech.bytedance.com
   
2. 验证凭证
   - 确认 APP ID 正确
   - 确认 Token 有效且未过期
   
3. 检查语音类型
   - 确保使用的 voice_type 是有效的
   - 常用类型: BV001_streaming, BV002_streaming
   
4. 查看项目配置
   - 启动时使用: python app.py --tts doubao --REF_FILE BV001_streaming
   - 检查 ttsreal.py 中的 DoubaoTTS 类配置
   
5. 依赖包
   - 确保安装了 websockets: pip install websockets
   
6. 查看日志
   - 运行主程序时查看控制台输出
   - 查找 "doubao" 相关的错误信息
""")

async def main():
    print("开始豆包 TTS 快速测试...\n")
    
    success = await quick_test()
    
    if not success:
        print_troubleshooting()
    else:
        print("\n下一步:")
        print("1. 运行完整测试: python test_doubao_tts.py")
        print("2. 启动主程序: python app.py --tts doubao --REF_FILE BV001_streaming")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n严重错误: {e}")
        sys.exit(1)
