# OSS 分片上传与列举学习摘记

本文件依据官方文档整理，不是官方全文。采集日期：2026-10-12。
UploadPart 来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart
ListParts 来源：https://help.aliyun.com/zh/oss/developer-reference/listparts
范围：接口字段和分片约束，不包含价格、速度保证或完整业务配置。数值单位沿用官方 KB、GB，不做字节换算。

## UploadPart 数值约束

| 项目 | 要求 | 适用范围 |
| --- | --- | --- |
| partNumber | 1～10000，包含端点 | 正整数编号 |
| 普通 Part 最小值 | 100 KB | 除最后一片外 |
| 最后一片最小值 | 可以小于 100 KB | 仅最后一片 |
| 单片最大值 | 5 GB | 所有 Part |

## 分片大小校验时机

UploadPart 阶段不会立即校验分片大小；CompleteMultipartUpload 阶段才做该校验。

## 初始化与覆盖

上传 Part 之前，先调用 InitiateMultipartUpload 获取 uploadId。
在同一上传任务中使用相同 partNumber 重新上传，会覆盖对应旧 Part。

## ListParts 参数与返回字段

| 参数或字段 | 定义 |
| --- | --- |
| max-parts | 默认 1000，最大 1000 |
| part-number-marker | 只返回编号大于该值的 Part，不包含该编号本身 |
| 返回顺序 | 按 Part 编号升序 |
| IsTruncated=true | 本次没有返回全部结果 |
| NextPartNumberMarker | 未列举完时，用作下一次请求的起始标记 |

## 编号范围与列举页大小的区别

partNumber 的编号范围不是一次 ListParts 返回的条数；后者由 max-parts 限制。
