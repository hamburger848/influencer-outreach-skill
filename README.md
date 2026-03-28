# KOL Workflow - AI Agent Skill for KOL Marketing Automation

<div align="center">

**一个可被AI Agent直接调用的KOL达人投放管理Skill**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[English](#english) | [中文](#中文)

</div>

---

<a name="中文"></a>

## 🤖 什么是 Agent Skill？

这是一个专为AI Agent设计的**可执行技能包**。当你在支持Skill的AI助手（如Trae IDE）中使用时，Agent可以：

- ✅ **自动理解用户意图** - 通过决策树判断用户需要哪个步骤
- ✅ **自动执行完整流程** - 从产品分析到达人建联全自动化
- ✅ **智能环境配置** - 自动检查并引导配置环境变量
- ✅ **调用Python脚本** - 直接执行搜索、评分、提取、发送等操作

## 🎯 Skill 能做什么？

当用户说：
- "帮我找一些美妆达人" → Agent自动执行步骤1-2
- "给这些达人评分" → Agent执行步骤3
- "提取联系方式并发邮件" → Agent执行步骤4-6
- "帮我做达人投放" → Agent执行完整流程（步骤0-6）

## 📋 完整工作流

```
步骤0: 环境变量检查 → 引导配置API密钥
步骤1: 生成话题关键词 → 基于产品信息
步骤2: 搜索达人爬取数据 → TikHub API
       ├─ 方案A: 关键词搜索达人
       └─ 方案B: 同类达人扩展
       └─ 获取用户完整信息(含linktree)
步骤3: 评分筛选达人 → 8维度评分系统
步骤4: 提取联系方式 → LLM智能提取(含linktree)
步骤5: 生成建联话术 → 个性化话术
步骤6: 发送邮件 → Gmail自动化
```

## 🚀 快速开始

### 1. 安装为 Skill

将此项目克隆到你的AI助手Skill目录：

```bash
# 对于 Trae IDE
git clone https://github.com/hamburger848/kol-workflow.git
# 将 kol-workflow 文件夹放入 .trae/skills/ 目录
```

### 2. 配置环境变量

Agent会自动引导你配置，或手动创建 `.env` 文件：

```env
TIKHUB_API_KEY=your_tikhub_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_OUTPUT_PATH=assets/outputs/KOL达人评分最终报告.xlsx
PRODUCT_INFO_FILE=references/产品信息.md
SCRIPT_STRATEGY_FILE=references/邀约话术.md
GMAIL_SENDER_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
GMAIL_SENDER_NAME=KOL Workflow
```

**获取API密钥：**
- TikHub API: https://tikhub.io
- OpenAI API: https://platform.openai.com
- Gmail应用专用密码: https://myaccount.google.com/apppasswords

### 3. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. 开始使用

直接告诉AI Agent你的需求：

```
用户: "帮我找一些护肤达人并评分"
Agent: [自动执行步骤1-3，生成报告]

用户: "给高优先级达人发邮件"
Agent: [自动执行步骤4-6，发送邮件]
```

## 📁 项目结构

```
kol-workflow/
├── SKILL.md                    # ⭐ Agent Skill定义文件
│                               # 包含决策树、步骤说明、代码示例
├── scripts/                    # 可执行的Python脚本
│   ├── search/
│   │   └── tikhub_client.py    # TikHub API客户端
│   ├── analyze/
│   │   └── anaylze_kol_v2.py  # 8维度评分系统
│   └── outreach/
│       ├── extract_email.py           # 联系方式提取
│       ├── generate_script.py         # 话术生成
│       └── smtp_gmail_sender.py       # Gmail SMTP发送
├── references/                 # 配置文件
│   ├── 产品信息.md            # 产品信息模板
│   └── 邀约话术.md           # 话术策略模板
└── requirements.txt            # Python依赖
```

## 🔧 SKILL.md 核心机制

`SKILL.md` 是Agent的"大脑"，包含：

### 1. Skill 元数据

```yaml
name: "kol-workflow"
description: "KOL达人投放管理工作流 - 从产品话题生成到达人建联发送的完整流程"
```

### 2. 决策树

Agent通过决策树判断用户意图：

```
用户需求是什么？
├─ 没有明确指定 → 执行全流程
├─ 我只需要某个步骤 → 执行对应步骤
└─ 我不知道在哪一步 → 查看数据文件状态
```

### 3. 步骤定义

每个步骤包含：
- 执行方式说明
- Python代码示例
- 输入输出说明
- 环境变量引用

### 4. 最佳实践与陷阱

Agent会自动避免常见错误，遵循最佳实践。

## 💡 使用场景

### 场景1：新品推广

```
用户: "我们新出了一款面膜，帮我找达人推广"
Agent: 
  1. 询问产品信息并保存到 references/产品信息.md
  2. 生成关键词：#facemask #skincare #beauty
  3. 搜索达人并爬取数据
  4. 8维度评分筛选
  5. 提取联系方式
  6. 生成个性化话术
  7. 发送邮件
```

### 场景2：达人筛选

```
用户: "帮我从已有的达人列表中筛选高性价比的"
Agent:
  1. 读取现有Excel文件
  2. 执行步骤3评分分析
  3. 筛选出高优先级达人
  4. 生成建议报价
```

### 场景3：批量建联

```
用户: "给这些达人发邮件"
Agent:
  1. 提取联系方式（步骤4）
  2. 生成话术（步骤5）
  3. 发送邮件（步骤6）
```

## 🎨 8维度评分系统

Agent使用智能评分系统评估达人：

1. **体量权重** - 粉丝数与播放量关系
2. **数据质量** - 播放稳定性、变异系数
3. **爆款识别** - 识别爆款视频
4. **性价比分析** - CPM计算
5. **趋势分析** - 上升/下降趋势
6. **内容匹配度** - 与产品相关性
7. **互动率评估** - 点赞评论率
8. **综合评分** - 加权总分

## 🛠️ 技术栈

- **Python 3.8+** - 核心语言
- **TikHub API** - TikTok数据获取
- **OpenAI API** - LLM智能处理
- **Playwright** - 浏览器自动化
- **Pandas/OpenPyXL** - 数据处理

## 📝 开发新的 Agent Skill

如果你想开发自己的Agent Skill，参考本项目结构：

1. 创建 `SKILL.md` 文件，定义：
   - Skill名称和描述
   - 决策树逻辑
   - 步骤说明和代码示例
   - 最佳实践

2. 编写可执行的Python脚本

3. 提供配置文件模板

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

<a name="english"></a>

## 🤖 What is an Agent Skill?

This is an **executable skill package** designed for AI Agents. When used in AI assistants that support Skills (like Trae IDE), the Agent can:

- ✅ **Automatically understand user intent** - Via decision tree logic
- ✅ **Execute complete workflows** - From product analysis to influencer outreach
- ✅ **Smart environment configuration** - Auto-check and guide environment setup
- ✅ **Call Python scripts** - Directly execute search, scoring, extraction, and sending

## 🎯 What Can the Skill Do?

When users say:
- "Find me some beauty influencers" → Agent executes steps 1-2
- "Score these influencers" → Agent executes step 3
- "Extract contacts and send emails" → Agent executes steps 4-6
- "Help me with influencer marketing" → Agent executes full workflow (steps 0-6)

## 📋 Complete Workflow

```
Step 0: Environment Check → Guide API key configuration
Step 1: Generate Keywords → Based on product info
Step 2: Search & Crawl → TikHub API
        ├─ Plan A: Keyword search
        └─ Plan B: Similar influencer expansion
        └─ Get full profile (including linktree)
Step 3: Score & Filter → 8-dimension scoring
Step 4: Extract Contacts → LLM smart extraction (including linktree)
Step 5: Generate Scripts → Personalized outreach
Step 6: Send Emails → Gmail automation
```

## 🚀 Quick Start

### 1. Install as Skill

Clone this project to your AI assistant's Skill directory:

```bash
# For Trae IDE
git clone https://github.com/hamburger848/kol-workflow.git
# Place kol-workflow folder in .trae/skills/ directory
```

### 2. Configure Environment

Agent will guide you, or manually create `.env` file:

```env
TIKHUB_API_KEY=your_tikhub_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_OUTPUT_PATH=assets/outputs/KOL达人评分最终报告.xlsx
PRODUCT_INFO_FILE=references/产品信息.md
SCRIPT_STRATEGY_FILE=references/邀约话术.md
GMAIL_SENDER_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
GMAIL_SENDER_NAME=KOL Workflow
```

**Get API Keys:**
- TikHub API: https://tikhub.io
- OpenAI API: https://platform.openai.com
- Gmail App Password: https://myaccount.google.com/apppasswords

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Start Using

Just tell the AI Agent what you need:

```
User: "Find me skincare influencers and score them"
Agent: [Auto executes steps 1-3, generates report]

User: "Send emails to high-priority influencers"
Agent: [Auto executes steps 4-6, sends emails]
```

## 📁 Project Structure

```
kol-workflow/
├── SKILL.md                    # ⭐ Agent Skill definition file
│                               # Contains decision tree, steps, code examples
├── scripts/                    # Executable Python scripts
│   ├── search/
│   │   └── tikhub_client.py    # TikHub API client
│   ├── analyze/
│   │   └── anaylze_kol_v2.py  # 8-dimension scoring
│   └── outreach/
│       ├── extract_email.py           # Contact extraction
│       ├── generate_script.py         # Script generation
│       └── smtp_gmail_sender.py       # Gmail SMTP sending
├── references/                 # Configuration files
│   ├── 产品信息.md            # Product info template
│   └── 邀约话术.md           # Script strategy template
└── requirements.txt            # Python dependencies
```

## 🔧 SKILL.md Core Mechanism

`SKILL.md` is the Agent's "brain", containing:

### 1. Skill Metadata

```yaml
name: "kol-workflow"
description: "KOL influencer marketing workflow - complete process from product topic generation to influencer outreach"
```

### 2. Decision Tree

Agent determines user intent via decision tree:

```
What does the user need?
├─ Not specified → Execute full workflow
├─ Need specific step → Execute that step
└─ Don't know progress → Check data file status
```

### 3. Step Definitions

Each step includes:
- Execution instructions
- Python code examples
- Input/output specifications
- Environment variable references

### 4. Best Practices & Pitfalls

Agent automatically avoids common errors and follows best practices.

## 💡 Use Cases

### Case 1: New Product Launch

```
User: "We launched a new face mask, help me find influencers"
Agent: 
  1. Ask for product info and save to references/产品信息.md
  2. Generate keywords: #facemask #skincare #beauty
  3. Search influencers and crawl data
  4. 8-dimension scoring and filtering
  5. Extract contact information
  6. Generate personalized scripts
  7. Send emails
```

### Case 2: Influencer Filtering

```
User: "Help me filter cost-effective influencers from existing list"
Agent:
  1. Read existing Excel file
  2. Execute step 3 scoring analysis
  3. Filter high-priority influencers
  4. Generate suggested pricing
```

### Case 3: Batch Outreach

```
User: "Send emails to these influencers"
Agent:
  1. Extract contacts (step 4)
  2. Generate scripts (step 5)
  3. Send emails (step 6)
```

## 🎨 8-Dimension Scoring System

Agent uses intelligent scoring to evaluate influencers:

1. **Volume Weight** - Follower vs view relationship
2. **Data Quality** - View stability, coefficient of variation
3. **Viral Detection** - Identify viral videos
4. **Cost-Effectiveness** - CPM calculation
5. **Trend Analysis** - Upward/downward trends
6. **Content Match** - Product relevance
7. **Engagement Rate** - Like/comment rates
8. **Overall Score** - Weighted total

## 🛠️ Tech Stack

- **Python 3.8+** - Core language
- **TikHub API** - TikTok data retrieval
- **OpenAI API** - LLM intelligent processing
- **Playwright** - Browser automation
- **Pandas/OpenPyXL** - Data processing

## 📝 Develop Your Own Agent Skill

To develop your own Agent Skill, reference this project structure:

1. Create `SKILL.md` file defining:
   - Skill name and description
   - Decision tree logic
   - Step instructions and code examples
   - Best practices

2. Write executable Python scripts

3. Provide configuration file templates

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

MIT License

---

<div align="center">

**Made with ❤️ for AI Agent Automation**

</div>
