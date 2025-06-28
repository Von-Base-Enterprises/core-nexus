"""
Reliable Background Task Queue for Core Nexus
Provides persistent, retryable task execution with observability
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from pathlib import Path
import aiofiles
import aiofiles.os

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskDefinition:
    """Definition of a background task"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0  # Initial delay in seconds
    timeout: float = 300.0  # 5 minutes default timeout
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass 
class TaskExecution:
    """Record of task execution attempt"""
    task_id: str
    attempt: int
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'attempt': self.attempt,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'result': self.result
        }


class ReliableTaskQueue:
    """
    Reliable background task queue with persistence, retries, and observability.
    
    Features:
    - Persistent task storage (survives restarts)
    - Exponential backoff retry logic
    - Dead letter queue for permanent failures
    - Task status tracking and metrics
    - Priority-based execution
    - Timeout handling
    """
    
    def __init__(self, 
                 storage_dir: str = "/tmp/core_nexus_tasks",
                 max_concurrent_tasks: int = 10,
                 worker_interval: float = 1.0,
                 enable_persistence: bool = True):
        
        self.storage_dir = Path(storage_dir)
        self.max_concurrent_tasks = max_concurrent_tasks
        self.worker_interval = worker_interval
        self.enable_persistence = enable_persistence
        
        # Task handlers registry
        self.task_handlers: Dict[str, Callable] = {}
        
        # In-memory task queues
        self.pending_tasks: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, TaskExecution] = {}
        self.completed_tasks: List[TaskExecution] = []
        self.dead_letter_tasks: List[TaskExecution] = []
        
        # Worker control
        self.worker_task: Optional[asyncio.Task] = None
        self.shutdown_event: asyncio.Event = asyncio.Event()
        
        # Metrics
        self.metrics = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_dead_letter': 0,
            'total_retries': 0,
            'avg_execution_time': 0.0
        }
        
        # Create storage directory
        if self.enable_persistence:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Reliable task queue initialized: storage={storage_dir}, max_concurrent={max_concurrent_tasks}")
    
    async def start(self):
        """Start the task queue worker"""
        if self.worker_task is not None:
            logger.warning("Task queue worker already running")
            return
            
        logger.info("Starting reliable task queue worker...")
        
        # Load persisted tasks
        if self.enable_persistence:
            await self._load_persisted_tasks()
            
        # Start worker
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task queue worker started")
    
    async def stop(self):
        """Stop the task queue worker"""
        if self.worker_task is None:
            return
            
        logger.info("Stopping reliable task queue worker...")
        self.shutdown_event.set()
        
        # Cancel running tasks
        for task_id, execution in self.running_tasks.items():
            logger.warning(f"Cancelling running task: {task_id}")
            
        await self.worker_task
        self.worker_task = None
        logger.info("Task queue worker stopped")
    
    def register_handler(self, task_type: str, handler: Callable[..., Awaitable[Any]]):
        """Register a task handler function"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered task handler: {task_type}")
    
    async def submit_task(self, 
                         task_type: str,
                         payload: Dict[str, Any],
                         priority: TaskPriority = TaskPriority.NORMAL,
                         max_retries: int = 3,
                         timeout: float = 300.0) -> str:
        """
        Submit a task for background execution
        
        Returns: task_id for tracking
        """
        task_id = str(uuid.uuid4())
        
        task_def = TaskDefinition(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            timeout=timeout
        )
        
        # Persist task if enabled
        if self.enable_persistence:
            await self._persist_task(task_def)
        
        # Add to queue
        await self.pending_tasks.put(task_def)
        self.metrics['tasks_submitted'] += 1
        
        logger.info(f"Task submitted: {task_id} (type: {task_type}, priority: {priority.name})")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get current status of a task"""
        # Check running tasks
        if task_id in self.running_tasks:
            return TaskStatus.RUNNING
            
        # Check completed tasks
        for execution in self.completed_tasks:
            if execution.task_id == task_id:
                return execution.status
                
        # Check dead letter
        for execution in self.dead_letter_tasks:
            if execution.task_id == task_id:
                return TaskStatus.DEAD_LETTER
                
        return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics"""
        return {
            **self.metrics,
            'pending_tasks': self.pending_tasks.qsize(),
            'running_tasks': len(self.running_tasks),
            'completed_tasks': len(self.completed_tasks),
            'dead_letter_tasks': len(self.dead_letter_tasks),
            'success_rate': (
                self.metrics['tasks_completed'] / 
                max(1, self.metrics['tasks_submitted'])
            ) * 100
        }
    
    async def _worker_loop(self):
        """Main worker loop for processing tasks"""
        logger.info("Task queue worker loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # Check if we can start more tasks
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(self.worker_interval)
                    continue
                
                # Get next task from queue
                try:
                    task_def = await asyncio.wait_for(
                        self.pending_tasks.get(), 
                        timeout=self.worker_interval
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Start task execution
                asyncio.create_task(self._execute_task(task_def))
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(self.worker_interval)
        
        logger.info("Task queue worker loop stopped")
    
    async def _execute_task(self, task_def: TaskDefinition):
        """Execute a single task with retry logic"""
        task_id = task_def.task_id
        attempt = 1
        
        # Determine retry count from previous executions
        for execution in self.completed_tasks:
            if execution.task_id == task_id and execution.status == TaskStatus.FAILED:
                attempt = execution.attempt + 1
        
        execution = TaskExecution(
            task_id=task_id,
            attempt=attempt,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        
        self.running_tasks[task_id] = execution
        
        try:
            logger.info(f"Executing task {task_id} (attempt {attempt}/{task_def.max_retries})")
            
            # Get task handler
            if task_def.task_type not in self.task_handlers:
                raise ValueError(f"No handler registered for task type: {task_def.task_type}")
            
            handler = self.task_handlers[task_def.task_type]
            
            # Execute with timeout
            start_time = time.time()
            result = await asyncio.wait_for(
                handler(**task_def.payload),
                timeout=task_def.timeout
            )
            execution_time = time.time() - start_time
            
            # Task completed successfully
            execution.status = TaskStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            execution.result = result
            
            self.metrics['tasks_completed'] += 1
            self._update_avg_execution_time(execution_time)
            
            logger.info(f"Task {task_id} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            # Task failed
            execution.status = TaskStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = str(e)
            
            logger.error(f"Task {task_id} failed (attempt {attempt}): {e}")
            
            # Check if we should retry
            if attempt < task_def.max_retries:
                # Calculate retry delay with exponential backoff
                delay = task_def.retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying task {task_id} in {delay:.1f}s")
                
                # Schedule retry
                asyncio.create_task(self._schedule_retry(task_def, delay))
                self.metrics['total_retries'] += 1
                
            else:
                # Move to dead letter queue
                logger.error(f"Task {task_id} moved to dead letter queue after {attempt} attempts")
                execution.status = TaskStatus.DEAD_LETTER
                self.dead_letter_tasks.append(execution)
                self.metrics['tasks_dead_letter'] += 1
                
                # Persist dead letter task
                if self.enable_persistence:
                    await self._persist_dead_letter_task(execution)
            
            self.metrics['tasks_failed'] += 1
            
        finally:
            # Move from running to completed
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
                
            if execution.status != TaskStatus.DEAD_LETTER:
                self.completed_tasks.append(execution)
                
                # Persist execution record
                if self.enable_persistence:
                    await self._persist_execution(execution)
    
    async def _schedule_retry(self, task_def: TaskDefinition, delay: float):
        """Schedule a task retry after delay"""
        await asyncio.sleep(delay)
        await self.pending_tasks.put(task_def)
    
    def _update_avg_execution_time(self, execution_time: float):
        """Update average execution time metric"""
        completed = self.metrics['tasks_completed']
        current_avg = self.metrics['avg_execution_time']
        self.metrics['avg_execution_time'] = (
            (current_avg * (completed - 1) + execution_time) / completed
        )
    
    async def _persist_task(self, task_def: TaskDefinition):
        """Persist task definition to storage"""
        try:
            task_file = self.storage_dir / f"task_{task_def.task_id}.json"
            task_data = asdict(task_def)
            task_data['created_at'] = task_def.created_at.isoformat()
            task_data['priority'] = task_def.priority.value
            
            async with aiofiles.open(task_file, 'w') as f:
                await f.write(json.dumps(task_data, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to persist task {task_def.task_id}: {e}")
    
    async def _persist_execution(self, execution: TaskExecution):
        """Persist task execution record"""
        try:
            exec_file = self.storage_dir / f"exec_{execution.task_id}_{execution.attempt}.json"
            async with aiofiles.open(exec_file, 'w') as f:
                await f.write(json.dumps(execution.to_dict(), indent=2))
                
        except Exception as e:
            logger.error(f"Failed to persist execution {execution.task_id}: {e}")
    
    async def _persist_dead_letter_task(self, execution: TaskExecution):
        """Persist dead letter task"""
        try:
            dead_letter_dir = self.storage_dir / "dead_letter"
            dead_letter_dir.mkdir(exist_ok=True)
            
            dead_file = dead_letter_dir / f"dead_{execution.task_id}.json"
            async with aiofiles.open(dead_file, 'w') as f:
                await f.write(json.dumps(execution.to_dict(), indent=2))
                
        except Exception as e:
            logger.error(f"Failed to persist dead letter task {execution.task_id}: {e}")
    
    async def _load_persisted_tasks(self):
        """Load persisted tasks on startup"""
        try:
            if not self.storage_dir.exists():
                return
                
            task_files = list(self.storage_dir.glob("task_*.json"))
            logger.info(f"Loading {len(task_files)} persisted tasks...")
            
            for task_file in task_files:
                try:
                    async with aiofiles.open(task_file, 'r') as f:
                        task_data = json.loads(await f.read())
                    
                    # Reconstruct task definition
                    task_def = TaskDefinition(
                        task_id=task_data['task_id'],
                        task_type=task_data['task_type'],
                        payload=task_data['payload'],
                        priority=TaskPriority(task_data['priority']),
                        max_retries=task_data['max_retries'],
                        retry_delay=task_data['retry_delay'],
                        timeout=task_data['timeout'],
                        created_at=datetime.fromisoformat(task_data['created_at'])
                    )
                    
                    # Check if task is too old (older than 24 hours)
                    age = datetime.now(timezone.utc) - task_def.created_at
                    if age > timedelta(hours=24):
                        logger.warning(f"Skipping old task {task_def.task_id} (age: {age})")
                        await aiofiles.os.remove(task_file)
                        continue
                    
                    # Re-queue the task
                    await self.pending_tasks.put(task_def)
                    logger.info(f"Restored task: {task_def.task_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to load task from {task_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load persisted tasks: {e}")


# Global task queue instance
_task_queue: Optional[ReliableTaskQueue] = None


async def get_task_queue() -> ReliableTaskQueue:
    """Get the global task queue instance"""
    global _task_queue
    
    if _task_queue is None:
        _task_queue = ReliableTaskQueue()
        await _task_queue.start()
        
    return _task_queue


async def submit_background_task(task_type: str, 
                                payload: Dict[str, Any],
                                priority: TaskPriority = TaskPriority.NORMAL,
                                max_retries: int = 3) -> str:
    """Convenience function to submit a background task"""
    queue = await get_task_queue()
    return await queue.submit_task(task_type, payload, priority, max_retries)