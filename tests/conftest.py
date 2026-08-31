import sys
from types import ModuleType, SimpleNamespace

# Provide a minimal aiogram stub to allow importing modules that reference aiogram in tests
aiogram = ModuleType("aiogram")

# Minimal Dispatcher placeholder
class _Dispatcher:
    pass
aiogram.Dispatcher = _Dispatcher

# Minimal Router placeholder with decorator behavior
class _Router:
    def message(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

aiogram.Router = _Router

# Minimal F placeholder that supports F.text.casefold() == "..." style used in handlers
class _CasefoldExpr:
    def __init__(self):
        pass
    def casefold(self):
        return self
    def __call__(self, *args, **kwargs):
        return self
    def __eq__(self, other):
        # return a placeholder filter object
        return f"Filter(eq:{other})"

class _F:
    def __init__(self):
        self.text = _CasefoldExpr()

aiogram.F = _F()

# Minimal types namespace with ReplyKeyboardRemove placeholder
# Provide a minimal types namespace used in annotations and code
_types_ns = SimpleNamespace()
_types_ns.ReplyKeyboardRemove = lambda: None
# Minimal Message class placeholder for type annotations
class _Message:
    pass
_types_ns.Message = _Message
# Provide LinkPreviewOptions used in handlers.start
class _LinkPreviewOptions:
    def __init__(self, is_disabled=False):
        self.is_disabled = is_disabled
_types_ns.LinkPreviewOptions = _LinkPreviewOptions

aiogram.types = _types_ns

sys.modules["aiogram"] = aiogram

# Stub asyncpg to avoid installing it for unit tests of utils
import types as _types
_asyncpg = ModuleType("asyncpg")
# Minimal attributes used by stubs in code
_asyncpg.Pool = object
sys.modules["asyncpg"] = _asyncpg
