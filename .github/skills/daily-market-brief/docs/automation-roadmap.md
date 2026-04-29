# Automation Roadmap

## 当前阶段：MVP 可运行

当前版本已经做到：

- 五个模块统一走同一套 CLI 和 artifact 结构
- 关键模块先出 temp，剩余模块补 final
- 配置变更可以改变 coverage 范围，但不会改坏报告结构
- 每个配置驱动对象都有显式状态

## 下一阶段：来源硬化

下一阶段优先做的不是“加更多模块”，而是把现有来源变得更稳：

- 为 commodities 绑定更稳定的 live symbol adapter
- 为 social/research 增加更多可持续的 HTTP feed 入口
- 把 `source_missing` 细分成更有操作性的错误原因

## 再下一阶段：运营化

当单次流程稳定后，再补这些：

- 连续交易日稳定性观测
- 运行时指标和告警
- 更细的人工复核触发器
- 更完整的 runbook

## 判断标准

每进入下一阶段，必须先确认三件事：

1. 当前阶段的 artifact contract 没有破坏
2. temp/final 的交付速度没有明显变慢
3. 新增自动化不会让人工 review 失去抓手