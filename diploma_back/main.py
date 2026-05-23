import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from application.routes import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём папки и монтируем статику
for folder in ["uploads/patents", "uploads/avatars"]:
    os.makedirs(folder, exist_ok=True)

app.mount("/static/patents", StaticFiles(directory="uploads/patents"), name="patent_pdfs")
app.mount("/static/avatars", StaticFiles(directory="uploads/avatars"), name="avatars")

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
