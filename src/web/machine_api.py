"""
========================================
web/machine_api.py — [fork加装] 机器对机器端点
========================================

给外部自动化服务（desire 欲望系统、bridge 脚本等）用的最小 HTTP API，
不走 dashboard 会话，鉴权复用 hooks 的 token 体系（OMBRE_HOOK_TOKEN，
Bearer / ?token= / x-ombre-hook-token 三种供给方式，见 hooks._is_hook_request_authorized）。

- POST /api/hold  {content, tags?, importance?, pinned?, feel?} → 直接建桶
- POST /api/dream            → dream 候选（JSON {"content": ...}），desire 服务的
  fatigue 触发做梦依赖此端点；上游 v3 重构删掉了它，这里按 /dream-hook 的逻辑
  重建并保持旧响应格式，desire 侧无需改动。
"""

from . import _shared as sh
from .hooks import _is_hook_request_authorized

logger = sh.logger


def register(mcp) -> None:

    @mcp.custom_route("/api/hold", methods=["POST"])
    async def api_hold(request):
        from starlette.responses import JSONResponse
        if not _is_hook_request_authorized(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        content = body.get("content", "")
        if not content or not str(content).strip():
            return JSONResponse({"error": "content is required"}, status_code=400)
        try:
            from ..tools.hold import dispatch as hold_dispatch
            result = await hold_dispatch(
                content=str(content),
                tags=str(body.get("tags", "") or ""),
                importance=int(body.get("importance", 5) or 5),
                pinned=bool(body.get("pinned", False)),
                feel=bool(body.get("feel", False)),
                source_role=str(body.get("source_role", "unknown") or "unknown"),
                created_by=str(body.get("created_by", "unknown") or "unknown"),
                initiated_by=str(body.get("initiated_by", "unknown") or "unknown"),
                source_turn_id=str(body.get("source_turn_id", "") or ""),
                source_timestamp=str(body.get("source_timestamp", "") or ""),
                source_quote=str(body.get("source_quote", "") or ""),
                confidence=body.get("confidence"),
            )
            return JSONResponse({"ok": True, "result": result})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @mcp.custom_route("/api/dream", methods=["POST", "GET"])
    async def api_dream(request):
        from starlette.responses import JSONResponse
        if not _is_hook_request_authorized(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            all_buckets = await sh.bucket_mgr.list_all(include_archive=False)
            candidates = [
                b for b in all_buckets
                if b["metadata"].get("type") not in ("permanent", "feel", "plan", "letter", "self", "i")
                and not b["metadata"].get("pinned", False)
                and not b["metadata"].get("protected", False)
                and not b["metadata"].get("dont_surface", False)
            ]
            candidates.sort(key=lambda b: b["metadata"].get("created", ""), reverse=True)
            recent = candidates[:10]
            if not recent:
                return JSONResponse({"content": ""})
            from ..utils import strip_wikilinks
            parts = []
            for b in recent:
                meta = b["metadata"]
                parts.append(
                    f"{meta.get('name', b['id'])}\n{strip_wikilinks(b['content'][:200])}"
                )
            return JSONResponse({"content": "\n---\n".join(parts)})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
