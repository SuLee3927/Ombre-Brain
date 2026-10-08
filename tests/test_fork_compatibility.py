from web import _shared, hooks, oauth


class Request:
    def __init__(self, authorization="", hook_token=""):
        self.headers = {
            "authorization": authorization,
            "x-ombre-hook-token": hook_token,
        }
        self.cookies = {}
        self.query_params = {}


def test_machine_token_authenticates_dashboard_api(monkeypatch):
    monkeypatch.setenv("OMBRE_MACHINE_TOKEN", "machine-secret")
    request = Request("Bearer machine-secret")
    assert _shared._require_auth(request) is None


def test_machine_token_authenticates_hook_compatible_routes(monkeypatch):
    monkeypatch.delenv("OMBRE_HOOK_ALLOW_PUBLIC", raising=False)
    monkeypatch.delenv("OMBRE_HOOK_TOKEN", raising=False)
    monkeypatch.setenv("OMBRE_MACHINE_TOKEN", "machine-secret")
    monkeypatch.setattr(hooks, "_hook_setting", lambda _name, default="": default)
    assert hooks._is_hook_request_authorized(Request("Bearer machine-secret")) is True


def test_legacy_static_mcp_token_name_is_accepted(monkeypatch):
    monkeypatch.delenv("OMBRE_MCP_TOKEN", raising=False)
    monkeypatch.delenv("OMBRE_MACHINE_TOKEN", raising=False)
    monkeypatch.setenv("OMBRE_MCP_STATIC_TOKEN", "legacy-secret")
    monkeypatch.setattr(oauth.sh, "config", {})
    assert oauth._is_valid_static_mcp_token("legacy-secret") is True
    assert oauth._is_valid_static_mcp_token("wrong") is False


def test_machine_api_is_registered():
    routes = []

    class MCP:
        def custom_route(self, path, methods):
            routes.append((path, tuple(methods)))
            return lambda function: function

    from web import machine_api

    machine_api.register(MCP())
    assert ("/api/hold", ("POST",)) in routes
    assert ("/api/dream", ("POST", "GET")) in routes
