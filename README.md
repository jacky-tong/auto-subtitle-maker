<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-teal?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Whisper-OpenAI-orange?style=flat-square&logo=openai" alt="Whisper">
  <img src="https://img.shields.io/badge/FFmpeg-required-green?style=flat-square&logo=ffmpeg" alt="FFmpeg">
  <img src="https://img.shields.io/badge/license-MIT-purple?style=flat-square" alt="License">
</p>

<h1 align="center">Zimu 字幕</h1>
<p align="center"><strong>智能视频字幕自动生成与合成工具</strong></p>
<p align="center">上传视频 → 自动识别语音或对齐文稿 → 下载带字幕的视频</p>

<p align="center">
  <sub>作者：<a href="https://github.com/jacky-tong">我的token都去哪了</a></sub>
</p>

---

## Features 功能

<table>
<tr>
<td width="50%">

### 🎙️ 自动语音识别 (Case B)
无需文稿，上传视频即可。基于 **OpenAI Whisper** 深度学习模型，自动提取音轨并生成逐字时间戳。中文识别准确率业界领先，同时支持中英混合场景。

</td>
<td width="50%">

### 📝 文稿强制对齐 (Case A)
上传 `.docx` / `.txt` 文稿，系统通过 **Smith-Waterman 局部对齐算法** 将文案精确映射到视频时间轴。字幕文字严格遵循原稿，适合有现成文案的解说视频、课程录像。

</td>
</tr>
<tr>
<td>

### ✂️ 智能断句
拒绝 "python" 被截断为 "pyth / on"。智能识别英文单词边界、中文标点、自然换气点，确保每条字幕完整可读。

</td>
<td>

### 🎬 一键烧录硬字幕
**黑色文字 + 白色描边**，通过 FFmpeg ASS 滤镜渲染。清晰可读，适配任何视频背景。处理完成后直接下载 MP4 和 SRT 文件。

</td>
</tr>
</table>

---

## Quick Start 快速开始

### 环境要求

- **Python** 3.8+
- **FFmpeg**（需在 PATH 中可用）

```bash
# macOS
brew install ffmpeg

# Windows
winget install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### 安装 & 启动

```bash
# 1. 克隆项目
git clone https://github.com/jacky-tong/auto-subtitle-maker.git
cd auto-subtitle-maker

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

或者 **双击 `启动.bat`**（Windows），自动完成上述步骤并打开浏览器。

浏览器访问 **http://localhost:8000** 即可使用。

首次启动会自动下载 Whisper 模型（tiny 约 72MB，medium 约 1.4GB）。

---

## How It Works 原理

```
上传视频 (+文稿)
      │
      ▼
┌──────────────┐
│ 1. 提取音频   │  FFmpeg → 16kHz 单声道 WAV
└──────┬───────┘
       ▼
┌──────────────┐
│ 2. 语音识别   │  Whisper → 逐词时间戳
└──────┬───────┘
       ▼
  ┌────┴────┐
  │ 有文稿？  │
  └────┬────┘
  Yes  │  No
  ┌────┴────┐
  │ Smith-  │  Whisper
  │Waterman │  直接输出
  └────┬────┘
       ▼
┌──────────────┐
│ 3. 生成字幕   │  智能断句 → SRT 格式
└──────┬───────┘
       ▼
┌──────────────┐
│ 4. 烧录合成   │  FFmpeg subtitles 滤镜
└──────────────┘
       │
       ▼
  带字幕视频.mp4  +  字幕.srt
```

---

## Tech Stack 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 后端框架 | **FastAPI** | HTTP API + 异步任务 |
| 语音识别 | **OpenAI Whisper** | 音频转录 + 逐词时间戳 |
| 强制对齐 | **Smith-Waterman** | 文稿 → 时间轴映射 |
| 视频处理 | **FFmpeg** | 音频提取 + 字幕烧录 |
| 文档解析 | **python-docx** | .docx / .txt 读取 |
| 前端 | **原生 HTML/CSS/JS** | 零依赖单文件 UI |

---

## Configuration 配置

编辑 `config.py`：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `WHISPER_MODEL_SIZE` | `medium` | 模型大小：tiny / base / small / medium / large-v3 |
| `WHISPER_LANGUAGE` | `zh` | 识别语言（99 种可选） |
| `WHISPER_DEVICE` | `cpu` | 推理设备：cpu / cuda |
| `MAX_UPLOAD_SIZE_MB` | `500` | 上传大小上限 |
| `CLEANUP_AGE_HOURS` | `6` | 生成文件过期时间 |

模型选择建议：**tiny** 最快占内存最少（测试用），**medium** 平衡推荐日常，**large-v3** 最准需要大显存 GPU。

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | 上传视频 + 可选文稿 |
| `GET` | `/api/task/{id}` | 查询处理进度 |
| `GET` | `/api/download/video/{id}` | 下载带字幕视频 |
| `GET` | `/api/download/subtitle/{id}` | 下载 SRT 字幕 |
| `DELETE` | `/api/task/{id}` | 删除任务 |

---

## Project Structure 项目结构

```
auto-subtitle-maker/
├── main.py                  # FastAPI 入口
├── config.py                # 全局配置
├── requirements.txt         # Python 依赖
├── 启动.bat                  # Windows 一键启动
├── routers/
│   └── api.py               # HTTP 路由
├── models/
│   ├── task.py              # 任务状态机
│   └── schemas.py           # 数据模型
├── services/
│   ├── pipeline.py          # 处理流水线
│   ├── whisper_service.py   # Whisper 封装
│   ├── aligner.py           # 强制对齐算法 ★
│   ├── subtitle_service.py  # SRT 生成 + 智能断句
│   ├── video_service.py     # FFmpeg 调用
│   ├── doc_parser.py        # 文档解析
│   └── file_manager.py      # 文件清理
├── utils/
│   └── text_utils.py        # 文本处理
├── static/
│   └── index.html           # 前端 UI
└── storage/                 # 上传 & 输出目录
```

---

## License

MIT License — 自由使用、修改、分发。

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/jacky-tong">我的token都去哪了</a></sub>
</p>
