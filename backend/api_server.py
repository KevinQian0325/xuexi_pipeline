import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import app_store
from backend import integrity_checker
from backend import storage_migration
from backend.pipeline_runner import run_real_pipeline_for_task


app = FastAPI(title="Xuexi Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_result_dir(result_storage_root: str, remark: str) -> str:
    return str(Path(result_storage_root).expanduser() / "结果文件" / remark)


def with_index(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "index": index,
        }
        for index, item in enumerate(items, start=1)
    ]


def is_local_request(request: Request) -> bool:
    client_host = request.client.host if request.client else ""
    return client_host in {"127.0.0.1", "::1", "localhost"}


class ListenerSiteCreate(BaseModel):
    remark: str
    pageUrl: str
    startDate: str | None = None
    endDate: str | None = None


class RemarkUpdate(BaseModel):
    remark: str


class TimeRangeUpdate(BaseModel):
    startDate: str | None = None
    endDate: str | None = None


class StatusUpdate(BaseModel):
    enabled: bool


class EnvConfigUpdate(BaseModel):
    xuexiAppId: str
    xuexiAccessToken: str
    resultFilesDir: str


class TaskRunStart(BaseModel):
    sites: list[dict[str, Any]]


class TaskRunDelete(BaseModel):
    ids: list[int]


class TaskRunVideoAction(BaseModel):
    ids: list[str]
    reason: str | None = None


class OpenPathRequest(BaseModel):
    path: str


class IntegrityCheckRequest(BaseModel):
    siteIds: list[int]


def resolve_open_target(raw_path: str) -> Path:
    if not raw_path.strip():
        raise HTTPException(status_code=400, detail="路径不能为空")

    path = Path(raw_path).expanduser()
    if path.exists():
        return path if path.is_dir() else path.parent

    parent = path.parent
    if parent.exists():
        return parent

    raise HTTPException(status_code=404, detail="路径不存在")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/listener-sites")
def list_listener_sites(keyword: str = "") -> dict[str, Any]:
    items = app_store.list_listener_sites(keyword)
    return {"items": with_index(items), "total": len(items)}


@app.post("/api/listener-sites")
def create_listener_site(payload: ListenerSiteCreate) -> dict[str, Any]:
    next_id = app_store.create_listener_site(payload.model_dump())
    return {"id": next_id, "message": "创建成功"}


@app.patch("/api/listener-sites/{site_id}/remark")
def update_listener_site_remark(site_id: int, payload: RemarkUpdate) -> dict[str, str]:
    if not app_store.update_listener_site_remark(site_id, payload.remark):
        raise HTTPException(status_code=404, detail="监听配置不存在")
    return {"message": "备注修改成功"}


@app.patch("/api/listener-sites/{site_id}/time-range")
def update_listener_site_time_range(site_id: int, payload: TimeRangeUpdate) -> dict[str, str]:
    if not app_store.update_listener_site_time_range(site_id, payload.startDate, payload.endDate):
        raise HTTPException(status_code=404, detail="监听配置不存在")
    return {"message": "时间范围更新成功"}


@app.patch("/api/listener-sites/{site_id}/status")
def update_listener_site_status(site_id: int, payload: StatusUpdate) -> dict[str, str]:
    if not app_store.update_listener_site_status(site_id, payload.enabled):
        raise HTTPException(status_code=404, detail="监听配置不存在")
    return {"message": "状态更新成功"}


@app.delete("/api/listener-sites/{site_id}")
def delete_listener_site(site_id: int) -> dict[str, str]:
    if not app_store.delete_listener_site(site_id):
        raise HTTPException(status_code=404, detail="监听配置不存在")
    return {"message": "删除成功"}


@app.get("/api/env-config")
def get_env_config() -> dict[str, str]:
    return app_store.get_env_config()


@app.put("/api/env-config")
def update_env_config(payload: EnvConfigUpdate, request: Request) -> dict[str, Any]:
    migration_result = None
    current_config = app_store.get_env_config()
    current_root = current_config.get("resultFilesDir", "")
    requested_root = payload.resultFilesDir
    path_changed = (
        is_local_request(request)
        and storage_migration.normalize_storage_root(current_root)
        != storage_migration.normalize_storage_root(requested_root)
    )
    if path_changed:
        if app_store.has_running_task_runs():
            raise HTTPException(status_code=409, detail="当前有运行中的任务，不能迁移保存根目录")
        try:
            migration_result = storage_migration.migrate_storage_root(
                current_root,
                requested_root,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    app_store.update_env_config(
        payload.model_dump(),
        allow_path_update=is_local_request(request),
    )
    return {"message": "密钥配置已保存", "migration": migration_result}


@app.get("/api/task-runs")
def list_task_runs() -> dict[str, Any]:
    items = app_store.list_task_runs()
    return {"items": with_index(items), "total": len(items)}


@app.delete("/api/task-runs")
def clear_task_runs() -> dict[str, Any]:
    if app_store.has_running_task_runs():
        raise HTTPException(status_code=409, detail="当前有运行中的任务，不能清除记录")

    deleted_count = app_store.clear_task_runs()
    return {"deletedCount": deleted_count, "message": "任务执行记录已清除"}


@app.post("/api/task-runs/delete")
def delete_task_runs(payload: TaskRunDelete) -> dict[str, Any]:
    run_ids = sorted({int(run_id) for run_id in payload.ids})
    if not run_ids:
        raise HTTPException(status_code=400, detail="请选择要清除的记录")

    if app_store.has_running_task_runs(run_ids):
        raise HTTPException(status_code=409, detail="所选记录中有运行中的任务，不能清除")

    deleted_count = app_store.delete_task_runs(run_ids)
    return {"deletedCount": deleted_count, "message": "任务执行记录已清除"}


@app.post("/api/open-path")
def open_path(payload: OpenPathRequest, request: Request) -> dict[str, str]:
    if not is_local_request(request):
        raise HTTPException(status_code=403, detail="只能在服务器本机打开文件夹")

    target_path = resolve_open_target(payload.path)
    try:
        subprocess.run(["open", str(target_path)], check=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="当前系统不支持 open 命令") from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"打开路径失败：{target_path}") from exc

    return {"message": "已打开", "path": str(target_path)}


@app.post("/api/integrity-check")
def check_file_integrity(payload: IntegrityCheckRequest) -> dict[str, Any]:
    if not payload.siteIds:
        raise HTTPException(status_code=400, detail="请选择要检查的网页")

    return integrity_checker.check_sites(payload.siteIds)


@app.post("/api/integrity-check/repair")
def repair_file_integrity(
    payload: IntegrityCheckRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    if not payload.siteIds:
        raise HTTPException(status_code=400, detail="请选择要补齐文件的网页")
    if app_store.has_running_task_runs():
        raise HTTPException(status_code=409, detail="当前有运行中的任务，不能创建文件补齐任务")

    prepared = integrity_checker.prepare_repair_sites(payload.siteIds)
    targets = prepared.get("targets", [])
    if not targets:
        raise HTTPException(status_code=400, detail="没有需要补齐文件的视频")

    now = now_string()
    env_config = app_store.get_env_config()
    new_runs = []
    background_sites = []
    for target in targets:
        site = target["site"]
        item_ids = sorted({str(item_id) for item_id in target["itemIds"]})
        details = []
        for index, detail in enumerate(target["details"], start=1):
            details.append({
                "id": detail["itemId"],
                "title": detail["videoTitle"],
                "detailUrl": detail.get("detailUrl") or "",
                "publishTime": detail.get("publishTime") or "",
                "executedAt": now,
                "status": "PROCESSING",
                "mp4Path": detail.get("mp4Path") or "",
                "wavPath": detail.get("wavPath") or "",
                "docxPath": detail.get("docxPath") or "",
                "errorStep": "",
                "errorType": "",
                "errorMessage": "",
                "sortOrder": index,
            })

        new_runs.append({
            "remark": f"文件补齐：{site['remark']}",
            "pageUrl": site["pageUrl"],
            "resultDir": build_result_dir(env_config["resultFilesDir"], site["remark"]),
            "status": "RUNNING",
            "successCount": 0,
            "totalCount": len(item_ids),
            "executedAt": now,
            "duration": "00:00:00",
            "startDate": None,
            "endDate": None,
            "details": details,
        })
        background_sites.append({
            "remark": site["remark"],
            "pageUrl": site["pageUrl"],
            "startDate": None,
            "endDate": None,
            "itemIds": item_ids,
            "includeExistingDone": False,
        })

    created_runs = app_store.create_task_runs(new_runs)
    for created_run, site in zip(created_runs, background_sites, strict=True):
        background_tasks.add_task(run_real_pipeline_for_task, created_run["id"], site)

    return {
        "items": created_runs,
        "prepared": prepared,
        "message": "缺失文件补齐任务已创建",
    }


@app.post("/api/task-runs/start")
def start_task_runs(payload: TaskRunStart, background_tasks: BackgroundTasks) -> dict[str, Any]:
    now = now_string()
    env_config = app_store.get_env_config()
    new_runs = []
    for site in payload.sites:
        result_dir = build_result_dir(env_config["resultFilesDir"], site["remark"])
        run = {
            "remark": site["remark"],
            "pageUrl": site["pageUrl"],
            "resultDir": result_dir,
            "status": "RUNNING",
            "successCount": 0,
            "totalCount": 0,
            "executedAt": now,
            "duration": "00:00:00",
            "startDate": site.get("startDate"),
            "endDate": site.get("endDate"),
            "details": [],
        }
        new_runs.append(run)

    created_runs = app_store.create_task_runs(new_runs)
    for created_run, site in zip(created_runs, payload.sites, strict=True):
        background_tasks.add_task(run_real_pipeline_for_task, created_run["id"], site)

    return {"items": created_runs, "message": "运行任务已创建"}


@app.post("/api/task-runs/{run_id}/rerun-failed")
def rerun_failed_task_videos(run_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    run = app_store.get_task_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="任务记录不存在")
    if run["status"] == "RUNNING":
        raise HTTPException(status_code=409, detail="任务仍在运行中")

    failed_details = [
        detail
        for detail in run["details"]
        if detail["status"] not in {"DOCX_DONE", "EXISTING", "IGNORED"}
    ]
    if not failed_details:
        raise HTTPException(status_code=400, detail="没有失败视频需要重新运行")

    app_store.update_task_run_summary(
        run_id,
        status="RUNNING",
        executed_at=now_string(),
        duration="00:00:00",
    )
    background_tasks.add_task(
        run_real_pipeline_for_task,
        int(run["id"]),
        {
            "remark": run["remark"],
            "pageUrl": run["pageUrl"],
            "startDate": run.get("startDate"),
            "endDate": run.get("endDate"),
        },
    )

    updated_run = app_store.get_task_run(run_id)
    return {"item": updated_run, "message": "失败视频重新运行任务已创建"}


@app.post("/api/task-runs/{run_id}/rerun-videos")
def rerun_selected_task_videos(
    run_id: str,
    payload: TaskRunVideoAction,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    item_ids = sorted({str(item_id) for item_id in payload.ids if str(item_id).strip()})
    if not item_ids:
        raise HTTPException(status_code=400, detail="请选择要重新运行的视频")

    run = app_store.get_task_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="任务记录不存在")
    if run["status"] == "RUNNING":
        raise HTTPException(status_code=409, detail="任务仍在运行中")

    available_failed_ids = {
        str(detail["id"])
        for detail in run["details"]
        if detail["status"] not in {"DOCX_DONE", "EXISTING", "IGNORED"}
    }
    invalid_ids = [item_id for item_id in item_ids if item_id not in available_failed_ids]
    if invalid_ids:
        raise HTTPException(status_code=400, detail="只能重新运行当前任务中的失败视频")

    app_store.update_task_run_summary(
        run_id,
        status="RUNNING",
        executed_at=now_string(),
        duration="00:00:00",
    )
    background_tasks.add_task(
        run_real_pipeline_for_task,
        int(run["id"]),
        {
            "remark": run["remark"],
            "pageUrl": run["pageUrl"],
            "startDate": run.get("startDate"),
            "endDate": run.get("endDate"),
            "itemIds": item_ids,
            "includeExistingDone": False,
        },
    )

    updated_run = app_store.get_task_run(run_id)
    return {"item": updated_run, "message": "所选失败视频重新运行任务已创建"}


@app.post("/api/task-runs/{run_id}/ignore-videos")
def ignore_task_run_videos(run_id: str, payload: TaskRunVideoAction) -> dict[str, Any]:
    item_ids = sorted({str(item_id) for item_id in payload.ids if str(item_id).strip()})
    if not item_ids:
        raise HTTPException(status_code=400, detail="请选择要忽略的视频")

    run = app_store.get_task_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="任务记录不存在")
    if run["status"] == "RUNNING":
        raise HTTPException(status_code=409, detail="任务仍在运行中，不能忽略视频")

    available_failed_ids = {
        str(detail["id"])
        for detail in run["details"]
        if detail["status"] not in {"DOCX_DONE", "EXISTING", "IGNORED"}
    }
    invalid_ids = [item_id for item_id in item_ids if item_id not in available_failed_ids]
    if invalid_ids:
        raise HTTPException(status_code=400, detail="只能忽略当前任务中的失败视频")

    reason = (payload.reason or "用户确认忽略").strip() or "用户确认忽略"
    app_detail_count = app_store.ignore_task_run_details(run_id, item_ids, reason)
    runtime_count = app_store.ignore_runtime_videos(run["pageUrl"], item_ids, reason)
    updated_run = app_store.get_task_run(run_id)
    return {
        "item": updated_run,
        "ignoredCount": app_detail_count,
        "runtimeIgnoredCount": runtime_count,
        "message": "已忽略所选失败视频",
    }
