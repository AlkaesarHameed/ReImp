"""
Async Processing Service.
Source: Design Document Section 5.1 - Performance Optimization
Verified: 2025-12-18

Provides optimized async batch processing and task management.
"""

import asyncio
import time
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, TypeVar, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Async task status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class BatchConfig(BaseModel):
    """Batch processing configuration."""

    batch_size: int = 100
    max_concurrent: int = 10
    timeout_per_item: float = 30.0  # seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds
    fail_fast: bool = False  # Stop on first failure


class ProcessingStats(BaseModel):
    """Processing statistics."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    in_progress_tasks: int = 0
    total_processing_time_ms: float = 0.0
    avg_task_time_ms: float = 0.0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0


class TaskResult(BaseModel):
    """Result of a processed task."""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    attempts: int = 1
    processing_time_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


T = TypeVar("T")
R = TypeVar("R")


class AsyncTask(Generic[T, R]):
    """Async task wrapper."""

    def __init__(
        self,
        task_id: str,
        data: T,
        processor: Callable[[T], R],
        priority: TaskPriority = TaskPriority.NORMAL,
    ):
        """Initialize async task."""
        self.task_id = task_id
        self.data = data
        self.processor = processor
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.result: Optional[R] = None
        self.error: Optional[str] = None
        self.attempts = 0
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def __lt__(self, other: "AsyncTask") -> bool:
        """Compare for priority queue."""
        return self.priority.value > other.priority.value


class AsyncProcessor:
    """Async batch processing service."""

    def __init__(self, config: BatchConfig | None = None):
        """Initialize AsyncProcessor."""
        self._config = config or BatchConfig()
        self._tasks: dict[str, AsyncTask] = {}
        self._pending_queue: asyncio.PriorityQueue[tuple[int, AsyncTask]] = asyncio.PriorityQueue()
        self._running_count = 0
        self._lock = asyncio.Lock()
        self._shutdown = False

        # Statistics
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._cancelled_tasks = 0
        self._processing_times: deque[float] = deque(maxlen=1000)
        self._start_time: Optional[float] = None

    @property
    def config(self) -> BatchConfig:
        """Get processing configuration."""
        return self._config

    async def submit(
        self,
        data: T,
        processor: Callable[[T], R],
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: str | None = None,
    ) -> str:
        """Submit a task for processing."""
        task_id = task_id or str(uuid4())

        task = AsyncTask(
            task_id=task_id,
            data=data,
            processor=processor,
            priority=priority,
        )

        self._tasks[task_id] = task
        self._total_tasks += 1

        # Add to priority queue (negative priority for max-heap behavior)
        await self._pending_queue.put((-priority.value, task))

        return task_id

    async def submit_batch(
        self,
        items: list[T],
        processor: Callable[[T], R],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> list[str]:
        """Submit a batch of tasks."""
        task_ids = []

        for item in items:
            task_id = await self.submit(item, processor, priority)
            task_ids.append(task_id)

        return task_ids

    async def process_one(self, task: AsyncTask) -> TaskResult:
        """Process a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.attempts += 1

        start_time = time.perf_counter()
        error: Optional[str] = None

        try:
            # Execute processor
            if asyncio.iscoroutinefunction(task.processor):
                result = await asyncio.wait_for(
                    task.processor(task.data),
                    timeout=self._config.timeout_per_item,
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, task.processor, task.data
                    ),
                    timeout=self._config.timeout_per_item,
                )

            task.result = result
            task.status = TaskStatus.COMPLETED

        except asyncio.TimeoutError:
            error = "Task timed out"
            task.status = TaskStatus.FAILED
        except asyncio.CancelledError:
            error = "Task cancelled"
            task.status = TaskStatus.CANCELLED
        except Exception as e:
            error = str(e)
            task.status = TaskStatus.FAILED

        task.error = error
        task.completed_at = datetime.utcnow()
        processing_time = (time.perf_counter() - start_time) * 1000

        # Update stats
        self._processing_times.append(processing_time)
        if task.status == TaskStatus.COMPLETED:
            self._completed_tasks += 1
        elif task.status == TaskStatus.FAILED:
            self._failed_tasks += 1
        elif task.status == TaskStatus.CANCELLED:
            self._cancelled_tasks += 1

        return TaskResult(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            attempts=task.attempts,
            processing_time_ms=processing_time,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    async def process_all(
        self,
        callback: Callable[[TaskResult], None] | None = None,
    ) -> list[TaskResult]:
        """Process all pending tasks."""
        if self._start_time is None:
            self._start_time = time.perf_counter()

        results: list[TaskResult] = []
        tasks_to_process: list[AsyncTask] = []

        # Collect all pending tasks
        while not self._pending_queue.empty():
            try:
                _, task = await asyncio.wait_for(
                    self._pending_queue.get(),
                    timeout=0.1,
                )
                tasks_to_process.append(task)
            except asyncio.TimeoutError:
                break

        # Process in batches with concurrency limit
        for i in range(0, len(tasks_to_process), self._config.batch_size):
            batch = tasks_to_process[i : i + self._config.batch_size]

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self._config.max_concurrent)

            async def process_with_semaphore(task: AsyncTask) -> TaskResult:
                async with semaphore:
                    return await self._process_with_retry(task)

            # Process batch concurrently
            batch_results = await asyncio.gather(
                *[process_with_semaphore(task) for task in batch],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    # Handle unexpected exceptions
                    results.append(TaskResult(
                        task_id="unknown",
                        status=TaskStatus.FAILED,
                        error=str(result),
                    ))
                else:
                    results.append(result)
                    if callback:
                        callback(result)

                # Check fail fast
                if self._config.fail_fast and result.status == TaskStatus.FAILED:
                    # Cancel remaining tasks
                    for remaining in tasks_to_process[i + len(batch) :]:
                        remaining.status = TaskStatus.CANCELLED
                        self._cancelled_tasks += 1
                    break

        return results

    async def _process_with_retry(self, task: AsyncTask) -> TaskResult:
        """Process task with retry logic."""
        result: Optional[TaskResult] = None

        for attempt in range(self._config.retry_attempts):
            result = await self.process_one(task)

            if result.status == TaskStatus.COMPLETED:
                return result

            if result.status == TaskStatus.CANCELLED:
                return result

            # Failed - retry if attempts remaining
            if attempt < self._config.retry_attempts - 1:
                await asyncio.sleep(self._config.retry_delay * (attempt + 1))
                task.status = TaskStatus.PENDING

        return result or TaskResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            error="Max retries exceeded",
        )

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result for a specific task."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        return TaskResult(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            attempts=task.attempts,
            processing_time_ms=0.0,  # Would need to track
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    async def wait_for(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskResult:
        """Wait for a task to complete."""
        start = time.perf_counter()
        timeout = timeout or self._config.timeout_per_item * self._config.retry_attempts

        while True:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return await self.get_result(task_id)

            elapsed = time.perf_counter() - start
            if elapsed > timeout:
                raise TimeoutError(f"Timeout waiting for task: {task_id}")

            await asyncio.sleep(0.1)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self._cancelled_tasks += 1
            return True

        return False

    async def cancel_all(self) -> int:
        """Cancel all pending tasks."""
        count = 0

        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                self._cancelled_tasks += 1
                count += 1

        return count

    def get_stats(self) -> ProcessingStats:
        """Get processing statistics."""
        elapsed = (
            time.perf_counter() - self._start_time
            if self._start_time else 0.0
        )

        total_time = sum(self._processing_times) if self._processing_times else 0.0
        avg_time = total_time / len(self._processing_times) if self._processing_times else 0.0

        throughput = (
            self._completed_tasks / elapsed if elapsed > 0 else 0.0
        )

        error_rate = (
            self._failed_tasks / self._total_tasks * 100
            if self._total_tasks > 0 else 0.0
        )

        in_progress = sum(
            1 for t in self._tasks.values()
            if t.status == TaskStatus.RUNNING
        )

        return ProcessingStats(
            total_tasks=self._total_tasks,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            cancelled_tasks=self._cancelled_tasks,
            in_progress_tasks=in_progress,
            total_processing_time_ms=total_time,
            avg_task_time_ms=avg_time,
            throughput_per_second=throughput,
            error_rate=error_rate,
        )

    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._cancelled_tasks = 0
        self._processing_times.clear()
        self._start_time = None

    async def shutdown(self) -> None:
        """Gracefully shutdown processor."""
        self._shutdown = True
        await self.cancel_all()


# =============================================================================
# Factory Functions
# =============================================================================


_async_processor: AsyncProcessor | None = None


def get_async_processor(config: BatchConfig | None = None) -> AsyncProcessor:
    """Get singleton AsyncProcessor instance."""
    global _async_processor
    if _async_processor is None:
        _async_processor = AsyncProcessor(config)
    return _async_processor


def create_async_processor(config: BatchConfig | None = None) -> AsyncProcessor:
    """Create new AsyncProcessor instance."""
    return AsyncProcessor(config)
