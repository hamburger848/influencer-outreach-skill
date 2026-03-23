#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱提取工具
使用 AI 模型从 signature 中提取联系方式
"""

import os
import pandas as pd
from openai import OpenAI


def extract_contact_with_ai(excel_path: str, output_path: str = None):
    """
    使用 OpenAI API 从 signature 中提取联系方式

    Args:
        excel_path: Excel 文件路径
        output_path: 输出 Excel 文件路径（可选，默认覆盖原文件）
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    if output_path is None:
        output_path = excel_path

    client = OpenAI(api_key=api_key)

    df = pd.read_excel(excel_path)

    if "signature" not in df.columns:
        print("文件中没有 signature 列")
        return

    contacts = []

    for idx, row in df.iterrows():
        signature = row.get("signature", "")
        kol_name = row.get("达人昵称", f"Row {idx}")

        if pd.isna(signature) or not signature:
            contacts.append("")
            print(f"[{idx+1}/{len(df)}] {kol_name}: 无 signature")
            continue

        prompt = f"""从以下 TikTok 达人签名中提取联系方式（邮箱、Instagram、WhatsApp 等）。

签名内容：
{signature}

请提取所有联系方式，以 JSON 格式返回：
{{"contacts": ["邮箱1", "邮箱2", "Instagram: @xxx", "WhatsApp: +123456"]}}

如果没有找到任何联系方式，返回：
{{"contacts": []}}

只返回 JSON，不要有其他说明文字。"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            contact_list = result.get("contacts", [])
            contact_str = "; ".join(contact_list) if contact_list else ""
            contacts.append(contact_str)
            print(f"[{idx+1}/{len(df)}] {kol_name}: {contact_str if contact_str else '未找到'}")

        except Exception as e:
            contacts.append("")
            print(f"[{idx+1}/{len(df)}] {kol_name}: 提取失败 - {e}")

    df["联系方式"] = contacts
    df.to_excel(output_path, index=False)
    print(f"\n✅ 提取完成，结果已保存到: {output_path}")


if __name__ == "__main__":
    import json
    import argparse

    parser = argparse.ArgumentParser(description="使用 AI 从 signature 提取联系方式")
    parser.add_argument("excel_path", help="Excel 文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")

    args = parser.parse_args()

    extract_contact_with_ai(
        excel_path=args.excel_path,
        output_path=args.output
    )
