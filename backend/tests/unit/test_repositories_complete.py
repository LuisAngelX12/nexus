from unittest.mock import MagicMock
from uuid import uuid4

from backend.app.core.database import get_db
from backend.app.repositories.file_repository import FileRepository
from backend.app.repositories.workspace_repository import WorkspaceRepository


def test_get_db_closes_session() -> None:
    session = MagicMock()

    import backend.app.core.database as database

    original = database.SessionLocal

    database.SessionLocal = lambda: session

    try:
        generator = get_db()

        result = next(generator)

        assert result is session

        try:
            next(generator)
        except StopIteration:
            pass

        session.close.assert_called_once()
    finally:
        database.SessionLocal = original


def test_file_repository_get_fingerprints_by_size() -> None:
    session = MagicMock()

    result = MagicMock()
    result.__iter__.return_value = iter(
        [
            (100, "hash-a"),
            (100, "hash-b"),
            (200, "hash-c"),
        ]
    )

    session.execute.return_value = result

    repository = FileRepository(session)

    workspace_id = uuid4()

    fingerprints = repository.get_fingerprints_by_size(
        workspace_id,
    )

    assert fingerprints == {
        100: {"hash-a", "hash-b"},
        200: {"hash-c"},
    }

    session.execute.assert_called_once()


def test_file_repository_get_by_hash() -> None:
    session = MagicMock()
    expected = MagicMock()

    session.scalar.return_value = expected

    repository = FileRepository(session)

    result = repository.get_by_hash(
        uuid4(),
        "abc123",
    )

    assert result is expected
    session.scalar.assert_called_once()


def test_file_repository_get_by_path() -> None:
    session = MagicMock()
    expected = MagicMock()

    session.scalar.return_value = expected

    repository = FileRepository(session)

    result = repository.get_by_path(
        uuid4(),
        "/workspace/file.txt",
    )

    assert result is expected
    session.scalar.assert_called_once()


def test_file_repository_get_paths() -> None:
    session = MagicMock()

    session.scalars.return_value = [
        "/workspace/a.txt",
        "/workspace/b.txt",
    ]

    repository = FileRepository(session)

    result = repository.get_paths(uuid4())

    assert result == {
        "/workspace/a.txt",
        "/workspace/b.txt",
    }


def test_file_repository_create() -> None:
    session = MagicMock()
    file = MagicMock()

    repository = FileRepository(session)

    result = repository.create(file)

    assert result is file

    session.add.assert_called_once_with(file)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(file)


def test_file_repository_get_hashes_by_size() -> None:
    session = MagicMock()

    session.scalars.return_value = [
        "hash-a",
        "hash-b",
    ]

    repository = FileRepository(session)

    result = repository.get_hashes_by_size(
        uuid4(),
        100,
    )

    assert result == {
        "hash-a",
        "hash-b",
    }


def test_file_repository_exists_by_size_true() -> None:
    session = MagicMock()
    session.scalar.return_value = uuid4()

    repository = FileRepository(session)

    assert repository.exists_by_size(
        uuid4(),
        100,
    )


def test_file_repository_exists_by_size_false() -> None:
    session = MagicMock()
    session.scalar.return_value = None

    repository = FileRepository(session)

    assert not repository.exists_by_size(
        uuid4(),
        100,
    )


def test_workspace_repository_get_by_id() -> None:
    session = MagicMock()
    workspace = MagicMock()

    session.scalar.return_value = workspace

    repository = WorkspaceRepository(session)

    result = repository.get_by_id(uuid4())

    assert result is workspace


def test_workspace_repository_get_by_user() -> None:
    session = MagicMock()

    workspaces = [
        MagicMock(),
        MagicMock(),
    ]

    session.scalars.return_value = workspaces

    repository = WorkspaceRepository(session)

    result = repository.get_by_user(uuid4())

    assert result == workspaces


def test_workspace_repository_get_by_id_for_user() -> None:
    session = MagicMock()
    workspace = MagicMock()

    session.scalar.return_value = workspace

    repository = WorkspaceRepository(session)

    result = repository.get_by_id_for_user(
        uuid4(),
        uuid4(),
    )

    assert result is workspace


def test_workspace_repository_create() -> None:
    session = MagicMock()
    workspace = MagicMock()

    repository = WorkspaceRepository(session)

    result = repository.create(workspace)

    assert result is workspace

    session.add.assert_called_once_with(workspace)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(workspace)
