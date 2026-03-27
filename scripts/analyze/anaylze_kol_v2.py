import os
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ======================【1】核心配置（可自由修改）======================
# 权重配置（所有加分都在这里，支持不同场景快速切换）
SCORE_WEIGHTS = {
    # 体量权重
    "low_fans_explosive": 5,     # <5000粉 + 播粉比>5
    "mid_fans_explosive": 6,     # 5k-3w粉 + 播粉比>15
    "stable_mid": 4,             # 5k-10w粉 + 播粉比>1
    "large_scale": 3,            # >10w粉

    # 数据质量
    "ratio_high": 1,             # 播粉比≥3
    "ratio_mid": 1,              # 播粉比≥1.5
    "cv_very_stable": 2,         # 变异系数<30%
    "cv_stable": 1,              # 变异系数<50%

    # 爆款
    "multi_outlier": 2,          # 爆款≥2

    # 性价比
    "cpm_super": 2,              # CPM<8

    # 趋势
    "trend_strong_up": 2,
    "trend_mild_up": 1,
    "trend_strong_down": -2,
    "trend_mild_down": -1,

    # 新增维度（业务关键）
    "content_match_high": 2,     # 内容完全匹配
    "content_match_mid": 1,      # 部分匹配
    "content_match_low": -1,     # 不匹配

    "interact_high": 2,          # 互动率≥5%
    "interact_mid": 1,           # 互动率≥2%
    "interact_low": -1,          # 互动率<1%
}

# 基础参数
PLAY_COLS = ["播放1", "播放2", "播放3", "播放4", "播放5"]
BASE_CPM = 15
DEFAULT_OUTPUT_PATH = os.getenv("DEFAULT_OUTPUT_PATH", "outputs/KOL达人评分最终报告.xlsx")
OUTPUT_DIR = Path(DEFAULT_OUTPUT_PATH).parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_contact(signature):
    import re
    if pd.isna(signature):
        return ""
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', str(signature))
    return email.group(0) if email else ""

# ======================【2】数据清洗：极值处理（优化版）======================
def clean_play_data(row):
    play_list = [row[col] for col in PLAY_COLS if pd.notna(row[col]) and row[col] > 0]
    if len(play_list) < 3:
        return None, None, None, False, 0

    # IQR 极值判断（更科学）
    q25, q75 = np.percentile(play_list, [25, 75])
    iqr = q75 - q25
    upper = q75 + 3 * iqr
    lower = q25 - 3 * iqr

    cleaned = [x for x in play_list if lower <= x <= upper]
    outliers = [x for x in play_list if x > upper]
    has_outlier = len(outliers) > 0
    outlier_count = len(outliers)

    # 最多只删2个极值，避免数据过度清洗
    if len(play_list) - len(cleaned) > 2:
        cleaned = play_list.copy()
        cleaned.sort()
        cleaned = cleaned[:-2]

    avg_all = round(np.mean(play_list), 1)
    avg_clean = round(np.mean(cleaned), 1)
    return avg_all, avg_clean, round(np.median(cleaned), 1), has_outlier, outlier_count


# ======================【3】播放趋势判断======================
def get_trend_score(video_plays):
    if len(video_plays) < 3:
        return "stable", 0

    k = np.polyfit(range(len(video_plays)), video_plays, 1)[0]
    ratio = (video_plays[0] / video_plays[-1]) if video_plays[-1] > 0 else 1

    if k > 0 and ratio >= 1.3:
        return "strong_up", SCORE_WEIGHTS["trend_strong_up"]
    elif k > 0:
        return "mild_up", SCORE_WEIGHTS["trend_mild_up"]
    elif k < 0 and ratio <= 0.7:
        return "strong_down", SCORE_WEIGHTS["trend_strong_down"]
    elif k < 0:
        return "mild_down", SCORE_WEIGHTS["trend_mild_down"]
    else:
        return "stable", 0


# ======================【4】动态CPM定价（市场真实逻辑）======================
def dynamic_price(fans, avg_play, ratio, trend_type):
    if avg_play is None or fans <= 0:
        return 0, 0, 0, "数据不足"

    cpm = BASE_CPM
    note = ""

    # 粉丝量级溢价
    if fans < 5000:
        cpm = 8
        note = "小体量"
    elif 5000 <= fans <= 30000:
        cpm = 15 if ratio < 15 else 16.5
        note = "中体量"
    elif 30000 < fans <= 100000:
        cpm = 18
        note = "大体量"
    else:
        cpm = 19.5
        note = "超大体量"

    # 趋势溢价
    if trend_type in ["strong_up", "mild_up"]:
        cpm *= 1.1
        note += " + 上升溢价"

    mid = round(avg_play * cpm / 1000, 2)
    low = round(mid * 0.75, 2)
    high = round(mid * 1.25, 2)
    return low, mid, high, note


# ======================【5】最终评分计算（核心）======================
def calculate_total_score(row):
    score = 0
    detail = []

    fans = row["粉丝数"]
    avg_clean = row["平均播放_清洗后"]
    ratio = row["播粉比"]
    cv = row["变异系数"]
    outlier_num = row["爆款数量"]
    interact_rate = row["互动率"]
    content_match = str(row["内容匹配度"]).strip()
    trend_score = row["趋势得分"]

    # 1. 体量分
    if fans < 5000 and ratio > 5:
        score += SCORE_WEIGHTS["low_fans_explosive"]
        detail.append(f"低粉爆款({SCORE_WEIGHTS['low_fans_explosive']})")
    elif 5000 <= fans <= 30000 and ratio > 15:
        score += SCORE_WEIGHTS["mid_fans_explosive"]
        detail.append(f"中粉爆款({SCORE_WEIGHTS['mid_fans_explosive']})")
    elif 5000 <= fans <= 100000 and ratio > 1:
        score += SCORE_WEIGHTS["stable_mid"]
        detail.append(f"稳定中体量({SCORE_WEIGHTS['stable_mid']})")
    elif fans > 100000:
        score += SCORE_WEIGHTS["large_scale"]
        detail.append(f"大体量({SCORE_WEIGHTS['large_scale']})")

    # 2. 播粉比
    if ratio >= 3:
        score += SCORE_WEIGHTS["ratio_high"]
        detail.append(f"播粉比高({SCORE_WEIGHTS['ratio_high']})")
    elif ratio >= 1.5:
        score += SCORE_WEIGHTS["ratio_mid"]
        detail.append(f"播粉比中({SCORE_WEIGHTS['ratio_mid']})")

    # 3. 稳定性
    if pd.notna(cv):
        if cv < 30:
            score += SCORE_WEIGHTS["cv_very_stable"]
            detail.append(f"极稳定({SCORE_WEIGHTS['cv_very_stable']})")
        elif cv < 50:
            score += SCORE_WEIGHTS["cv_stable"]
            detail.append(f"较稳定({SCORE_WEIGHTS['cv_stable']})")

    # 4. 爆款
    if outlier_num >= 2:
        score += SCORE_WEIGHTS["multi_outlier"]
        detail.append(f"多爆款({SCORE_WEIGHTS['multi_outlier']})")

    # 5. 性价比
    if pd.notna(row["实际CPM"]) and row["实际CPM"] < 8:
        score += SCORE_WEIGHTS["cpm_super"]
        detail.append(f"超高性价比({SCORE_WEIGHTS['cpm_super']})")

    # 6. 趋势
    score += trend_score
    if trend_score > 0:
        detail.append(f"趋势+{trend_score}")
    elif trend_score < 0:
        detail.append(f"趋势{trend_score}")

    # 7. 内容匹配度（新增）
    if "完全" in content_match:
        score += SCORE_WEIGHTS["content_match_high"]
        detail.append(f"内容匹配({SCORE_WEIGHTS['content_match_high']})")
    elif "部分" in content_match:
        score += SCORE_WEIGHTS["content_match_mid"]
        detail.append(f"内容部分匹配({SCORE_WEIGHTS['content_match_mid']})")
    else:
        score += SCORE_WEIGHTS["content_match_low"]
        detail.append(f"内容不匹配({SCORE_WEIGHTS['content_match_low']})")

    # 8. 互动率（新增）
    if interact_rate >= 0.05:
        score += SCORE_WEIGHTS["interact_high"]
        detail.append(f"高互动({SCORE_WEIGHTS['interact_high']})")
    elif interact_rate >= 0.02:
        score += SCORE_WEIGHTS["interact_mid"]
        detail.append(f"中互动({SCORE_WEIGHTS['interact_mid']})")
    else:
        score += SCORE_WEIGHTS["interact_low"]
        detail.append(f"低互动({SCORE_WEIGHTS['interact_low']})")

    return round(score, 1), " | ".join(detail)


# ======================【6】主流程：一键运行======================
def run_kol_analysis(file_path=DEFAULT_OUTPUT_PATH):
    print("开始分析 KOL 达人数据...")
    df = pd.read_excel(file_path)

    df["联系方式"] = df["signature"].apply(extract_contact)

    # 清洗播放数据
    clean_result = df.apply(clean_play_data, axis=1).tolist()
    df[["平均播放_原始", "平均播放_清洗后", "中位数播放", "有爆款", "爆款数量"]] = pd.DataFrame(clean_result, index=df.index)

    # 计算核心指标
    df["播粉比"] = round(df["平均播放_清洗后"] / df["粉丝数"], 2)
    df["变异系数"] = df[PLAY_COLS].std(axis=1) / df[PLAY_COLS].mean(axis=1) * 100

    # 计算互动率：每个视频独立计算后取平均
    def calc_interact_rate(row):
        rates = []
        for i in range(1, 6):
            play = row.get(f"播放{i}", 0)
            like = row.get(f"点赞{i}", 0)
            comment = row.get(f"评论{i}", 0)
            collect = row.get(f"收藏{i}", 0)
            if play and play > 0:
                rate = (like + comment + collect) / play
                rates.append(rate)
        return np.mean(rates) if rates else 0
    df["互动率"] = df.apply(calc_interact_rate, axis=1)

    df["实际CPM"] = df["报价"] / df["平均播放_清洗后"] * 1000

    # 趋势
    trend_data = df.apply(lambda r: get_trend_score([r[c] for c in PLAY_COLS if pd.notna(r[c])]), axis=1)
    df[["趋势类型", "趋势得分"]] = pd.DataFrame(trend_data.tolist(), index=df.index)

    # 定价
    price_data = df.apply(lambda r: dynamic_price(r["粉丝数"], r["平均播放_清洗后"], r["播粉比"], r["趋势类型"]), axis=1)
    df[["建议底价", "建议中位价", "建议高价", "定价说明"]] = pd.DataFrame(price_data.tolist(), index=df.index)

    # 最终评分
    score_data = df.apply(calculate_total_score, axis=1).tolist()
    df[["总分", "评分构成"]] = pd.DataFrame(score_data, index=df.index)

    # 排序
    df = df.sort_values("总分", ascending=False).reset_index(drop=True)
    df["投放优先级"] = df["总分"].apply(lambda x: "高" if x >= 12 else "中" if x >= 8 else "低")

    # 输出（追加模式）
    with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name='评分结果', index=False)
    print(f"分析完成！评分结果已追加到 {file_path}")
    return df


# ======================【启动】======================
if __name__ == "__main__":
    final_df = run_kol_analysis()
