#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import yaml
import re
import os
import json
import traceback
from dotenv import load_dotenv
from openai import OpenAI
import httpx

try:
    from PIL import Image, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 加载当前目录或项目根目录下的 .env 文件
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

class DigitalFriendChatApp:
    def __init__(self, root):
        """
        初始化微信风格聊天应用。
        """
        self.root = root
        self.root.title("微信好友数字分身 - 未加载 Skill")
        self.root.geometry("450x700")
        self.root.configure(bg="#F5F5F5")
        
        # 内部状态
        self.system_prompt = ""
        self.friend_name = "数字好友"
        self.chat_history = []
        
        # 头像图片缓存 (防止被垃圾回收)
        self._avatar_images = {}
        # 气泡图片缓存
        self._bubble_images = {}
        
        # 优先读取 OFOX 的配置，如果没有则回退读取 SILICONFLOW 或 OPENAI 的配置
        self.api_key = os.environ.get("OFOX_API_KEY") or os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OFOX_BASE_URL") or os.environ.get("SILICONFLOW_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model_name = os.environ.get("OFOX_MODEL") or os.environ.get("SILICONFLOW_MODEL") or os.environ.get("OPENAI_MODEL_NAME", "gpt-4o")
        
        # 初始化 OpenAI Client
        # 增加 timeout=300.0 以避免在等待思考时间过长时超时断开
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=300.0,
                max_retries=3 # 允许 SDK 在遇到临时网络错误时自动重试
            )
        
        self.setup_ui()
        self.check_api_key()

    def check_api_key(self):
        """
        检查是否配置了 API Key，如果没有则提示用户。
        """
        if not self.api_key:
            messagebox.showwarning(
                "缺少 API Key", 
                "未检测到 API Key 配置（如 OFOX_API_KEY 或 SILICONFLOW_API_KEY）。\n\n"
                "请在项目根目录下的 .env 文件中设置，例如：\n"
                "OFOX_API_KEY='sk-xxx'\n"
                "OFOX_MODEL='openai/gpt-5.4-mini'\n"
                "OFOX_BASE_URL='https://api.ofox.ai/v1'"
            )

    def setup_ui(self):
        """
        构建类似微信的简单 UI 界面。
        """
        # 顶部菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="加载 Skill (.md)", command=self.load_skill_file)
        file_menu.add_separator()
        file_menu.add_command(label="清空聊天记录", command=self.clear_chat)
        
        # 聊天记录显示区 (使用 Canvas + Frame)
        self.chat_frame = tk.Frame(self.root, bg="#EDEDED")
        self.chat_frame.pack(expand=True, fill=tk.BOTH)
        
        # 移除滚动条占位，使用隐藏式的鼠标滚轮绑定
        self.chat_canvas = tk.Canvas(self.chat_frame, bg="#EDEDED", highlightthickness=0, bd=0)
        self.scrollable_frame = tk.Frame(self.chat_canvas, bg="#EDEDED")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(
                scrollregion=self.chat_canvas.bbox("all")
            )
        )
        
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # 绑定 Canvas 尺寸变化以自适应内部 Frame 宽度
        self.chat_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # 绑定鼠标滚轮事件 (Mac 和 Windows/Linux)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.chat_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.chat_canvas.bind_all("<Button-5>", self._on_mousewheel)
        
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        # 底部输入区容器
        input_container = tk.Frame(self.root, bg="#F5F5F5", bd=0)
        input_container.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 分隔线
        separator = tk.Frame(input_container, bg="#D6D6D6", height=1)
        separator.pack(fill=tk.X, side=tk.TOP)
        
        input_inner_frame = tk.Frame(input_container, bg="#F5F5F5")
        input_inner_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # 输入框 (取消黑边，强制指定前景色为黑色，插入光标也为黑色)
        self.input_text = tk.Text(input_inner_frame, height=4, font=("Arial", 14), 
                                  highlightthickness=0, bd=0, bg="#F5F5F5", fg="#000000", insertbackground="#000000")
        self.input_text.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.input_text.bind("<Return>", self.handle_return)
        
        # 发送按钮
        self.send_btn = tk.Button(input_inner_frame, text="发送", width=8, height=2, command=self.send_message, bg="#07C160", fg="black", highlightbackground="#F5F5F5")
        self.send_btn.pack(side=tk.RIGHT, anchor="s", padx=(10, 0))
        
        self.append_system_msg("欢迎！请从菜单 [文件 -> 加载 Skill] 载入好友的 .skill.md 文件。")

    def _on_canvas_configure(self, event):
        """当 Canvas 改变大小时，调整内部 scrollable_frame 的宽度"""
        self.chat_canvas.itemconfig(self.chat_window, width=event.width)

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        # Mac 系统的 event.delta 需要特别处理，通常比较小
        # Windows 系统的 event.delta 通常是 120 的倍数
        # Linux 系统使用 Button-4 和 Button-5
        if event.num == 4 or event.delta > 0:
            self.chat_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.chat_canvas.yview_scroll(1, "units")

    def load_skill_file(self):
        """
        选择并解析 .skill.md 或 .skill.json 文件，提取/拼接系统提示词。
        """
        file_path = filedialog.askopenfilename(
            title="选择 Skill 文件",
            filetypes=(("JSON Skill", "*.json"), ("Markdown files", "*.md"), ("All files", "*.*"))
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if file_path.endswith('.json'):
                # V4.0 JSON 格式结构化 Skill
                skill_data = json.loads(content)
                metadata = skill_data.get("metadata", {})
                self.friend_name = metadata.get("source_friend", "数字好友")
                
                persona = skill_data.get("persona", {})
                language_habits = persona.get("language_habits", {})
                knowledge_base = skill_data.get("knowledge_base", {})
                chat_samples = skill_data.get("chat_samples", [])
                recent_context = skill_data.get("recent_context", [])
                
                # 将 chat_samples 格式化为对话字符串
                formatted_samples = ""
                for sample in chat_samples:
                    formatted_samples += f"用户: {sample.get('q', '')}\n{self.friend_name}: {sample.get('a', '')}\n\n"
                    
                formatted_context = "\n".join(recent_context)
                
                # 动态组装 System Prompt
                self.system_prompt = f"""
# 角色设定
{persona.get('role_description', f'你现在是{self.friend_name}，请1:1模仿该人物的语气进行对话。')}

核心性格特征：{', '.join(persona.get('core_traits', []))}

# 语言与回复习惯
- 句子长度偏好：{language_habits.get('sentence_length', '')}
- 标点符号偏好：{language_habits.get('punctuation_preference', '')}
- 常用口头禅：{', '.join(language_habits.get('catchphrases', []))}
- 常用表情包/符号：{', '.join(language_habits.get('emoji_usage', []))}

# 共同记忆与知识库
- 经常聊的话题：{', '.join(knowledge_base.get('top_topics', []))}
- 关键记忆：{knowledge_base.get('key_memories', '')}

# 行为要求
- 必须遵守微信聊天的口语化、碎片化习惯。
- 严禁以 AI 助手身份回答，不要解释你在扮演谁。
- 绝不要使用书面语，严格遵循上述的标点符号和表情包偏好。
- 如果需要分段表达多层意思，请使用换行（回车）。
- 在回复前，请在 <thinking></thinking> 标签内进行内心独白，思考“我作为一个具有上述性格和价值观的人，平时是怎么回复这句话的？”。

# 典型对话参考 (仅供模仿语感，不要生硬照搬内容)
{formatted_samples}

# 最近的真实对话上下文 (短期记忆，请接续语境)
{formatted_context}
"""
            else:
                # V2.0 兼容旧版的 Markdown 格式
                frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
                if frontmatter_match:
                    yaml_content = frontmatter_match.group(1)
                    try:
                        metadata = yaml.safe_load(yaml_content)
                        if 'description' in metadata:
                            desc = metadata['description']
                            name_match = re.search(r'：(.*)$', desc)
                            if name_match:
                                self.friend_name = name_match.group(1).strip()
                            else:
                                self.friend_name = desc
                    except yaml.YAMLError:
                        pass
                
                self.system_prompt = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL).strip()
            
            self.root.title(f"微信聊天 - {self.friend_name}")
            self.clear_chat()
            self.append_system_msg(f"已成功加载 [{self.friend_name}] 的数字灵魂。开始聊天吧！")
            
            self.chat_history = [
                {"role": "system", "content": self.system_prompt}
            ]
            
        except Exception as e:
            messagebox.showerror("加载失败", f"无法读取文件: {e}")

    def clear_chat(self):
        """清空界面和对话历史。"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        if self.system_prompt:
            self.chat_history = [{"role": "system", "content": self.system_prompt}]
        else:
            self.chat_history = []

    def handle_return(self, event):
        """处理回车键发送消息（Shift+回车换行）。"""
        if not event.state & 0x0001:  # 如果没有按 Shift
            self.send_message()
            return 'break'  # 阻止默认换行行为

    def _scroll_to_bottom(self):
        """滚动到底部"""
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _create_round_rect_image(self, size, radius, color_bg, text, text_color):
        """生成一个带文字的圆角矩形图片作为默认头像"""
        if not HAS_PIL:
            return None
            
        img = Image.new("RGBA", size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=color_bg)
        
        # 简单居中文字（由于没有外部字体文件，使用默认字体可能比较小，这里只做最基础实现）
        # 更好的做法是依赖 tkinter 本身的机制，但为了统一，如果用图就用到底
        # 这里为了稳定，我们干脆就不在图里画字了，而是让没有图片时直接用 Label 渲染
        return ImageTk.PhotoImage(img)

    def _create_bubble_image(self, width, height, radius, color_bg, is_me):
        """生成一个带有小尖角的圆角气泡图片"""
        if not HAS_PIL:
            return None
            
        # 防止尺寸过小报错
        width = max(width, 20)
        height = max(height, 20)
            
        # 缓存键
        cache_key = f"{width}_{height}_{radius}_{color_bg}_{is_me}"
        if cache_key in self._bubble_images:
            return self._bubble_images[cache_key]
            
        # 额外加一点宽度给尖角 (10px)
        img = Image.new("RGBA", (width + 10, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 气泡主体
        if is_me:
            # 我：尖角在右
            draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=color_bg)
            # 画尖角 (多边形)
            triangle_points = [
                (width - 2, 15),  # 内部上面一点
                (width + 8, 20),  # 尖尖
                (width - 2, 25)   # 内部下面一点
            ]
            draw.polygon(triangle_points, fill=color_bg)
        else:
            # 对方：尖角在左
            draw.rounded_rectangle((10, 0, width + 10, height), radius=radius, fill=color_bg)
            triangle_points = [
                (12, 15),
                (2, 20),
                (12, 25)
            ]
            draw.polygon(triangle_points, fill=color_bg)
            
        photo = ImageTk.PhotoImage(img)
        self._bubble_images[cache_key] = photo
        return photo

    def get_avatar(self, sender_type):
        """获取头像图片（如果没有真实的图片，就返回 None，由调用方用 Label 渲染字）"""
        if not HAS_PIL:
            return None
            
        if sender_type in self._avatar_images:
            return self._avatar_images[sender_type]
            
        # 尝试读取本地头像文件
        # 约定：如果是用户，找 assets/me.jpg；如果是好友，找 assets/friend.jpg
        # 这里为了通用性，我们直接画个纯色圆角方块作为占位图
        size = (40, 40)
        radius = 8
        color_bg = "#95EC69" if sender_type == "me" else "#FFFFFF"
        
        try:
            img = Image.new("RGBA", size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=color_bg)
            photo = ImageTk.PhotoImage(img)
            self._avatar_images[sender_type] = photo
            return photo
        except Exception:
            return None
        """滚动到底部"""
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def append_system_msg(self, text):
        """在界面插入居中的系统提示。"""
        container = tk.Frame(self.scrollable_frame, bg="#EDEDED")
        container.pack(fill=tk.X, pady=15)
        
        lbl = tk.Label(container, text=text, bg="#DADADA", fg="#FFFFFF", font=("Arial", 11), padx=8, pady=4)
        lbl.pack(anchor="center")
        self.root.after(10, self._scroll_to_bottom)

    def append_chat_bubble(self, sender_type, text):
        """在界面插入带头像的气泡状聊天消息，极度还原微信样式。"""
        container = tk.Frame(self.scrollable_frame, bg="#F5F5F5")
        container.pack(fill=tk.X, pady=6, padx=12)
        
        max_bubble_width = int(self.root.winfo_width() * 0.65)
        if max_bubble_width < 200:
            max_bubble_width = 240
            
        bubble_bg = "#95EC69" if sender_type == "me" else "#FFFFFF"
        bubble_fg = "#000000"
        
        # 计算文字所需的宽高 (粗略估计，供背景图使用)
        # Arial 14pt，大概中文字符宽14px，高20px
        # 但因为是流式，可能需要动态调整大小。由于 Tkinter 不支持动态拉伸背景图
        # 我们这里做个折中：
        # 如果安装了 Pillow，且不是在 "思考中" 流式更新阶段（初始或者一次性发送完毕时）
        # 我们就不画三角图片了，而是用之前的方法，但优化了三角的字符。
        # 截图中，微信其实也是通过极其圆润的边框+贴合度极高的小三角实现的。
        # 这里为了稳定性和流式更新的丝滑，我们继续使用组合 Label 方案，但调整了间距和对齐方式，让它们严丝合缝。
        
        if sender_type == "me":
            # --- 我（靠右排版） ---
            photo = self.get_avatar("me")
            if photo:
                avatar_lbl = tk.Label(container, image=photo, bg="#F5F5F5")
            else:
                avatar_lbl = tk.Label(container, text="我", bg="#576B95", fg="white", font=("Arial", 12, "bold"), width=3, height=1)
            avatar_lbl.pack(side=tk.RIGHT, anchor="n", padx=(8, 0))
            
            # 画一个极简的小三角 (利用特殊的 Unicode 三角字符)
            triangle = tk.Label(container, text="▶", fg=bubble_bg, bg="#F5F5F5", font=("Arial", 10), bd=0, padx=0, pady=0)
            triangle.pack(side=tk.RIGHT, anchor="n", pady=14, padx=0)
            
            # 气泡内容
            bubble = tk.Label(container, text=text, bg=bubble_bg, fg=bubble_fg, font=("Arial", 14), 
                              padx=14, pady=10, justify=tk.LEFT, wraplength=max_bubble_width, relief="flat", bd=0)
            bubble.pack(side=tk.RIGHT, anchor="n")
        else:
            # --- 对方（靠左排版） ---
            photo = self.get_avatar("friend")
            if photo:
                avatar_lbl = tk.Label(container, image=photo, bg="#F5F5F5")
            else:
                avatar_char = self.friend_name[0] if self.friend_name else "友"
                avatar_lbl = tk.Label(container, text=avatar_char, bg="#E2E2E2", fg="#333333", font=("Arial", 12, "bold"), width=3, height=1)
            avatar_lbl.pack(side=tk.LEFT, anchor="n", padx=(0, 8))
            
            # 气泡尖角
            triangle = tk.Label(container, text="◀", fg=bubble_bg, bg="#F5F5F5", font=("Arial", 10), bd=0, padx=0, pady=0)
            triangle.pack(side=tk.LEFT, anchor="n", pady=14, padx=0)
            
            # 气泡内容
            bubble = tk.Label(container, text=text, bg=bubble_bg, fg=bubble_fg, font=("Arial", 14), 
                              padx=14, pady=10, justify=tk.LEFT, wraplength=max_bubble_width, relief="flat", bd=0)
            bubble.pack(side=tk.LEFT, anchor="n")
            
        self.root.after(10, self._scroll_to_bottom)
        return bubble

    def send_message(self):
        """处理发送逻辑。"""
        user_text = self.input_text.get(1.0, tk.END).strip()
        if not user_text:
            return
            
        if not self.system_prompt:
            messagebox.showwarning("提示", "请先加载 Skill 文件！")
            return
            
        if not self.api_key:
            messagebox.showwarning("提示", "未配置 API Key！")
            return

        self.input_text.delete(1.0, tk.END)
        
        # 渲染我的消息
        self.append_chat_bubble("me", user_text)
        self.chat_history.append({"role": "user", "content": user_text})
        
        # --- 滑动窗口机制 ---
        # 仅保留 System Prompt 和最近的 3 轮对话（6条消息），确保 Token 消耗降至最低
        # 索引 0 永远是 system prompt
        MAX_HISTORY_MESSAGES = 6
        if len(self.chat_history) > MAX_HISTORY_MESSAGES + 1:
            self.chat_history = [self.chat_history[0]] + self.chat_history[-MAX_HISTORY_MESSAGES:]
            
        # 禁用发送按钮
        self.send_btn.config(state=tk.DISABLED, text="发送中")
        
        # 将窗口标题修改为“对方正在输入...”
        self.root.title(f"微信聊天 - {self.friend_name} (对方正在输入...)")
        
        # 启动线程调用 API (不再预先创建空白气泡)
        threading.Thread(target=self.call_llm_api, daemon=True).start()

    def get_streaming_response(self):
        """
        后端推理逻辑：通过 yield 实现流式推送
        """
        print("\n[请求发送] 正在调用 LLM API，模型:", self.model_name)
        response_stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.chat_history,
            temperature=0.7,
            max_tokens=800,
            stream=True
        )
        
        print("[流式响应开始] ", end="", flush=True)
        for chunk in response_stream:
            # 安全地提取内容，防止返回空 choices 或没有 content 的 chunk
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    print(delta.content, end="", flush=True)
                    yield delta.content
        print("\n[流式响应结束]\n")

    def call_llm_api(self):
        """
        处理前端渲染的线程函数，调用后端的流式生成器
        """
        if not self.client:
            self.root.after(0, lambda: self.append_system_msg("[错误] API 客户端未初始化，请检查 API Key。"))
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL, text="发送"))
            return
            
        try:
            full_reply = ""
            
            # 使用提取的流式生成器
            for content_chunk in self.get_streaming_response():
                full_reply += content_chunk
                
                # 处理流式的显示逻辑
                if "<thinking>" in full_reply and "</thinking>" not in full_reply:
                    # 正在思考，只保持按钮和标题提示
                    self.root.after(0, lambda: self.send_btn.config(text="正在思考..."))
                else:
                    # 思考结束或开始产生实际内容，提取真实的回复内容
                    display_text = re.sub(r'<thinking>.*?</thinking>', '', full_reply, flags=re.DOTALL).strip()
                    if display_text:
                        # 动态组装提示，并提示正在输入
                        self.root.after(0, lambda: self.send_btn.config(text="正在输入..."))
                        
                        # 当第一个真实字符出现时，我们在主线程创建一个气泡
                        if not hasattr(self, '_current_stream_bubble') or self._current_stream_bubble is None:
                            # 跨线程调用一个辅助方法来创建和保存气泡引用
                            self.root.after(0, self._create_empty_bubble_for_stream)
                            # 短暂休眠让主线程有时间创建组件
                            import time
                            time.sleep(0.05)
                        
                        # 如果气泡已经创建，则逐字/逐词更新它的内容
                        if hasattr(self, '_current_stream_bubble') and self._current_stream_bubble is not None:
                            self.root.after(0, lambda t=display_text: self._update_stream_bubble(t))
                        
            # 最终获取完整回复后加入历史记录
            self.chat_history.append({"role": "assistant", "content": full_reply})
            
            # 清理当前流式气泡的引用
            self._current_stream_bubble = None
            
        except Exception as e:
            print("\n=== [网络/执行错误详情] ===")
            traceback.print_exc()
            print("==========================\n")
            error_msg = f"[网络错误] {str(e)}"
            self.root.after(0, lambda: self.append_system_msg(error_msg))
        finally:
            # 恢复发送按钮和窗口标题
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL, text="发送"))
            self.root.after(0, lambda: self.root.title(f"微信聊天 - {self.friend_name}"))

    def _create_empty_bubble_for_stream(self):
        """在主线程中创建一个空的对方气泡，供流式更新使用"""
        # 防止重复创建
        if hasattr(self, '_current_stream_bubble') and self._current_stream_bubble is not None:
            return
        self._current_stream_bubble = self.append_chat_bubble("friend", "...")
        
    def _update_stream_bubble(self, text):
        """在主线程中更新气泡的文字内容"""
        if hasattr(self, '_current_stream_bubble') and self._current_stream_bubble is not None:
            self._current_stream_bubble.config(text=text)
            self._scroll_to_bottom()

if __name__ == "__main__":
    root = tk.Tk()
    app = DigitalFriendChatApp(root)
    root.mainloop()
