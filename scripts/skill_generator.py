#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import os
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import httpx
from collections import Counter
import datetime

# 加载环境变量
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

class SkillGenerator:
    def __init__(self, api_key=None, base_url=None, model_name=None):
        """
        初始化 SkillGenerator，连接大模型
        """
        self.api_key = api_key or os.environ.get("OFOX_API_KEY") or os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OFOX_BASE_URL") or os.environ.get("SILICONFLOW_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model_name = model_name or os.environ.get("OFOX_MODEL") or os.environ.get("SILICONFLOW_MODEL") or os.environ.get("OPENAI_MODEL_NAME", "gpt-4o")
        
        if not self.api_key:
            raise ValueError("未找到 API Key。请在 .env 文件中配置 OFOX_API_KEY 或 SILICONFLOW_API_KEY。")
            
        self.client = OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url, 
            timeout=300.0, 
            max_retries=3
        )

    def extract_emojis(self, text):
        """提取文本中的微信表情包，格式如 [旺柴], [呲牙]"""
        emojis = re.findall(r'\[.*?\]', text)
        return [e for e, c in Counter(emojis).most_common(5)]

    def clean_data(self, raw_lines):
        """
        数据清洗 (Data Cleaning): 过滤无效系统信息和噪点（如图片、表情代码）
        """
        cleaned_lines = []
        # 丢弃整条消息的正则
        drop_patterns = [
            r'撤回了一条消息',
            r'已收款',
            r'转账给你',
            r'语音通话',
            r'视频通话',
            r'拍了拍',
            r'领取了你的红包',
            r'加入群聊'
        ]
        
        # 只替换掉占位符的正则
        replace_patterns = r'\[表情\]|\[图片\]|\[视频\]|\[语音\]|\[位置\]|\[链接\]|\[动画表情\]|\[视频号.*?\]'
        
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否包含需要整条丢弃的系统消息特征
            if any(re.search(p, line) for p in drop_patterns):
                continue
                
            # 替换非文本内容
            line = re.sub(replace_patterns, '', line).strip()
            
            if line:
                cleaned_lines.append(line)
                
        return cleaned_lines

    def generate(self, input_file, friend_name, output_file=None):
        """
        核心生成逻辑：清洗数据 -> 抽样 -> LLM 分析 -> 结构化存储
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"找不到输入文件: {input_file}")
            
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
            
        # 1. 数据清洗
        cleaned_lines = self.clean_data(raw_lines)
        total_messages = len(cleaned_lines)
        
        if total_messages < 10:
            print("警告：清洗后的有效消息过少，可能无法生成准确的画像。")
            
        # 2. 样本压缩与截取
        # 抽取前 100 条和后 100 条作为 LLM 侧写的样本
        head_samples = cleaned_lines[:100]
        tail_samples = cleaned_lines[-100:] if total_messages > 100 else []
        analysis_sample = "\n".join(head_samples + tail_samples)
        
        emojis = self.extract_emojis("\n".join(cleaned_lines))
        
        print(f"正在分析 {friend_name} 的聊天记录 (共计 {total_messages} 条有效消息)...")
        print("正在调用 LLM 进行深度人格侧写，请稍候...")
        
        # 3. 人格侧写 Prompt (Persona Profiling)
        persona_prompt = f"""
你是一位顶尖的心理学家和语言行为分析师。请深度分析以下与微信好友【{friend_name}】的聊天记录样本。

你的任务是：输出该好友的深度性格标签、语言回复习惯、口头禅，并总结出关键记忆和几个典型的对话问答对(QA Pair)。
请严格按照以下 JSON 格式输出，不要有任何 Markdown 代码块包裹，只输出合法的 JSON 字符串：

{{
  "persona": {{
    "core_traits": ["特征1", "特征2", "特征3"],
    "language_habits": {{
      "sentence_length": "短句为主 / 喜欢发长段落文字",
      "punctuation_preference": "对标点符号的使用偏好描述",
      "emoji_usage": ["提取到的最典型的3个表情或文字符号"],
      "catchphrases": ["口头禅1", "口头禅2", "口头禅3"]
    }},
    "role_description": "你现在是{friend_name}，你和用户的关系是[基于聊天推断的关系]。你说话的语气特点是[详细描述]。"
  }},
  "knowledge_base": {{
    "top_topics": ["常聊话题1", "常聊话题2"],
    "key_memories": "从聊天中提取的最核心的共同记忆或事件总结"
  }},
  "chat_samples": [
    {{"q": "用户发的话", "a": "{friend_name}的典型回复"}},
    {{"q": "用户发的话", "a": "{friend_name}的典型回复"}},
    {{"q": "用户发的话", "a": "{friend_name}的典型回复"}},
    {{"q": "用户发的话", "a": "{friend_name}的典型回复"}},
    {{"q": "用户发的话", "a": "{friend_name}的典型回复"}}
  ]
}}

聊天记录样本如下：
{analysis_sample}
"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "你是一个严格的 JSON 结构化数据提取器。"},
                {"role": "user", "content": persona_prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        # 移除可能带有 Markdown 的前缀后缀
        content = re.sub(r'^```json\n|\n```$', '', content.strip(), flags=re.MULTILINE)
        content = re.sub(r'^```\n|\n```$', '', content.strip(), flags=re.MULTILINE)
        
        try:
            llm_result = json.loads(content)
        except json.JSONDecodeError:
            print("错误：大模型返回的不是有效的 JSON 格式。")
            print("原始返回:\n", content)
            return
            
        # 如果大模型没有提取出足够的 Emoji，用正则提取的补上
        if not llm_result['persona']['language_habits'].get('emoji_usage'):
            llm_result['persona']['language_habits']['emoji_usage'] = emojis
            
        # 4. 结构化存储
        # 组合最终的 Skill JSON
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 只保留最近的少量上下文作为“短期记忆”
        recent_context = cleaned_lines[-30:] if total_messages > 30 else cleaned_lines
        
        skill_data = {
            "version": "4.0",
            "metadata": {
                "source_friend": friend_name,
                "created_at": today,
                "total_messages_analyzed": total_messages
            },
            "persona": llm_result.get("persona", {}),
            "knowledge_base": llm_result.get("knowledge_base", {}),
            "chat_samples": llm_result.get("chat_samples", []),
            "recent_context": recent_context
        }
        
        if not output_file:
            output_file = f"{friend_name}.skill.json"
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ 成功生成结构化且高信息密度的 Skill 文件: {output_file}")
        print("核心性格标签:", skill_data['persona'].get('core_traits'))
        print("典型对话样本数:", len(skill_data.get('chat_samples', [])))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="微信好友 Skill Generator (重构优化版)")
    parser.add_argument("-i", "--input", required=True, help="已经由 wechat_parser.py 预处理过的 Markdown 聊天记录文件")
    parser.add_argument("-f", "--friend", required=True, help="好友的称呼")
    parser.add_argument("-o", "--output", help="输出的 .skill.json 文件路径")
    
    args = parser.parse_args()
    
    try:
        generator = SkillGenerator()
        generator.generate(args.input, args.friend, args.output)
    except Exception as e:
        print(f"执行失败: {e}")
