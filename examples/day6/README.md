# Day 6：固定的 100 题 OSS 开发评测集

出题工作已集中完成。旧的教学题集和报告仍保留，本目录使用独立语料、集合和报告。

## 文件

- `oss_cases_100.json`：100 道题，带参考答案、必要原文依据、事实 ID、来源和情景前提。
- `oss_corpus.md`：配套固定学习摘记，不是官方全文。
- `facts.json`：52 个事实/短表块及对应的官方来源。
- `manifest.json`：版本、配比、来源、采集日期和内容 SHA-256。
- `baseline.json`：通过核对的 top-1/top-3 结果与报告位置。

## 配比

| 题型 | 数量 |
| --- | ---: |
| 单跳事实 | 40 |
| 多跳 | 20 |
| 对比 | 15 |
| 表格/数值 | 15 |
| 资料不足，应当拒答 | 10 |

单跳指依据同一事实或段落即可回答，不要求只有一个数值。多跳题至少涉及两个规则块，需要串联或应用规则。表格题包括边界和例外，相同规则的多个边界问题并非独立样本。

## 本次完成的审核

- 助手逐题核对参考答案、条件、单位与官方来源，所有题标为 `assistant_reviewed`。
- 检查题数/配比、唯一 ID、重复问题、空字段、可回答性与依据对应关系。
- 验证依据存在于配套材料及来源事实块中，且完整保留在实际索引中。
- 独立重新核对报告引用的候选正文、缺失依据、字符数、逐题分数与汇总。
- 确认资料不足题不计入检索覆盖率，分数为 null；这不是已经验证了生成拒答。

这是开发/回归集，包含已讨论规则和已查看题目，不作为独立测试集。不是用户或外部专家完成的独立人工评审，也不是生产验收数据集。

## 基线

使用 BAAI/bge-small-zh-v1.5、Chroma 余弦距离、正文上限 400 字符、overlap=0。资料有 53 条索引记录，包含标题与来源文字。

| 参数 | 可回答题平均依据覆盖率 |
| --- | ---: |
| top-1 | 56.11% |
| top-3 | 80.37% |

90 道可回答题参与上述均值。10 道资料不足题保留检索记录，不进入此均值。这里是严格原文包含检查，不是标准 Recall、语义忠实度、生成准确率或拒答率。

| 题型 | top-1 | top-3 |
| --- | ---: | ---: |
| 单跳事实 | 75.00% | 92.50% |
| 多跳 | 25.83% | 52.50% |
| 对比 | 38.89% | 75.56% |
| 表格/数值 | 63.33% | 90.00% |

新语料包含更广的事实和更多候选，不能直接把此均值与此前小题集比较成系统变好或退步。样例数量本身也不保证能分辨某个固定百分比的改进。

## 复现

在 `D:\develop\m2` 执行：

```powershell
.\.venv\Scripts\python.exe scripts/prepare_day6_dataset.py
.\.venv\Scripts\python.exe scripts/build_index.py --document examples/day6/oss_corpus.md --collection day6_oss_v1_bge_small_zh --id-prefix day6-oss
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --cases examples/day6/oss_cases_100.json --collection day6_oss_v1_bge_small_zh --top-k 1
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --cases examples/day6/oss_cases_100.json --collection day6_oss_v1_bge_small_zh --top-k 3
.\.venv\Scripts\python.exe scripts/validate_day6_dataset.py
```

以上是固定 v1 的复现方法。变更资料、切片或题目应建立新版本/新集合，不要把旧报告当成新版本结果；当前建库 upsert 不自动清理多余旧 ID。

检查程序会核对内容指纹和实际索引。在候选生成之外未调用 DeepSeek，不产生生成接口调用。相关基线位于 `data/eval_results/day6_oss_v1_bge_small_zh_oss_cases_100_top1.json` 和 `...top3.json`。

## 来源与范围

采集及核对日期：2026-10-12。官方页面列表在 `manifest.json` 中，每个事实和可回答题也有对应来源。

- [Bucket ACL](https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl)
- [Object ACL](https://help.aliyun.com/zh/oss/user-guide/object-acl)
- [阻止公共访问](https://help.aliyun.com/zh/oss/user-guide/block-public-access/)
- [UploadPart](https://help.aliyun.com/zh/oss/developer-reference/uploadpart)
- [ListParts](https://help.aliyun.com/zh/oss/developer-reference/listparts)
- [版本控制](https://help.aliyun.com/zh/oss/user-guide/overview-78/)
- [删除标记](https://help.aliyun.com/zh/oss/user-guide/delete-marker)
- [暂停版本控制下 Object 操作](https://help.aliyun.com/zh/oss/user-guide/manage-objects-in-a-versioning-suspended-bucket)
- [开启版本控制下 Object 操作](https://help.aliyun.com/zh/oss/manage-objects-in-a-versioning-enabled-bucket)
- [基于最后修改时间的生命周期规则](https://help.aliyun.com/zh/oss/lifecycle-rules-based-on-the-last-modified-time)
- [保留策略](https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies)

引用使用原始页面，检索使用经过整理的摘记。资料不足标签相对于这份材料，不代表整个 OSS 官方网站不存在答案。数值单位按来源保留，不擅自推断字节换算。情景假定配置/上传/删除操作已满足权限，但不额外给匿名用户添加授权。

后续学习重点是 Day 7 的检索指标与生成评测，不需要继续手工抄题。外部技能课程和独立人工审核未因这次批处理自动完成。
