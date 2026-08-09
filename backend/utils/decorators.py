import time
import inspect
from functools import wraps
from typing import Any
from contextvars import ContextVar

# تعريف متغيرات السياق مرة واحدة فقط
_active_node: ContextVar[str | None] = ContextVar("active_node", default=None)
_active_usage: ContextVar[dict | None] = ContextVar("active_usage", default=None)

def _empty_usage() -> dict:
    return {"llm_input_tokens": 0, "llm_output_tokens": 0, "llm_total_tokens": 0, "llm_calls": 0}

def _start_token_tracking(node_name: str):
    node_token = _active_node.set(node_name)
    usage_token = _active_usage.set(_empty_usage())
    return node_token, usage_token

def _finish_token_tracking(tokens):
    usage = _active_usage.get() or _empty_usage()
    _active_usage.reset(tokens[1])
    _active_node.reset(tokens[0])
    return usage

def record_model_usage(*, input_tokens: int = 0, output_tokens: int = 0) -> None:
    usage = _active_usage.get()
    if usage is None: return
    usage["llm_calls"] += 1
    i_tokens = input_tokens or 0
    o_tokens = output_tokens or 0
    usage["llm_input_tokens"] += i_tokens
    usage["llm_output_tokens"] += o_tokens
    usage["llm_total_tokens"] += (i_tokens + o_tokens)

def _add_node_metrics(result: Any, node_name: str, usage: dict, duration: float):
    # نحدث الـ result (الـ state) مباشرة
    if isinstance(result, dict):
        result.setdefault("token_usage", {})
        result.setdefault("execution_time", {})
        result["token_usage"][node_name] = usage
        result["execution_time"][node_name] = round(duration, 3)
    elif hasattr(result, "token_usage"):
        if result.token_usage is None: result.token_usage = {}
        if result.execution_time is None: result.execution_time = {}
        result.token_usage[node_name] = usage
        result.execution_time[node_name] = round(duration, 3)
    return result

def track_tokens(node_name: str):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(state, *args, **kwargs):
                start = time.perf_counter()
                tokens = _start_token_tracking(node_name)
                try:
                    result = await func(state, *args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    usage = _finish_token_tracking(tokens)
                return _add_node_metrics(result, node_name, usage, duration)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(state, *args, **kwargs):
                start = time.perf_counter()
                tokens = _start_token_tracking(node_name)
                try:
                    result = func(state, *args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    usage = _finish_token_tracking(tokens)
                return _add_node_metrics(result, node_name, usage, duration)
            return sync_wrapper
    return decorator