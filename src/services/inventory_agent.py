"""
LangGraph 1.0 agent implementation for inventory management.
Uses the new graph-based architecture with proper state management and middleware.
"""
from typing import Optional, Any
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.types import StateSnapshot
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool as create_tool
from sqlalchemy.orm import Session

from ..config import settings
from ..prompts import load_prompt
from .llm_model import create_openai_model, OpenAIModel
from .middleware import (
    MiddlewareChain,
    MiddlewareContext,
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
    LLMToolSelectorMiddleware,
    TodoListMiddleware,
)
from .inventory_tools import (
    inventory_tools,
    set_db_session,
    get_all_categories,
)


class AgentState:
    """
    State container for the LangGraph agent.
    Holds all relevant context and history during execution.
    """
    
    def __init__(self):
        """Initialize agent state."""
        self.messages = []
        self.metadata = {}
        self.current_iteration = 0
        self.max_iterations = 10
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert state to dictionary for LangGraph.
        
        Returns:
            Dictionary representation of state
        """
        return {
            "messages": self.messages,
            "metadata": self.metadata,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
        }


class InventoryAgent:
    """
    LangGraph-based inventory management agent.
    Coordinates model, tools, and middleware for agentic workflows.
    """
    
    def __init__(
        self,
        model: Optional[OpenAIModel] = None,
        max_iterations: int = 10,
        enable_middleware: bool = True,
        verbose: bool = False,
    ):
        """
        Initialize the inventory agent.
        
        Args:
            model: OpenAI model wrapper (creates default if not provided)
            max_iterations: Maximum iterations for agent loop
            enable_middleware: Whether to enable middleware chain
            verbose: Whether to print debug information
        """
        self.model = model or create_openai_model()
        self.max_iterations = max_iterations
        self.verbose = verbose
        self._graph = None
        self._db_session: Optional[Session] = None
        
        # Initialize middleware chain
        self.middleware = MiddlewareChain()
        if enable_middleware:
            self.middleware.add(ModelCallLimitMiddleware(max_calls=max_iterations))
            self.middleware.add(ToolCallLimitMiddleware(max_calls=max_iterations * 2))
            self.middleware.add(LLMToolSelectorMiddleware(verbose=verbose))
            self.middleware.add(TodoListMiddleware(verbose=verbose))
    
    def set_db_session(self, db: Session) -> None:
        """
        Set the database session for tool execution.
        
        Args:
            db: SQLAlchemy database session
        """
        self._db_session = db
        set_db_session(db)
    
    def _build_graph(self) -> Any:
        """
        Build the LangGraph execution graph.
        
        Returns:
            Compiled execution graph
        """
        workflow = StateGraph(dict)
        
        # Define nodes
        workflow.add_node("input_processor", self._process_input)
        workflow.add_node("model_caller", self._call_model)
        workflow.add_node("tool_executor", self._execute_tools)
        workflow.add_node("response_formatter", self._format_response)
        
        # Define edges
        workflow.add_edge(START, "input_processor")
        workflow.add_edge("input_processor", "model_caller")
        workflow.add_conditional_edges(
            "model_caller",
            self._should_use_tools,
            {
                "continue": "tool_executor",
                "end": "response_formatter",
            },
        )
        workflow.add_edge("tool_executor", "model_caller")
        workflow.add_edge("response_formatter", END)
        
        return workflow.compile()
    
    def _process_input(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process and validate input state.
        
        Args:
            state: Current execution state
            
        Returns:
            Updated state
        """
        if self.verbose:
            print("📥 Processing input...")
        
        if "messages" not in state:
            state["messages"] = []
        
        if "metadata" not in state:
            state["metadata"] = {}
        
        state["metadata"]["input_processed_at"] = datetime.now().isoformat()
        return state
    
    def _call_model(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Call the OpenAI model for the next action.
        
        Args:
            state: Current execution state
            
        Returns:
            Updated state with model response
        """
        if self.verbose:
            print("🤖 Calling model...")
        
        self.model.increment_call_count()
        
        # Get system prompt with current context
        existing_categories = get_all_categories.invoke({})
        system_prompt = load_prompt(
            "inventory_agent",
            existing_categories=existing_categories
        )
        
        # Build messages for model
        messages = state.get("messages", [])
        if not messages:
            if "user_input" in state:
                messages = [HumanMessage(content=state["user_input"])]
        
        # Call model with tools
        response = self.model.instance.bind_tools(inventory_tools).invoke(
            [SystemMessage(content=system_prompt)] + messages
        )
        
        messages.append(response)
        state["messages"] = messages
        state["metadata"]["last_model_call"] = datetime.now().isoformat()
        
        return state
    
    def _should_use_tools(self, state: dict[str, Any]) -> str:
        """
        Determine if tools should be called or if we should end.
        
        Args:
            state: Current execution state
            
        Returns:
            Either "continue" to use tools or "end" to finish
        """
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        return "end"
    
    def _execute_tools(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute tool calls from the model response.
        
        Args:
            state: Current execution state
            
        Returns:
            Updated state with tool results
        """
        if self.verbose:
            print("🔧 Executing tools...")
        
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        if not last_message or not hasattr(last_message, "tool_calls"):
            return state
        
        tool_calls = last_message.tool_calls or []
        
        # Execute each tool call
        for tool_call in tool_calls:
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
            tool_input = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
            
            # Find and execute the tool
            for tool in inventory_tools:
                if tool.name == tool_name:
                    result = tool.invoke(tool_input)
                    if self.verbose:
                        print(f"  ✓ {tool_name}: {result[:50]}...")
                    
                    from langchain_core.messages import ToolMessage
                    messages.append(ToolMessage(
                        tool_call_id=tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", ""),
                        name=tool_name,
                        content=str(result),
                    ))
                    break
        
        state["messages"] = messages
        state["metadata"]["last_tool_execution"] = datetime.now().isoformat()
        
        return state
    
    def _format_response(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Format the final response from the agent.
        
        Args:
            state: Current execution state
            
        Returns:
            Updated state with formatted response
        """
        if self.verbose:
            print("📤 Formatting response...")
        
        messages = state.get("messages", [])
        
        # Find the last AI message with content
        response_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.type == "ai":
                response_text = msg.content
                break
        
        state["final_response"] = response_text
        state["metadata"]["completed_at"] = datetime.now().isoformat()
        
        return state
    
    def invoke(self, user_input: str, db: Session) -> dict[str, Any]:
        """
        Execute the agent with user input.
        
        Args:
            user_input: The user's text input
            db: Database session for tool execution
            
        Returns:
            Dictionary with result, response_message, and metadata
        """
        self.set_db_session(db)
        
        # Initialize middleware context
        context = MiddlewareContext(state={})
        
        # Before invoke middleware
        context = self.middleware.before_invoke(context)
        
        # Build and execute graph
        if self._graph is None:
            self._graph = self._build_graph()
        
        initial_state = {
            "user_input": user_input,
            "messages": [],
            "metadata": {"started_at": datetime.now().isoformat()},
        }
        
        result = self._graph.invoke(initial_state)
        
        # After invoke middleware
        context, result = self.middleware.after_invoke(context, result)
        
        # Extract response
        response_message = result.get("final_response", "")
        
        return {
            "result": "success",
            "response_message": response_message,
            "model_calls": self.model.get_call_count(),
            "tools_used": context.tools_used,
            "todos": context.todos,
            "metadata": result.get("metadata", {}),
        }


def create_inventory_agent(
    model: Optional[OpenAIModel] = None,
    enable_middleware: bool = True,
    verbose: bool = False,
) -> InventoryAgent:
    """
    Factory function to create an inventory agent.
    
    Args:
        model: OpenAI model wrapper (creates default if not provided)
        enable_middleware: Whether to enable middleware
        verbose: Whether to print debug information
        
    Returns:
        Configured InventoryAgent instance
    """
    return InventoryAgent(
        model=model,
        enable_middleware=enable_middleware,
        verbose=verbose,
    )


def run_inventory_agent(user_input: str, db: Session) -> dict:
    """
    Run the inventory agent with the LangGraph implementation.
    
    Args:
        user_input: The user's text input
        db: Database session
        
    Returns:
        Dictionary with result and response_message
    """
    agent = create_inventory_agent(verbose=False)
    return agent.invoke(user_input, db)
