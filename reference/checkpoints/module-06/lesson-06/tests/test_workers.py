import asyncio
from threading import current_thread

import pytest

from app.security.workers import run_password_operation


pytestmark = pytest.mark.anyio


async def test_cpu_bound_operation_runs_outside_the_event_loop_thread() -> None:
    event_loop_thread = current_thread().name

    worker_thread = await run_password_operation(lambda: current_thread().name)

    assert worker_thread.startswith("library-password")
    assert worker_thread != event_loop_thread


async def test_worker_propagates_operation_errors() -> None:
    def fail() -> None:
        raise ValueError("falha controlada")

    with pytest.raises(ValueError, match="falha controlada"):
        await run_password_operation(fail)
