import builtins
import importlib
import sys


def test_supabase_client_module_imports_without_supabase_sdk(monkeypatch):
    module_name = "backend.app.core.supabase_client"
    monkeypatch.delitem(sys.modules, module_name, raising=False)

    original_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "supabase":
            raise ModuleNotFoundError("No module named 'supabase'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    module = importlib.import_module(module_name)

    assert module.get_supabase_admin_client() is None
    assert module.create_supabase_admin_client() is None
    assert module.get_supabase_client_optional() is None
