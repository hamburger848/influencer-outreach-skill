#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outreach Script Generator
Generate personalized outreach messages for KOL creators on TikTok
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / 'outputs'

def build_script_text(kol):
    """Build outreach script text, returns string"""
    fans = kol['粉丝数']
    avg_play = kol['平均播放_清洗后']
    price = kol.get('建议中位价', 0)

    if fans >= 50000:
        script = f"""TikTok DM Script:

Hi there!

I'm reaching out from [Brand Name], a productivity app for professionals.

We've been running influencer campaigns on TikTok and really like your content.
With {fans/10000:.1f}M followers and an average of {avg_play/10000:.1f}M views,
your content quality stands out.

I'd love to discuss:
1. Your business collaboration rates
2. Your availability for Q1 [or specific timeframe]

If you're interested, let's connect on Instagram or WhatsApp: [your contact]
Looking forward to collaborating!"""
    elif fans < 5000:
        script = f"""TikTok DM Script:

Hi! I noticed your video hit {avg_play/10000:.1f}M views - that's amazing! 🎉

I'm from [Brand Name], a productivity tool app. We're looking to collaborate
with creators like you for our upcoming TikTok campaign.

What's your typical rate for sponsored content? We're working with a budget
of around ${price:.0f} for this project, mainly focusing on content fit
and value.

Would love to chat more! Add me on Instagram/WhatsApp: [your contact]"""
    else:
        script = f"""TikTok DM Script:

Hi!

I'm [Your Name], working with [Brand Name].

I came across your profile and really like your content - you have an
average of {avg_play/10000:.1f}M views and great engagement!

We're a productivity app looking to partner with creators for our upcoming
TikTok campaign. Would love to hear about your collaboration rates and
availability.

Open to connecting on Instagram or WhatsApp: [your contact]"""

    follow_up = f"""
================================================================================
Follow-up Message Template (send after connecting):
================================================================================

Hi again!

Thanks for connecting! Here's a quick intro:

About us:
- Product: [Brand Name] - productivity tool for professionals
- Campaign timing: Q1/Q2 [adjust as needed]
- Current stage: Building our creator network

What I noticed about your profile:
- {fans/10000:.1f}M followers, ~{avg_play/10000:.1f}M avg views
- Consistent content quality

Our collaboration model:
- Content creation (integrated posts, duets, etc.)
- Feel free to quote your rate - we estimate around ${price:.0f}
- I'll confirm details 1-2 weeks before the campaign starts

A few questions:
1. What's your rate for sponsored content?
2. Are you available for Q1/Q2 campaigns?
3. Have you worked with productivity/tools apps before?
"""
    return script + follow_up


def generate_script(kol_name, excel_path=None, save=True):
    """Generate outreach script for a specific creator"""

    if excel_path is None:
        excel_path = DATA_DIR / 'KOL达人评分最终报告.xlsx'

    df = pd.read_excel(excel_path)
    kol = df[df['达人昵称'] == kol_name]

    if len(kol) == 0:
        print(f"❌ Creator not found: {kol_name}")
        return

    kol = kol.iloc[0]
    fans = kol['粉丝数']
    avg_play = kol['平均播放_清洗后']
    price = kol.get('建议中位价', 0)
    contact = kol.get('联系方式', '')
    priority = kol.get('投放优先级', '')

    script_text = build_script_text(kol)

    print("="*80)
    print(f"📝 Outreach Script - 【{kol_name}】")
    print("="*80)

    print(f"\nCreator Info:")
    print(f"  Followers: {fans:,.0f}")
    print(f"  Avg Views: {avg_play:,.0f}")
    print(f"  Suggested Price: ${price:.0f}" if price else "  Suggested Price: TBD")
    print(f"  Priority: {priority}")
    print(f"  Contact: {contact if contact else 'Not found'}")

    print("\n" + "="*80)
    print(script_text)

    if save:
        idx = kol.name
        df.at[idx, '话术'] = script_text
        df.to_excel(excel_path, index=False)
        print("\n✅ Script saved to Excel")

    return script_text


def batch_generate(excel_path=None, top_n=3, save=True):
    """Batch generate outreach scripts for top N priority creators"""

    if excel_path is None:
        excel_path = DATA_DIR / 'KOL达人评分最终报告.xlsx'

    df = pd.read_excel(excel_path)
    df_valid = df[df['达人昵称'].notna() & (df['达人昵称'] != '') & (df['达人昵称'] != 'N/A')].copy()

    not_contacted = df_valid[df_valid.get('建联状态', '') == '未建联'].copy()

    if len(not_contacted) == 0:
        print("✅ All creators have been contacted!")
        return

    not_contacted = not_contacted.sort_values('总分', ascending=False)

    top_kols = not_contacted.head(top_n)

    print("="*80)
    print(f"📝 Batch Generate Outreach Scripts (Top {top_n})")
    print("="*80)

    saved_count = 0
    for idx, row in top_kols.iterrows():
        print("\n")
        generate_script(row['达人昵称'], excel_path, save=False)
        print("\n" + "="*80 + "\n")

        script_text = build_script_text(row)
        df.at[idx, '话术'] = script_text
        saved_count += 1

    if save:
        df.to_excel(excel_path, index=False)
        print(f"\n✅ Generated scripts for {saved_count} creators and saved to Excel")

    return df


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        kol_name = sys.argv[1]
        generate_script(kol_name)
    else:
        batch_generate(top_n=3)
