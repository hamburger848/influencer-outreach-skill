#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright Gmail 自动发邮件脚本
适用于每天少量发送（10封左右）的建联场景
"""

import os
import time
import json
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError


CHROMIUM_PATH = "C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1124\\chrome-win\\chrome.exe"

class GmailAutoSender:
    def __init__(self, auth_state_path: str = "gmail_auth_state.json"):
        self.auth_state_path = auth_state_path
        self.browser = None
        self.context = None
        self.page = None

    def login(self, headless: bool = False):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=headless, executable_path=CHROMIUM_PATH)
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            if os.path.exists(self.auth_state_path):
                self.context.storage_state(path=self.auth_state_path)
                print(f"✅ 已加载登录状态: {self.auth_state_path}")

            self.page = self.context.new_page()
            self.page.goto("https://mail.google.com", wait_until="networkidle", timeout=60000)

            if self._is_logged_in():
                print("✅ 已登录 Gmail")
            else:
                print("⚠️ 需要登录 Gmail")
                input("请在浏览器中完成登录，然后按 Enter 继续...")
                self.context.storage_state(path=self.auth_state_path)
                print(f"✅ 登录状态已保存到: {self.auth_state_path}")

            self.browser.close()

    def _is_logged_in(self) -> bool:
        try:
            self.page.wait_for_selector('[data-testid="compose-button"]', timeout=3000)
            return True
        except:
            return False

    def send_email(self, to: str, subject: str, body: str, delay: int = 3) -> bool:
        try:
            self.page.goto("https://mail.google.com/mail/u/0/#inbox?compose=new", timeout=30000)
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)

            self.page.fill('textarea[name="to"]', to)
            time.sleep(0.5)

            self.page.fill('input[name="subjectbox"]', subject)
            time.sleep(0.5)

            self.page.click('div[aria-label="Message body"]')
            self.page.fill('div[aria-label="Message body"]', body)
            time.sleep(1)

            send_button = self.page.locator('div[data-tooltip="Send ‪(Ctrl+Enter)"]')
            send_button.click()

            time.sleep(delay)

            try:
                self.page.wait_for_selector('div[data-tooltip="Undo"]', timeout=5000)
                print(f"✅ 邮件已发送至: {to}")
                return True
            except:
                print(f"⚠️ 可能发送失败，请检查: {to}")
                return False

        except TimeoutError:
            print(f"⏰ 超时: {to}")
            return False
        except PlaywrightError as e:
            print(f"❌ Playwright错误: {to} - {e}")
            return False
        except Exception as e:
            print(f"❌ 发送失败: {to} - {e}")
            return False

    def send_batch(self, recipients: list, subject: str, body_template: str,
                   delay_between: int = 30) -> dict:
        results = {"success": 0, "failed": 0, "failed_emails": []}

        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False, executable_path=CHROMIUM_PATH)
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            if os.path.exists(self.auth_state_path):
                self.context.storage_state(path=self.auth_state_path)

            self.page = self.context.new_page()
            self.page.goto("https://mail.google.com", wait_until="networkidle", timeout=60000)

            if not self._is_logged_in():
                print("⚠️ 未登录，请先运行 login() 方法")
                self.browser.close()
                return results

            for i, recipient in enumerate(recipients):
                print(f"\n[{i+1}/{len(recipients)}] 发送给: {recipient}")

                personalized_body = body_template.replace("{{name}}", recipient.split("@")[0])

                success = self.send_email(recipient, subject, personalized_body)

                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["failed_emails"].append(recipient)

                if i < len(recipients) - 1:
                    print(f"⏳ 等待 {delay_between} 秒后发送下一封...")
                    time.sleep(delay_between)

            self.browser.close()

        return results


def load_recipients_from_csv(csv_path: str, email_column: str = "提取邮箱") -> list:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if email_column not in df.columns:
        raise ValueError(f"CSV中没有找到列: {email_column}")

    emails = df[email_column].dropna().tolist()
    emails = [e for e in emails if "@" in str(e) and "nan" not in str(e).lower()]
    return emails


DEFAULT_EMAIL_SUBJECT = "【商务合作邀请】您好，我是XXX品牌方"

DEFAULT_EMAIL_BODY = """您好 {{name}}，

我在抖音上关注了您的内容，非常欣赏您的创作风格！

我们是XXX品牌，正在寻找优质达人合作。本次合作包括：
• 有竞争力的报酬
• 自由创作空间
• 长期合作机会

如果您对我们的合作感兴趣，欢迎回复这封邮件，我很期待能进一步沟通！

祝好，
XXX品牌商务团队
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Gmail 自动发邮件工具")
    parser.add_argument("--csv", "-c", help="CSV文件路径，包含邮箱地址列")
    parser.add_argument("--emails", "-e", nargs="+", help="直接指定邮箱地址")
    parser.add_argument("--subject", "-s", default=DEFAULT_EMAIL_SUBJECT, help="邮件主题")
    parser.add_argument("--body", "-b", default=DEFAULT_EMAIL_BODY, help="邮件正文模板（可用{{name}}）")
    parser.add_argument("--delay", "-d", type=int, default=30, help="发送间隔（秒）")
    parser.add_argument("--login", "-l", action="store_true", help="仅执行登录")
    parser.add_argument("--headless", action="store_true", help="无头模式运行浏览器")

    args = parser.parse_args()

    sender = GmailAutoSender()

    if args.login or not os.path.exists(sender.auth_state_path):
        print("🔐 开始登录 Gmail...")
        sender.login(headless=args.headless)
        if args.login:
            return

    recipients = []
    if args.emails:
        recipients = args.emails
    elif args.csv:
        recipients = load_recipients_from_csv(args.csv)
    else:
        print("⚠️ 请指定 --csv 或 --emails")
        return

    print(f"\n📤 开始发送邮件，共 {len(recipients)} 封")
    print(f"   主题: {args.subject}")
    print(f"   间隔: {args.delay} 秒")
    print("-" * 50)

    results = sender.send_batch(
        recipients=recipients,
        subject=args.subject,
        body_template=args.body,
        delay_between=args.delay
    )

    print("\n" + "=" * 50)
    print(f"📊 发送完成!")
    print(f"   成功: {results['success']}")
    print(f"   失败: {results['failed']}")
    if results['failed_emails']:
        print(f"   失败邮箱: {results['failed_emails']}")


if __name__ == "__main__":
    main()