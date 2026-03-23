#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw KOL建联工作流 - 统一入口
整合从发现达人到发送邮件的完整流程

流程:
  1. 发现达人 → 2. 获取数据 → 3. 提取邮箱 → 4. 评分分析 → 5. 建联追踪 → 6. 发送邮件

使用方式:
    python kol_workflow.py --step 1           # 只运行步骤1
    python kol_workflow.py --step 1-3         # 运行步骤1-3
    python kol_workflow.py --all              # 运行全部步骤
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(SCRIPTS_DIR.parent, ".env"))

SCRIPTS_DIR = Path(__file__).parent
DATA_DIR = SCRIPTS_DIR.parent / "data"

STEPS = {
    "1": {
        "name": "发现达人（已废弃）",
        "desc": "请使用 TikHub API 手动搜索",
        "script": None
    },
    "2": {
        "name": "获取数据",
        "desc": "通过TikHub API获取达人视频数据",
        "script": "search/tikhub_client.py"
    },
    "3": {
        "name": "提取邮箱",
        "desc": "从签名/Linktr.ee提取达人邮箱",
        "script": None  # 直接调用函数
    },
    "4": {
        "name": "评分分析",
        "desc": "分析达人评分和推荐",
        "script": None  # 已删除
    },
    "5": {
        "name": "建联追踪",
        "desc": "追踪建联进度，生成每日任务",
        "script": "outreach/daily_tasks.py"
    },
    "6": {
        "name": "发送邮件",
        "desc": "通过Playwright自动发送邮件",
        "script": "outreach/playwright_gmail_sender.py"
    }
}


def step1_discover_creators(args):
    """步骤1: 发现达人（已废弃，请使用TikHub API直接搜索）"""
    print("\n⚠️ 步骤1已废弃")
    print("请使用 TikHub API 的 search_tiktok_users 方法搜索达人")
    print("或使用 MediaCrawler 等工具手动构建UID池")
    print("✅ 步骤1完成")
    return True


def step2_fetch_data(args):
    """步骤2: 获取达人数据"""
    print("\n" + "=" * 60)
    print("📊 步骤2: 获取达人数据")
    print("=" * 60)

    from search.tikhub_client import TikHubClient

    uid_file = DATA_DIR / f"uid_pool_{args.date}.txt" if args.date else None

    if not uid_file or not uid_file.exists():
        uid_file = list(DATA_DIR.glob("uid_pool_*.txt"))[-1] if list(DATA_DIR.glob("uid_pool_*.txt")) else None

    if not uid_file:
        print("⚠️ 未找到UID池文件，请先运行步骤1")
        return False

    print(f"📂 从文件加载UID: {uid_file}")

    with open(uid_file, "r") as f:
        uids = [line.strip() for line in f if line.strip()]

    print(f"📋 共 {len(uids)} 个UID待处理")

    client = TikHubClient()

    kol_csv = DATA_DIR / "达人跟进表.csv"

    for i, uid in enumerate(uids[:args.limit], 1):
        print(f"[{i}/{min(len(uids), args.limit)}] 获取达人数据: {uid}")

        try:
            kol_data = client.fetch_kol_play_data(sec_uid=uid)
            if kol_data:
                client.save_kol_to_csv(kol_data, str(kol_csv))
                print(f"   ✅ 已保存: {kol_data.get('达人昵称', 'unknown')}")
            else:
                print(f"   ⚠️ 无数据")

        except Exception as e:
            print(f"   ❌ 失败: {e}")

        import time
        time.sleep(0.5)

    print("✅ 步骤2完成")
    return True


def step3_extract_emails(args):
    """步骤3: 提取邮箱"""
    print("\n" + "=" * 60)
    print("📧 步骤3: 提取邮箱")
    print("=" * 60)

    kol_csv = DATA_DIR / "达人跟进表.csv"

    if not kol_csv.exists():
        print("⚠️ 未找到达人数据文件，请先运行步骤2")
        return False

    sys.path.insert(0, str(SCRIPTS_DIR / "outreach"))
    from extract_email_from_signature import analyze_emails_from_signature
    from extract_email_from_linktree import analyze_emails_from_linktree

    output_sig = kol_csv.parent / f"{kol_csv.stem}_邮箱提取{kol_csv.suffix}"
    print("📧 方式1: 从签名提取邮箱...")
    analyze_emails_from_signature(str(kol_csv), str(output_sig), use_openai=not args.no_openai)

    output_linktree = kol_csv.parent / f"{kol_csv.stem}_linktree{kol_csv.suffix}"
    print("\n🔗 方式2: 从Linktr.ee提取邮箱...")
    analyze_emails_from_linktree(str(kol_csv), str(output_linktree), use_openai=not args.no_openai)

    print("✅ 步骤3完成")
    return True


def step4_analyze_kol(args):
    """步骤4: 评分分析"""
    print("\n" + "=" * 60)
    print("📈 步骤4: 评分分析")
    print("=" * 60)

    sys.path.insert(0, str(SCRIPTS_DIR))
    from anaylze_kol_v2 import run_kol_analysis

    kol_csv = Path(args.csv) if args.csv else DATA_DIR / "达人跟进表.csv"

    if not kol_csv.exists():
        print(f"⚠️ 未找到数据文件: {kol_csv}")
        return False

    result_df = run_kol_analysis(str(kol_csv))

    print(f"\n📊 分析完成，共 {len(result_df)} 个达人")
    print(f"TOP5 达人:")
    for i, row in result_df.head(5).iterrows():
        print(f"   {i+1}. {row['达人昵称']} - 总分: {row['总分']}")

    print("✅ 步骤4完成")
    return True


def step5_contact_tracker(args):
    """步骤5: 建联追踪"""
    print("\n" + "=" * 60)
    print("📋 步骤5: 建联追踪")
    print("=" * 60)

    sys.path.insert(0, str(SCRIPTS_DIR / "outreach"))
    from daily_tasks import generate_daily_tasks

    generate_daily_tasks(contact_limit=args.contact_limit)

    print("✅ 步骤5完成")
    return True


def step6_send_email(args):
    """步骤6: 发送邮件"""
    print("\n" + "=" * 60)
    print("📤 步骤6: 发送邮件")
    print("=" * 60)

    from outreach.playwright_gmail_sender import GmailAutoSender, load_recipients_from_csv

    kol_csv = DATA_DIR / "达人跟进表.csv"

    if not kol_csv.exists():
        print("⚠️ 未找到达人数据文件，请先运行步骤2和3")
        return False

    sender = GmailAutoSender()

    if args.login or not os.path.exists(sender.auth_state_path):
        print("🔐 需要登录Gmail...")
        sender.login(headless=args.headless)
        if args.login:
            return True

    if args.csv:
        recipients = load_recipients_from_csv(args.csv, args.email_column)
    else:
        print(f"📂 从 {kol_csv} 加载邮箱...")
        recipients = load_recipients_from_csv(str(kol_csv), args.email_column)

    if not recipients:
        print("⚠️ 未找到邮箱地址，请先运行步骤3提取邮箱")
        return False

    print(f"📋 共 {len(recipients)} 个邮箱待发送")
    print(f"⏳ 发送间隔: {args.delay} 秒")

    results = sender.send_batch(
        recipients=recipients[:args.limit],
        subject=args.subject,
        body_template=args.body,
        delay_between=args.delay
    )

    print(f"\n📊 发送结果:")
    print(f"   成功: {results['success']}")
    print(f"   失败: {results['failed']}")

    print("✅ 步骤6完成")
    return True


def show_status():
    """显示当前项目状态"""
    print("\n" + "=" * 60)
    print("📊 OpenClaw KOL建联工作流 - 项目状态")
    print("=" * 60)

    files_to_check = [
        ("UID池", DATA_DIR / "uid_pool_*.txt"),
        ("达人数据", DATA_DIR / "达人跟进表.csv"),
        ("邮箱提取结果", DATA_DIR / "达人跟进表_邮箱提取.csv"),
        ("Linktree邮箱", DATA_DIR / "达人跟进表_linktree.csv"),
        ("评分报告", DATA_DIR.parent / "outputs" / "KOL达人评分最终报告.xlsx"),
        ("Gmail登录状态", SCRIPTS_DIR / "gmail_auth_state.json"),
    ]

    print("\n📁 数据文件状态:")
    for name, path in files_to_check:
        if "*" in str(path):
            files = list(DATA_DIR.glob("uid_pool_*.txt"))
            if files:
                latest = max(files, key=lambda p: p.stat().st_mtime)
                status = f"✅ {latest.name}"
            else:
                status = "❌ 未找到"
        elif path.exists:
            status = f"✅ 存在 ({path.name})"
        else:
            status = "❌ 未找到"

        print(f"   {name}: {status}")

    print("\n🔧 可用步骤:")
    for num, info in STEPS.items():
        print(f"   {num}. {info['name']} - {info['desc']}")

    print("\n💡 使用方式:")
    print("   python kol_workflow.py --step 1 --keywords 'skincare,beauty'")
    print("   python kol_workflow.py --step 1-3 --keywords 'skincare'")
    print("   python kol_workflow.py --status          # 查看项目状态")


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw KOL建联工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看项目状态
  python kol_workflow.py --status

  # 步骤1: 发现达人
  python kol_workflow.py --step 1 --keywords "skincare,beauty" --country US

  # 步骤2: 获取达人数据
  python kol_workflow.py --step 2 --limit 50

  # 步骤3: 提取邮箱
  python kol_workflow.py --step 3 --no-openai

  # 步骤4: 评分分析
  python kol_workflow.py --step 4

  # 步骤5: 建联追踪
  python kol_workflow.py --step 5 --contact-limit 30

  # 步骤6: 发送邮件
  python kol_workflow.py --step 6 --login
  python kol_workflow.py --step 6 --csv data/达人跟进表_邮箱提取.csv --delay 30

  # 运行多个步骤
  python kol_workflow.py --step 1-3 --keywords "skincare"
  python kol_workflow.py --all --keywords "skincare" --limit 20
        """
    )

    parser.add_argument("--step", "-s", help="步骤编号或范围，如 1, 1-3, all")
    parser.add_argument("--status", action="store_true", help="显示项目状态")

    parser.add_argument("--keywords", "-k", help="搜索关键词（逗号分隔）")
    parser.add_argument("--hashtags", "-t", help="话题标签（逗号分隔）")
    parser.add_argument("--category", "-c", help="品类名称")
    parser.add_argument("--country", default="US", help="目标国家（默认US）")

    parser.add_argument("--limit", type=int, default=50, help="处理数量限制")
    parser.add_argument("--date", help="指定日期的UID文件")

    parser.add_argument("--no-openai", action="store_true", help="不使用OpenAI API")

    parser.add_argument("--contact-limit", type=int, default=50, help="每日建联数量限制")

    parser.add_argument("--csv", help="邮件发送的CSV文件")
    parser.add_argument("--email-column", default="提取邮箱", help="邮箱列名")
    parser.add_argument("--subject", default="【商务合作邀请】您好，我是XXX品牌方", help="邮件主题")
    parser.add_argument("--body", default="您好 {{name}}，...", help="邮件正文模板")
    parser.add_argument("--delay", type=int, default=30, help="发送间隔（秒）")
    parser.add_argument("--login", action="store_true", help="仅登录Gmail")
    parser.add_argument("--headless", action="store_true", help="无头模式运行浏览器")

    parser.add_argument("--keyword-limit", type=int, default=50, help="关键词搜索数量限制")
    parser.add_argument("--hashtag-limit", type=int, default=30, help="话题搜索数量限制")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not args.step:
        print("⚠️ 请指定 --step 或 --status")
        print("   使用 --status 查看项目状态")
        print("   使用 --step 1-6 运行对应步骤")
        return

    if args.step == "all":
        steps_to_run = list(STEPS.keys())
    elif "-" in args.step:
        start, end = args.step.split("-")
        steps_to_run = [str(i) for i in range(int(start), int(end) + 1)]
    else:
        steps_to_run = [args.step]

    print(f"\n🚀 将执行步骤: {', '.join(steps_to_run)}")
    print(f"   {[STEPS[s]['name'] for s in steps_to_run]}")

    step_functions = {
        "1": step1_discover_creators,
        "2": step2_fetch_data,
        "3": step3_extract_emails,
        "4": step4_analyze_kol,
        "5": step5_contact_tracker,
        "6": step6_send_email,
    }

    for step_num in steps_to_run:
        if step_num in step_functions:
            success = step_functions[step_num](args)
            if not success:
                print(f"\n⚠️ 步骤 {step_num} 执行中断")
                break
        else:
            print(f"⚠️ 未知步骤: {step_num}")

    print("\n" + "=" * 60)
    print("✅ 工作流执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()