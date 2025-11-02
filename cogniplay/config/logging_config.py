import logging
import logging.handlers
import structlog
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any, Dict


def setup_comprehensive_logging(log_level: str = "DEBUG", log_file: str = "cogniplay.log"):
    """
    Set up comprehensive logging with both console and file output,
    including full stack traces for errors.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    
    # Use current directory for log file (no subdirectory)
    log_file_path = Path(log_file)
    
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=0
            )
        ]
    )
    
    # Custom processor to add stack traces for errors
    def add_stack_trace(logger, method_name, event_dict):
        """Add full stack trace for error level logs"""
        if method_name == "error" and "error" in event_dict:
            # Get current stack trace
            stack_trace = traceback.format_stack()
            event_dict["stack_trace"] = "".join(stack_trace)
            
            # If there's an exception, get its traceback too
            if sys.exc_info()[0] is not None:
                event_dict["exception_traceback"] = traceback.format_exc()
        
        return event_dict
    
    def add_context_info(logger, method_name, event_dict):
        """Add additional context information to all logs"""
        event_dict["process_id"] = os.getpid() if 'os' in globals() else "unknown"
        event_dict["thread_id"] = threading.current_thread().ident if 'threading' in globals() else "unknown"
        return event_dict
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            add_context_info,
            add_stack_trace,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def log_function_entry_exit(func_name: str, args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None):
    """
    Decorator-style function to log function entry and exit
    
    Args:
        func_name: Name of the function
        args: Function arguments
        kwargs: Function keyword arguments
    """
    logger = structlog.get_logger()
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            logger.debug(
                "function_entry",
                function=func_name,
                args_count=len(args) if args else 0,
                kwargs_keys=list(kwargs.keys()) if kwargs else []
            )
            try:
                result = await func(*args, **kwargs)
                logger.debug(
                    "function_exit_success",
                    function=func_name,
                    result_type=type(result).__name__ if result is not None else "None"
                )
                return result
            except Exception as e:
                logger.error(
                    "function_exit_error",
                    function=func_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            logger.debug(
                "function_entry",
                function=func_name,
                args_count=len(args) if args else 0,
                kwargs_keys=list(kwargs.keys()) if kwargs else []
            )
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    "function_exit_success",
                    function=func_name,
                    result_type=type(result).__name__ if result is not None else "None"
                )
                return result
            except Exception as e:
                logger.error(
                    "function_exit_error",
                    function=func_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_object_details(obj: Any, obj_name: str = "object") -> Dict[str, Any]:
    """
    Create detailed logging information about an object
    
    Args:
        obj: Object to analyze
        obj_name: Name to use in logs
        
    Returns:
        Dictionary with object details for logging
    """
    details = {
        f"{obj_name}_type": type(obj).__name__,
        f"{obj_name}_str": str(obj)[:200],  # Truncate long strings
        f"{obj_name}_has_dict": hasattr(obj, '__dict__'),
        f"{obj_name}_is_none": obj is None,
    }
    
    # Add attributes if object has __dict__
    if hasattr(obj, '__dict__'):
        details[f"{obj_name}_attributes"] = list(obj.__dict__.keys())
        details[f"{obj_name}_attribute_count"] = len(obj.__dict__)
    
    # Add dir() information
    try:
        details[f"{obj_name}_methods"] = [attr for attr in dir(obj) if not attr.startswith('_')][:10]  # First 10 methods
    except:
        details[f"{obj_name}_methods"] = "error_getting_methods"
    
    # Check if it's subscriptable
    try:
        # Try to access with a test key to see if it's subscriptable
        test_access = obj['__test_key_that_should_not_exist__']
        details[f"{obj_name}_is_subscriptable"] = True
    except (TypeError, KeyError):
        # TypeError means not subscriptable, KeyError means subscriptable but key doesn't exist
        details[f"{obj_name}_is_subscriptable"] = isinstance(obj, (dict, list, tuple))
    except:
        details[f"{obj_name}_is_subscriptable"] = "unknown"
    
    return details


# Import required modules for context processors
import os
import threading
