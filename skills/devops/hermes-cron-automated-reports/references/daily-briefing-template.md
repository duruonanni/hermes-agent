# Daily Multi-Category Briefing Template

Production template for an agent-based cron job delivering a 7-category daily briefing to a construction industry professional in Chengdu. Delivers at 8:00 AM via Feishu DM.

## Cron Job

```python
cronjob(
    action='create',
    name='daily-briefing',
    schedule='0 8 * * *',       # Every morning at 8:00
    enabled_toolsets=['web'],    # Only web search — no terminal or file access needed
    # no_agent=False (default) — LLM-driven
)
```

## Full Prompt Template

```
You are an information assistant for [USER_NAME], who works in [INDUSTRY], based in [CITY].

Every morning at 8:00, search and compile a detailed briefing covering these [N] categories:

Search each category with 1-2 different keywords, taking the top 5 results each.

### Categories

1. **[CATEGORY_1_ICON] CATEGORY_1_NAME**
   Keywords: "keyword1 2026", "keyword2 新闻"
   Focus: what to look for

2. **[CATEGORY_2_ICON] CATEGORY_2_NAME**
   Keywords: "keyword1 最新", "keyword2 调整"
   Focus: what to look for

   [Repeat for all categories]

### Output Format

━━━ Daily Briefing ━━━
📅 YYYY-MM-DD DayOfWeek

[ICON] CATEGORY_1
• [Article title] — 1-line summary (SourceName)
• [Article title] — 1-line summary (SourceName)

[ICON] CATEGORY_2
• [Article title] — 1-line summary (SourceName)
• [Article title] — 1-line summary (SourceName)

[Repeat per category — keep each section 2-3 items]

━━━ Footer message ━━━
```

### Constraints

- All content from real web search results — do not fabricate
- If a category has no results, write "今日暂无相关更新"
- Cite source name (website) per item
- Use [zh-CN] / [en] as appropriate
- No markdown tables — Feishu doesn't support them in post messages
- Avoid box-drawing characters (`━`, `─`, `│`) — they trigger Feishu delivery errors 99992402

## Production Example (7-Category)

The actual prompt used for Raya (construction industry, Chengdu):

### 1. 🏗️ 建筑行业动态
- Keywords: "建筑行业 最新政策 2026", "建筑工程 行业新闻 新规"
- Focus: policy changes, large project updates, industry trends

### 2. 💰 工程造价资讯
- Keywords: "工程造价 最新资讯 计价", "造价行业 数字化 定额调整"
- Focus: pricing adjustments, digital transformation, industry conferences

### 3. 🌍 国际局势
- Keywords: "国际局势 最新 中美", "亚太 地缘政治 今天"
- Focus: Asia-Pacific geopolitics, US-China relations, global economy

### 4. 📰 时事热点
- Keywords: "今日热点新闻 国内", "今日要闻 社会"
- Focus: domestic major news, social hot topics

### 5. 🎪 成都活动指南
- Keywords: "成都 周末活动 展览 YYYY年MM月", "成都 演出 市集 近期"
- Focus: local exhibitions, performances, markets, lectures — include location + time
- **Must provide specific location and time for each event**

### 6. 💡 生活小妙招
- Keywords: "生活小妙招 实用", "生活技巧 厨房 收纳 省钱"
- Focus: 1-2 practical life tips (storage, cleaning, cooking, money-saving)

### 7. 📚 每日涨知识
- Keywords: "公务员考试 常识判断 知识点", "每日一学 百科知识 冷知识"
- Focus: civil service exam style general knowledge — astronomy, geography, history, tech, law, economics. 1-2 items with brief explanations (2-3 sentences each)

### Output Template

```
━━━ 每日信息差简报 ━━━
📅 YYYY年MM月DD日 星期X

🏗️ 建筑行业
• [Title] — Summary (Source)
• [Title] — Summary (Source)

💰 工程造价
• [Title] — Summary (Source)
• [Title] — Summary (Source)

🌍 国际局势
• [Title] — Summary (Source)
• [Title] — Summary (Source)

📰 时事热点
• [Title] — Summary (Source)
• [Title] — Summary (Source)

🎪 成都活动
• [Event] — 📍Location | 🕐Time | Description

💡 生活小妙招
• [Tip Title]: How-to description

📚 每日涨知识
• [Category] Knowledge Point
  Brief explanation (2-3 sentences)

━━━ 以上为每日自动推送，回复关键词可查看详情 ━━━
```

## Customization Checklist

When adapting for another user:

- [ ] Change user name, industry, city
- [ ] Adjust categories to match their profession/interests
- [ ] Update search keywords for each category
- [ ] Choose output language (zh-CN / en)
- [ ] Set delivery time based on their timezone
- [ ] Verify the schedule cron expression (Beijing = UTC+8)
- [ ] Run `cronjob(action='run', job_id='...')` to test
- [ ] Review output and iterate based on user feedback

## Common Adjustments

| Issue | Fix |
|-------|-----|
| Too many results per category | Limit to 2-3 items in the prompt |
| Not enough local events | Narrow keyword to "成都 TODAY+WEEKEND" |
| Life tips are boring | Add "实用 2026" or specific topics the user likes |
| Trivia too shallow | Add "公务员考试 真题" for exam-grade rigor |
| Delivery error | Check for box-drawing chars in the template |
