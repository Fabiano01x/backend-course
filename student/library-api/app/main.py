import uvicorn
from fastapi import FastAPI,status, HTTPException
from app.routers import books, users, system

app = FastAPI(
    title="Library API",
    description="Projeto cumulativo do curso de backend Python",
    version="0.1.0"
)

app.include_router(system.router)
app.include_router(books.router)
app.include_router(users.router)

def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)
if __name__ == "__main__":
    main()
