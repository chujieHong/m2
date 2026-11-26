# OSS ACL 与阻止公共访问扩展学习摘记

本文件依据官方资料整理，不是官方全文。采集日期：2026-10-12。用于 RAG 学习，范围不包括完整授权策略、计费及业务配置建议。
Bucket ACL 来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl
Object ACL 来源：https://help.aliyun.com/zh/oss/user-guide/object-acl
阻止公共访问来源：https://help.aliyun.com/zh/oss/user-guide/block-public-access/

## Bucket ACL 默认与继承

Bucket ACL 的默认权限值是 private。
Object 未指定自己的 ACL 时，继承所属 Bucket 的 ACL。

## Bucket 公开权限

Bucket 的 public-read 允许匿名读取，写入仍需要所有者或授权用户资格。
Bucket 的 public-read-write 将读写资格开放给匿名用户。
这些是 ACL 权限定义；实际访问仍受阻止公共访问等规则影响。

## Object ACL 范围与默认值

Object ACL 控制单个文件，而 Bucket ACL 控制存储空间级别的权限。
Object ACL 的默认值是 default，其含义是继承所属 Bucket 的 ACL。

## Object ACL 私有权限

Object ACL 为 private 时，文件读写资格限于 Object 所有者及获得授权的用户。

## Object ACL 公开权限

Object ACL 为 public-read 时，匿名用户有读取资格，但没有写入资格。
Object ACL 为 public-read-write 时，匿名用户具有读取和写入资格。
这些是 ACL 权限定义；实际访问仍受阻止公共访问等规则影响。

## Object ACL 优先级

Object 设置了非 default 的 ACL 时，ACL 判定采用 Object 的设置，而不继承 Bucket ACL。

## Object ACL 设置限制

Bucket 默认开启阻止公共访问，此时 Object ACL 可以设置为 private 或 default。
若要把 Object ACL 设置为 public-read 或 public-read-write，需要先关闭阻止公共访问。

## 阻止公共访问的效果

开启阻止公共访问后，Bucket Policy 和 ACL 中已有的公共访问配置会被忽略，也不能创建新的公共访问权限。
关闭阻止公共访问后，原有公开权限配置恢复生效，并允许创建新的公共访问权限。

## 阻止公共访问的四个维度

阻止公共访问可配置在 OSS 全局、Bucket、接入点、对象 FC 接入点这四个维度。

## 阻止公共访问的层级规则

阻止公共访问的优先层级从高到低是 OSS 全局、Bucket、接入点、对象 FC 接入点。
上层开启阻止公共访问时，下层关闭该功能也不能放行公共访问。

## 放行公共访问的层级前提

若要允许某个 Bucket 的公共访问，需要同时关闭 OSS 全局和该 Bucket 的阻止公共访问。
若要允许某个接入点的公共访问，需要关闭 OSS 全局、关联 Bucket 和该接入点的阻止公共访问。
关闭这些开关只是解除阻止；是否授予公开访问仍取决于权限配置。

## 复制对象与阻止公共访问

复制时，源或目标 Bucket 是否开启阻止公共访问，不会改变复制前后的 Object ACL。
若目标 Bucket 开启阻止公共访问，即使复制得到的 Object ACL 为公开权限，仍不能公共访问。
