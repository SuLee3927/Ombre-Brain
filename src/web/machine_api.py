"""Fork compatibility endpoints used by local automation services."""

from . import _shared as sh
from .hooks import _is_hook_request_authorized


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
        content = str(body.get("content", "") or "")
        if not content.strip():
            return JSONResponse({"error": "content is required"}, status_code=400)

        # v3 has a first-class immutable source/quote layer.  Preserve the old
        # machine API by translating its source_quote field instead of reviving
        # the fork's parallel provenance metadata model.
        quotes = body.get("quotes")
        source_quote = str(body.get("source_quote", "") or "").strip()
        if quotes in (None, "", []) and source_quote:
            quotes = [{"text": source_quote}]
        try:
            from tools.hold import dispatch as hold_dispatch

            result = await hold_dispatch(
                content=content,
                title=str(body.get("title", "") or ""),
                tags=body.get("tags", "") or "",
                importance=body.get("importance", 5),
                pinned=body.get("pinned", False),
                feel=body.get("feel", False),
                source_bucket=str(body.get("source_bucket", "") or ""),
                valence=body.get("valence", -1),
                arousal=body.get("arousal", -1),
                why_remembered=str(body.get("why_remembered", "") or ""),
                meaning=str(body.get("meaning", "") or ""),
                domain=body.get("domain", "") or "",
                source_content=str(body.get("source_content", "") or ""),
                source_ranges=body.get("source_ranges"),
                quotes=quotes,
            )
            return JSONResponse({"ok": True, "result": result})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

    @mcp.custom_route("/api/dream", methods=["POST", "GET"])
    async def api_dream(request):
        from starlette.responses import JSONResponse
        from utils import strip_wikilinks

        if not _is_hook_request_authorized(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            all_buckets = await sh.bucket_mgr.list_all(include_archive=False)
            candidates = [
                bucket for bucket in all_buckets
                if bucket["metadata"].get("type")
                not in ("permanent", "feel", "plan", "letter", "self", "i")
                and not bucket["metadata"].get("pinned", False)
                and not bucket["metadata"].get("protected", False)
                and not bucket["metadata"].get("dont_surface", False)
            ]
            candidates.sort(
                key=lambda bucket: bucket["metadata"].get("created", ""), reverse=True
            )
            parts = []
            for bucket in candidates[:10]:
                meta = bucket["metadata"]
                parts.append(
                    f"{meta.get('name', bucket['id'])}\n"
                    f"{strip_wikilinks(bucket['content'][:200])}"
                )
            return JSONResponse({"content": "\n---\n".join(parts)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
