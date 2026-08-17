from collections import deque


class ScalarResult:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def all(self) -> list[object]:
        return self.items


class Result:
    def __init__(
        self,
        *,
        rows: list[object] | None = None,
        scalars: list[object] | None = None,
    ) -> None:
        self.rows = rows or []
        self.scalar_items = scalars or []

    def all(self) -> list[object]:
        return self.rows

    def one_or_none(self) -> object | None:
        if not self.rows:
            return None
        if len(self.rows) != 1:
            raise AssertionError("o resultado preparado deveria ter no máximo uma linha")
        return self.rows[0]

    def scalars(self) -> ScalarResult:
        return ScalarResult(self.scalar_items)


class RecordingSession:
    def __init__(self) -> None:
        self.execute_results: deque[Result] = deque()
        self.scalar_results: deque[int | None] = deque()
        self.get_results: deque[object | None] = deque()
        self.commit_errors: deque[Exception] = deque()
        self.statements: list[object] = []
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commit_count = 0
        self.rollback_count = 0
        self.refresh_count = 0
        self.next_identity = 1

    async def execute(self, statement: object) -> Result:
        self.statements.append(statement)
        return self.execute_results.popleft() if self.execute_results else Result()

    async def scalar(self, statement: object) -> int | None:
        self.statements.append(statement)
        return self.scalar_results.popleft() if self.scalar_results else 0

    async def get(self, _model: type[object], _identity: int) -> object | None:
        return self.get_results.popleft() if self.get_results else None

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commit_count += 1
        if self.commit_errors:
            raise self.commit_errors.popleft()

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def refresh(self, instance: object) -> None:
        self.refresh_count += 1
        if getattr(instance, "id", None) is None:
            setattr(instance, "id", self.next_identity)
            self.next_identity += 1
        if hasattr(instance, "active") and getattr(instance, "active", None) is None:
            setattr(instance, "active", True)

    async def delete(self, instance: object) -> None:
        self.deleted.append(instance)
