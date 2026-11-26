"""生成人工编排、助手核对的 Day 6 开发/回归题集，不调用生成接口。"""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "day6"
SOURCES = {
    "bucket": "https://help.aliyun.com/zh/oss/user-guide/oss-bucket-acl",
    "object": "https://help.aliyun.com/zh/oss/user-guide/object-acl",
    "block": "https://help.aliyun.com/zh/oss/user-guide/block-public-access/",
    "upload": "https://help.aliyun.com/zh/oss/developer-reference/uploadpart",
    "list": "https://help.aliyun.com/zh/oss/developer-reference/listparts",
    "version": "https://help.aliyun.com/zh/oss/user-guide/overview-78/",
    "marker": "https://help.aliyun.com/zh/oss/user-guide/delete-marker",
    "suspended": "https://help.aliyun.com/zh/oss/user-guide/manage-objects-in-a-versioning-suspended-bucket",
    "enabled": "https://help.aliyun.com/zh/oss/manage-objects-in-a-versioning-enabled-bucket",
    "lifecycle": "https://help.aliyun.com/zh/oss/lifecycle-rules-based-on-the-last-modified-time",
    "worm": "https://help.aliyun.com/zh/oss/user-guide/oss-retention-policies",
}

# 事实文字采用摘记表述；来源是核对页面，不把摘记冒充官方全文。
FACT_ROWS = [
    ("B01", "Bucket 默认权限", "Bucket ACL 的默认权限值是 private。", "bucket"),
    ("B02", "Object 未指定 ACL", "上传 Object 时未指定自己的 ACL，它会继承所属 Bucket 的 ACL。", "bucket"),
    ("B03", "Bucket 私有资格", "Bucket ACL 为 private 时，读写资格限于 Bucket 所有者及获得授权的用户。", "bucket"),
    ("B04", "Bucket 公共读资格", "Bucket ACL 为 public-read 时，匿名用户有读取资格，写入仍需要所有者或授权用户资格。", "bucket"),
    ("B05", "Bucket 公共读写资格", "Bucket ACL 为 public-read-write 时，匿名用户具有读取和写入资格。", "bucket"),
    ("B06", "Bucket 初始阻止开关", "创建 Bucket 时默认开启阻止公共访问，Bucket ACL 此时只能设置为 private。", "bucket"),
    ("O01", "Object 默认权限", "Object ACL 的默认值是 default，表示继承所属 Bucket 的 ACL。", "object"),
    ("O02", "两种 ACL 的范围", "Object ACL 控制单个文件，Bucket ACL 控制存储空间级别的权限。", "object"),
    ("O03", "Object 私有资格", "Object ACL 为 private 时，读写资格限于 Object 所有者及获得授权的用户。", "object"),
    ("O04", "Object 公共读资格", "Object ACL 为 public-read 时，匿名用户有读取资格，但没有写入资格。", "object"),
    ("O05", "Object 公共读写资格", "Object ACL 为 public-read-write 时，匿名用户具有读取和写入资格。", "object"),
    ("O06", "Object 独立 ACL", "Object 设置了非 default 的 ACL 时，ACL 判定采用 Object 的设置，而不继承 Bucket ACL。", "object"),
    ("O07", "阻止开关下的 Object ACL", "Bucket 开启阻止公共访问时，Object ACL 可以设置为 private 或 default；设置公开 ACL 前需先关闭阻止公共访问。", "object"),
    ("O08", "私有文件临时分享", "可用具有指定有效期的预签名 URL 临时分享私有 Object，无需修改 Object ACL。", "object"),
    ("P01", "阻止公开权限", "开启阻止公共访问后，Bucket Policy 和 ACL 中已有的公开访问权限会被忽略，也不能创建新的公开访问权限。", "block"),
    ("P02", "关闭阻止开关", "关闭阻止公共访问后，已有公开权限配置恢复生效，并允许创建新的公开访问权限。", "block"),
    ("P03", "配置维度", "阻止公共访问可配置在 OSS 全局、Bucket、接入点、对象 FC 接入点四个维度。", "block"),
    ("P04", "配置层级", "阻止公共访问从高到低的层级为 OSS 全局、Bucket、接入点、对象 FC 接入点；上层开启时，下层关闭也不能放行公共访问。", "block"),
    ("P05", "Bucket 放行前提", "若要允许单个 Bucket 的公共访问，需要同时关闭 OSS 全局和该 Bucket 的阻止公共访问。", "block"),
    ("P06", "接入点放行前提", "若要允许单个接入点的公共访问，需要关闭 OSS 全局、关联 Bucket 和该接入点的阻止公共访问。", "block"),
    ("P07", "复制时 ACL 保留", "复制时，源或目标 Bucket 是否开启阻止公共访问，不会改变复制前后的 Object ACL。", "block"),
    ("P08", "目标 Bucket 的阻止规则", "目标 Bucket 开启阻止公共访问时，复制得到的 Object 即使带有公开 ACL，仍不能公共访问。", "block"),
    ("U01", "初始化分片任务", "上传 Part 前，先调用 InitiateMultipartUpload 获取 uploadId。", "upload"),
    ("U02", "重复分片号", "同一上传任务中，用相同 partNumber 上传新数据会覆盖该编号的旧 Part。", "upload"),
    ("U03", "分片校验返回头", "UploadPart 把服务器收到的 Part 数据的 MD5 值放在 ETag 响应头中返回。", "upload"),
    ("U04", "大小校验阶段", "UploadPart 阶段不立即校验分片大小，CompleteMultipartUpload 阶段才做该校验。", "upload"),
    ("U05", "上传分片权限", "UploadPart 对应的权限 Action 是 oss:PutObject。", "upload"),
    ("U06", "上传必选字段", "UploadPart 的 partNumber 和 uploadId 都是必选请求字段。", "upload"),
    ("U07", "编号越界错误", "partNumber 超出 1～10000 时，UploadPart 的错误码为 InvalidArgument，HTTP 状态码为 400。", "upload"),
    ("U08", "上传任务不存在", "分片上传 ID 不存在时，UploadPart 的错误码为 NoSuchUpload，HTTP 状态码为 404。", "upload"),
    ("V01", "版本控制默认状态", "Bucket 版本控制默认未开启，状态包括未开启、开启和暂停。", "version"),
    ("V02", "不可回到未开启", "版本控制开启后不能返回未开启状态；可以暂停，但还需满足保留策略等对状态变更的限制。", "version"),
    ("V03", "开启后的覆盖", "版本控制开启时，覆盖同名 Object 会生成新版本，已有历史版本不受影响。", "version"),
    ("V04", "暂停后的覆盖", "版本控制暂停时，新上传的 Object 使用 null 版本；再次上传同名文件会覆盖暂停期的同名版本，但保留暂停前的历史版本。", "version"),
    ("V05", "开启后的版本标识", "版本控制开启时，Object 的每个版本都有唯一的 versionId。", "version"),
    ("V06", "普通删除与标记", "版本控制开启时，DELETE 未指定 versionId 会添加删除标记作为当前版本，原有数据版本不被该操作永久删除。", "enabled"),
    ("V07", "标记作为当前版本", "当 Object 当前版本为删除标记时，读取当前版本的 GET 请求返回 404。", "marker"),
    ("V08", "删除标记后恢复", "已有数据历史版本时，指定 versionId 删除当前删除标记后，最近的数据历史版本成为当前版本，Object 恢复可访问。", "marker"),
    ("L01", "生命周期规则数量", "单个 Bucket 最多配置 1000 条生命周期规则。", "lifecycle"),
    ("L02", "生命周期覆盖语义", "PutBucketLifecycle 覆盖已有规则；保留旧规则并追加新规则时，应先获取旧配置，再合并新规则，最后提交完整配置。", "lifecycle"),
    ("V09", "永久删除指定版本", "通过 versionId 删除指定数据版本是永久删除，该版本不能通过版本控制恢复。", "enabled"),
    ("V10", "暂停后的下载", "版本控制暂停时，GET 未指定 versionId 返回当前版本；指定 versionId 可下载对应的历史版本。", "suspended"),
    ("V11", "未开启时覆盖", "未开启版本控制时，同名 Object 被直接覆盖，旧内容不能通过版本控制恢复。", "version"),
    ("L03", "当前文件过期起点", "基于最后修改时间的生命周期规则中，当前版本的过期天数从 Object 最后修改时间开始计算。", "lifecycle"),
    ("L04", "历史文件过期起点", "非当前版本过期天数从该版本成为非当前版本的时间开始计算，而不是原文件的最后修改时间。", "lifecycle"),
    ("W01", "保护期数据版本", "保留策略保护期内的 Object 数据版本不能被修改或删除，生命周期也不能删除这些受保护版本；允许上传同名 Object 生成受保护的新版本。", "worm"),
    ("W02", "删除标记不受保护", "保留策略不保护删除标记，删除标记可以被清理。", "worm"),
    ("W03", "锁定后暂停限制", "锁定保留策略后，版本控制不能从开启切换到暂停。", "worm"),
    ("W04", "保护下恢复开启", "已暂停版本控制的 Bucket 开启保留策略后，仍允许把版本控制恢复为开启。", "worm"),
    ("A01", "列举分片权限", "ListParts 对应的权限 Action 是 oss:ListParts。", "list"),
]

SINGLE_QUESTIONS = [
    ("B01", "Bucket ACL 默认是什么权限值？", "private。"),
    ("B02", "上传 Object 时不指定它自己的 ACL，会采用什么权限？", "继承所属 Bucket 的 ACL。"),
    ("B03", "按 private 的 ACL 定义，谁有 Bucket 内文件的读写资格？", "Bucket 所有者及获得授权的用户。"),
    ("B04", "按 Bucket public-read 定义，匿名用户有哪些读写资格？", "可以读取，但没有写入资格。"),
    ("B05", "按 Bucket public-read-write 定义，匿名用户有哪些读写资格？", "读取和写入资格都具备。"),
    ("B06", "新建 Bucket 的默认阻止公共访问状态及此时允许的 Bucket ACL 是什么？", "默认开启，Bucket ACL 只能设置为 private。"),
    ("O01", "Object ACL 的默认值是什么，含义是什么？", "default，继承所属 Bucket 的 ACL。"),
    ("O02", "只给一个文件单独设置权限，应关注哪一种 ACL？", "Object ACL。"),
    ("O03", "按 Object private 定义，文件读写资格属于谁？", "Object 所有者及获得授权的用户。"),
    ("O04", "按 Object public-read 定义，匿名用户可以写入吗？", "不能写入，只有读取资格。"),
    ("O05", "按 Object public-read-write 定义，匿名用户有写入资格吗？", "有，并具有读取资格。"),
    ("O06", "Object 有非 default 的 ACL 时，ACL 判定采用哪一级设置？", "采用 Object 的设置。"),
    ("O07", "Bucket 开启阻止公共访问时，可以给 Object 设置哪些 ACL 值？", "private 或 default。"),
    ("O08", "资料给出的临时分享私有 Object 且无需改 ACL 的方式是什么？", "使用有指定有效期的预签名 URL。"),
    ("P01", "开启阻止公共访问后，已有公开权限和新建公开权限分别怎样处理？", "已有公开权限被忽略，也不能创建新的公开权限。"),
    ("P02", "关闭阻止公共访问后，已有公开权限如何处理？", "恢复生效。"),
    ("P03", "阻止公共访问支持配置在哪四个维度？", "OSS 全局、Bucket、接入点、对象 FC 接入点。"),
    ("P04", "阻止公共访问的层级从高到低如何排列？", "OSS 全局、Bucket、接入点、对象 FC 接入点。"),
    ("P05", "解除单个 Bucket 的公共访问阻止，需要关闭哪些层级？", "OSS 全局和该 Bucket。"),
    ("P06", "解除接入点的公共访问阻止，需要关闭哪些层级？", "OSS 全局、关联 Bucket 和该接入点。"),
    ("P07", "复制时，源或目标 Bucket 的阻止公共访问开关会改变 Object ACL 吗？", "不会改变复制前后的 Object ACL。"),
    ("P08", "目标 Bucket 开启阻止公共访问时，复制来的公开 ACL 文件能否公共访问？", "不能。"),
    ("U01", "上传 Part 前，用什么接口取得 uploadId？", "InitiateMultipartUpload。"),
    ("U02", "同一任务再次上传相同 partNumber，会怎样处理旧分片？", "覆盖该编号的旧 Part。"),
    ("U03", "UploadPart 的 ETag 响应头记录哪种数据的 MD5？", "服务器收到的 Part 数据的 MD5。"),
    ("U04", "分片大小是在哪个阶段校验的？", "CompleteMultipartUpload 阶段。"),
    ("U05", "UploadPart 对应哪一个权限 Action？", "oss:PutObject。"),
    ("U06", "UploadPart 的 partNumber 和 uploadId 是否都是必选字段？", "都是必选字段。"),
    ("U07", "partNumber 越界时的错误码和 HTTP 状态码是什么？", "InvalidArgument，400。"),
    ("U08", "上传任务 ID 不存在时的错误码和 HTTP 状态码是什么？", "NoSuchUpload，404。"),
    ("V01", "Bucket 版本控制默认处于什么状态？", "未开启。"),
    ("V02", "已经开启版本控制的 Bucket 能直接回到未开启状态吗？", "不能。"),
    ("V03", "版本控制开启时，覆盖同名 Object 会不会破坏历史版本？", "不会；生成新版本，历史版本不受影响。"),
    ("V04", "版本控制暂停后，再次上传同名文件会影响暂停前的历史版本吗？", "不会，但会覆盖暂停期的同名 null 版本。"),
    ("V05", "版本控制开启时，区分同一 Object 不同版本使用什么标识？", "唯一的 versionId。"),
    ("V06", "版本控制开启时，不指定 versionId 的 DELETE 会怎样处理 Object？", "添加删除标记作为当前版本，不永久删除原有数据版本。"),
    ("V07", "当前版本是删除标记时，读取当前版本的 GET 返回什么状态？", "404。"),
    ("V08", "保留数据历史版本的情况下，删除当前删除标记后哪个版本成为当前版本？", "最近的数据历史版本。"),
    ("L01", "单个 Bucket 的生命周期规则数上限是多少？", "1000 条。"),
    ("L02", "PutBucketLifecycle 是追加规则还是覆盖规则？", "覆盖；追加时需先获取旧配置并合并后提交。"),
]

MULTI_QUESTIONS = [
    ("假设阻止公共访问已关闭且没有其他限制：Bucket 为 public-read，Object 未指定 ACL，匿名用户能写入这个 Object 吗？", "不能；Object 继承 public-read，只给匿名用户读取资格。", ["B02", "B04"]),
    ("只按 ACL 规则判断：Bucket 使用默认 ACL，Object 也未指定自己的 ACL，匿名用户能读取它吗？", "不能；Bucket 默认 private，Object 继承它，private 不给匿名用户读取资格。", ["B01", "B02", "B03"]),
    ("假设公共访问未被阻止且没有其他限制：Bucket 是 public-read-write，Object ACL 为 default，匿名用户可以读写它吗？", "可以；default 继承 Bucket 的公开读写资格。", ["O01", "B05"]),
    ("假设公共访问未被阻止且没有其他限制：Bucket private，但 Object 独立设为 public-read，匿名用户可以读取文件吗？", "可以；独立 Object ACL 生效，public-read 给匿名用户读取资格。", ["O06", "O04"]),
    ("假设没有其他授权或限制：Bucket public-read，但 Object 独立设为 private，匿名用户可以读这个文件吗？", "不能；独立 Object ACL 为 private，不给匿名用户读取资格。", ["O06", "O03"]),
    ("Object 已设为 public-read，但其 Bucket 开启阻止公共访问，匿名读取是否仍可用？", "不可用；public-read 的公开读取权限被阻止公共访问忽略。", ["O04", "P01"]),
    ("Object 为 public-read，Bucket 关闭阻止开关但 OSS 全局开关仍开启，匿名读取可以放行吗？", "不能；上层阻止开关覆盖下层放行，即使 ACL 有公开读取资格。", ["O04", "P04"]),
    ("Object 为 public-read，全局和 Bucket 阻止开关已关闭，但访问所用接入点仍开启阻止公共访问，经此接入点能匿名读吗？", "不能；接入点放行还需关闭它自身的阻止开关。", ["O04", "P06"]),
    ("public-read Object 被复制到开启阻止公共访问的目标 Bucket；既然复制没改 ACL，匿名读取一定仍可用吗？", "不一定且本条件下不可用；ACL 保留为公开读，但公开资格被目标阻止开关忽略。", ["P07", "O04", "P01"]),
    ("某 public-read Object 先被公共访问开关阻止，随后所有相关阻止开关都关闭；假设无其他限制，匿名读取会恢复吗？", "会；关闭开关恢复公开配置，public-read 提供匿名读取资格。", ["P02", "O04"]),
    ("版本控制开启时，对文件执行未指定 versionId 的 DELETE，随后不指定版本读当前文件，会发生什么？", "删除产生当前删除标记，因此当前版本 GET 返回 404。", ["V06", "V07"]),
    ("版本控制开启且保留历史数据时，先普通删除文件，再指定版本删除新产生的当前删除标记，原数据可以恢复访问吗？", "可以；普通删除不永久删除数据版本，清理当前标记使最近历史数据版本恢复为当前版本。", ["V06", "V08"]),
    ("无保留策略限制时，版本开启的文件先从 A 覆盖为 B，再普通删除，然后删除当前删除标记，最近恢复的内容是 A 还是 B？", "B；覆盖生成 B 版本且保留 A，普通删除保留数据，删除标记后恢复最近数据版本 B。", ["V03", "V06", "V08"]),
    ("暂停版本控制时同名文件先上传 A 后上传 B，再执行未指定 versionId 的 GET，会读到哪个内容？", "B；暂停期同名 null 版本被 B 覆盖，未指定版本的 GET 读当前版本。", ["V04", "V10"]),
    ("无保留策略限制时，暂停版本 Bucket 的某历史版本被指定 versionId 永久删除；能再靠下载这个 versionId 恢复它吗？", "不能；指定版本已永久删除，按该 versionId 下载不能恢复已删除版本。", ["V09", "V10"]),
    ("版本控制与保留策略同时开启，数据还在保护期：普通删除后清理当前删除标记，是否必须先删除受保护数据版本才能恢复访问？", "不必；普通删除保留数据，标记不受保留策略保护，清理当前标记即可让最近历史数据版本恢复访问。", ["V06", "W02", "V08"]),
    ("某受保护的历史版本已达到配置的非当前版本过期天数，但仍在保留策略保护期，生命周期可以立即永久删除它吗？", "不能；非当前版本达到过期阈值不解除保留策略对数据版本的保护。", ["L04", "W01"]),
    ("保留策略保护期内且版本控制开启时，上传同名新内容一定是在修改已有受保护版本吗？", "不是；可以生成新的受保护版本，开启版本控制的覆盖保留历史版本。", ["W01", "V03"]),
    ("历史版本最后修改是 20 天前，但 5 天前才成为非当前版本；非当前过期阈值为 10 天，达到阈值还差几天？", "还差 5 天；非当前版本从成为历史版本起算，不能按最后修改时间当作当前版本规则计算；达到阈值不保证任务当刻执行完。", ["L03", "L04"]),
    ("一个非最后分片为 50 KB，UploadPart 返回成功就能证明最终大小校验一定通过吗？", "不能；普通分片最小 100 KB，大小在 CompleteMultipartUpload 阶段才校验。", ["U04", "TU"]),
]

COMPARISON_QUESTIONS = [
    ("Bucket ACL 和 Object ACL 默认值有何不同？", "Bucket 默认 private，Object 默认 default 并继承 Bucket。", ["B01", "O01"]),
    ("Bucket ACL 与 Object ACL 的权限控制范围有什么区别？", "前者是存储空间级别，后者是单个文件。", ["O02"]),
    ("按 ACL 定义，Bucket public-read 与 public-read-write 对匿名写入资格有什么区别？", "public-read 不允许匿名写入，public-read-write 允许。", ["B04", "B05"]),
    ("按 ACL 定义，Object public-read 和 public-read-write 对匿名用户的权限有何不同？", "前者只读，后者可读写。", ["O04", "O05"]),
    ("Object ACL 为 default 与非 default 时，采用权限的来源有什么区别？", "default 继承 Bucket；非 default 采用 Object 的独立设置。", ["O01", "O06"]),
    ("开启和关闭阻止公共访问，对已有公开权限的作用有何不同？", "开启时忽略已有公开权限；关闭后恢复其生效。", ["P01", "P02"]),
    ("OSS 全局阻止开关和 Bucket 开关不一致时，哪个层级优先？", "OSS 全局优先；上层开启不能靠下层关闭放行。", ["P04"]),
    ("解除 Bucket 与接入点的公共访问阻止，所需关闭的层级有什么区别？", "Bucket 需关闭全局和 Bucket；接入点还需关闭接入点本身。", ["P05", "P06"]),
    ("复制时 Object ACL 保持不变，与目标 Bucket 中实际能否公共访问，是不是同一件事？", "不是；ACL 可以保持公开，但目标开了阻止公共访问仍不可公共访问。", ["P07", "P08"]),
    ("未开启和开启版本控制时，同名覆盖对旧内容的影响有何不同？", "未开启直接覆盖且不能通过版本控制恢复；开启生成新版本并保留历史。", ["V11", "V03"]),
    ("开启与暂停版本控制时，再次上传同名文件的版本行为有何区别？", "开启生成新的唯一版本；暂停期同名 null 版本会被后续上传覆盖，暂停前历史仍保留。", ["V03", "V04", "V05"]),
    ("开启版本控制时，未指定版本的普通 DELETE 与指定数据版本的 DELETE 有何区别？", "前者产生删除标记并保留数据；后者永久删除指定版本。", ["V06", "V09"]),
    ("保留策略对数据版本与删除标记的保护有何区别？", "保护期内数据版本不能修改删除，删除标记不受此保护。", ["W01", "W02"]),
    ("当前版本和非当前版本的生命周期过期天数，计算起点有何区别？", "当前版本按最后修改时间；非当前版本按成为非当前版本的时间。", ["L03", "L04"]),
    ("UploadPart 与 ListParts 所需的权限 Action 有何不同？", "UploadPart 用 oss:PutObject；ListParts 用 oss:ListParts。", ["U05", "A01"]),
]

UNANSWERABLE_QUESTIONS = [
    ("OSS 标准存储在杭州每 GB 每月的具体价格是多少？", "资料没有具体地域价格。"),
    ("分片上传每秒保证至少达到多少 MB？", "资料没有最低速度保证。"),
    ("所有账号允许的最大并发 UploadPart 数是多少？", "资料没有账号并发上限。"),
    ("删除标记会在创建后固定多少小时自动消失？", "资料没有固定自动清理时长，不能把手动删除规则当成定时清理。"),
    ("预签名 URL 的最大允许有效期是多少秒？", "资料只提到指定有效期，没有给出最大值。"),
    ("我的 uploadId abc123 现在是否存在？", "资料没有用户上传任务的实时状态。"),
    ("我今天产生了多少 GB 的 OSS 外网流量？", "资料没有用户账户的流量数据。"),
    ("一个 Object 最多能保留多少个历史版本？", "资料没有版本数量上限。"),
    ("这个 Bucket 的当前 ACL 实际设置是什么？", "资料描述规则，没有该 Bucket 的实际配置。"),
    ("昨天是哪位用户修改了我的 Object ACL？", "资料没有该用户的操作审计记录。"),
]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    facts = {
        item_id: {"id": item_id, "title": title, "text": text, "source_url": SOURCES[source]}
        for item_id, title, text, source in FACT_ROWS
    }
    multipart_sections = []
    # 复用已核对的两张短表，避免改变边界值或单位。
    from kb.ingestion import load_document
    for section in load_document(ROOT / "examples" / "oss_multipart_notes.md"):
        if section.text.startswith("|"):
            multipart_sections.append(section)
    assert len(multipart_sections) == 2
    for item_id, section, source in zip(("TU", "TL"), multipart_sections, ("upload", "list")):
        facts[item_id] = {"id": item_id, "title": section.heading_path[-1], "text": section.text, "source_url": SOURCES[source]}

    corpus = "# Day 6 OSS 评测资料 v1\n\n"
    corpus += "本文件是依据官方页面核对的学习摘记，不是官方全文。采集日期：2026-10-12。"
    corpus += "用于开发与回归评测，不涉及真实账户操作；ACL 场景按题目声明的前提判断，资料不包含具体价格、账户状态、速度保证或未列出的配额。\n"
    corpus += "情景中的配置、上传、删除操作假定满足所需操作权限；匿名访问不额外假设存在其他策略授权。保留策略与版本状态以题面声明为准。\n"
    for fact in facts.values():
        corpus += f"\n## {fact['id']} {fact['title']}\n\n{fact['text']}\n来源：{fact['source_url']}\n"
    corpus_path = OUTPUT / "oss_corpus.md"
    corpus_path.write_text(corpus, encoding="utf-8")
    (OUTPUT / "facts.json").write_text(json.dumps(list(facts.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cases: list[dict] = []
    counters: Counter = Counter()

    def add(category: str, question: str, answer: str, refs: list[str], evidence: list[str] | None = None, reason: str | None = None) -> None:
        counters[category] += 1
        citations = [facts[item] for item in refs]
        required = evidence if evidence is not None else [item["text"] for item in citations]
        case = {
            "id": f"{category}_{counters[category]:03d}",
            "category": category,
            "question": question,
            "answerable": category != "unanswerable",
            "expected_answer": answer,
            "required_evidence": required,
            "evidence_ids": refs,
            "source_urls": list(dict.fromkeys(item["source_url"] for item in citations)),
            "split": "development",
            "review_status": "assistant_reviewed",
            "common_assumptions": "配置、上传、删除操作已满足操作权限；匿名访问不额外假设其他策略授权；按题面保留策略与版本状态判断。",
        }
        if reason:
            case["unanswerable_reason"] = reason
        if category == "multi_hop":
            case["reasoning_note"] = "需要应用并串联所列规则；覆盖率只检查证据，未评分推理结果。"
        cases.append(case)

    for item_id, question, answer in SINGLE_QUESTIONS:
        add("single_hop", question, answer, [item_id])
    for question, answer, refs in MULTI_QUESTIONS:
        if refs == ["U04", "TU"]:
            add("multi_hop", question, answer, refs, [facts["U04"]["text"], "| 普通 Part 最小值 | 100 KB | 除最后一片外 |"])
        else:
            add("multi_hop", question, answer, refs)
    for question, answer, refs in COMPARISON_QUESTIONS:
        add("comparison", question, answer, refs)
    numeric_cases = json.loads((ROOT / "examples" / "oss_multipart_cases.json").read_text(encoding="utf-8"))
    for case in numeric_cases:
        refs = [item_id for item_id in ("TU", "TL") if any(evidence in facts[item_id]["text"] for evidence in case["required_evidence"])]
        add("table_numeric", case["question"], case["expected_answer"], refs, case["required_evidence"])
    for question, reason in UNANSWERABLE_QUESTIONS:
        add("unanswerable", question, "资料未说明。", [], reason=reason)

    expected = {"single_hop": 40, "multi_hop": 20, "comparison": 15, "table_numeric": 15, "unanswerable": 10}
    assert dict(counters) == expected, counters
    assert len(cases) == 100
    assert len({case["id"] for case in cases}) == len({case["question"] for case in cases}) == 100
    for case in cases:
        assert bool(case["required_evidence"]) == case["answerable"]
        for evidence in case["required_evidence"]:
            assert evidence in corpus, (case["id"], evidence)
            assert any(evidence in facts[item]["text"] for item in case["evidence_ids"]), case["id"]
    cases_path = OUTPUT / "oss_cases_100.json"
    cases_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "dataset_version": "v1",
        "collected_on": "2026-10-12",
        "case_count": len(cases),
        "category_counts": dict(counters),
        "sources": SOURCES,
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "review": "助手逐题编排并核对参考答案、条件和引用；非独立人工或外部评审。",
        "usage": "开发/回归集，不声称独立测试泛化；边界题共享规则，样本并非独立同分布。",
        "limitations": ["依据是整理摘记而非官方全文", "没有评测生成和拒答表现", "原文包含覆盖率不是标准 Recall 或语义判定", "未执行云端写操作"],
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("题集已生成：", cases_path)
    print("题型配比：", dict(counters))
    print("事实/表格块数：", len(facts))
    print("结构、重复题目、依据存在性、来源映射检查通过。")


if __name__ == "__main__":
    main()
