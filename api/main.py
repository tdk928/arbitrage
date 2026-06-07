from __future__ import annotations

from fastapi import FastAPI

from api.routes import arbitrage, health

app = FastAPI(title="Arbitrage API", version="0.1.0")
app.include_router(health.router)
app.include_router(arbitrage.router)
