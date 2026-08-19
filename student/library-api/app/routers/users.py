from fastapi import APIRouter, HTTPException, status

from app import data
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Usuarios"])

@router.get("", response_model=list[UserResponse])
async def list_users() -> list[UserResponse]:
    return list(data.users.values())

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    user = data.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(payload: UserCreate) -> UserResponse:
    return data.create_user(payload)