# Day 6 OSS 评测资料 v1

本文件是依据官方页面核对的学习摘记，不是官方全文。采集日期：2026-10-12。用于开发与回归评测，不涉及真实账户操作；ACL 场景按题目声明的前提判断，资料不包含具体价格、账户状态、速度保证或未列出的配额。
情景中的配置、上传、删除操作假定满足所需操作权限；匿名访问不额外假设存在其他策略授权。保留策略与版本状态以题面声明为准。

## B01 Bucket 默认权限

Bucket ACL 的默认权限值是 private。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl

## B02 Object 未指定 ACL

上传 Object 时未指定自己的 ACL，它会继承所属 Bucket 的 ACL。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl

## B03 Bucket 私有资格

Bucket ACL 为 private 时，读写资格限于 Bucket 所有者及获得授权的用户。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl

## B04 Bucket 公共读资格

Bucket ACL 为 public-read 时，匿名用户有读取资格，写入仍需要所有者或授权用户资格。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl

## B05 Bucket 公共读写资格

Bucket ACL 为 public-read-write 时，匿名用户具有读取和写入资格。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl

## B06 Bucket 初始阻止开关

创建 Bucket 时默认开启阻止公共访问，Bucket ACL 此时只能设置为 private。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl

## O01 Object 默认权限

Object ACL 的默认值是 default，表示继承所属 Bucket 的 ACL。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O02 两种 ACL 的范围

Object ACL 控制单个文件，Bucket ACL 控制存储空间级别的权限。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O03 Object 私有资格

Object ACL 为 private 时，读写资格限于 Object 所有者及获得授权的用户。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O04 Object 公共读资格

Object ACL 为 public-read 时，匿名用户有读取资格，但没有写入资格。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O05 Object 公共读写资格

Object ACL 为 public-read-write 时，匿名用户具有读取和写入资格。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O06 Object 独立 ACL

Object 设置了非 default 的 ACL 时，ACL 判定采用 Object 的设置，而不继承 Bucket ACL。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O07 阻止开关下的 Object ACL

Bucket 开启阻止公共访问时，Object ACL 可以设置为 private 或 default；设置公开 ACL 前需先关闭阻止公共访问。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## O08 私有文件临时分享

可用具有指定有效期的预签名 URL 临时分享私有 Object，无需修改 Object ACL。
来源：https://help.aliyun.com/zh/oss/user-guide/object-acl

## P01 阻止公开权限

开启阻止公共访问后，Bucket Policy 和 ACL 中已有的公开访问权限会被忽略，也不能创建新的公开访问权限。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P02 关闭阻止开关

关闭阻止公共访问后，已有公开权限配置恢复生效，并允许创建新的公开访问权限。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P03 配置维度

阻止公共访问可配置在 OSS 全局、Bucket、接入点、对象 FC 接入点四个维度。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P04 配置层级

阻止公共访问从高到低的层级为 OSS 全局、Bucket、接入点、对象 FC 接入点；上层开启时，下层关闭也不能放行公共访问。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P05 Bucket 放行前提

若要允许单个 Bucket 的公共访问，需要同时关闭 OSS 全局和该 Bucket 的阻止公共访问。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P06 接入点放行前提

若要允许单个接入点的公共访问，需要关闭 OSS 全局、关联 Bucket 和该接入点的阻止公共访问。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P07 复制时 ACL 保留

复制时，源或目标 Bucket 是否开启阻止公共访问，不会改变复制前后的 Object ACL。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## P08 目标 Bucket 的阻止规则

目标 Bucket 开启阻止公共访问时，复制得到的 Object 即使带有公开 ACL，仍不能公共访问。
来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## U01 初始化分片任务

上传 Part 前，先调用 InitiateMultipartUpload 获取 uploadId。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U02 重复分片号

同一上传任务中，用相同 partNumber 上传新数据会覆盖该编号的旧 Part。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U03 分片校验返回头

UploadPart 把服务器收到的 Part 数据的 MD5 值放在 ETag 响应头中返回。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U04 大小校验阶段

UploadPart 阶段不立即校验分片大小，CompleteMultipartUpload 阶段才做该校验。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U05 上传分片权限

UploadPart 对应的权限 Action 是 oss:PutObject。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U06 上传必选字段

UploadPart 的 partNumber 和 uploadId 都是必选请求字段。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U07 编号越界错误

partNumber 超出 1～10000 时，UploadPart 的错误码为 InvalidArgument，HTTP 状态码为 400。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## U08 上传任务不存在

分片上传 ID 不存在时，UploadPart 的错误码为 NoSuchUpload，HTTP 状态码为 404。
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## V01 版本控制默认状态

Bucket 版本控制默认未开启，状态包括未开启、开启和暂停。
来源：https://help.aliyun.com/zh/oss/user-guide/overview-78/

## V02 不可回到未开启

版本控制开启后不能返回未开启状态；可以暂停，但还需满足保留策略等对状态变更的限制。
来源：https://help.aliyun.com/zh/oss/user-guide/overview-78/

## V03 开启后的覆盖

版本控制开启时，覆盖同名 Object 会生成新版本，已有历史版本不受影响。
来源：https://help.aliyun.com/zh/oss/user-guide/overview-78/

## V04 暂停后的覆盖

版本控制暂停时，新上传的 Object 使用 null 版本；再次上传同名文件会覆盖暂停期的同名版本，但保留暂停前的历史版本。
来源：https://help.aliyun.com/zh/oss/user-guide/overview-78/

## V05 开启后的版本标识

版本控制开启时，Object 的每个版本都有唯一的 versionId。
来源：https://help.aliyun.com/zh/oss/user-guide/overview-78/

## V06 普通删除与标记

版本控制开启时，DELETE 未指定 versionId 会添加删除标记作为当前版本，原有数据版本不被该操作永久删除。
来源：https://help.aliyun.com/zh/oss/manage-objects-in-a-versioning-enabled-bucket

## V07 标记作为当前版本

当 Object 当前版本为删除标记时，读取当前版本的 GET 请求返回 404。
来源：https://help.aliyun.com/zh/oss/user-guide/delete-marker

## V08 删除标记后恢复

已有数据历史版本时，指定 versionId 删除当前删除标记后，最近的数据历史版本成为当前版本，Object 恢复可访问。
来源：https://help.aliyun.com/zh/oss/user-guide/delete-marker

## L01 生命周期规则数量

单个 Bucket 最多配置 1000 条生命周期规则。
来源：https://help.aliyun.com/zh/oss/lifecycle-rules-based-on-the-last-modified-time

## L02 生命周期覆盖语义

PutBucketLifecycle 覆盖已有规则；保留旧规则并追加新规则时，应先获取旧配置，再合并新规则，最后提交完整配置。
来源：https://help.aliyun.com/zh/oss/lifecycle-rules-based-on-the-last-modified-time

## V09 永久删除指定版本

通过 versionId 删除指定数据版本是永久删除，该版本不能通过版本控制恢复。
来源：https://help.aliyun.com/zh/oss/manage-objects-in-a-versioning-enabled-bucket

## V10 暂停后的下载

版本控制暂停时，GET 未指定 versionId 返回当前版本；指定 versionId 可下载对应的历史版本。
来源：https://help.aliyun.com/zh/oss/user-guide/manage-objects-in-a-versioning-suspended-bucket

## V11 未开启时覆盖

未开启版本控制时，同名 Object 被直接覆盖，旧内容不能通过版本控制恢复。
来源：https://help.aliyun.com/zh/oss/user-guide/overview-78/

## L03 当前文件过期起点

基于最后修改时间的生命周期规则中，当前版本的过期天数从 Object 最后修改时间开始计算。
来源：https://help.aliyun.com/zh/oss/lifecycle-rules-based-on-the-last-modified-time

## L04 历史文件过期起点

非当前版本过期天数从该版本成为非当前版本的时间开始计算，而不是原文件的最后修改时间。
来源：https://help.aliyun.com/zh/oss/lifecycle-rules-based-on-the-last-modified-time

## W01 保护期数据版本

保留策略保护期内的 Object 数据版本不能被修改或删除，生命周期也不能删除这些受保护版本；允许上传同名 Object 生成受保护的新版本。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies

## W02 删除标记不受保护

保留策略不保护删除标记，删除标记可以被清理。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies

## W03 锁定后暂停限制

锁定保留策略后，版本控制不能从开启切换到暂停。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies

## W04 保护下恢复开启

已暂停版本控制的 Bucket 开启保留策略后，仍允许把版本控制恢复为开启。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies

## A01 列举分片权限

ListParts 对应的权限 Action 是 oss:ListParts。
来源：https://help.aliyun.com/zh/oss/developer-reference/listparts

## TU UploadPart 数值约束

| 项目 | 要求 | 适用范围 |
| --- | --- | --- |
| partNumber | 1～10000，包含端点 | 正整数编号 |
| 普通 Part 最小值 | 100 KB | 除最后一片外 |
| 最后一片最小值 | 可以小于 100 KB | 仅最后一片 |
| 单片最大值 | 5 GB | 所有 Part |
来源：https://help.aliyun.com/zh/oss/developer-reference/uploadpart

## TL ListParts 参数与返回字段

| 参数或字段 | 定义 |
| --- | --- |
| max-parts | 默认 1000，最大 1000 |
| part-number-marker | 只返回编号大于该值的 Part，不包含该编号本身 |
| 返回顺序 | 按 Part 编号升序 |
| IsTruncated=true | 本次没有返回全部结果 |
| NextPartNumberMarker | 未列举完时，用作下一次请求的起始标记 |
来源：https://help.aliyun.com/zh/oss/developer-reference/listparts
