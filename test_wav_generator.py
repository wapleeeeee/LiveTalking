#!/usr/bin/env python3
"""
生成标准 WAV 测试文件
生成一个服务端肯定能识别的标准 PCM WAV 文件

使用方法：
    python test_wav_generator.py
    python test_wav_generator.py --text "自定义文本"
"""

import numpy as np
import wave
import argparse
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def generate_sine_wave(frequency=440, duration=2, sample_rate=16000, amplitude=0.5):
    """生成正弦波音频"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
    return wave_data

def generate_silence(duration=2, sample_rate=16000):
    """生成静音"""
    return np.zeros(int(sample_rate * duration))

def save_wav(filename, audio_data, sample_rate=16000):
    """保存为标准 PCM WAV 文件"""
    # 转换为 16-bit PCM
    audio_data = np.clip(audio_data, -1, 1)
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # 写入 WAV 文件
    with wave.open(filename, 'wb') as wav_file:
        # 设置参数：1通道，2字节采样，16kHz
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)  # 采样率
        wav_file.writeframes(audio_data.tobytes())
    
    return filename

def generate_test_wav(output_file="test_standard.wav", type="sine"):
    """生成测试 WAV 文件"""
    
    logger.info("=" * 50)
    logger.info("🎵 生成标准 WAV 测试文件")
    logger.info("=" * 50)
    
    sample_rate = 16000
    
    if type == "sine":
        logger.info("生成类型: 正弦波（440Hz，2秒）")
        audio_data = generate_sine_wave(440, 2, sample_rate)
    elif type == "silence":
        logger.info("生成类型: 静音（2秒）")
        audio_data = generate_silence(2, sample_rate)
    elif type == "beep":
        logger.info("生成类型: 哔哔声")
        # 生成哔-停-哔的模式
        beep1 = generate_sine_wave(800, 0.2, sample_rate)
        silence = generate_silence(0.1, sample_rate)
        beep2 = generate_sine_wave(800, 0.2, sample_rate)
        audio_data = np.concatenate([beep1, silence, beep2, silence])
    else:
        logger.info("生成类型: 混合测试音")
        # 生成不同频率的音调
        tone1 = generate_sine_wave(440, 0.5, sample_rate)  # A4
        tone2 = generate_sine_wave(523, 0.5, sample_rate)  # C5
        tone3 = generate_sine_wave(659, 0.5, sample_rate)  # E5
        silence = generate_silence(0.2, sample_rate)
        audio_data = np.concatenate([tone1, silence, tone2, silence, tone3])
    
    # 保存文件
    save_wav(output_file, audio_data, sample_rate)
    
    # 显示文件信息
    file_size = os.path.getsize(output_file)
    logger.info(f"输出文件: {output_file}")
    logger.info(f"文件大小: {file_size / 1024:.2f} KB")
    logger.info(f"采样率: {sample_rate} Hz")
    logger.info(f"位深度: 16-bit")
    logger.info(f"声道数: 1 (单声道)")
    logger.info(f"时长: {len(audio_data) / sample_rate:.2f} 秒")
    
    return output_file

def verify_wav_file(filename):
    """验证 WAV 文件格式"""
    try:
        with wave.open(filename, 'rb') as wav_file:
            logger.info("\n验证 WAV 文件:")
            logger.info(f"  声道数: {wav_file.getnchannels()}")
            logger.info(f"  采样宽度: {wav_file.getsampwidth()} 字节")
            logger.info(f"  采样率: {wav_file.getframerate()} Hz")
            logger.info(f"  总帧数: {wav_file.getnframes()}")
            logger.info(f"  时长: {wav_file.getnframes() / wav_file.getframerate():.2f} 秒")
            logger.info("✅ WAV 文件格式正确")
            return True
    except Exception as e:
        logger.error(f"❌ WAV 文件验证失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="生成标准 WAV 测试文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
类型说明：
    sine    - 440Hz 正弦波
    silence - 静音
    beep    - 哔哔声
    mixed   - 混合测试音

示例：
    python test_wav_generator.py
    python test_wav_generator.py --type beep
    python test_wav_generator.py --output my_test.wav
        """
    )
    
    parser.add_argument(
        "--output", "-o",
        default="test_standard.wav",
        help="输出文件名（默认: test_standard.wav）"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["sine", "silence", "beep", "mixed"],
        default="beep",
        help="音频类型（默认: beep）"
    )
    parser.add_argument(
        "--verify",
        help="验证现有 WAV 文件"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        # 验证模式
        if os.path.exists(args.verify):
            verify_wav_file(args.verify)
        else:
            logger.error(f"文件不存在: {args.verify}")
    else:
        # 生成模式
        output_file = generate_test_wav(args.output, args.type)
        verify_wav_file(output_file)
        
        logger.info("\n✅ 测试文件已生成！")
        logger.info("\n使用方法：")
        logger.info("1. 在浏览器打开 http://localhost:8010/webrtcapi.html")
        logger.info("2. 点击 Start 获取 Session ID")
        logger.info(f"3. 运行: python test_audio_upload_simple.py --audio {output_file} --session <SESSION_ID>")

if __name__ == "__main__":
    main()
