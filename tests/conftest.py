import sys
from types import ModuleType, SimpleNamespace

# Provide a minimal aiogram stub to allow importing modules that reference aiogram in tests
aiogram = ModuleType("aiogram")
# Minimal Dispatcher placeholder
class _Dispatcher:
    pass
aiogram.Dispatcher = _Dispatcher
# Minimal types namespace with ReplyKeyboardRemove placeholder
# Provide a minimal types namespace used in annotations and code
_types_ns = SimpleNamespace()
_types_ns.ReplyKeyboardRemove = lambda: None
# Minimal Message class placeholder for type annotations
class _Message:
    pass
_types_ns.Message = _Message
aiogram.types = _types_ns

sys.modules["aiogram"] = aiogram

# Stub asyncpg to avoid installing it for unit tests of utils
import types as _types
_asyncpg = ModuleType("asyncpg")
# Minimal attributes used by stubs in code
_asyncpg.Pool = object
sys.modules["asyncpg"] = _asyncpg
