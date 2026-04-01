# 微信好友.skill

本项目基于 [colleague-skill](https://github.com/titanwings/colleague-skill) 的思想，结合 [WeChatMsgGrabber](https://github.com/KcUt3Hk/WeChatMsgGrabber) 抓取的本地微信聊天记录，帮助你使用大语言模型（如 Claude）生成一个高度还原的“微信好友”数字分身 Skill。

将冰冷的离别化为温暖的 Skill，复刻你最熟悉的聊天默契。

## 核心特性
- **数据无缝对接**：配套 Python 脚本 `wechat_parser.py`，一键将 WeChatMsgGrabber 导出的 JSON/CSV 转化为大模型友好的 Markdown 纯文本。
- **深度画像剖析**：不仅提取性格标签，更深入挖掘口头禅、标点习惯、表情包使用频率、长短句偏好等微信特有“网感”。
- **专属记忆留存**：自动提取你们之间的专属暗号、黑历史、共同的人际关系图谱。
- **AgentSkills 标准**：生成的 `.skill` 文件完美兼容 AgentSkills 标准，可直接在 Claude Code 等工具中调用。

## 项目结构
```
微信好友.skill/
├── README.md             # 项目说明文档
├── SKILL.md              # Skill 主入口，Claude 执行入口
├── prompts/              # 分析与生成用的 Prompt 模板
│   ├── intake.md         # 引导用户输入基础信息
│   ├── persona_analyzer.md # 性格与表达习惯分析
│   ├── knowledge_analyzer.md # 记忆与人际图谱分析
│   └── skill_builder.md  # 最终 Skill 生成指令
└── scripts/
    └── wechat_parser.py  # 微信聊天记录预处理脚本
```

## 环境要求
- 脚本依赖 Python 3.6 及以上版本。
- 本项目不包含第三方 Python 库，仅使用标准库。

## 使用指南

### 1. 准备聊天记录数据
使用 [WeChatMsgGrabber](https://github.com/KcUt3Hk/WeChatMsgGrabber) 工具抓取你与目标好友的聊天记录，导出为 JSON 或 CSV 格式（如 `chat_with_friend.json`）。

### 2. 数据预处理
使用提供的 Python 脚本将原始数据转化为模型更易分析的纯文本 Markdown 格式。
请确保在终端中运行（Mac系统下请使用 Python3）：

```bash
python3 scripts/wechat_parser.py -i /path/to/chat_with_friend.json -o ./chat_data.md -m "我" -f "好友名称"
```

### 3. 安装与运行 Skill 生成器
确保你已经安装了 Claude Code，然后将本仓库作为 skill 引入并运行：

```bash
# 进入你的工作目录或全局目录
cd /你的/项目/路径
# 运行 skill
claude /create-wechat-friend
```
*(注意：请根据你的 Agent 工具链的实际调用方式执行。本项目的 `SKILL.md` 即为入口文件)*

随后，AI 将根据 `intake.md` 向你提问。你需要：
1. 提供好友的名字和基本设定。
2. 将第2步生成的 `chat_data.md` 路径或内容提供给 AI。
3. 等待 AI 依次执行画像提取、记忆提取，并最终在你的本地生成 `[好友名称].skill`。

### 4. 召唤你的数字好友（通过 Agent 工具）
生成完毕后，你就可以用生成的专属 Skill 来和“他/她”聊天了，他/她会用你最熟悉的语气、抛出你们才懂的梗来回复你！
在支持 AgentSkills 标准的工具中加载即可。

### 5. 桌面版“微信”对话 UI (新增)
如果你不想在命令行里测试，我们提供了一个开箱即用的轻量级桌面聊天窗口，可以直接加载 `.skill.md` 并模拟微信聊天界面！

**安装依赖：**
```bash
pip install requests pyyaml python-dotenv openai pillow
```

**配置大模型 API 密钥：**
我们推荐使用环境配置文件来管理密钥。在项目根目录下创建一个 `.env` 文件（或直接使用已有的），并写入配置：

```env
# 硅基流动 (SiliconFlow) 配置示例
SILICONFLOW_API_KEY="sk-替换为你的真实_API_KEY"
SILICONFLOW_MODEL="Pro/deepseek-ai/DeepSeek-V3.2"
SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"

# 你也可以使用 OpenAI 兼容配置
# OPENAI_API_KEY="你的_API_KEY"
# OPENAI_BASE_URL="https://api.openai.com/v1"
# OPENAI_MODEL_NAME="gpt-4o"
```

**启动桌面聊天程序：**
```bash
python3 scripts/chat_ui.py
```
启动后，点击左上角菜单 **[文件] -> [加载 Skill (.md)]**，选择生成的 `[好友名字].skill.md`。加载成功后，即可开始丝滑的“微信对线”！

## 致谢
- [colleague-skill](https://github.com/titanwings/colleague-skill) 提供了最初的“数字生命”灵感。
- [WeChatMsgGrabber](https://github.com/KcUt3Hk/WeChatMsgGrabber) 提供了优秀的本地微信数据抓取方案。
