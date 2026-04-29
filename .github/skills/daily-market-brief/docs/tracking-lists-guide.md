# Tracking Lists Guide

## 维护目标

tracking lists 的作用不是“把来源堆得越多越好”，而是用最少、最稳的核心对象覆盖盘前判断所需的范围。

## 三类清单怎么维护

### social_accounts

- 适合放：高频讨论、观点扩散快、能代表市场短线情绪的账号流
- 不适合放：噪音大、更新不稳定、经常脱离盘面主题的来源

示例：

```yaml
- item_id: eastmoney-forum
  item_type: social_account
  display_name: 东方财富股吧精选
  enabled: true
  priority: core
  source_locator: https://example.com/feeds/eastmoney-forum.xml
```

### research_institutions

- 适合放：更新频率稳定、观点影响力高的券商或研究机构
- 不适合放：很少更新、来源结构经常变化的入口

示例：

```yaml
- item_id: huaan
  item_type: research_institution
  display_name: 华安证券研究
  enabled: true
  priority: core
  source_locator: https://example.com/research/huaan.rss
```

### commodities

- 适合放：能直接影响 A 股重点链条的商品
- 不适合放：对盘前判断帮助很弱、且数据抓取成本高的长尾品种

示例：

```yaml
- item_id: aluminum
  item_type: commodity
  display_name: 沪铝
  enabled: true
  priority: extended
  source_locator: ALUMINUM
```

## 调整策略

- 想扩大覆盖：优先新增 `extended`，跑几轮稳定后再升到 `core`
- 想缩小范围：先把对象设为 `enabled: false`，不要立刻删掉
- 想彻底移除：确认最近几轮都没有价值，再删掉条目

## 调整后要做什么

每次修改 tracking lists 后，至少跑一次：

```bash
pytest .github/skills/daily-market-brief/tests/integration/test_config_update_roundtrip.py -q
```

这个测试保证范围可以变，但报告结构不能被改坏。