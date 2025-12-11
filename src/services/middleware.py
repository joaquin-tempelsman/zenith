"""
Middleware for LangGraph agent execution.
Provides monitoring, limiting, and control flow for agent operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from langchain_core.messages import BaseMessage


@dataclass
class MiddlewareContext:
    """Context passed through middleware during execution."""
    
    state: dict[str, Any]
    model_calls: int = 0
    tool_calls: int = 0
    tools_used: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    execution_start: Optional[datetime] = None
    execution_end: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMiddleware(ABC):
    """
    Abstract base class for middleware.
    All middleware should inherit from this class.
    """
    
    @abstractmethod
    def before_invoke(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Called before agent invocation.
        
        Args:
            context: Current middleware context
            
        Returns:
            Modified or original context
        """
        pass
    
    @abstractmethod
    def after_invoke(self, context: MiddlewareContext, result: Any) -> tuple[MiddlewareContext, Any]:
        """
        Called after agent invocation.
        
        Args:
            context: Current middleware context
            result: Result from agent execution
            
        Returns:
            Tuple of (modified context, result)
        """
        pass


class ModelCallLimitMiddleware(BaseMiddleware):
    """
    Limits the number of model calls allowed during execution.
    Raises exception if limit is exceeded.
    """
    
    def __init__(self, max_calls: int = 10):
        """
        Initialize model call limit middleware.
        
        Args:
            max_calls: Maximum number of model calls allowed
        """
        self.max_calls = max_calls
    
    def before_invoke(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Check if model call limit will be exceeded.
        
        Args:
            context: Current middleware context
            
        Returns:
            Unchanged context
            
        Raises:
            RuntimeError: If max calls already exceeded
        """
        if context.model_calls >= self.max_calls:
            raise RuntimeError(
                f"Model call limit exceeded: {context.model_calls}/{self.max_calls}"
            )
        return context
    
    def after_invoke(self, context: MiddlewareContext, result: Any) -> tuple[MiddlewareContext, Any]:
        """
        Increment model call count.
        
        Args:
            context: Current middleware context
            result: Result from agent execution
            
        Returns:
            Tuple of (updated context with incremented model_calls, result)
        """
        context.model_calls += 1
        if context.model_calls > self.max_calls:
            raise RuntimeError(
                f"Model call limit exceeded: {context.model_calls}/{self.max_calls}"
            )
        return context, result


class ToolCallLimitMiddleware(BaseMiddleware):
    """
    Limits the total number of tool calls allowed during execution.
    Tracks and limits tool invocations.
    """
    
    def __init__(self, max_calls: int = 20):
        """
        Initialize tool call limit middleware.
        
        Args:
            max_calls: Maximum number of tool calls allowed
        """
        self.max_calls = max_calls
    
    def before_invoke(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Check if tool call limit will be exceeded.
        
        Args:
            context: Current middleware context
            
        Returns:
            Unchanged context
            
        Raises:
            RuntimeError: If max tool calls already exceeded
        """
        if context.tool_calls >= self.max_calls:
            raise RuntimeError(
                f"Tool call limit exceeded: {context.tool_calls}/{self.max_calls}"
            )
        return context
    
    def after_invoke(self, context: MiddlewareContext, result: Any) -> tuple[MiddlewareContext, Any]:
        """
        Track tool calls from result.
        
        Args:
            context: Current middleware context
            result: Result from agent execution
            
        Returns:
            Tuple of (updated context with incremented tool_calls, result)
        """
        context.tool_calls += 1
        if context.tool_calls > self.max_calls:
            raise RuntimeError(
                f"Tool call limit exceeded: {context.tool_calls}/{self.max_calls}"
            )
        return context, result


class LLMToolSelectorMiddleware(BaseMiddleware):
    """
    Tracks which tools are selected and used by the LLM.
    Provides visibility into tool selection patterns.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize tool selector middleware.
        
        Args:
            verbose: Whether to log tool selections
        """
        self.verbose = verbose
    
    def before_invoke(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Prepare for tool tracking.
        
        Args:
            context: Current middleware context
            
        Returns:
            Unchanged context with cleared tools list
        """
        context.tools_used = []
        return context
    
    def after_invoke(self, context: MiddlewareContext, result: Any) -> tuple[MiddlewareContext, Any]:
        """
        Extract tool calls from result and track them.
        
        Args:
            context: Current middleware context
            result: Result from agent execution (dict with 'messages' key)
            
        Returns:
            Tuple of (updated context with tools_used, result)
        """
        if isinstance(result, dict) and "messages" in result:
            messages = result.get("messages", [])
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
                        if tool_name and tool_name not in context.tools_used:
                            context.tools_used.append(tool_name)
                            if self.verbose:
                                print(f"📌 Tool selected: {tool_name}")
        
        return context, result


class TodoListMiddleware(BaseMiddleware):
    """
    Tracks todos extracted from agent execution.
    Can populate or update a todo list based on agent outputs.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize todo list middleware.
        
        Args:
            verbose: Whether to log todo updates
        """
        self.verbose = verbose
    
    def before_invoke(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Prepare todo tracking.
        
        Args:
            context: Current middleware context
            
        Returns:
            Unchanged context with cleared todos list
        """
        context.todos = []
        return context
    
    def after_invoke(self, context: MiddlewareContext, result: Any) -> tuple[MiddlewareContext, Any]:
        """
        Extract todos from agent response.
        Looks for todo-like patterns in the final response.
        
        Args:
            context: Current middleware context
            result: Result from agent execution (dict with 'messages' key)
            
        Returns:
            Tuple of (updated context with todos, result)
        """
        if isinstance(result, dict) and "messages" in result:
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    content = msg.content.lower()
                    # Look for common todo indicators
                    if any(indicator in content for indicator in ["todo:", "task:", "reminder:", "- [ ]"]):
                        context.todos.append(msg.content)
                        if self.verbose:
                            print(f"✓ Todo extracted: {msg.content[:50]}...")
                    break
        
        return context, result


class MiddlewareChain:
    """
    Chains multiple middleware together for sequential execution.
    Handles before/after invoke lifecycle for all middleware.
    """
    
    def __init__(self, middleware: Optional[List[BaseMiddleware]] = None):
        """
        Initialize middleware chain.
        
        Args:
            middleware: List of middleware to chain
        """
        self.middleware = middleware or []
    
    def add(self, mw: BaseMiddleware) -> "MiddlewareChain":
        """
        Add middleware to the chain.
        
        Args:
            mw: Middleware instance to add
            
        Returns:
            Self for chaining
        """
        self.middleware.append(mw)
        return self
    
    def before_invoke(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Execute all middleware before_invoke in order.
        
        Args:
            context: Initial middleware context
            
        Returns:
            Final context after all middleware
        """
        for mw in self.middleware:
            context = mw.before_invoke(context)
        return context
    
    def after_invoke(self, context: MiddlewareContext, result: Any) -> tuple[MiddlewareContext, Any]:
        """
        Execute all middleware after_invoke in reverse order.
        
        Args:
            context: Current middleware context
            result: Result from agent execution
            
        Returns:
            Tuple of (final context, result)
        """
        for mw in reversed(self.middleware):
            context, result = mw.after_invoke(context, result)
        return context, result
