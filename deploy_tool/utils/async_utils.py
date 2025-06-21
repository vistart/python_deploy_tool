# deploy_tool/utils/async_utils.py
"""Asynchronous operation utilities"""

import asyncio
import functools
from typing import Any, Callable, Coroutine, List, Optional, TypeVar, Union

T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine in sync context

    Args:
        coro: Coroutine to run

    Returns:
        Coroutine result
    """
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop
        pass

    if loop and loop.is_running():
        # Already in async context, create new thread
        import concurrent.futures
        import threading

        result = None
        exception = None

        def run_in_thread():
            nonlocal result, exception
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(coro)
                new_loop.close()
            except Exception as e:
                exception = e

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()

        if exception:
            raise exception
        return result
    else:
        # No running loop, use asyncio.run
        return asyncio.run(coro)


async def gather_with_progress(tasks: List[Coroutine],
                               callback: Optional[Callable[[int, int], None]] = None,
                               return_exceptions: bool = False) -> List[Any]:
    """
    Gather tasks with progress callback

    Args:
        tasks: List of coroutines
        callback: Progress callback(completed, total)
        return_exceptions: Whether to return exceptions instead of raising

    Returns:
        List of results
    """
    total = len(tasks)
    completed = 0
    results = []

    async def wrapped_task(task):
        nonlocal completed
        try:
            result = await task
            completed += 1
            if callback:
                callback(completed, total)
            return result
        except Exception as e:
            completed += 1
            if callback:
                callback(completed, total)
            if return_exceptions:
                return e
            else:
                raise

    wrapped_tasks = [wrapped_task(task) for task in tasks]
    results = await asyncio.gather(*wrapped_tasks, return_exceptions=False)

    return results


async def timeout_async(coro: Coroutine[Any, Any, T],
                        timeout: float,
                        default: Any = None) -> Union[T, Any]:
    """
    Run coroutine with timeout

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        default: Default value on timeout

    Returns:
        Coroutine result or default
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default


async def retry_async(coro_func: Callable[..., Coroutine[Any, Any, T]],
                      *args,
                      max_attempts: int = 3,
                      delay: float = 1.0,
                      backoff: float = 2.0,
                      exceptions: tuple = (Exception,),
                      **kwargs) -> T:
    """
    Retry async operation with exponential backoff

    Args:
        coro_func: Coroutine function
        *args: Function arguments
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Exceptions to catch
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all attempts fail
    """
    current_delay = delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await coro_func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                raise


def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to convert async function to sync

    Args:
        func: Async function

    Returns:
        Sync wrapper function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        coro = func(*args, **kwargs)
        return run_async(coro)

    return wrapper


def sync_to_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to convert sync function to async

    Args:
        func: Sync function

    Returns:
        Async wrapper function
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    return wrapper


async def run_in_chunks(items: List[Any],
                        processor: Callable[[Any], Coroutine[Any, Any, Any]],
                        chunk_size: int = 10) -> List[Any]:
    """
    Process items in chunks to limit concurrency

    Args:
        items: Items to process
        processor: Async processor function
        chunk_size: Number of items to process concurrently

    Returns:
        List of results
    """
    results = []

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        chunk_results = await asyncio.gather(
            *[processor(item) for item in chunk]
        )
        results.extend(chunk_results)

    return results


class AsyncContextManager:
    """Base class for async context managers"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class AsyncPool:
    """Simple async task pool"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.tasks = []

    async def submit(self, coro: Coroutine) -> asyncio.Task:
        """Submit task to pool"""

        async def wrapped():
            async with self.semaphore:
                return await coro

        task = asyncio.create_task(wrapped())
        self.tasks.append(task)
        return task

    async def wait_all(self) -> List[Any]:
        """Wait for all tasks to complete"""
        results = await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.wait_all()