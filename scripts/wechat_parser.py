#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import csv
import argparse
from pathlib import Path

def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。
    
    返回:
        argparse.Namespace: 包含解析后的命令行参数对象。
    """
    parser = argparse.ArgumentParser(description="预处理 WeChatMsgGrabber 导出的聊天记录数据")
    parser.add_argument("-i", "--input", required=True, help="输入的聊天记录文件路径 (支持 .json 或 .csv)")
    parser.add_argument("-o", "--output", required=True, help="输出的 Markdown 文件路径")
    parser.add_argument("-m", "--me", default="我", help="代表用户自己的昵称，默认为'我'")
    parser.add_argument("-f", "--friend", default="好友", help="代表微信好友的昵称，默认为'好友'")
    return parser.parse_args()

def parse_json(file_path: str) -> list[dict]:
    """
    解析 JSON 格式的聊天记录。
    支持标准的 JSON 数组/对象，以及 JSON Lines 格式。
    
    参数:
        file_path (str): JSON 文件路径。
        
    返回:
        list[dict]: 解析后的消息字典列表，每个字典包含 'sender', 'content', 'time' 等信息。
    """
    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        # 首先尝试按 JSON Lines 格式读取
        content = f.read().strip()
        if not content:
            return []
            
        try:
            # 尝试作为整个 JSON 对象/数组解析
            data = json.loads(content)
            if isinstance(data, dict) and "messages" in data:
                return data["messages"]
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            # 如果失败，则假设是 JSON Lines 格式（每行一个 JSON 对象）
            f.seek(0)
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError as e:
                    print(f"警告: 解析第 {line_num} 行失败: {e}")
                    
    return messages

def parse_csv(file_path: str) -> list[dict]:
    """
    解析 CSV 格式的聊天记录。
    
    参数:
        file_path (str): CSV 文件路径。
        
    返回:
        list[dict]: 解析后的消息字典列表。
    """
    messages = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append(row)
    return messages

def format_to_markdown(messages: list[dict], my_name: str, friend_name: str) -> str:
    """
    将消息列表格式化为易于 LLM 分析的 Markdown 纯文本格式。
    
    参数:
        messages (list[dict]): 消息字典列表。
        my_name (str): 用户的昵称。
        friend_name (str): 好友的昵称。
        
    返回:
        str: 格式化后的 Markdown 字符串。
    """
    lines = []
    lines.append(f"# 与 {friend_name} 的微信聊天记录\n")
    
    for msg in messages:
        # WeChatMsgGrabber 可能的字段名：sender, is_send, content, time, type 等
        # 这里做一些启发式的映射
        
        # 判断发送者
        sender_raw = msg.get("sender", msg.get("name", ""))
        is_send = msg.get("is_send", None)
        
        if is_send is not None:
            # 如果有 is_send 字段，1/True 通常表示自己发出的
            sender = my_name if str(is_send) in ("1", "true", "True") else friend_name
        else:
            # 否则根据名字判断，或者默认
            sender = sender_raw if sender_raw else "未知"
            
        content = msg.get("content", msg.get("text", msg.get("msg", "")))
        time_str = msg.get("time", msg.get("timestamp", ""))
        
        # 跳过空消息
        if not content:
            continue
            
        time_prefix = f"[{time_str}] " if time_str else ""
        lines.append(f"{time_prefix}**{sender}**: {content}")
        
    return "\n".join(lines)

def main():
    """
    主执行函数，处理命令行参数并执行文件转换流程。
    """
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"错误: 输入文件 {input_path} 不存在。")
        return
        
    print(f"正在读取 {input_path} ...")
    
    messages = []
    if input_path.suffix.lower() == '.json':
        messages = parse_json(str(input_path))
    elif input_path.suffix.lower() == '.csv':
        messages = parse_csv(str(input_path))
    else:
        print("错误: 仅支持 .json 或 .csv 格式的文件。")
        return
        
    if not messages:
        print("警告: 未解析到任何消息或文件格式不支持。")
        return
        
    print(f"成功解析 {len(messages)} 条消息，正在格式化...")
    markdown_content = format_to_markdown(messages, args.me, args.friend)
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"处理完成！已将结果保存至 {output_path}")

if __name__ == "__main__":
    main()
