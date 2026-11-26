# 阿里云 OSS Bucket ACL 学习摘记

本文件是依据官方文档整理的简短学习摘记，不是官方全文。采集日期：2026-10-12。
来源：https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl
范围：Bucket ACL 的预定义权限与设置前提，不覆盖完整权限体系或计费规则。

## 默认权限与继承

Bucket ACL 的默认权限值是 private。
上传 Object 时没有指定它的 ACL，该 Object 的访问权限会继承 Bucket ACL。

## private

private 表示私有权限，读写资格限于 Bucket 所有者及获得授权的用户。

## public-read

public-read 允许匿名用户读取，但写入资格仍限于 Bucket 所有者及获得授权的用户。

## public-read-write

public-read-write 将读取和写入都开放给匿名用户。

## 设置公开权限的前提

创建 Bucket 时，阻止公共访问默认处于开启状态，此时 Bucket ACL 只能设置为 private。
若要配置 public-read 或 public-read-write，需要先关闭阻止公共访问。
