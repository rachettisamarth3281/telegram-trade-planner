from fastapi import APIRouter
from typing import Dict, Any
from app.services.price_monitor import price_monitor
from app.utils.instrument_specs import INSTRUMENT_SPECS

router = APIRouter(prefix="/market", tags=["Market Data"])

@router.get("/quotes")
async def get_quotes():
    """Return latest market price quotes for all supported instruments."""
    quotes = {}
    for symbol in INSTRUMENT_SPECS.keys():
        quotes[symbol] = price_monitor.get_price(symbol)
    return quotes

@router.get("/quotes/{symbol}")
async def get_single_quote(symbol: str):
    """Return latest quote for a single symbol."""
    return price_monitor.get_price(symbol)

@router.get("/instruments")
async def list_instruments():
    """Return supported instruments and their specs."""
    return INSTRUMENT_SPECS

