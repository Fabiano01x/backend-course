"""Operações de persistência do ciclo de empréstimos."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Book, Loan


def build_loan_detail_query():
    return (
        select(Loan)
        .options(joinedload(Loan.user), joinedload(Loan.book))
        .order_by(Loan.id)
    )


class LoanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_book(self, book_id: int) -> Book | None:
        statement = select(Book).where(Book.id == book_id).with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_active_by_book(self, book_id: int) -> Loan | None:
        statement = select(Loan).where(
            Loan.book_id == book_id, Loan.returned_at.is_(None)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_all_with_details(self) -> list[Loan]:
        statement = build_loan_detail_query()
        return list((await self.session.execute(statement)).scalars().all())

    async def lock_loan(self, loan_id: int) -> Loan | None:
        statement = select(Loan).where(Loan.id == loan_id).with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    def add(self, *, user_id: int, book_id: int, due_at: datetime) -> Loan:
        loan = Loan(user_id=user_id, book_id=book_id, due_at=due_at)
        self.session.add(loan)
        return loan

    async def flush(self) -> None:
        await self.session.flush()
