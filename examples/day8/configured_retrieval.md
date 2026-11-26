# Day 8：配置驱动的单题检索

2026-10-13：实现 scripts/run_experiment.py 单题入口，读取 ExperimentConfig 并复用 VectorRetriever。默认仅检索，添加 --generate 后调用 M1/DeepSeek 生成答案；100题统一评测尚未接入。

同一问题“Bucket ACL 默认是什么权限？”实际运行 top3 和 top5 配置，分别返回3和5个片段；前三个片段 ID 均为 day6-oss-1、day6-oss-7、day6-oss-15。第一条直接包含正确依据。新增的两个候选不代表质量提升。

记录位于 data/eval_results/day8/retrieval_1791857169240676400.json 与 retrieval_1791857183380496100.json；每次运行保存配置快照、配置文件SHA256、问题、检索结果及阶段耗时。

检索计时覆盖问题向量化和Chroma查询，初始化单独计时。每个配置只运行一次，含首次查询及缓存影响，不能据此比较速度或计算稳定p50。

配置类、检索类和入口共3个文件的mypy检查通过。用户填写retrieve时出现定义缩进错误，已修正为与__init__同级。

## 接通答案生成

生成提示词整理到 src/kb/generation.py，沿用 Day 7 相同来源约束，检索片段编号后与问题一起发送，不加入参考答案。ChatOptions 实际使用配置的 chat_model、temperature、max_tokens。

首次在受限执行环境中遇到 ProviderConnectionError，保留失败记录 rag_1791857767218537800.json。随后允许网络的重试成功，记录 rag_1791857800603905200.json：回答“Bucket ACL 的默认权限值是 private。[1]”；检索0.042秒、生成及解析1.712秒、问答链路1.755秒。此处是一次真实 API 调用观察，不能作为100题p50或通用速度结论。

问答链路计时从问题向量化开始，到答案解析、状态整理结束。包括检索、提示词拼接、生成及响应处理，不含模型/数据库初始化、provider对象创建、结果文件写入和评分。首次API调用的连接建立包含在内。保留 usage 和调用开始UTC时间；失败状态单独记录，不能当成功回答指标。入口在生成失败或返回不完整时保存记录后以非零状态退出。

配置、检索、提示词构建与入口共4个文件mypy通过。
