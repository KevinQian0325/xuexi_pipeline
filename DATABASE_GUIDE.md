# 数据库说明和使用手册

本文档说明 `xuexi_pipeline` 的运行数据库结构、字段含义、功能用途和常用检查方法。

## 目录位置

运行数据库保存在：

```text
程序运行文件夹/运行数据库/<网站名>/<固定json名>.db
```

当前设计是：每个固定 JSON 对应一个 SQLite 数据库。数据库会在建立索引或处理视频时自动创建和迁移，不需要手动删库重建。

## 数据库表

每个 `.db` 里包含三张核心表：

```text
videos       视频主表，保存视频基础信息、处理状态、产物路径和最近一次错误
crawl_runs   运行批次表，保存每次 pipeline 运行的范围、数量、状态和日志路径
video_events 视频阶段事件表，保存每条视频每个处理阶段的开始、成功、失败记录
```

## videos 表

`videos` 是主表，一条记录对应一个视频。

### 基础字段

| 字段 | 说明 |
| --- | --- |
| `item_id` | 视频唯一 ID，主键 |
| `title` | 视频标题 |
| `detail_url` | 视频详情页地址 |
| `publish_time` | 发布时间，格式为 `YYYY-MM-DD HH:MM:SS` |
| `item_type` | 原始 JSON 里的内容类型 |
| `content_type` | 原始 JSON 里的内容分类 |
| `status` | 当前处理状态 |
| `created_at` | 记录首次入库时间 |
| `updated_at` | 记录最近更新时间 |

### 来源字段

| 字段 | 说明 |
| --- | --- |
| `source_page_url` | 来源网站入口 URL |
| `source_json_name` | 来源固定 JSON 文件名 |
| `material_dir` | 该视频对应的结果文件目录 |

### 产物字段

| 字段 | 说明 |
| --- | --- |
| `m3u8_url` | 捕获到的视频 m3u8 地址 |
| `mp4_path` | 下载后的视频文件路径 |
| `wav_path` | 提取后的音频文件路径 |
| `docx_path` | 最终转写 Word 文档路径 |
| `mp4_size` | mp4 文件大小，单位字节 |
| `wav_size` | wav 文件大小，单位字节 |
| `audio_duration_ms` | 音频时长，单位毫秒 |

### 运行和排错字段

| 字段 | 说明 |
| --- | --- |
| `attempt_count` | 累计进入处理流程的次数 |
| `last_run_id` | 最近一次处理它的运行批次 ID |
| `last_processed_at` | 最近一次进入处理流程的时间 |
| `error_step` | 最近一次失败发生的步骤 |
| `error_type` | 最近一次失败的异常类型 |
| `error_message` | 最近一次失败信息 |

### 阶段完成时间

| 字段 | 说明 |
| --- | --- |
| `m3u8_done_at` | m3u8 捕获完成时间 |
| `video_done_at` | mp4 下载完成时间 |
| `audio_done_at` | wav 提取完成时间 |
| `asr_done_at` | ASR 识别完成时间 |
| `docx_done_at` | Word 文档生成完成时间 |

## crawl_runs 表

`crawl_runs` 保存每次 pipeline 的运行批次。一轮 pipeline 会生成一个 `run_id`，并写入到每个被处理的数据库中。

| 字段 | 说明 |
| --- | --- |
| `run_id` | 运行批次 ID，主键 |
| `page_url` | 本次运行对应的网站入口 URL |
| `process_start_time` | 本次处理的开始发布时间范围 |
| `process_end_time` | 本次处理的结束发布时间范围 |
| `started_at` | pipeline 开始时间 |
| `finished_at` | 当前数据库处理完成时间 |
| `status` | 批次状态：`RUNNING`、`SUCCESS`、`FAILED`、`PARTIAL_FAILED` |
| `target_count` | 本次进入处理流程的视频数量 |
| `success_count` | 本次成功生成 Word 的视频数量 |
| `failed_count` | 本次失败的视频数量 |
| `crawl_log_path` | 本次生成的爬取日志 JSON 路径 |
| `error_message` | 批次级错误信息，预留字段 |

## video_events 表

`video_events` 保存阶段级事件，适合排查某条视频卡在哪里。

| 字段 | 说明 |
| --- | --- |
| `event_id` | 自增事件 ID |
| `run_id` | 运行批次 ID |
| `item_id` | 视频 ID |
| `step` | 处理步骤 |
| `status` | 阶段状态：`START`、`SUCCESS`、`FAILED` |
| `message` | 阶段说明、产物路径或错误信息 |
| `created_at` | 事件记录时间 |

### step 取值

| step | 含义 |
| --- | --- |
| `M3U8_CAPTURE` | 打开详情页并捕获 m3u8 |
| `VIDEO_DOWNLOAD` | 使用 ffmpeg 下载 mp4 |
| `AUDIO_EXTRACT` | 使用 ffmpeg 提取 wav |
| `ASR_RECOGNIZE` | 调用 ASR 大模型识别 |
| `DOCX_GENERATE` | 生成 Word 转写文档 |

## 状态流转

`videos.status` 的主要流转如下：

```text
NEW
  -> M3U8_DONE
  -> VIDEO_DONE
  -> AUDIO_DONE
  -> ASR_DONE
  -> DOCX_DONE
```

任意阶段失败时会变成：

```text
FAILED
```

失败时会同时写入：

```text
videos.error_step
videos.error_type
videos.error_message
video_events(step='失败步骤', status='FAILED')
```

## 常用检查 SQL

进入某个数据库后执行：

```bash
sqlite3 "程序运行文件夹/运行数据库/<网站名>/<固定json名>.db"
```

### 查看视频状态分布

```sql
SELECT status, COUNT(*) AS count
FROM videos
GROUP BY status
ORDER BY count DESC;
```

### 查看最近一次运行批次

```sql
SELECT *
FROM crawl_runs
ORDER BY started_at DESC
LIMIT 5;
```

### 查看某次运行处理了哪些视频

```sql
SELECT item_id, title, publish_time, status, docx_path
FROM videos
WHERE last_run_id = '<run_id>'
ORDER BY publish_time DESC;
```

### 查看本次运行失败的视频

```sql
SELECT item_id, title, error_step, error_type, error_message
FROM videos
WHERE last_run_id = '<run_id>'
  AND status = 'FAILED'
ORDER BY updated_at DESC;
```

### 查看某条视频的阶段事件

```sql
SELECT step, status, message, created_at
FROM video_events
WHERE item_id = '<item_id>'
ORDER BY event_id;
```

### 查看某个阶段失败最多的位置

```sql
SELECT error_step, COUNT(*) AS count
FROM videos
WHERE status = 'FAILED'
GROUP BY error_step
ORDER BY count DESC;
```

### 查看已完成视频和文档地址

```sql
SELECT title, publish_time, docx_path
FROM videos
WHERE status = 'DOCX_DONE'
ORDER BY publish_time DESC;
```

## 前端展示建议

前端优先读取 `结果文件夹/爬取日志/*.json` 展示客户可见日志。运行数据库更适合内部管理页面使用。

爬取日志 JSON 会包含：

```text
run_id
page_url
crawl_time
video_count
done_count
pending_count
videos[].title
videos[].status
videos[].docx_path
```

建议前端管理页提供这些视图：

```text
运行批次列表：读取 crawl_runs
本次视频列表：按 videos.last_run_id 查询
失败排查页：按 videos.error_step / video_events 查询
结果文件入口：读取 videos.docx_path
```

## 维护说明

1. 建索引时会自动创建或升级数据库结构。
2. 处理视频时也会自动执行数据库迁移，确保旧库可以补齐新字段。
3. 不建议手动删除 `videos` 表，否则会丢失历史处理状态。
4. 如果需要重新处理某条视频，可以把该视频的 `status` 改回 `NEW` 或非 `DOCX_DONE` 状态。
5. 如果只想重跑失败视频，可以筛选 `status = 'FAILED'` 后重置状态。

示例：

```sql
UPDATE videos
SET status = 'NEW',
    error_step = NULL,
    error_type = NULL,
    error_message = NULL
WHERE item_id = '<item_id>';
```

## 推荐检查顺序

每次 pipeline 运行后，建议按下面顺序检查：

1. 打开最新爬取日志 JSON，确认客户可见结果。
2. 查询 `crawl_runs`，确认 `target_count / success_count / failed_count`。
3. 如果有失败，查询 `videos.error_step` 和 `video_events`。
4. 确认 `videos.docx_path` 指向的 Word 文件存在。
5. 如需重跑，先重置目标视频状态，再重新执行 pipeline。
