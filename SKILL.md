***

name: "kol-workflow"
description: "KOL达人投放管理工作流 - 从产品话题生成到达人建联发送的完整流程。当用户需要：生成产品话题关键词、搜索达人并爬取数据、评分筛选达人、提取联系方式、生成建联话术、发送邮件时调用此技能。"
------------------------------------------------------------------------------------------------------------

***

# KOL Claw - 达人投放管理系统

一套完整的KOL达人投放工作流，从产品分析到达人建联全流程自动化。

## 决策树：选择你的下一步

```
用户需求是什么？
│
├─ 没有明确指定 → 默认执行全流程（步骤0→1→2→3→4→5→6）
│   └─ 步骤0：检查环境变量，未配置时引导用户配置
│
├─ 我只需要某个步骤 → 执行对应步骤
│   ├─ 步骤1：生成话题关键词 → 使用环境变量 PRODUCT_INFO_FILE
│   ├─ 步骤2：搜索达人爬取数据 → 使用 DEFAULT_OUTPUT_PATH
│   ├─ 步骤3：评分筛选达人 → 使用 DEFAULT_OUTPUT_PATH
│   ├─ 步骤4：提取联系方式 → 使用 DEFAULT_OUTPUT_PATH
│   ├─ 步骤5：生成建联话术 → 使用 DEFAULT_OUTPUT_PATH
│   └─ 步骤6：发送邮件 → 使用 DEFAULT_OUTPUT_PATH
│
└─ 我不知道在哪一步 → 先查看数据文件状态，判断当前进度
```

## 步骤 0：环境变量配置检查

执行全流程前，检查以下环境变量，未配置时询问用户并添加到 `.env` 文件：

| 环境变量                   | 说明            | 默认值                        |
| ---------------------- | ------------- | -------------------------- |
| `DEFAULT_OUTPUT_PATH`  | 输出文件路径        | `outputs/KOL达人评分最终报告.xlsx` |
| `PRODUCT_INFO_FILE`    | 产品信息文件路径      | `references/产品信息.md`       |
| `SCRIPT_STRATEGY_FILE` | 话术策略文件路径      | `references/邀约话术.md`       |
| `GMAIL_SENDER_EMAIL`   | Gmail 发件人邮箱   | 无（必需）                      |
| `GMAIL_APP_PASSWORD`   | Gmail 应用专用密码  | 无（必需）                      |
| `GMAIL_SENDER_NAME`    | 发件人名称         | 无（必需）                      |
| `TIKHUB_API_KEY`       | TikHub API 密钥 | 无（必需）                      |

***

## 步骤 1：生成并验证产品话题关键词

**核心目标**：生成精准的搜索关键词，确保搜到的达人符合产品定位。

### 1.1 读取产品信息

1. 从环境变量 `PRODUCT_INFO_FILE` 读取产品信息文件
2. 如果文件不存在，询问用户目标产品信息并保存

### 1.2 生成候选关键词（多维度）

根据产品信息，生成 **3类关键词组合**，覆盖不同搜索角度：

| 关键词类型     | 说明              | 生成指导                                                  |
| --------- | --------------- | ----------------------------------------------------- |
| **品类核心词** | 直接描述产品品类        | 精准的产品英文名称，如 `beauty product`, `skincare item`         |
| **用户场景词** | 目标用户的真实生活场景     | 用户日常场景，如 `morning routine`, `daily tips`, `lifestyle` |
| **趋势话题词** | TikTok上该领域的热门话题 | 平台热门但相关的标签                                            |

**关键词生成原则**：

- 优先选择**目标用户会搜索的词**，而非产品名称本身
- 场景词要贴近用户日常生活，如 `morning routine`, `daily tips`
- 避免过于宽泛的词（如 `wellness`, `lifestyle`, `beauty`）
- 避免不相关的词

**禁止生成的词**：

- ❌ 过于宽泛的词（如 `wellness`, `lifestyle`, `generic`）
- ❌ 与产品品类不相关的词（如护肤品禁用 `hair care`, `nail art`）
- ❌ 被API限制的敏感词

### 1.3 向用户确认关键词

展示生成的关键词组合，向用户确认是否使用或修改：

```
关键词组合：
- 主词: "品类核心词"
- 辅词: "用户场景词", "趋势话题词"
- 排除词: 禁止词（过滤用）
```

确认后进入步骤2搜索达人。

## 步骤 2：搜索达人并爬取数据

使用 TikHub API 搜索达人并获取视频数据，所有数据统一保存到最终报告文件。

**统一输出文件**：`DEFAULT_OUTPUT_PATH` 环境变量

**执行方式**：根据用户需求选择方案

### 方案A：关键词搜索达人

根据步骤1确认的关键词，循环调用 `search_users` 搜索达人：

```python
from scripts.search.tikhub_client import TikHubClient
client = TikHubClient()

keywords = ["品类核心词", "用户场景词", "趋势话题词"]
for keyword in keywords:
    users = client.search_users(
        keyword=keyword,
        count=10,
        follower_count="ONE_H_K_PLUS",
        output_path=output_path
    )
```

### 方案B：同类达人扩展

基于已有关达列表，通过 `fetch_similar_user_recommendations` 搜索同类达人：

```python
from scripts.search.tikhub_client import TikHubClient
client = TikHubClient()

# 从 Excel 读取达人 sec_uid
import pandas as pd
df = pd.read_excel(excel_path)
sec_uids = df['sec_uid'].dropna().unique()

# 对每个达人获取同类推荐
for sec_uid in sec_uids:
    similar_users = client.fetch_similar_user_recommendations(
        sec_uid=sec_uid,
        output_path=output_path
    )
```

**说明**：同类达人推荐可扩充达人池，覆盖更多潜在合作对象

### 2.1 获取达人视频数据

对每个达人调用 `fetch_kol_play_data` 获取5个视频的播放数据和内容话题：

```python
from scripts.search.tikhub_client import TikHubClient
client = TikHubClient()

# 从 Excel 读取达人 sec_uid
import pandas as pd
df = pd.read_excel(output_path)
sec_uids = df['sec_uid'].dropna().unique()

for sec_uid in sec_uids:
    client.fetch_kol_play_data(
        sec_uid=sec_uid,
        output_path=output_path
    )
```

**保存内容**：

- 达人基本信息（昵称、粉丝数、签名）
- 5个视频的播放、点赞、评论、收藏、分享数据
- 5个视频的文案
- 内容话题标签（从 hashtag 提取）

### 2.2 向用户确认

展示搜索到的达人数量和覆盖情况，请用户确认是否进入步骤3评分。

**输出**：`DEFAULT_OUTPUT_PATH`（包含达人基本信息、粉丝数、视频播放量、互动数据、文案、内容话题等）

***

## 步骤 3：评分筛选达人

对达人进行 8 维度加权评分，确定投放优先级和报价建议。

3.1 **过滤判断**：根据以下信息判断达人是否适合投放

| 判断维度      | 说明              | 判断标准                                             |
| --------- | --------------- | ------------------------------------------------ |
| **商家账号**  | 是否为商家/工厂账号      | 昵称含 factory, manufacturer, wholesale, supplier 等 |
| **广告内容**  | 视频文案是否全是产品展示/广告 | 缺乏真实生活内容                                         |
| **内容相关性** | 内容是否与产品相关       | 如经期护理、生活分享                                       |
| **真人运营**  | 是否有真人运营         | 真人达人有真实生活内容                                      |

**3.2 评分输出**：总分(0-100)、投放优先级(高/中/低)、建议报价

```python
from scripts.analyze.anaylze_kol_v2 import run_kol_analysis
import os

output_path = os.getenv("DEFAULT_OUTPUT_PATH", "outputs/KOL达人评分最终报告.xlsx")
run_kol_analysis(output_path)
```

**输出**：同一文件中新增评分相关列（总分、投放优先级、建议报价等）

**3.3 向用户确认建联名单**：展示筛选后的达人列表，确认是否进入联系方式提取阶段

**建联名单确认**：

- 投放优先级为"高"的达人
- 已过滤商家账号、广告内容、劣质达人

<br />

***

## 步骤 4：提取联系方式

从达人签名中提取邮箱、Instagram、WhatsApp 等联系方式。对于未提取到邮箱的达人，调用 `fetch_user_profile` 获取 `bio_url`（linktree 链接）。

```python
from scripts.outreach.extract_email import extract_contact_with_ai
import os

excel_path = os.getenv("DEFAULT_OUTPUT_PATH", "outputs/KOL达人评分最终报告.xlsx")
extract_contact_with_ai(excel_path)
```

**输出**：同一文件中新增"联系方式"列

**说明**：
- 使用正则表达式自动识别邮箱、Instagram、WhatsApp 等联系方式
- 对于正则无法提取的联系信息，由 LLM 辅助补充提取
- **当未提取到邮箱时**：调用 `fetch_user_profile` 获取 `bio_url`（linktree 链接），可从 linktree 页面进一步提取邮箱

***

## 步骤 5：生成建联话术

根据达人粉丝量和播放数据以及文案内容判断作品风格，从话术策略文件读取话术模板，生成个性化建联话术。

**执行方式**：

1. 从环境变量 `SCRIPT_STRATEGY_FILE` 读取话术策略文件
2. 让用户确认或修改话术策略
3. 根据达人数据生成个性化话术

**输出**：同一文件中新增"建联话术"列

***

## 步骤 6：发送邮件

通过 Gmail SMTP 发送邮件（更稳定可靠）。

```python
from scripts.outreach.smtp_gmail_sender import GmailSMTPSender
import os

sender = GmailSMTPSender()
sender.send_from_excel(
    excel_path=os.getenv("DEFAULT_OUTPUT_PATH"),
    delay=30
)
```

**执行方式**：

1. 从 Excel 文件读取收件人信息（邮箱、主题、正文）
2. **发送前必须确认**：显示收件人数量、邮件主题预览，请用户确认是否发送
3. 用户确认后开始发送，设置合理的发送间隔（建议30秒以上）

**前提条件**：

1. 配置环境变量 `GMAIL_SENDER_EMAIL` 和 `GMAIL_APP_PASSWORD`
2. 获取应用专用密码：<https://myaccount.google.com/apppasswords>

**参数**：

- `delay`：发送间隔（秒），建议 30 以上
- `html`：是否发送HTML格式邮件（默认False）

***

## 常见陷阱

❌ **评分显示"数据不足"**
→ 确保每个达人至少有 3 个有效播放数据

❌ **CPM 报价不知道是否合理**
→ 计算 CPM = 报价 ÷ (平均播放 ÷ 1000)，CPM ≤ 15 为合理

❌ **Gmail 发送失败**
→ 检查应用专用密码是否正确，确保已启用两步验证

❌ **SMTP认证失败**
→ 确认使用的是应用专用密码而非登录密码，访问 <https://myaccount.google.com/apppasswords> 生成

❌ **邮箱提取不到**
→ 确认达人 signature 中确实包含联系方式

***

## 最佳实践

- 步骤1的话题关键词要精准，直接影响达人搜索质量
- 步骤2爬取数据时注意 API 调用频率，避免被限流
- 步骤3评分后优先处理"高"优先级达人
- 步骤5话术可根据品牌特点调整模板
- 步骤6发送前先测试登录是否成功

***

## 项目结构

```
kol-workflow/
├── SKILL.md                    # 技能定义文件
├── scripts/                    # 可执行代码
│   ├── search/
│   │   └── tikhub_client.py    # TikHub API：搜索达人、爬取数据
│   ├── analyze/
│   │   └── anaylze_kol_v2.py  # 8维度评分分析
│   ├── outreach/
│   │   ├── extract_email.py           # 提取联系方式
│   │   ├── generate_script.py         # 生成建联话术
│   │   └── smtp_gmail_sender.py      # Gmail发送
├── references/                # 文档资料
│   ├── 产品信息.md           # 产品信息
│   ├── 邀约话术.md          # 话术策略模板
├── outputs/                   # 输出目录
│   └── KOL达人评分最终报告.xlsx
├── .env                       # 环境变量配置
└── requirements.txt
```

***

## 前提条件

### 1. 安装依赖

```bash
cd kol-workflow
pip install -r requirements.txt
```

