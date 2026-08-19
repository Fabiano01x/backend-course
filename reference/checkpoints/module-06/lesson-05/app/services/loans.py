"""Casos de uso atômicos do ciclo de empréstimos."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization import LIBRARIAN_ROLE, MEMBER_ROLE
from app.models import Loan
from app.repositories.authorization import AuthorizationRepository
from app.repositories.loans import LoanRepository
from app.schemas import LoanCreate


class LoanRuleError(Exception):
    def __init__(
        self,
        detail: str,
        *,
        not_found: bool = False,
        unauthorized: bool = False,
        forbidden: bool = False,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.not_found = not_found
        self.unauthorized = unauthorized
        self.forbidden = forbidden


async def require_role(
    repository: AuthorizationRepository,
    *,
    user_id: int,
    role: str,
) -> None:
    principal = await repository.find_active_principal(user_id)
    if principal is None:
        raise LoanRuleError(
            "Credencial de acesso inválida", unauthorized=True
        )
    if not principal.has_role(role):
        raise LoanRuleError("Permissão insuficiente", forbidden=True)


async def borrow_book(
    session: AsyncSession, payload: LoanCreate, *, user_id: int
) -> Loan:
    repository = LoanRepository(session)
    authorization = AuthorizationRepository(session)
    try:
        async with session.begin():
            await require_role(
                authorization, user_id=user_id, role=MEMBER_ROLE
            )

            book = await repository.lock_book(payload.book_id)
            if book is None:
                raise LoanRuleError("Livro não encontrado", not_found=True)
            if await repository.find_active_by_book(payload.book_id) is not None:
                raise LoanRuleError("Livro indisponível para empréstimo")

            loan = repository.add(
                user_id=user_id,
                book_id=payload.book_id,
                due_at=payload.due_at,
            )
            await repository.flush()
    except IntegrityError as error:
        # A constraint parcial continua sendo a garantia final sob concorrência.
        raise LoanRuleError("Livro indisponível para empréstimo") from error
    return loan


async def return_book(
    session: AsyncSession, loan_id: int, *, user_id: int
) -> Loan:
    repository = LoanRepository(session)
    authorization = AuthorizationRepository(session)
    async with session.begin():
        await require_role(
            authorization, user_id=user_id, role=LIBRARIAN_ROLE
        )
        loan = await repository.lock_loan(loan_id)
        if loan is None:
            raise LoanRuleError("Empréstimo não encontrado", not_found=True)
        if loan.returned_at is not None:
            raise LoanRuleError("Empréstimo já devolvido")

        loan.returned_at = datetime.now(UTC)
        await repository.flush()
    return loan
