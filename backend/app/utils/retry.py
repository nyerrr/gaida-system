"""
Retry utility with exponential backoff for external service calls.
"""

import time
import random
from typing import TypeVar, Callable, Any
from app.utils.logger import logger
from app.core.config import MAX_RETRIES, RETRY_INITIAL_DELAY, RETRY_MAX_DELAY, RETRY_EXPONENTIAL_BASE

T = TypeVar('T')


def exponential_backoff_retry(
    func: Callable[..., T],
    *args,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = RETRY_INITIAL_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    exponential_base: float = RETRY_EXPONENTIAL_BASE,
    exception_types: tuple = (Exception,),
    **kwargs
) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to call
        *args: Positional arguments for func
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff (e.g., 2 for doubling)
        exception_types: Tuple of exception types to catch and retry on
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from func
        
    Raises:
        The last exception if all retries exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except exception_types as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"All {max_retries + 1} attempts exhausted for {func.__name__}: {e}")
                raise
            
            # Calculate delay with jitter
            delay = min(initial_delay * (exponential_base ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # 10% jitter
            sleep_time = delay + jitter
            
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                f"Retrying in {sleep_time:.2f}s..."
            )
            time.sleep(sleep_time)
    
    if last_exception:
        raise last_exception
