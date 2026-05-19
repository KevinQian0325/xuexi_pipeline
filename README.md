# Xuexi Pipeline

本项目是一个本地运行的“学习强国网页视频自动处理工具”。用户在前端配置需要监听的网页、密钥和结果目录后，后端会抓取网页固定 JSON，建立视频索引，下载视频，提取音频，调用 ASR 转写，并生成 Word 文档。

这份 README 主要给后续 Codex/维护者快速接手使用，优先说明架构、数据流、状态流转和关键文件。

## 当前技术栈

- 后端：Python、FastAPI、SQLite、Playwright、requests、ffmpeg、pydub、python-docx
- 前端：Vue 3、Vite
- 数据库：SQLite
- 本地运行入口：
  - 后端 API：`python -m uvicorn backend.api_server:app --host 127.0.0.1 --port 8000`
  - 前端：进入 `frontend/` 后执行 `npm run dev`

## 目录结构

```text
backend/
  api_server.py          FastAPI 接口层，给前端调用
  app_store.py           前端管理台数据库 app.db 的读写逻辑
  pipeline_runner.py     API 触发任务后的后台 pipeline 调度
  config.py              路径、状态常量、ASR 默认配置、命名规则
  discover_json.py       打开网页并捕获 /lgdata/*.json 固定 JSON
  build_index.py         从固定 JSON 提取视频条目，写入运行数据库
  process_video.py       核心处理链路：m3u8、mp4、wav、ASR、docx
  refresh_summary.py     生成爬取日志 JSON
  capture_m3u8.py        打开视频详情页并捕获 m3u8
  integrity_checker.py   文件完整性检查和补齐任务准备
  storage_migration.py   结果保存根目录迁移

frontend/
  src/App.vue                         主界面，监听配置和任务记录
  src/api/*.js                        前端 API 调用封装
  src/components/*                    弹窗和任务详情组件
  src/utils/statusLabels.js           运行状态、视频状态展示文案
  vite.config.js                      Vite 配置，/api 代理到 127.0.0.1:8000

dev_backup_databases.py   开发调试：备份 app.db 和运行数据库
dev_reset_databases.py    开发调试：重置 app.db 和运行数据库
dev_restore_databases.py  开发调试：从备份恢复数据库
DATABASE_GUIDE.md         运行数据库结构说明
启动.md                   本地启动命令备忘
功能.md                   功能说明草稿/产品说明
```

根目录以前有 `run_pipeline.py`、`discover_json.py`、`build_index.py`、`capture_m3u8.py` 四个 wrapper，已删除。命令行需要直接运行后端模块时使用：

```bash
python -m backend.run_pipeline
python -m backend.discover_json
python -m backend.build_index
python -m backend.capture_m3u8
```

## 运行数据目录

运行时会生成本地数据，不提交 git：

```text
程序运行文件夹/
  app.db                         前端管理台状态库
  json存储库/<网站名>/*.json       固定 JSON
  运行数据库/<网站名>/*.db          每个固定 JSON 对应的视频处理状态库
  爬取日志/*.json                 面向查看的爬取日志
  运行日志/api_pipeline.log       API 任务后台日志

结果文件夹/
  结果文件/<网页备注>/<栏目名>/<视频标题__发布时间>/
    视频.mp4
    音频.wav
    文本.docx
```

`app.db` 和运行数据库是两套不同职责：

- `app.db`：前端展示、监听配置、密钥配置、任务记录、任务详情。
- `运行数据库/*.db`：真实视频处理状态、产物路径、失败阶段、运行批次和事件。

前端“清除记录”只清 `app.db` 的任务记录，不会删除运行数据库和结果文件。后端实际判断视频是否要处理，主要看运行数据库里的 `videos.status`。

## 配置方式

当前产品流程以**前端密钥配置弹窗**为准。配置会保存到：

```text
程序运行文件夹/app.db -> env_config
```

包含：

- `xuexiAppId`
- `xuexiAccessToken`
- `resultFilesDir`

项目现在不再保留 `.env` 和 `.env.example`。`backend/config.py` 仍保留“如果 `.env` 存在就读取”的兼容逻辑，但正常前端流程不依赖它。

如果 `app.db` 被重置，需要重新在前端填写密钥和结果目录。

## 前端主流程

1. 用户在“网页监听配置”里添加网页、备注、时间范围。
2. 用户在“密钥配置”里填写 ASR key/token 和结果保存根目录。
3. 点击“运行”。
4. 前端调用 `POST /api/task-runs/start`。
5. 后端为每个启用网页创建一条 `task_runs` 记录。
6. FastAPI `BackgroundTasks` 调用 `pipeline_runner.run_real_pipeline_for_task()`。
7. 前端轮询 `GET /api/task-runs`，展示任务进度和明细。

## 后端 pipeline 主链路

API 任务入口在 `backend/pipeline_runner.py`：

```text
run_real_pipeline_for_task()
  1. 从 app.db 读取 env_config 并应用到运行时 config
  2. crawl_fixed_jsons_for_page()
  3. build_index_for_site()
  4. process_sites()
  5. refresh_summaries()
  6. load_task_details_from_process_results()
  7. replace_task_run_details()
```

核心视频处理在 `backend/process_video.py`：

```text
process_sites()
  -> process_one_db()
    -> sync_video_statuses_with_local_artifacts()
    -> load_pending_videos()
    -> process_one_video()
      1. 捕获 m3u8
      2. ffmpeg 下载 视频.mp4
      3. ffmpeg 提取 音频.wav
      4. recognize_flash_smart() 调 ASR
      5. json_to_word() 生成 文本.docx
```

`json_to_word()` 负责把 ASR 返回 JSON 转成 Word。当前已设置 A4 页面和固定表格宽度，避免“分段时间轴”表格超出正文范围。

## 运行数据库状态

运行数据库 `videos.status` 是真实处理状态：

```text
NEW
M3U8_DONE
VIDEO_DONE
AUDIO_DONE
ASR_DONE
DOCX_DONE
FAILED
IGNORED
```

待处理查询条件在 `process_video.load_pending_videos()`：

```sql
WHERE status NOT IN ('DOCX_DONE', 'IGNORED')
```

所以 `NEW / FAILED / M3U8_DONE / VIDEO_DONE / AUDIO_DONE / ASR_DONE` 都会被当作未完成继续处理。

每次处理数据库前会执行：

```text
sync_video_statuses_with_local_artifacts()
```

它会根据数据库记录的 `docx_path / wav_path / mp4_path / m3u8_url` 和本地文件是否存在，校准视频状态：

- `文本.docx` 存在 -> `DOCX_DONE`
- `音频.wav` 存在 -> `AUDIO_DONE`
- `视频.mp4` 存在 -> `VIDEO_DONE`
- 只有 `m3u8_url` -> `M3U8_DONE`
- 都没有 -> `NEW`

## 前端任务状态

`app.db.task_runs.status` 是前端任务主状态：

```text
RUNNING          执行中
STOP_REQUESTED   停止中，当前视频仍在收尾
STOPPED          已停止，可恢复
SUCCESS          全部完成
PARTIAL_FAILED   部分失败
FAILED           执行失败
```

`app.db.task_run_details.status` 是前端任务明细展示状态。它可能包含运行数据库没有的展示态：

```text
PROCESSING       本次任务排队/处理中
PENDING          待恢复处理
EXISTING         本次范围内已经有成品
```

注意：`PENDING / PROCESSING / EXISTING` 主要是前端任务明细展示态，不写入运行数据库 `videos.status`。

## 停止和恢复逻辑

当前实现的是“软停止”：

1. 用户在“任务执行情况”点击“停止运行”。
2. 后端把所有 `RUNNING` 任务改为 `STOP_REQUESTED`。
3. 当前正在处理的视频不会被强杀，会先跑完。
4. 每处理完一个视频后检查是否 `STOP_REQUESTED`。
5. 如果后面还有未开始的视频，把它们在 `task_run_details` 中标成 `PENDING`。
6. 任务主状态变成 `STOPPED`。
7. 用户点击“恢复”时，只恢复这条任务中的 `PENDING` 视频。

如果用户在最后一个视频运行时点击停止：

- 当前视频跑完后，如果没有剩余视频，就正常结算为 `SUCCESS / PARTIAL_FAILED / FAILED`。
- 不会出现 `STOPPED`，也不会出现“恢复”按钮。

恢复后的进度展示按整条原任务统计，而不是只按剩余视频统计。例如原任务 `2/3` 时停止，恢复后仍显示 `执行中 2/3 条`，剩余视频完成后变为 `3/3`。

## 文件完整性检查

前端“文件检查”调用：

```text
POST /api/integrity-check
POST /api/integrity-check/repair
```

后端在 `backend/integrity_checker.py` 中检查已经完成的视频是否仍存在：

- `视频.mp4`
- `音频.wav`
- `文本.docx`

如果缺失，可以创建“文件补齐”任务。补齐任务会根据缺失文件把运行库状态回退到合适阶段，然后只处理需要补齐的视频。

## 结果目录迁移

用户在前端修改“结果文件存储根目录”时，后端会调用 `backend/storage_migration.py`：

- 移动旧根目录内容到新根目录。
- 更新 `app.db.task_runs/result_dir` 和 `task_run_details` 路径。
- 更新运行数据库 `videos.material_dir/mp4_path/wav_path/docx_path`。

当前有运行中或停止中的任务时，不允许迁移。

## 开发维护提示

- 不要提交 `程序运行文件夹/`、`结果文件夹/`、`frontend/dist/`、`__pycache__/`、`.env*`。
- `dev_backup_databases.py`、`dev_reset_databases.py`、`dev_restore_databases.py` 是开发调试 DB 用脚本，保留。
- 新环境安装 Python 依赖后，需要安装 Playwright Chromium：

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

- 本项目依赖系统 `ffmpeg`。如果视频下载或音频提取失败，先确认 `ffmpeg` 是否在 PATH 中。

## 当前推荐启动方式

```bash
conda activate xuexi-pipeline
cd "/Users/kevinqian/Documents/Code/Intern XuanRong Technology/xuexi_pipeline"
python -m uvicorn backend.api_server:app --host 127.0.0.1 --port 8000
```

另开一个终端：

```bash
cd "/Users/kevinqian/Documents/Code/Intern XuanRong Technology/xuexi_pipeline/frontend"
npm run dev
```

前端默认通过 Vite proxy 把 `/api` 转发到 `http://127.0.0.1:8000`，因此本地开发通常不需要前端 `.env`。
