import os
import threading
import queue
import time
import importlib.util
from typing import Callable, Any, Dict, List, Optional, Tuple, Union

# Get the absolute path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Import modules directly using file paths
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import required modules
utils_logger = import_from_file("logger", os.path.join(current_dir, "logger.py"))

# Get required functions
error = utils_logger.error


class ThreadWorker:
    """
    Worker for executing tasks in a separate thread.
    """
    
    def __init__(self, name: str = "Worker"):
        """
        Initialize thread worker.
        
        Args:
            name: Worker name
        """
        self.name = name
        self.task_queue = queue.Queue()
        self.results = {}
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the worker thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, name=self.name)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the worker thread."""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def add_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """
        Add a task to the queue.
        
        Args:
            task_id: Task identifier
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        self.task_queue.put((task_id, func, args, kwargs))
        return task_id
    
    def get_result(self, task_id: str, remove: bool = True) -> Tuple[bool, Any]:
        """
        Get the result of a task.
        
        Args:
            task_id: Task identifier
            remove: Whether to remove the result after retrieval
            
        Returns:
            Tuple of (success, result)
        """
        if task_id not in self.results:
            return False, None
            
        success, result = self.results[task_id]
        
        if remove:
            del self.results[task_id]
            
        return success, result
    
    def _worker_loop(self):
        """Worker thread loop."""
        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task_id, func, args, kwargs = self.task_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Execute task
                try:
                    result = func(*args, **kwargs)
                    self.results[task_id] = (True, result)
                except Exception as e:
                    error(f"Error executing task {task_id}", e)
                    self.results[task_id] = (False, str(e))
                
                # Mark task as done
                self.task_queue.task_done()
            except Exception as e:
                error(f"Error in worker loop", e)


class TaskPool:
    """
    Pool of worker threads for executing tasks.
    """
    
    def __init__(self, num_workers: int = 4):
        """
        Initialize task pool.
        
        Args:
            num_workers: Number of worker threads
        """
        self.workers = []
        self.task_count = 0
        self.task_map = {}
        
        # Create workers
        for i in range(num_workers):
            worker = ThreadWorker(f"Worker-{i+1}")
            worker.start()
            self.workers.append(worker)
    
    def add_task(
        self,
        func: Callable,
        *args,
        callback: Optional[Callable[[bool, Any], None]] = None,
        **kwargs
    ) -> str:
        """
        Add a task to the pool.
        
        Args:
            func: Function to execute
            *args: Function arguments
            callback: Optional callback function
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        # Generate task ID
        task_id = f"task-{self.task_count}"
        self.task_count += 1
        
        # Select worker (round-robin)
        worker_idx = (self.task_count - 1) % len(self.workers)
        worker = self.workers[worker_idx]
        
        # Add task to worker
        worker.add_task(task_id, func, *args, **kwargs)
        
        # Store callback if provided
        if callback:
            self.task_map[task_id] = (worker, callback)
            
            # Start result checker if needed
            if len(self.task_map) == 1:
                threading.Thread(target=self._check_results, daemon=True).start()
        
        return task_id
    
    def get_result(self, task_id: str) -> Tuple[bool, Any]:
        """
        Get the result of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Tuple of (success, result)
        """
        if task_id not in self.task_map:
            return False, None
            
        worker, _ = self.task_map[task_id]
        return worker.get_result(task_id, remove=True)
    
    def _check_results(self):
        """Check for completed tasks and call callbacks."""
        while self.task_map:
            # Copy task map to avoid modification during iteration
            tasks = list(self.task_map.items())
            
            for task_id, (worker, callback) in tasks:
                success, result = worker.get_result(task_id, remove=False)
                
                if success is not None:
                    # Call callback
                    try:
                        callback(success, result)
                    except Exception as e:
                        error(f"Error in callback for task {task_id}", e)
                    
                    # Remove task
                    del self.task_map[task_id]
            
            # Sleep briefly
            time.sleep(0.1)
    
    def shutdown(self):
        """Shutdown the task pool."""
        for worker in self.workers:
            worker.stop()
        self.workers = []
        self.task_map = {}


# Global task pool
_global_pool = None


def get_task_pool() -> TaskPool:
    """
    Get the global task pool.
    
    Returns:
        Global task pool
    """
    global _global_pool
    
    if _global_pool is None:
        _global_pool = TaskPool()
        
    return _global_pool


def run_in_thread(
    func: Callable,
    *args,
    callback: Optional[Callable[[bool, Any], None]] = None,
    **kwargs
) -> str:
    """
    Run a function in a separate thread.
    
    Args:
        func: Function to execute
        *args: Function arguments
        callback: Optional callback function
        **kwargs: Function keyword arguments
        
    Returns:
        Task ID
    """
    return get_task_pool().add_task(func, *args, callback=callback, **kwargs)


def shutdown_threads():
    """Shutdown all threads."""
    global _global_pool
    
    if _global_pool is not None:
        _global_pool.shutdown()
        _global_pool = None