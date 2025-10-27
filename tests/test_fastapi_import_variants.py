def test_import_with_and_without_fastapi(monkeypatch):
    import sys
    import importlib

    # Create a fake `fastapi` package with the minimal attributes used by the module
    class DummyApp:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def _dec(f):
                return f

            return _dec

        def post(self, *args, **kwargs):
            def _dec(f):
                return f

            return _dec

        def websocket(self, *args, **kwargs):
            def _dec(f):
                return f

            return _dec

    class DummyWebSocket:
        pass

    class DummyResponses:
        class JSONResponse:
            def __init__(self, status_code, content):
                self.status_code = status_code
                self.content = content

    fake_fastapi = type(sys)('fastapi')
    fake_fastapi.FastAPI = DummyApp
    fake_fastapi.WebSocket = DummyWebSocket

    fake_responses = type(sys)('fastapi.responses')
    fake_responses.JSONResponse = DummyResponses.JSONResponse

    # Install fake modules so importing `src.fastapi_app` thinks FastAPI is present
    sys.modules['fastapi'] = fake_fastapi
    sys.modules['fastapi.responses'] = fake_responses

    # Import (or reload) the module so it registers routes using the fake FastAPI
    mod = importlib.import_module('src.fastapi_app')
    importlib.reload(mod)
    assert getattr(mod, 'app', None) is not None

    # Now remove the fake package and reload to exercise the non-FastAPI branch
    del sys.modules['fastapi']
    del sys.modules['fastapi.responses']
    importlib.reload(mod)
    # If real FastAPI is installed in the environment, reloading will create
    # a real FastAPI `app`. If not installed, our module sets `app = None`.
    real_fastapi_installed = True
    try:
        import fastapi  # type: ignore
    except Exception:
        real_fastapi_installed = False

    if real_fastapi_installed:
        assert getattr(mod, 'app', None) is not None
    else:
        assert getattr(mod, 'app', None) is None
