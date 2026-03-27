#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱提取工具
使用正则表达式从 signature 中提取联系方式
"""

import os
import re
import pandas as pd


def extract_contact_from_signature(signature: str) -> str:
    """
    使用正则表达式从签名中提取联系方式
    
    Args:
        signature: 达人签名文本
        
    Returns:
        提取到的联系方式，多个用分号分隔
    """
    if not signature or pd.isna(signature):
        return ""
    
    signature = str(signature)
    contacts = []
    
    # 1. 提取邮箱地址
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, signature)
    contacts.extend(emails)
    
    # 2. 提取 Instagram 账号
    # 匹配格式: @username, instagram.com/username, ig: username
    ig_patterns = [
        r'(?:ig|insta|instagram)[:\s]*@?([a-zA-Z0-9._]+)',
        r'@([a-zA-Z0-9._]{3,})',  # @开头的账号
    ]
    for pattern in ig_patterns:
        matches = re.findall(pattern, signature, re.IGNORECASE)
        for match in matches:
            if match and len(match) > 2:
                contacts.append(f"IG: @{match}")
    
    # 3. 提取 WhatsApp 号码
    # 匹配格式: +1234567890, whatsapp: +123, wa.me/123
    wa_patterns = [
        r'(?:whatsapp|wa\.me)[:\s/]*\+?(\d[\d\s\-]{7,})',
        r'\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',  # 美国手机号格式
    ]
    for pattern in wa_patterns:
        matches = re.findall(pattern, signature, re.IGNORECASE)
        for match in matches:
            if match:
                contacts.append(f"WhatsApp: {match}")
    
    # 4. 提取链接
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, signature)
    for url in urls:
        # 排除常见的非联系方式链接
        if not any(x in url.lower() for x in ['tiktok.com', 'youtube.com', 'youtu.be', 'facebook.com']):
            contacts.append(f"Link: {url}")
    
    # 去重并保持顺序
    seen = set()
    unique_contacts = []
    for contact in contacts:
        contact_lower = contact.lower()
        if contact_lower not in seen:
            seen.add(contact_lower)
            unique_contacts.append(contact)
    
    return "; ".join(unique_contacts) if unique_contacts else ""


def extract_contact_with_ai(excel_path: str, output_path: str = None):
    """
    从 signature 中提取联系方式（无需 AI，使用正则表达式）

    Args:
        excel_path: Excel 文件路径
        output_path: 输出 Excel 文件路径（可选，默认覆盖原文件）
    """
    if output_path is None:
        output_path = excel_path

    # 读取所有 sheet
    xl_file = pd.ExcelFile(excel_path)
    sheet_names = xl_file.sheet_names
    
    print(f"发现 {len(sheet_names)} 个 sheet: {sheet_names}")
    
    # 优先处理 '评分结果' sheet，如果没有则处理第一个
    target_sheet = '评分结果' if '评分结果' in sheet_names else sheet_names[0]
    df = pd.read_excel(excel_path, sheet_name=target_sheet)
    
    print(f"正在处理 sheet: {target_sheet}, 共 {len(df)} 行")

    if "signature" not in df.columns:
        print("文件中没有 signature 列")
        return

    contacts = []
    found_count = 0

    for idx, row in df.iterrows():
        signature = row.get("signature", "")
        kol_name = row.get("unique_id", row.get("达人昵称", f"Row {idx}"))
        
        contact = extract_contact_from_signature(signature)
        contacts.append(contact)
        
        if contact:
            found_count += 1
            print(f"[{idx+1}/{len(df)}] @{kol_name}: {contact}")
        else:
            print(f"[{idx+1}/{len(df)}] @{kol_name}: 未找到联系方式")

    df["联系方式"] = contacts
    
    # 保存回 Excel，使用 openpyxl 引擎
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=target_sheet, index=False)
    
    print(f"\n提取完成！共找到 {found_count}/{len(df)} 个联系方式")
    print(f"结果已保存到: {output_path}")
    
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="从 signature 提取联系方式")
    parser.add_argument("excel_path", help="Excel 文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")

    args = parser.parse_args()

    extract_contact_with_ai(
        excel_path=args.excel_path,
        output_path=args.output
    )
