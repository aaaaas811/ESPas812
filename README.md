# ESPas812

xiaozhi-esp32-server 的二次开发拓展，集成 ESP32 固件、MQTT/UDP 网关、MCP 工具链与工厂演示板支持。

[![Contributors][contributors-shield]][contributors-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<!-- PROJECT LOGO -->
<br />

<p align="center">
  <h3 align="center">ESPas812</h3>
  <p align="center">
    xiaozhi 智能硬件助手 · 服务端增强拓展
    <br />
    <br />
    <a href="https://github.com/78/xiaozhi-esp32"><strong>上游项目 »</strong></a>
    ·
    <a href="./factory_demo">工厂演示板</a>
    ·
    <a href="https://github.com/78/xiaozhi-esp32/issues">报告 Bug</a>
  </p>
</p>

## 目录

- [项目简介](#项目简介)
- [架构概览](#架构概览)
- [上手指南](#上手指南)
  - [环境要求](#环境要求)
  - [安装步骤](#安装步骤)
- [文件目录说明](#文件目录说明)
- [核心模块](#核心模块)
- [部署](#部署)
- [使用到的框架](#使用到的框架)
- [贡献者](#贡献者)
- [版本控制](#版本控制)
- [作者](#作者)
- [鸣谢](#鸣谢)

## 项目简介

本项目是对 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 的二次开发拓展（fork），在原有服务端基础上增加了：

- **MCP 工具链**：MCP Endpoint Server + MCP Calculator Pipe，支持通过 MCP 协议扩展 LLM 工具调用能力
- **MQTT/UDP 网关**：Node.js MQTT 网关，桥接 MQTT/UDP 客户端到 WebSocket 服务端
- **工厂演示板固件**：基于 ESP-IDF 的 ESP32-S3 工厂演示程序，支持多语言、LVGL 图形界面、语音交互
- **一键启动**：`main.py` 统一编排 MCP Endpoint → MCP Pipe → xiaozhi-server 的启动流程

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py (启动器)                        │
│  按顺序启动: MCP Endpoint → MCP Pipe → xiaozhi-server         │
└──────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
   │ MCP Endpoint │  │  MCP Pipe    │  │ xiaozhi-server   │
   │   (:8004)    │  │ (calculator) │  │ (:8000 WS,       │
   │  工具执行服务  │◄─┤  计算器桥接   │  │  :8003 HTTP)     │
   └──────────────┘  └──────────────┘  │ AI 对话服务       │
                                       │ ASR → LLM → TTS   │
                                       └────────┬─────────┘
                                                │
                          ┌─────────────────────┤
                          ▼                     ▼
                 ┌──────────────┐     ┌──────────────────┐
                 │ MQTT Gateway │     │  ESP32 设备        │
                 │  (Node.js)   │     │  (factory_demo)   │
                 │  MQTT+UDP桥接 │     │  WiFi/BLE 连接    │
                 └──────────────┘     └──────────────────┘
```

## 上手指南

#### 环境要求

- **Conda** — 用于管理 Python 环境（`environment.yml` 定义了完整依赖）
- **ESP-IDF** v5.4+ — 编译 ESP32 固件（仅 `factory_demo` 需要）
- **Node.js** ≥ 18 — 运行 MQTT 网关（仅 `xiaozhi-mqtt-gateway` 需要）
- **系统**：Windows / Linux

#### 安装步骤

1. Clone 仓库
   ```sh
   git clone <your-repo-url> ESPas812
   cd ESPas812
   ```

2. 创建 Conda 环境
   ```sh
   conda env create -f environment.yml -p ./env
   ```
   此命令会在 `./env` 目录创建完整的 Python 3.10 运行环境，包含 FFmpeg、ASR/LLM/TTS 等全部依赖。

3. 配置环境变量
   ```sh
   cp xiaozhi-esp32-server/main/xiaozhi-server/.env.example .env
   # 编辑 .env 填入实际值
   ```

4. 配置服务端
   - 编辑 `xiaozhi-esp32-server/main/xiaozhi-server/config.yaml` 中的 LLM/ASR/TTS 模块选择与 API Key
   - （可选）编辑 `mcp-endpoint-server/mcp-endpoint-server.cfg` 配置 MCP 端点

5. 启动
   ```sh
   env/python main.py
   ```
   或手动分步启动：
   ```sh
   conda activate ./env
   cd xiaozhi-esp32-server/main/xiaozhi-server
   python app.py
   ```

## 文件目录说明

```
ESPas812/
├── main.py                          # 一键启动脚本（MCP Endpoint → Pipe → Server）
├── environment.yml                  # Conda 完整环境定义
├── LICENSE                          # MIT 开源协议
├── CLAUDE.md                        # AI 协作开发行为规范
├── .gitignore                       # Git 忽略规则（含密钥/证书/构建产物）
│
├── xiaozhi-esp32-server/            # 核心 AI 服务端（基于 xiaozhi-esp32）
│   └── main/xiaozhi-server/
│       ├── app.py                   # 服务端入口（WebSocket :8000 + HTTP :8003）
│       ├── config.yaml              # 主配置文件
│       ├── core/                    # 核心逻辑
│       │   ├── connection.py        # WebSocket 连接处理器（对话管线）
│       │   ├── websocket_server.py  # WebSocket 服务器
│       │   ├── http_server.py       # HTTP 服务器（OTA + Vision）
│       │   ├── handle/              # 消息处理（hello/listen/abort/iot/mcp）
│       │   ├── providers/           # 算法提供者
│       │   │   ├── asr/             # 语音识别（Aliyun/Baidu/Doubao/FunASR/OpenAI...）
│       │   │   ├── llm/             # 大语言模型（DeepSeek/ChatGLM/Doubao/Gemini/Ollama...）
│       │   │   ├── tts/             # 文本转语音（Edge/Doubao/CosyVoice/GPT-SoVITS...）
│       │   │   ├── memory/          # 记忆系统（mem0ai/local）
│       │   │   ├── intent/          # 意图识别
│       │   │   └── tools/           # MCP 工具客户端
│       │   └── utils/               # 工具函数（音频/VAD/对话）
│       ├── config/                  # 配置加载、日志、管理API
│       ├── plugins_func/            # 功能插件（天气/新闻/音乐/HomeAssistant）
│       ├── models/                  # 本地模型文件（SenseVoice/VAD）
│       └── data/                    # 运行时数据
│
├── mcp-endpoint-server/             # MCP 端点服务（:8004）
│   ├── main.py                      # FastAPI 入口
│   ├── src/                         # 工具执行引擎
│   ├── data/                        # 工具定义与数据
│   └── mcp-endpoint-server.cfg      # 端点配置
│
├── mcp-calculator/                  # MCP 计算器管道
│   ├── mcp_pipe.py                  # 管道主程序
│   ├── calculator.py                # 计算器工具实现
│   └── mcp_config.json              # MCP 配置
│
├── xiaozhi-mqtt-gateway/            # MQTT/UDP 网关 (Node.js)
│   ├── app.js                       # Express + MQTT 服务
│   ├── mqtt-protocol.js             # MQTT 协议适配
│   └── config/                      # 网关配置
│
├── factory_demo/                    # ESP32-S3 工厂演示固件
│   ├── main/                        # 主程序代码
│   ├── boards/                      # 板级支持（ESP32-S3）
│   ├── common_components/           # 通用组件
│   └── CMakeLists.txt               # ESP-IDF 构建定义
│
└── mcp-bme690/                      # BME690 环境传感器 MCP 插件（WIP）
```

## 核心模块

### xiaozhi-esp32-server — AI 对话服务

ESP32 智能设备的服务端核心，提供完整的语音/文本对话管线：

| 组件 | 功能 | 可选后端 |
|------|------|----------|
| VAD | 语音活动检测 | SileroVAD |
| ASR | 语音识别 | Aliyun、Baidu、Doubao、FunASR、OpenAI Whisper、Sherpa、Vosk |
| LLM | 大语言模型 | DeepSeek、ChatGLM、Doubao、Ali、Gemini、Ollama、Dify、Coze |
| TTS | 文本转语音 | Edge TTS、Doubao、CosyVoice、GPT-SoVITS、FishSpeech、Minimax |
| Memory | 对话记忆 | mem0ai、local |
| Intent | 意图识别 | LLM-based、function_call |

**通信协议：**
- **WebSocket** `ws://host:8000/xiaozhi/v1/` — 主通信通道（JSON 指令 + 二进制 Opus 音频）
- **HTTP** `http://host:8003/xiaozhi/ota/` — OTA 固件配置下发
- **HTTP** `http://host:8003/mcp/vision/explain` — 视觉分析

### MCP Endpoint Server — 工具执行服务

基于 FastAPI 的 MCP（Model Context Protocol）端点服务，运行于 `:8004`，提供：
- 外部工具注册与调度执行
- MCP 协议兼容的 tool/resource 接口
- Docker 容器化部署支持

### MCP Calculator Pipe — 计算器桥接

将 MCP 计算器工具接入 xiaozhi-server 的工具调用管线，实现：
- LLM 驱动的数学计算与表达式求值
- MCP tool → xiaozhi-server function_call 的连接桥

### MQTT Gateway — MQTT/UDP 桥接

Node.js 网关服务，桥接 MQTT/UDP 客户端到 xiaozhi-server：
- MQTT 客户端管理（QoS、保活）
- UDP 音频流传输
- MQTT → WebSocket 协议转换

### Factory Demo — ESP32 工厂演示固件

基于 ESP-IDF 的 ESP32-S3 工厂演示程序：
- LVGL 图形界面（多语言支持）
- WiFi / BLE 连接管理
- 语音唤醒与交互
- 硬件板级支持（SPI LCD、I2S 音频、触摸屏）

## 部署

### 普通运行

```sh
env/python main.py
```
此命令自动启动 MCP Endpoint Server → MCP Pipe → xiaozhi-server。

### 仅启动核心服务

```sh
conda activate ./env
cd xiaozhi-esp32-server/main/xiaozhi-server
python app.py
```

### Docker 部署（MCP Endpoint Server）

```sh
cd mcp-endpoint-server
docker compose up -d
```

### ESP32 固件编译

```sh
cd factory_demo
idf.py set-target esp32s3
idf.py build
idf.py -p <PORT> flash
```

## 使用到的框架

- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) — 上游 ESP32 AI 对话项目
- [ESP-IDF](https://github.com/espressif/esp-idf) — ESP32 官方开发框架
- [LVGL](https://lvgl.io) — 嵌入式图形库
- [FastAPI](https://fastapi.tiangolo.com) — MCP Endpoint 服务
- [websockets](https://github.com/python-websockets/websockets) — Python WebSocket 框架
- [MCP](https://modelcontextprotocol.io) — Model Context Protocol
- [Node.js](https://nodejs.org) — MQTT 网关运行时
- [Conda](https://docs.conda.io) — 环境与依赖管理

## 贡献者

本项目为个人项目，目前由 as811 维护。

#### 如何参与开源项目

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 版本控制

该项目使用 Git 进行版本管理。

## 作者

**as811** (aaaaas811)

## 版权说明

该项目签署了 MIT 授权许可，详情请参阅 [LICENSE](./LICENSE)。
基于 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 二次开发。

## 鸣谢

- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) — 优秀的 ESP32 AI 对话项目
- [xiaozhi-esp32-server](https://github.com/78/xiaozhi-esp32) — 服务端核心实现
- [ESP-IDF](https://github.com/espressif/esp-idf) — ESP32 官方开发框架
- [Best README Template](https://github.com/shaojintian/Best_README_template) — README 模板参考

<!-- links -->
[contributors-shield]: https://img.shields.io/github/contributors/aaaaas811/ESPas812.svg?style=flat-square
[contributors-url]: https://github.com/aaaaas811/ESPas812/graphs/contributors
[issues-shield]: https://img.shields.io/github/issues/aaaaas811/ESPas812.svg?style=flat-square
[issues-url]: https://github.com/aaaaas811/ESPas812/issues
[license-shield]: https://img.shields.io/github/license/aaaaas811/ESPas812.svg?style=flat-square
[license-url]: https://github.com/aaaaas811/ESPas812/blob/main/LICENSE
