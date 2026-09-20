from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx


BATCH_URL = "https://mineru.net/api/v4/file-urls/batch"
STATUS_URL = "https://mineru.net/api/v4/extract-results/batch/{batch_id}"


class MinerUError(RuntimeError):
    pass


def _safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    target_root = target.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            destination = (target / member.filename).resolve()
            if destination != target_root and target_root not in destination.parents:
                raise MinerUError(f"MinerU 压缩包包含不安全路径: {member.filename}")
        bundle.extractall(target)


def _first_result(response: dict[str, Any]) -> dict[str, Any]:
    try:
        return response["data"]["extract_result"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise MinerUError("MinerU 返回了无法识别的状态响应") from exc


def parse_pdf(
    pdf_path: Path,
    output_dir: Path,
    api_key: str,
    *,
    poll_interval: float = 5,
    poll_timeout: float = 900,
    request_timeout: float = 60,
) -> tuple[list[Any], str]:
    """Submit a PDF to MinerU and return its best structured content list."""
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
        "model_version": "vlm",
    }
    with httpx.Client(timeout=request_timeout, follow_redirects=True) as client:
        response = client.post(BATCH_URL, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0:
            raise MinerUError(f"MinerU 创建解析任务失败: {body.get('msg', 'unknown error')}")
        try:
            batch_id = body["data"]["batch_id"]
            upload_url = body["data"]["file_urls"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise MinerUError("MinerU 未返回上传地址") from exc

        with pdf_path.open("rb") as source:
            upload = client.put(upload_url, content=source)
        upload.raise_for_status()

        deadline = time.monotonic() + poll_timeout
        download_url: str | None = None
        while time.monotonic() < deadline:
            status = client.get(STATUS_URL.format(batch_id=batch_id), headers=headers)
            status.raise_for_status()
            result = _first_result(status.json())
            state = result.get("state")
            if state == "done" and result.get("full_zip_url"):
                download_url = str(result["full_zip_url"])
                break
            if state in {"failed", "error"}:
                raise MinerUError(f"MinerU 解析失败: {result.get('err_msg') or result.get('msg') or state}")
            time.sleep(poll_interval)
        if not download_url:
            raise MinerUError(f"MinerU 解析超时（{poll_timeout:g} 秒）")

        archive_path = output_dir / "mineru-result.zip"
        with client.stream("GET", download_url) as download:
            download.raise_for_status()
            with archive_path.open("wb") as target:
                for chunk in download.iter_bytes():
                    target.write(chunk)

    try:
        _safe_extract(archive_path, output_dir)
    finally:
        archive_path.unlink(missing_ok=True)

    v2_files = sorted(output_dir.rglob("*content_list_v2.json"))
    v1_files = sorted(output_dir.rglob("*content_list.json"))
    candidates = [(path, "v2") for path in v2_files] + [(path, "v1") for path in v1_files]
    if not candidates:
        raise MinerUError("MinerU 结果中缺少 content_list JSON")
    content_path, version = candidates[0]
    try:
        content = json.loads(content_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MinerUError(f"无法读取 MinerU 结果: {content_path.name}") from exc
    if not isinstance(content, list):
        raise MinerUError("MinerU content_list 的顶层结构不是数组")
    return content, version
