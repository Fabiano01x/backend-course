"""Execução limitada de operações CPU-bound sem bloquear o event loop."""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import ParamSpec, TypeVar


P = ParamSpec("P")
T = TypeVar("T")

_PASSWORD_WORKERS = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="library-password"
)


async def run_password_operation(
    operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """Executa hash/verify em um pool limitado e propaga seu resultado."""

    future = _PASSWORD_WORKERS.submit(operation, *args, **kwargs)
    try:
        while not future.done():
            await asyncio.sleep(0.005)
        return future.result()
    except asyncio.CancelledError:
        future.cancel()
        raise
