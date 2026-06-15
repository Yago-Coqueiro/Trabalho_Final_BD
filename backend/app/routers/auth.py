import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.connection import get_db
from app.models.schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
    ProfileUpdate,
    PasswordChange,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, conn: asyncpg.Connection = Depends(get_db)):
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", body.email)
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    user_id = uuid.uuid4()
    pw_hash = hash_password(body.password)

    await conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name) VALUES ($1, $2, $3, $4)",
        user_id,
        body.email,
        pw_hash,
        body.display_name,
    )

    # Seed das categorias padrão
    await conn.execute("SELECT insert_default_categories($1)", user_id)

    token = create_access_token({"sub": str(user_id), "email": body.email})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    row = await conn.fetchrow(
        "SELECT id, email, password_hash FROM users WHERE email = $1", body.email
    )
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    token = create_access_token({"sub": str(row["id"]), "email": row["email"]})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow(
        "SELECT id, email, display_name, created_at FROM users WHERE id = $1",
        uuid.UUID(current_user["sub"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return dict(row)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow(
        "UPDATE users SET display_name = $1 WHERE id = $2 RETURNING id, email, display_name, created_at",
        body.display_name,
        uuid.UUID(current_user["sub"]),
    )
    return dict(row)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChange,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter ao menos 6 caracteres")
    pw_hash = hash_password(body.new_password)
    await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE id = $2",
        pw_hash,
        uuid.UUID(current_user["sub"]),
    )
