# KOL Workflow - 达人投放管理系统

一套完整的KOL达人投放工作流，从产品分析到达人建联全流程自动化。

## 项目简介

KOL Workflow 是一个自动化的KOL（Key Opinion Leader）达人投放管理系统，帮助品牌方高效地完成达人营销全流程。系统支持从产品话题生成、达人搜索、评分筛选、联系方式提取、建联话术生成到邮件发送的完整工作流。

## 核心功能

### 🎯 完整工作流

1. **生成产品话题关键词** - 根据产品特点智能生成搜索关键词
2. **搜索达人并爬取数据** - 使用TikHub API搜索TikTok达人并获取详细数据
3. **评分筛选达人** - 8维度加权评分，智能确定投放优先级
4. **提取联系方式** - 从达人签名中智能提取邮箱、Instagram、WhatsApp等
5. **生成建联话术** - 基于达人数据生成个性化邀约话术
6. **发送邮件** - 通过Playwright自动化发送Gmail邮件

### 📊 8维度评分系统

- 体量权重（粉丝数与播放量关系）
- 数据质量（播放稳定性、变异系数）
- 爆款识别
- 性价比分析（CPM计算）
- 趋势分析
- 内容匹配度
- 互动率评估

## 技术栈

- **Python 3.8+**
- **TikHub API** - TikTok数据获取
- **OpenAI API** - 智能话术生成
- **Playwright** - Gmail自动化
- **Pandas/OpenPyXL** - 数据处理

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/hamburger848/kol-workflow.git
cd kol-workflow
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. 配置环境变量

创建 `.env` 文件并配置以下环境变量：

```env
TIKHUB_API_KEY=your_tikhub_api_key
OPENAI_API_KEY=your_openai_api_key
DEFAULT_OUTPUT_PATH=assets/outputs/KOL达人评分最终报告.xlsx
PRODUCT_INFO_FILE=references/产品信息.md
SCRIPT_STRATEGY_FILE=references/邀约话术.md
GMAIL_AUTH_STATE=gmail_auth_state.json
```

**获取API密钥：**
- TikHub API: https://tikhub.io
- OpenAI API: https://platform.openai.com

## 使用方法

### 快速开始

```python
from scripts.search.tikhub_client import TikHubClient
from scripts.analyze.anaylze_kol_v2 import run_kol_analysis
from scripts.outreach.extract_email import extract_contact_with_ai
import os

output_path = os.getenv("DEFAULT_OUTPUT_PATH")

# 步骤1: 搜索达人
client = TikHubClient()
users = client.search_tiktok_users(keyword="skincare", output_path=output_path)

# 步骤2: 爬取达人数据
for user in users:
    client.fetch_kol_play_data(sec_uid=user["sec_uid"], output_path=output_path)

# 步骤3: 评分筛选
run_kol_analysis(output_path)

# 步骤4: 提取联系方式
extract_contact_with_ai(output_path)
```

### 发送邮件

```python
from scripts.outreach.playwright_gmail_sender import GmailAutoSender

sender = GmailAutoSender(auth_state_path="gmail_auth_state.json")
sender.login()  # 首次运行需要登录
sender.send_from_excel(delay=30)  # 发送间隔30秒
```

## 项目结构

```
kol-workflow/
├── scripts/                    # 核心代码
│   ├── search/
│   │   └── tikhub_client.py    # TikHub API客户端
│   ├── analyze/
│   │   └── anaylze_kol_v2.py  # 8维度评分系统
│   └── outreach/
│       ├── extract_email.py           # 联系方式提取
│       ├── generate_script.py         # 话术生成
│       ├── playwright_gmail_sender.py # Gmail自动发送
│       ├── budget_tracker.py          # 预算跟踪
│       └── contact_tracker.py         # 联系人管理
├── references/                # 配置文件
│   ├── 产品信息.md           # 产品信息模板
│   └── 邀约话术.md          # 话术策略模板
├── requirements.txt           # Python依赖
└── README.md
```

## 核心模块说明

### TikHub Client (`tikhub_client.py`)

TikHub API客户端，支持：
- 搜索TikTok达人
- 获取达人详细数据
- 爬取视频播放数据
- 自动重试和错误处理

### KOL Analyzer (`anaylze_kol_v2.py`)

8维度评分系统，包括：
- 体量权重评分
- 数据质量评估
- 爆款识别
- CPM性价比计算
- 趋势分析
- 内容匹配度
- 互动率评估

### Gmail Sender (`playwright_gmail_sender.py`)

自动化邮件发送：
- Playwright浏览器自动化
- Gmail登录状态保存
- 批量邮件发送
- 可配置发送间隔

## 最佳实践

1. **关键词优化** - 步骤1的话题关键词要精准，直接影响达人搜索质量
2. **API限流** - 步骤2爬取数据时注意API调用频率，避免被限流
3. **优先级排序** - 步骤3评分后优先处理"高"优先级达人
4. **话术定制** - 步骤5话术可根据品牌特点调整模板
5. **发送测试** - 步骤6发送前先测试登录是否成功

## 常见问题

### 评分显示"数据不足"
确保每个达人至少有3个有效播放数据

### CPM报价不知道是否合理
计算 CPM = 报价 ÷ (平均播放 ÷ 1000)，CPM ≤ 15 为合理

### Gmail发送失败
先运行 `--login` 重新登录，确保Playwright浏览器已安装

### 邮箱提取不到
确认达人signature中确实包含联系方式

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过GitHub Issues联系。
