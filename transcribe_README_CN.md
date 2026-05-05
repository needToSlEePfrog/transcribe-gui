# Transcribe GUI

一个本地音频/视频转字幕的图形化工具，基于 [Groq](https://groq.com/) Whisper API + ffmpeg，支持大文件自动分段处理。

## 功能

- **多格式支持**：mp3、mp4、wav、m4a、mkv、webm、avi、mov、flac、ogg 等常见音视频格式
- **自动分段**：超过 20MB 的文件自动切分后逐段转录，绕过 API 上传限制
- **多语言识别**：支持中文、英文、日文、韩文、法文、德文、西班牙文，也可自动检测
- **设置持久化**：API Key、输出目录、语言偏好保存在本地配置文件，下次启动自动加载
- **实时日志**：转录进度实时显示，方便跟踪长文件处理状态
- **纯本地运行**：音频处理在本地完成，仅转录请求发送到 Groq API

## 使用前提

1. **Python 3.7+**
2. **Groq API Key** — 在 [console.groq.com/keys](https://console.groq.com/keys) 免费申请
3. **ffmpeg** — 确保在系统 PATH 中
4. 安装依赖：

```bash
pip install groq
```

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/你的用户名/transcribe-gui.git
cd transcribe-gui

# 安装依赖
pip install groq

# 运行
python transcribe_gui.py
```

## 使用方法

1. 启动程序，填入 Groq API Key（首次填写后点「保存设置」）
2. 选择要转录的音频/视频文件
3. 选择语言（不确定就选「自动检测」）
4. 点击「开始转录」
5. 转录完成后，字幕文本自动保存到输出目录

## 工作原理

```
输入文件 → ffmpeg 提取音频(16kHz mono mp3)
         → 检查大小，超过 20MB 自动分段
         → 逐段调用 Groq Whisper API 转录
         → 合并结果，保存为 .txt 文件
```

## 项目结构

```
transcribe-gui/
├── transcribe_gui.py    # 主程序（单文件）
├── README_CN.md            # 本文件
├── README.md         # English README
└── LICENSE              # MIT License
```

## 许可证

[MIT License](LICENSE)

## 致谢

- [Groq](https://groq.com/) — 提供高速 Whisper 推理 API
- [OpenAI Whisper](https://github.com/openai/whisper) — 语音识别模型
