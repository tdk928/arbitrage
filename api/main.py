from __future__ import annotations

from fastapi import FastAPI

from api.routes import arbitrage, arbitrage_v2, health

app = FastAPI(title="Arbitrage API", version="0.2.0")
app.include_router(health.router)
app.include_router(arbitrage.router)
app.include_router(arbitrage_v2.router)
