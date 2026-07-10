from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import arbitrage, arbitrage_v2, arbitrage_v3, auth, health

app = FastAPI(title="Arbitrage API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(arbitrage.router)
app.include_router(arbitrage_v2.router)
app.include_router(arbitrage_v3.router)
