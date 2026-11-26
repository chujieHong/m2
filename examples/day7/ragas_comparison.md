# Day 7：RAGAS 与自定义评分对照

查阅时间：2026-10-12；运行记录更新：2026-10-13。RAGAS 0.4.3 已安装，通过 M1/DeepSeek 完成一条真实回答的 Faithfulness 及编号格式对照，Answer Relevancy 的本地 BGE 接入与三条对照也已运行。

## 忠实度

我们的函数让裁判按规则直接给整条回答打 0～2 分。RAGAS 的 Faithfulness 则先抽取回答中的事实陈述，再判断每条是否能由实际检索上下文推出，最后计算“获得支持的陈述数 / 总陈述数”，分数在 0～1。

教学资料：发票申请后 2 个工作日内开具；退款审核通过后 3 个工作日内到账。

教学回答：发票 2 个工作日内开具；退款审核通过后 3 个工作日内到账；客服全天在线。

若恰好抽取为三个陈述，则前两个有依据，第三个缺少依据，手算支持比例为 2/3。我们的混合陈述规则通常记忠实度 1。这不是一次实际 RAGAS 调用；实际陈述拆分、支持判断仍受模型影响。不能把自定义得分除以 2 当成 RAGAS 得分。

该方法以回答的陈述为分母，不以参考答案应有事实为分母。只回答一个正确且有依据的事实，仍可能得到高忠实度，同时答案不完整。因此忠实度不替代正确性或完整性评估。

## 回答相关性

官方 Response Relevancy 页面介绍的 Answer Relevancy 方法：从回答反向生成若干可能的问题（默认三个），用向量比较这些问题与原始问题，再取平均余弦相似度。这不是我们的 0～2 分直接裁判判断。通常分数在 0～1，但余弦相似度的数学范围允许负值，不能将其看作概率。

该指标不检查事实正确性，需要 LLM 与 Embedding。采用哪个模型及怎样生成反向问题，都会影响分数。尤其不能直接套用我们“针对当前问题拒答相关性为 2”的自定义约定。

## 实验边界

现有 100 题报告继续标为自定义三维评分；39 条复核继续标为 AI 交叉审核。不把查阅文档或导入成功记为实际框架评分完成。

## 接入准备

评测可选依赖已固定 `ragas==0.4.3`、`langchain-community<0.4`；后者避免 0.4 移除 ChatVertexAI 导致的实际导入错误。本地最终安装 community 0.3.31。因官方源轮子下载缓慢，项目使用阿里云公共 PyPI 镜像，同步命令为 `uv sync --extra evaluation --link-mode copy`。M2 环境的 M1 调用选项测试 36 条通过。

本地核对了 `InstructorBaseRagasLLM` 的 `generate` / `agenerate` 接口，以及 collections 中的 `Faithfulness`。学习者已完成 `src/kb/ragas_adapter.py` 的核心方法，助手修正了 generate 方法的缩进；mypy 通过。异步入口用工作线程运行同步方法。

## 一条真实运行与编号对照

题目 `single_hop_001`，回答为“Bucket ACL 的默认权限值是 private。[1]”。第一次传入原始片段正文，RAGAS/DeepSeek 抽出两条陈述：默认 private；该信息在引用 [1] 中说明。第二条因为评测上下文没有编号被判不支持，得分 1/2=0.5。初次结果保存在 `data/eval_results/ragas_faithfulness_single_hop_001.json`。

只给同一顺序的片段补上生成时使用的 [1]、[2]、[3]，再次评测抽出了相同的两条陈述，并都判为支持，得分 2/2=1.0。新结果在 `data/eval_results/ragas_faithfulness_single_hop_001_numbered.json`。回答和原始资料未改，两个输出均保留；离线核对了事实列表一致、编号映射与支持比例计算。

这说明应保持评测资料与生成时引用编号的对应，不将缺失的编号格式误当作答案事实错误。它仍是单条观察，不证明整个 RAGAS 裁判可靠，也不是完整 100 题的 RAGAS 基线。事实拆分将引用说明计为一条陈述，同样需要检查其合理性。

运行入口 `scripts/run_ragas_faithfulness.py` 默认使用 numbered 上下文，记录实际提供的片段并保留中间结构化输出；`--context-format raw` 可对照。未生成可评分事实时 RAGAS 可给 NaN，脚本记为 unscorable 和 null，不能当作零分或成功。

## 回答相关性实际对照

`src/kb/ragas_embeddings.py` 适配已缓存的 BAAI/bge-small-zh-v1.5；原问题与反向问题都使用 query_embed，模型只初始化一次并禁止下载缺失模型。mypy 通过。`scripts/run_ragas_relevancy.py` 调用官方 collections 的 AnswerRelevancy，strictness=3，并本地核对平均余弦相似度及 noncommittal 处理公式。

原问题：Bucket ACL 默认是什么权限值？

| 回答 | 来源 | 实际相关性 |
| --- | --- | ---: |
| 默认 private。[1] | 先前保存的真实生成回答 | 0.97594 |
| 默认 public-read。 | 助手故意写错的教学反例 | 0.97594 |
| UploadPart 的 Action 为 oss:PutObject。 | 助手编写的答非所问反例 | 0.73106 |

结果保存在 `data/eval_results/ragas_relevancy_comparison.json`。前两条均反推为“Bucket ACL 的默认权限值是什么？”，故得到完全相同的分数。这实测说明该相关性不能判断 private/public-read 哪个正确。

第三条反推为 UploadPart 的权限问题，分数较低但仍有 0.73；不能把余弦相似度解释成正确概率，也不能未经自己的数据验证就采用 0.7 等统一阈值。以上只验证单题加反例，分数依赖当前 BGE 编码与生成模型，不是完整 100 题的 RAGAS 基线。

每个回答的三次生成在本次均得到完全相同的反向问题，仅一个不同问题。strictness=3 在此不代表三个不同角度或三个独立证据；温度0和相同提示词下重复问题没有带来多样性。非拒答样例的 noncommittal 均为0；尚未用本入口实测拒答的框架得分。

官方来源：

- [Faithfulness](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/)
- [Response Relevancy](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/answer_relevance/)
