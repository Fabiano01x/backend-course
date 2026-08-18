import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_documents_api_metadata_and_tag_order(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()

    assert schema["openapi"].startswith("3.1.")
    assert schema["info"]["title"] == "Library API"
    assert schema["info"]["version"] == "0.17.0"
    assert schema["info"]["summary"] == "API didática para gerenciar uma biblioteca."
    assert "livros e usuários são consultados" in schema["info"]["description"]
    assert [tag["name"] for tag in schema["tags"]] == [
        "Sistema",
        "Autenticação",
        "Livros",
        "Usuários",
        "Empréstimos",
    ]
    assert all(tag["description"] for tag in schema["tags"])


async def test_operations_have_stable_unique_ids_and_summaries(
    client: AsyncClient,
) -> None:
    schema = (await client.get("/openapi.json")).json()
    expected_operations = {
        ("/health", "get"): "checkHealth",
        ("/health/database", "get"): "checkDatabaseHealth",
        ("/info", "get"): "getAppInfo",
        ("/auth/register", "post"): "registerLocalUser",
        ("/auth/login", "post"): "loginForAccessToken",
        ("/books", "get"): "listBooks",
        ("/books", "post"): "createBook",
        ("/books/{book_id}", "get"): "getBook",
        ("/books/{book_id}", "put"): "replaceBook",
        ("/books/{book_id}", "delete"): "deleteBook",
        ("/users", "get"): "listUsers",
        ("/users/{user_id}", "get"): "getUser",
        ("/loans", "get"): "listLoans",
        ("/loans", "post"): "borrowBook",
        ("/loans/{loan_id}/return", "post"): "returnBook",
    }

    operation_ids = []
    for (path, method), expected_id in expected_operations.items():
        operation = schema["paths"][path][method]
        assert operation["operationId"] == expected_id
        assert operation["summary"]
        operation_ids.append(operation["operationId"])

    assert len(operation_ids) == len(set(operation_ids))


async def test_documents_examples_success_and_not_found_responses(
    client: AsyncClient,
) -> None:
    schema = (await client.get("/openapi.json")).json()
    schemas = schema["components"]["schemas"]
    create_book = schema["paths"]["/books"]["post"]
    get_book = schema["paths"]["/books/{book_id}"]["get"]

    assert schemas["BookCreate"]["examples"][0]["title"] == "Kindred"
    registration = schemas["RegistrationCreate"]
    assert registration["examples"][0]["email"] == "ada@example.com"
    assert "password" in registration["required"]
    assert "password_hash" not in schemas
    assert set(schemas["TokenResponse"]["required"]) == {
        "access_token",
        "expires_in",
    }
    assert create_book["responses"]["201"]["description"].startswith("O livro criado")
    assert get_book["responses"]["404"]["description"] == "Livro não encontrado."
    assert get_book["responses"]["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    assert "422" in create_book["responses"]
    assert create_book["responses"]["409"]["description"] == "ISBN já cadastrado."


async def test_documents_enriched_relationship_contracts(
    client: AsyncClient,
) -> None:
    schema = (await client.get("/openapi.json")).json()
    schemas = schema["components"]["schemas"]

    assert {"user", "book"} <= set(schemas["LoanDetailResponse"]["required"])
    assert "loans" in schemas["UserDetailResponse"]["required"]
    assert (
        schema["paths"]["/loans"]["get"]["responses"]["200"]["description"]
        == "Empréstimos enriquecidos em ordem de criação."
    )


async def test_documents_bearer_security_and_implicit_identity(
    client: AsyncClient,
) -> None:
    schema = (await client.get("/openapi.json")).json()
    operation = schema["paths"]["/loans"]["post"]
    loan_create = schema["components"]["schemas"]["LoanCreate"]

    assert schema["components"]["securitySchemes"]["AccessToken"] == {
        "type": "http",
        "description": "Access token JWT emitido por POST /auth/login.",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert operation["security"] == [{"AccessToken": []}]
    assert "401" in operation["responses"]
    assert "user_id" not in loan_create.get("properties", {})
    assert set(loan_create["required"]) == {"book_id", "due_at"}
