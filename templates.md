# idea-forecast 模板

## 0. CONFIG.md（放在 `<project>/idea-stage/terrain/CONFIG.md`）

```
direction: <一句话方向，例：智能体自进化 / 自改进 RL>
mode: <lineage | shoots | compare>
as_of: <YYYY-MM-DD，"最近 90 天"从这天倒算>
judge: <主会话模型，用你手上最强的推理模型>
searcher_A: <子代理模型，推荐 Opus 级；同一时刻只跑一个>
searcher_B: <外部 CLI 命令模板或 none；{out} 为输出文件，例：codex exec --skip-git-repo-check --ephemeral -s read-only -o {out} ->
backbone_queries: <引用骨干的检索词，至少两组，例：'"self-evolving" agent' / '"self-improving" "language model"'>
budget: A 子代理 <n> 次；B 调用 <n> 次；每次 B 约 5–10 万 token
local_repos: <本机已 clone 的相关仓库路径，逗号分隔>
```

## 1. 原子主张表（CLAIMS.md 的每一行）

| ID | 类型 | 主张（一句） | 测量单元 | 目标量 | 依赖 | 状态 | 最近邻（卡片 ID） | 差值类型 |
|---|---|---|---|---|---|---|---|---|
| E1 | 经验前提 | <某个已被测量的事实，例：对齐增益主要来自偏好数据而非 RL 算法> | <题 / 样本 / 模型> | <比例 / 均值差> | — | 未查 | | |
| M1 | 机制 | <某条机制预测，例：奖励模型过优化随规模不消失> | <组件×模型> | <斜率> | E1 | 未查 | | |
| A1 | 构件 | <某个构件，例：直接在偏好对上优化策略> | <样本对> | <胜率> | E1 | 有先例（<id>） | | 单元替换 |
| A1+A2 | 接合 | <构件 1 + 构件 2 的接合处> | <单元> | <目标量> | A1,A2 | 检索范围内未见 | | 整合型 |

状态只能是四个之一：未查 / 有先例 / 部分先例 / 检索范围内未见。`[abstract-only]` 表示未读正文，不能支撑"未见"。

## 2. 检索矩阵（每个原子一份，写进 CLAIMS.md 的检索日志）

| 词汇轴 | 时间片 | 来源 | 查询串 | 命中（ID/链接） | 读了正文? |
|---|---|---|---|---|---|
| 本领域 | 最新 90 天 | arXiv | | | |
| 相邻领域 1 | 经典 ≤2018 | 会议/期刊 | | | |
| 相邻领域 2 | 2019–2024 | arXiv | | | |
| 相邻领域 3 | 最新 90 天 | arXiv | | | |
| 工程/产品 | 最新 90 天 | 博客/changelog/issue | | | |
| 经典 | ≤2018 | 原始文献 | | | |

### 相邻领域词表（按原子类型选 ≥3；复盘时增补）
- 预算分配 / 选题 / 何时停：ranking and selection（two-stage、KN）、best-arm identification、active learning for model comparison（Sawade 2012）、computerized adaptive testing / IRT、optimal experimental design、sequential testing / e-process
- 组合 / 覆盖 / 路由：algorithm portfolios（marginal contribution）、per-instance algorithm selection、MAP-Elites / quality-diversity、submodular selection、mixture-of-experts routing
- 组件 × 模型能力：scale-dependent prompting、prompt inversion、harness-benefit、capability-dependent scaffolding、scaffold obsolescence
- 接受 / 保留 / 撤销：dependency management（semver、lockfile）、feature flags & rollback、regression testing、change management
- 多智能体 / 群体进化：cultural evolution、credit assignment、diversity collapse、population-based training
- 验证预算 / 接受器：verification budget、false-commit rate、selection regret、winner's curse clean-up（Boesel–Nelson–Kim）
- 训练信号 / 外部信息：active learning label acquisition、value of information（Howard 1966）、teaching on a budget、KWIK、learning to ask / help-seeking、privileged information distillation
- 评测有效性：construct validity、benchmark contamination、selection bias、multiple comparisons

### 来源清单（必须覆盖三类）
- 学术：arXiv（含 listing 最近 90 天）、Semantic Scholar、OpenReview
- 工程/产品：Anthropic engineering blog 与 Claude Code docs/changelog、OpenAI cookbook/Codex docs、Cursor changelog、LangChain/LangGraph docs
- 代码：GitHub（相关仓库 README 方法节、issue 讨论）、本机已 clone 的仓库

## 3. 近邻矩阵（每个原子）

| 近邻 | 做了什么（一句） | 测量单元 | 目标量 | 与本原子的精确差值 | 差值类型 | 证据原句 | 读取深度 |
|---|---|---|---|---|---|---|---|

差值类型：单元替换 / 加一列 / 改名 → 增量；接合 → 整合型；新对象 / 新测量 / 新仪器 → 可立项。

## 4. 竞争者画像

| 团队/产品 | 已做到 | 下一步最可能 | 时间窗 | 被抢概率 | 被抢后我们剩什么 |
|---|---|---|---|---|---|

## 5. 前提表与极限证据表（AXIOMS.md，模式 forecast 的核心）

| # | 前提（一句） | 在脉络里的样子（哪些工作默认它） | 极限证据（≥2 张全文卡，原句） | 是"做到头也不行"还是"还没做好"？ | 如果前提没错会看到什么 |
|---|---|---|---|---|---|

## 6. 否定推演表（每条前提一行）

| 前提 | 否定/替换后的世界 | 新对象 | 新目标量 | 不再需要 | 变成必需 | 别的领域怎么活 | 机制链 | 排序分（硬度 × 无人 × 可做） |
|---|---|---|---|---|---|---|---|---|

## 7. 杀伤测试清单（开实验前）

- [ ] 前提已测？每个 E 原子列出已有测量与其方向；反向结果已写入备择假设
- [ ] 构件即构念？每个臂写一句"它与概念的差别"；差别不为零则改臂
- [ ] 骨架已有？列出用过同设计的工作及其统计强度；只报我们新增的格子
- [ ] 可检出？最小可检测效应（按现有方差）与并列主量
- [ ] 最便宜的证伪路径？本地已有数据能否先否掉

## 8. 预注册头

- 原子 ID 与地形图卡片 ID
- 主量 / 并列主量 / 口径
- 判据三选一或更多形状（含非单调），判据先于数据
- 退路 A/B/C（按脆弱程度）
- 预算上限与停止规则

## 9. 三段输出模板（FORECAST_<date>.md）

```
# <方向> 选题预测（<date>）

## 一、发现的规律
（F2 的事实 1..n，每条：一句话 + 数字 + 原句 + 卡片 ID）
（F3 的前提表与极限证据表，直接贴）

## 二、已做的边界
（门 3 近邻差值表 ≤10 行；竞争者画像；本地已有的仪器与数据一句话）

## 三、未来可做的 idea
主押注：<新形态一句话>
第一个可检验实例：<臂 / 主量 / 判据 / 一个月内可做>
依赖的预测：<机制链；时间窗；可观察标志；错了会看到什么>
退路：A / B / C
备选（不同方向）：<一句话 + 为什么没押它>
被抢概率与竞争者：<表>
杀伤测试：四项结果
```

## 10. 芽卡（shoots 路线 S1，每颗芽一张，放 cards/）

```
id / 链接 / 日期 / 读取深度（full text | abstract-only）
解决了什么（一句，带数字）：
默认前提（它没质疑的假设）：
暴露了什么新问题：
被广泛采用后会发生什么：
原句：
```

## 10b. COMPARE 表（compare 模式，COMPARE_<date>.md）

| 候选 idea | 来自路线 | 证据硬度 1–5 | 门 3 类型 | 门 4 通过项 | 第一实例可做性 | 被抢概率 | 两路线是否同押 | 裁判备注（引卡片） |
|---|---|---|---|---|---|---|---|---|

结论行：哪条路线的主押注更硬、为什么；两条路线各自漏掉了什么；下次对比要改什么。

## 11. POSTMORTEM 条目

| 日期 | idea | 被谁做过 | 本可在哪个门拦住 | 缺的检索词/来源 | 本地是否已有 | 已增补到词表? |
|---|---|---|---|---|---|---|

## 12. 搜索者 B 的 brief 模板

用法：填好存成 `terrain/briefs/<name>.md`，然后
`python <skill>/scripts/search_b.py --brief terrain/briefs/<name>.md --name <name> --project <idea-stage>`（命令模板来自 CONFIG 的 searcher_B 或环境变量 SEARCH_B_CMD）

```
### Atoms (from gate 1; one line each: ID | type | claim | measurement unit | target quantity)
A1 | method | <one-line claim> | <unit> | <target quantity>
E1 | premise | <one-line measured fact> | <unit> | <quantity>

### Vocabulary axes to cover for EVERY atom (at least 2 queries per axis)
- own field: <...>
- adjacent fields: <3 from section 2>
- engineering/product: <blogs, docs, changelogs, issues>
- classic (<=2018): original statistics / SE / psychometrics literature

### Time slices: classic <=2018; 2019-2024; last 90 days (after <as_of - 90d>)

### Already known to this project (do NOT re-report, but DO report anything that cites or extends them)
<paste ids from terrain_index --query>

### Deliverable: the table + "Closest prior work per atom" + "Queries run"
```
