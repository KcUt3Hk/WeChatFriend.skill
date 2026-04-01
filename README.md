# 微信好友.skill

本项目基于 [colleague-skill](https://github.com/titanwings/colleague-skill) 的思想，结合 [WeChatMsgGrabber](https://github.com/KcUt3Hk/WeChatMsgGrabber) 抓取的本地微信聊天记录，帮助你使用大语言模型生成一个高度还原的“微信好友”数字分身。

将冰冷的离别化为温暖的 Skill，复刻你最熟悉的聊天默契。

## 🌟 核心特性
- **一键提取与清洗**：强力正则引擎自动剔除微信导出记录中的系统消息、撤回提示、`[图片]`、`[表情]`、`[视频号]` 等噪点，保证高信息密度的输入。
- **深度人格侧写**：自动抽取历史聊天样本交由 LLM 进行分析，提炼好友的**性格标签、长短句偏好、口头禅、标点符号习惯以及专属表情包**。
- **高压缩率的结构化存储**：告别几万行的全量聊天记录。最新版将生成的数字灵魂压缩为一个十几 KB 的 `.skill.json` 文件，仅保存结构化画像、5组经典 QA 范本和最近 30 条的短期记忆。
- **微信风格桌面模拟器**：开箱即用的轻量级桌面 UI (`chat_ui.py`)，高度还原微信交互体验。
- **极致的流式响应**：模拟器后端采用 `yield` 打字机流式输出 (Streaming)，配合极简的滑动窗口上下文（仅携带最近 3 轮历史），**首字响应 (TTFB) 压缩至 1 秒以内**！
- **多模型平台支持**：原生支持 OpenAI 兼容接口，并特别针对 OFOX 平台 (`gpt-5.4-mini`) 和硅基流动 (`DeepSeek-V3.2`) 进行了网络和解析优化，彻底告别超时断连。

## 📁 项目结构
```
微信好友.skill/
├── README.md             # 项目说明文档
├── SKILL.md              # 旧版兼容入口
├── prompts/              # (旧版) 分析与生成用的 Prompt 模板
└── scripts/
    ├── wechat_parser.py  # 微信聊天记录预处理脚本
    ├── skill_generator.py# 全新 JSON 格式 Skill 生成器
    └── chat_ui.py        # 微信风格流式桌面模拟器
```

## ⚙️ 环境要求
- Python 3.8+
- 安装依赖：
  ```bash
  pip install -r requirements.txt
  # 或者手动安装
  pip install requests pyyaml python-dotenv openai pillow httpx
  ```

## 🚀 使用指南

### 1. 准备聊天记录数据
使用 [WeChatMsgGrabber](https://github.com/KcUt3Hk/WeChatMsgGrabber) 工具抓取你与目标好友的聊天记录，导出为 JSON 或 CSV 格式（如 `chat_with_friend.json`）。

### 2. 数据预处理
将原始数据转化为纯文本 Markdown 格式：
```bash
python scripts/wechat_parser.py -i /path/to/chat_with_friend.json -o ./chat_data.md -m "我" -f "好友名称"
```

### 3. 生成专属数字灵魂 (.skill.json)
使用 `skill_generator.py` 对预处理后的文本进行深度清洗和人格侧写：
```bash
python scripts/skill_generator.py -i ./chat_data.md -f "老李" -o "老李.skill.json"
```
> **注：** 生成过程需要调用 LLM，请确保已配置下文提到的 `.env` API 密钥。执行完毕后，你会得到一个包含好友核心性格、语调和短期记忆的精简 JSON 文件。

### 4. 桌面版“微信”对线 (模拟器)
我们提供了一个高度还原的 Tkinter 桌面聊天窗口，支持流式渲染和实时“对方正在输入...”状态。

**配置大模型 API 密钥：**
在项目根目录下创建一个 `.env` 文件，并写入您的配置：

```env
# OFOX 配置示例 (推荐，首字响应极快，不易超时)
LLM_PROVIDER=ofox
OFOX_API_KEY="sk-替换为你的真实_API_KEY"
OFOX_MODEL="openai/gpt-5.4-mini"
OFOX_BASE_URL="https://api.ofox.ai/v1"

# 硅基流动 (SiliconFlow) 配置示例
SILICONFLOW_API_KEY="sk-替换为你的真实_API_KEY"
SILICONFLOW_MODEL="Pro/deepseek-ai/DeepSeek-V3.2"
SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
```

**启动模拟器：**
```bash
python scripts/chat_ui.py
```
启动后，点击左上角菜单 **[文件] -> [加载 Skill]**，选择刚才生成的 `老李.skill.json`。加载成功后，即可开始丝滑的流式对话！

## 💡 模拟器技术内幕
- **滑动窗口机制**：为了节省 Token 和提高速度，每次点击发送时，程序只会将 `System Prompt` (由 `.skill.json` 动态拼接) 和**最近 3 轮（6条）**对话历史发送给大模型。
- **流式解析防崩**：针对带有思考过程（如 DeepSeek `<thinking>`）的模型，模拟器内置了多层解析防护，避免了空 Chunk 引发的崩溃，并能在控制台打印详细的网络堆栈日志供排错。

## 🙏 致谢
- [colleague-skill](https://github.com/titanwings/colleague-skill) 提供了最初的“数字生命”灵感。
- [WeChatMsgGrabber](https://github.com/KcUt3Hk/WeChatMsgGrabber) 提供了优秀的本地微信数据抓取方案。
