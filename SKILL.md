---
name: "kol-workflow"
description: "KOL达人投放管理工作流 - 达人搜索、评级定价、建联话术生成、邮件发送。Invoke when user needs to find/analyze KOL creators, calculate CPM pricing, generate outreach scripts, or send outreach emails."
---

# KOL Claw - 达人投放管理系统

一套完整的KOL达人投放工作流，从达人发现到建联跟进全流程自动化。

## 项目结构

```
kol-workflow/
├── SKILL.md                              # 本文件
├── scripts/
│   ├── analyze/
│   │   └── anaylze_kol_v2.py           # KOL评分分析（8维度加权评分）
│   ├── outreach/
│   │   ├── extract_email.py             # 邮箱提取（AI + 正则）
│   │   ├── generate_script.py           # 建联话术生成
│   │   ├── daily_tasks.py              # 每日任务清单
│   │   ├── contact_tracker.py          # 建联进度追踪
│   │   ├── budget_tracker.py            # 预算追踪
│   │   └── playwright_gmail_sender.py  # Gmail自动发送
│   ├── search/
│   │   └── tikhub_client.py             # TikHub API客户端
│   └── kol_workflow.py                  # 工作流统一入口
├── outputs/                              # 输出目录
├── data/                                 # 数据目录（需手动创建）
├── docs/
│   ├── anaylze_kol_v2流程说明.md        # 评分分析详细文档
│   └── analyze_kol流程说明.md           # v1版本文档
└── requirements.txt
```

## 核心功能

| 功能 | 脚本 | 说明 |
|------|------|------|
| KOL评分分析 | `scripts/analyze/anaylze_kol_v2.py` | 8维度加权评分、动态CPM定价 |
| 建联话术生成 | `scripts/outreach/generate_script.py` | 根据达人数据生成个性化话术 |
| 邮箱提取 | `scripts/outreach/extract_email.py` | AI模型从signature提取联系方式 |
| 每日任务清单 | `scripts/outreach/daily_tasks.py` | 待建联/待跟进达人清单 |
| Gmail发送 | `scripts/outreach/playwright_gmail_sender.py` | Playwright自动化发送邮件 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：
```bash
OPENAI_API_KEY=your_openai_api_key
TIK_HUB_API_KEY=your_tikhub_api_key
FEISHU_WEBHOOK_URL=your_webhook_url  # 可选
```

### 3. 准备达人数据

创建 `data/kol_list.csv`，必需字段：
```csv
达人昵称,unique_id,signature,粉丝数,作品数,播放1,播放2,播放3,播放4,播放5,点赞1,点赞2,点赞3,点赞4,点赞5,评论1,评论2,评论3,评论4,评论5,收藏1,收藏2,收藏3,收藏4,收藏5
```

### 4. 运行分析

```bash
# 分析达人并生成评分报告
python scripts/analyze/anaylze_kol_v2.py

# 生成建联话术
python scripts/outreach/generate_script.py <达人昵称>

# 批量生成话术（TOP3未建联达人）
python scripts/outreach/generate_script.py
```

## 评分系统 (anaylze_kol_v2.py)

### 8维度评分体系

| 维度 | 条件 | 分数 |
|------|------|------|
| **体量分** | | |
| 低粉爆款 | <5千粉 + 播粉比>5 | +5 |
| 中粉爆款 | 5千-3万粉 + 播粉比>15 | +6 |
| 稳定中体量 | 5千-10万粉 + 播粉比>1 | +4 |
| 大体量 | >10万粉 | +3 |
| **播粉比** | ≥3 | +1 |
| **稳定性** | 变异系数<30% | +2 |
| **爆款** | ≥2个极值 | +2 |
| **性价比** | CPM<8 | +2 |
| **趋势** | 上升/下降 | ±2 |
| **内容匹配** | 完全/部分/不匹配 | +2/+1/-1 |
| **互动率** | ≥5%/≥2%/<1% | +2/+1/-1 |

### 优先级划分

| 优先级 | 总分 | 说明 |
|--------|------|------|
| 高 | ≥12分 | 强烈推荐投放 |
| 中 | 8-12分 | 可考虑投放 |
| 低 | <8分 | 暂不推荐 |

### 动态CPM定价

```
粉丝量级：
  < 5千粉    → CPM = 8
  5千-3万    → CPM = 15
  3万-10万   → CPM = 18
  > 10万     → CPM = 19.5

趋势溢价：上升趋势 ×1.1

报价计算：
  中位价 = 播放量 × CPM / 1000
  低价   = 中位价 × 0.75
  高价   = 中位价 × 1.25
```

## 话术生成 (generate_script.py)

### 使用方式

```bash
# 单个达人
python scripts/outreach/generate_script.py skincare_emma

# 批量生成（未建联TOP3）
python scripts/outreach/generate_script.py
```

### 话术策略

| 达人类型 | 条件 | 策略 |
|----------|------|------|
| 大达人 | ≥5万粉 | 正式商务型 |
| 中达人 | 5千-5万 | 询价型 |
| 小达人 | <5千 | 爆款突出型 |

话术内容包含：
- 初始联系话术（TikTok DM）
- 跟进消息模板

## 邮箱提取 (extract_email.py)

### 使用方式

```bash
# 从Excel文件提取联系方式
python scripts/outreach/extract_email.py "outputs/KOL达人评分最终报告.xlsx"
```

### 功能特点

- 使用 OpenAI GPT-4o-mini 模型
- 从 signature 字段提取邮箱、Instagram、WhatsApp 等联系方式
- 支持多种联系方式格式

## 工作流入口 (kol_workflow.py)

```bash
# 查看项目状态
python kol_workflow.py --status

# 步骤1: 发现达人（已废弃）
python kol_workflow.py --step 1

# 步骤2: 获取数据
python kol_workflow.py --step 2 --limit 50

# 步骤3: 提取邮箱
python kol_workflow.py --step 3

# 步骤4: 评分分析
python kol_workflow.py --step 4

# 步骤5: 建联追踪
python kol_workflow.py --step 5

# 步骤6: 发送邮件
python kol_workflow.py --step 6 --login

# 运行多个步骤
python kol_workflow.py --step 3-5
python kol_workflow.py --all
```

## 依赖

```
pandas>=2.0.0
openpyxl>=3.1.0
numpy>=1.24.0
requests>=2.31.0
openai>=1.0.0
playwright>=1.40.0
python-dotenv>=1.0.0
```

安装 Playwright 浏览器：
```bash
playwright install chromium
```

## 常见问题

### Q: 评分显示"数据不足"？
A: 确保每个达人至少有3个有效播放数据。

### Q: 如何判断报价是否合理？
A: 计算 CPM = 报价 ÷ (平均播放 ÷ 1000)，CPM ≤ 15 为合理。

### Q: 话术保存在哪里？
A: 话术保存在 Excel 报告的"话术"列，可直接复制使用。

### Q: 如何批量处理？
A: 使用 `generate_script.py` 不带参数时，自动处理未建联的 TOP3 达人。
