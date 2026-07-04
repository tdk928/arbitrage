from __future__ import annotations

from fastapi import FastAPI

from api.routes import arbitrage, arbitrage_v2, arbitrage_v3, health

app = FastAPI(title="Arbitrage API", version="0.3.0")
app.include_router(health.router)
app.include_router(arbitrage.router)
app.include_router(arbitrage_v2.router)
app.include_router(arbitrage_v3.router)
