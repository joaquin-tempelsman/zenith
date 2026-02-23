"""
Shared pytest fixtures for the inventory system test suite.

Provides in-memory SQLite sessions, FastAPI test client, and mock helpers.
Includes retry infrastructure for non-deterministic e2e tests.
"""
import functools
import inspect
import sys
from collections import OrderedDict

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.database.models import Base, Item
from src.main import app


# ---------------------------------------------------------------------------
# Non-deterministic test retry infrastructure
# ---------------------------------------------------------------------------

_e2e_results: OrderedDict[str, list[bool]] = OrderedDict()


def _reset_db_for_retry(db_session: Session) -> None:
    """Clear all Item rows and agent chat history between retry attempts.

    Args:
        db_session: The SQLAlchemy session to reset.
    """
    import src.agent.state as agent_state

    db_session.rollback()
    db_session.query(Item).delete()
    db_session.commit()
    agent_state.clear_chat_history(99999)


def nondeterministic(attempts: int = 3):
    """Decorator for non-deterministic e2e tests.

    Runs the test up to *attempts* times.  The test passes if it succeeds
    at least once.  All attempt outcomes are recorded so pass-rate
    percentages can be printed at the end of the session.

    Args:
        attempts: Number of times to run the test.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Locate the thread_safe_db session from args/kwargs.
            db = kwargs.get("thread_safe_db")
            if db is None:
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if "thread_safe_db" in params:
                    idx = params.index("thread_safe_db")
                    if idx < len(args):
                        db = args[idx]

            results: list[bool] = []
            last_error: BaseException | None = None

            for attempt in range(attempts):
                if attempt > 0 and db is not None:
                    _reset_db_for_retry(db)
                try:
                    func(*args, **kwargs)
                    results.append(True)
                except Exception as exc:
                    results.append(False)
                    last_error = exc

            test_name = func.__qualname__
            _e2e_results[test_name] = results

            passed = sum(results)
            if passed == 0:
                raise AssertionError(
                    f"Non-deterministic test failed all {attempts} attempts. "
                    f"Last error: {last_error}"
                ) from last_error

        return wrapper
    return decorator


@pytest.fixture(scope="session", autouse=True)
def _print_e2e_summary():
    """Print pass-rate summary for non-deterministic e2e tests at session end."""
    yield
    if not _e2e_results:
        return
    sep = "=" * 72
    print(f"\n\n{sep}")
    print("  NON-DETERMINISTIC E2E TEST RESULTS")
    print(sep)
    print(f"  {'Test':<55} {'Pass Rate':>12}")
    print("-" * 72)
    total_passed = 0
    total_attempts = 0
    for name, results in _e2e_results.items():
        passed = sum(results)
        n = len(results)
        pct = passed / n * 100
        total_passed += passed
        total_attempts += n
        status = "PASS" if passed > 0 else "FAIL"
        print(f"  {name:<55} {passed}/{n} ({pct:5.1f}%) {status}")
    print("-" * 72)
    overall = total_passed / total_attempts * 100 if total_attempts else 0
    print(f"  {'OVERALL':<55} {total_passed}/{total_attempts} ({overall:5.1f}%)")
    print(f"{sep}\n")


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """Create an in-memory SQLite engine with schema initialised."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    """Yield a fresh SQLAlchemy session; rolls back after each test."""
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = _SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded_db(db_session) -> Session:
    """Session pre-populated with sample inventory items."""
    from datetime import date

    items = [
        Item(name="apples", quantity=10, category="fruits", expire_date=date(2026, 3, 15)),
        Item(name="bananas", quantity=5, category="fruits", expire_date=date(2026, 2, 28)),
        Item(name="milk", quantity=3, category="dairy", expire_date=date(2026, 3, 1)),
        Item(name="bread", quantity=2, category="bakery"),
        Item(name="chicken", quantity=4, category="meat", expire_date=date(2026, 4, 10)),
    ]
    db_session.add_all(items)
    db_session.commit()
    for item in items:
        db_session.refresh(item)
    return db_session


# ---------------------------------------------------------------------------
# FastAPI / HTTP fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def async_client():
    """Async HTTP client wired to the FastAPI app (no network)."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# Agent state helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def agent_state_with_db(db_session):
    """Set agent module-level state to use the test db_session."""
    from src.agent.state import set_db_session, set_detected_language, set_chat_id

    set_db_session(db_session)
    set_detected_language("en")
    set_chat_id(99999)
    return db_session


@pytest.fixture()
def seeded_agent_state(seeded_db):
    """Agent state wired to the seeded database."""
    from src.agent.state import set_db_session, set_detected_language, set_chat_id

    set_db_session(seeded_db)
    set_detected_language("en")
    set_chat_id(99999)
    return seeded_db


@pytest.fixture()
def thread_safe_db(tmp_path):
    """Thread-safe DB fixture for e2e agent tests with parallel tool calls.

    LangGraph may execute tool calls concurrently in separate threads.
    Uses a file-based SQLite database so each thread gets its own connection
    (avoiding the single-connection limitation of in-memory + StaticPool).
    A ``scoped_session`` gives each thread its own session automatically.

    Patches ``src.agent.state.get_db_session`` so every tool call gets a
    thread-local session.

    Args:
        tmp_path: pytest tmp_path fixture for temporary file storage.

    Yields:
        The main-thread SQLAlchemy session.
    """
    import src.agent.state as agent_state
    import src.agent.tools as agent_tools

    # Clear any accumulated chat history from prior tests so the LLM
    # cannot "remember" operations that belong to a different DB session.
    agent_state.clear_chat_history(99999)

    db_file = tmp_path / "test_e2e.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)

    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    registry = scoped_session(factory)

    main_session = registry()

    # Patch in BOTH modules: tools.py imports get_db_session with
    # ``from .state import get_db_session`` which creates its own reference.
    getter = lambda: registry()
    orig_state_get = agent_state.get_db_session
    orig_tools_get = agent_tools.get_db_session
    agent_state.get_db_session = getter
    agent_tools.get_db_session = getter

    yield main_session

    agent_state.get_db_session = orig_state_get
    agent_tools.get_db_session = orig_tools_get
    registry.remove()
    engine.dispose()

