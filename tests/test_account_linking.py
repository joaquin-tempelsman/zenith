"""Tests for account linking: models, CRUD, resolution, and agent tools."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.models import MetadataBase, Base
from src.database import crud


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def meta_engine():
    """In-memory SQLite engine with metadata schema initialised."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MetadataBase.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def meta_session(meta_engine) -> Session:
    """Fresh session for the shared metadata database."""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=meta_engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def inventory_engine():
    """In-memory SQLite engine for inventory (Item table)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def inventory_session(inventory_engine) -> Session:
    """Fresh session for per-user inventory tables."""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=inventory_engine)
    session = factory()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# UserCode CRUD
# ---------------------------------------------------------------------------


class TestGetOrCreateUserCode:
    """Tests for crud.get_or_create_user_code."""

    def test_creates_code_for_new_user(self, meta_session):
        """First call creates a new code."""
        code = crud.get_or_create_user_code(meta_session, 111)
        assert isinstance(code, str)
        assert len(code) > 0

    def test_returns_same_code_on_second_call(self, meta_session):
        """Subsequent calls return the same code."""
        first = crud.get_or_create_user_code(meta_session, 111)
        second = crud.get_or_create_user_code(meta_session, 111)
        assert first == second

    def test_different_users_get_different_codes(self, meta_session):
        """Each user gets a unique code."""
        code_a = crud.get_or_create_user_code(meta_session, 111)
        code_b = crud.get_or_create_user_code(meta_session, 222)
        assert code_a != code_b


class TestRegenerateUserCode:
    """Tests for crud.regenerate_user_code."""

    def test_regenerate_changes_code(self, meta_session):
        """Regenerated code differs from original."""
        original = crud.get_or_create_user_code(meta_session, 111)
        new_code = crud.regenerate_user_code(meta_session, 111)
        assert new_code != original

    def test_regenerate_for_new_user(self, meta_session):
        """Regenerate works even if no code existed yet."""
        code = crud.regenerate_user_code(meta_session, 333)
        assert isinstance(code, str)
        assert len(code) > 0


# ---------------------------------------------------------------------------
# Account linking CRUD
# ---------------------------------------------------------------------------


class TestLinkAccount:
    """Tests for crud.link_account."""

    def test_link_with_valid_code(self, meta_session):
        """Linking with a valid code succeeds."""
        code = crud.get_or_create_user_code(meta_session, 111)
        result = crud.link_account(meta_session, code, 222)
        assert result["ok"] is True
        assert result["owner_chat_id"] == 111

    def test_link_with_invalid_code(self, meta_session):
        """Linking with a non-existent code fails."""
        result = crud.link_account(meta_session, "BADCODE", 222)
        assert result["ok"] is False
        assert result["msg"] == "invalid_code"

    def test_self_link_rejected(self, meta_session):
        """A user cannot link to themselves."""
        code = crud.get_or_create_user_code(meta_session, 111)
        result = crud.link_account(meta_session, code, 111)
        assert result["ok"] is False
        assert result["msg"] == "self_link"

    def test_already_linked_rejected(self, meta_session):
        """A user cannot link twice without unlinking first."""
        code = crud.get_or_create_user_code(meta_session, 111)
        crud.link_account(meta_session, code, 222)
        result = crud.link_account(meta_session, code, 222)
        assert result["ok"] is False
        assert result["msg"] == "already_linked"

    def test_multiple_users_link_to_same_owner(self, meta_session):
        """Multiple users can link to the same owner."""
        code = crud.get_or_create_user_code(meta_session, 111)
        r1 = crud.link_account(meta_session, code, 222)
        r2 = crud.link_account(meta_session, code, 333)
        assert r1["ok"] is True
        assert r2["ok"] is True


class TestUnlinkAccount:
    """Tests for crud.unlink_account."""

    def test_unlink_linked_user(self, meta_session):
        """Unlinking a linked user succeeds."""
        code = crud.get_or_create_user_code(meta_session, 111)
        crud.link_account(meta_session, code, 222)
        result = crud.unlink_account(meta_session, 222)
        assert result["ok"] is True

    def test_unlink_when_not_linked(self, meta_session):
        """Unlinking when not linked returns error."""
        result = crud.unlink_account(meta_session, 999)
        assert result["ok"] is False
        assert result["msg"] == "not_linked"


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


class TestResolveEffectiveChatId:
    """Tests for crud.resolve_effective_chat_id."""

    def test_unlinked_user_resolves_to_self(self, meta_session):
        """Unlinked user gets their own chat_id back."""
        assert crud.resolve_effective_chat_id(meta_session, 999) == 999

    def test_linked_user_resolves_to_owner(self, meta_session):
        """Linked user resolves to the owner's chat_id."""
        code = crud.get_or_create_user_code(meta_session, 111)
        crud.link_account(meta_session, code, 222)
        assert crud.resolve_effective_chat_id(meta_session, 222) == 111

    def test_owner_resolves_to_self(self, meta_session):
        """The owner (who has a code) resolves to themselves."""
        crud.get_or_create_user_code(meta_session, 111)
        assert crud.resolve_effective_chat_id(meta_session, 111) == 111

    def test_unlink_restores_self_resolution(self, meta_session):
        """After unlinking, user resolves to themselves again."""
        code = crud.get_or_create_user_code(meta_session, 111)
        crud.link_account(meta_session, code, 222)
        crud.unlink_account(meta_session, 222)
        assert crud.resolve_effective_chat_id(meta_session, 222) == 222


# ---------------------------------------------------------------------------
# Linked users list
# ---------------------------------------------------------------------------


class TestGetLinkedUsers:
    """Tests for crud.get_linked_users."""

    def test_no_linked_users(self, meta_session):
        """Owner with no linked users returns empty list."""
        assert crud.get_linked_users(meta_session, 111) == []

    def test_returns_linked_chat_ids(self, meta_session):
        """Returns all chat_ids linked to the owner."""
        code = crud.get_or_create_user_code(meta_session, 111)
        crud.link_account(meta_session, code, 222)
        crud.link_account(meta_session, code, 333)
        linked = crud.get_linked_users(meta_session, 111)
        assert set(linked) == {222, 333}

    def test_unlinked_user_removed_from_list(self, meta_session):
        """Unlinking a user removes them from the list."""
        code = crud.get_or_create_user_code(meta_session, 111)
        crud.link_account(meta_session, code, 222)
        crud.link_account(meta_session, code, 333)
        crud.unlink_account(meta_session, 222)
        linked = crud.get_linked_users(meta_session, 111)
        assert linked == [333]


# ---------------------------------------------------------------------------
# Agent tool tests (unit level, mocked state)
# ---------------------------------------------------------------------------


class TestLinkingTools:
    """Tests for the account-linking agent tools."""

    @pytest.fixture(autouse=True)
    def _setup_state(self, meta_session, inventory_session):
        """Wire agent state to test sessions."""
        import src.agent.state as state
        import src.agent.tools as tools

        state.set_db_session(inventory_session)
        state.set_meta_session(meta_session)
        state.set_chat_id(1000)
        state.set_detected_language("en")

        # Also patch the tools module reference
        self._orig_meta = tools.get_meta_session
        self._orig_chat = tools.get_chat_id
        self._orig_db = tools.get_db_session
        self._orig_set_db = tools.set_db_session
        tools.get_meta_session = lambda: meta_session
        tools.get_chat_id = lambda: state.get_chat_id()
        tools.get_db_session = lambda: inventory_session
        tools.set_db_session = state.set_db_session

        self.meta_session = meta_session
        self.inventory_session = inventory_session
        yield

        tools.get_meta_session = self._orig_meta
        tools.get_chat_id = self._orig_chat
        tools.get_db_session = self._orig_db
        tools.set_db_session = self._orig_set_db

    def test_get_my_link_code_returns_code(self):
        """get_my_link_code returns a message containing the code."""
        from src.agent.tools import get_my_link_code

        result = get_my_link_code.invoke({"dummy": None})
        assert "link code" in result.lower() or "código" in result.lower()

    def test_get_my_link_code_idempotent(self):
        """Calling twice returns the same code."""
        from src.agent.tools import get_my_link_code

        r1 = get_my_link_code.invoke({"dummy": None})
        r2 = get_my_link_code.invoke({"dummy": None})
        assert r1 == r2

    def test_link_account_invalid_code(self):
        """link_account with bad code returns error."""
        from src.agent.tools import link_account

        result = link_account.invoke({"code": "BADCODE"})
        assert "invalid" in result.lower() or "inválido" in result.lower()

    def test_link_account_self_link(self):
        """link_account with own code returns self-link error."""
        from src.agent.tools import get_my_link_code, link_account

        code_msg = get_my_link_code.invoke({"dummy": None})
        # Extract the code from the message (between **)
        code = code_msg.split("**")[1]
        result = link_account.invoke({"code": code})
        assert "cannot link" in result.lower() or "no podés" in result.lower()

    def test_unlink_when_not_linked(self):
        """unlink_account when not linked returns info message."""
        from src.agent.tools import unlink_account

        result = unlink_account.invoke({"dummy": None})
        assert "not linked" in result.lower() or "no está vinculada" in result.lower()

    def test_get_link_status_unlinked(self):
        """Link status shows not linked by default."""
        from src.agent.tools import get_link_status

        result = get_link_status.invoke({"dummy": None})
        assert "not linked" in result.lower() or "no está vinculada" in result.lower()

    def test_full_link_unlink_flow(self):
        """End-to-end: owner gets code -> requester links -> requester unlinks."""
        import src.agent.state as state
        from src.agent.tools import get_my_link_code, link_account, unlink_account, get_link_status

        # Owner (chat_id=1000) gets their code
        code_msg = get_my_link_code.invoke({"dummy": None})
        code = code_msg.split("**")[1]

        # Requester (chat_id=2000) links
        state.set_chat_id(2000)
        link_result = link_account.invoke({"code": code})
        assert "successfully" in link_result.lower() or "exitosamente" in link_result.lower()

        # Verify link status
        status = get_link_status.invoke({"dummy": None})
        assert "linked" in status.lower() or "vinculada" in status.lower()

        # Requester unlinks
        unlink_result = unlink_account.invoke({"dummy": None})
        assert "unlinked" in unlink_result.lower() or "desvinculada" in unlink_result.lower()

        # Verify status after unlink
        status_after = get_link_status.invoke({"dummy": None})
        assert "not linked" in status_after.lower() or "no está vinculada" in status_after.lower()
