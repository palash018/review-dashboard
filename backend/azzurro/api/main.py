"""FastAPI application: JSON API + static frontend hosting."""
from __future__ import annotations

import pathlib
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .. import config
from ..database import connect, init_db
from . import service

app = FastAPI(title="Azzurro Hotels Review Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    conn = connect(config.DB_PATH)
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def _parse_date(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(400, f"invalid {name}: {value!r} (want yyyy-mm-dd)") from exc


@app.get("/api/meta")
def meta(conn=Depends(get_conn)):
    return service.meta(conn)


@app.get("/api/kpis")
def kpis(conn=Depends(get_conn),
         property: str | None = Query(None, description="property slug or omit for all"),
         start: str | None = Query(None, description="period start yyyy-mm-dd"),
         end: str | None = Query(None, description="period end yyyy-mm-dd")):
    """KPIs for the selected period vs the previous period of equal length.
    With no params: the current calendar week vs the previous week."""
    end_d = _parse_date(end, "end") or date.today()
    start_d = _parse_date(start, "start") or end_d - timedelta(days=end_d.weekday())
    return service.kpis(conn, property, start_d, end_d)


@app.get("/api/properties/breakdown")
def breakdown(conn=Depends(get_conn),
              property: str | None = None,
              start: str | None = None,
              end: str | None = None):
    end_d = _parse_date(end, "end") or date.today()
    start_d = _parse_date(start, "start") or end_d.fromordinal(
        end_d.toordinal() - 6)
    return service.property_breakdown(conn, property, start_d, end_d)


@app.get("/api/trends")
def trends(conn=Depends(get_conn),
           property: str | None = None,
           start: str | None = None,
           end: str | None = None):
    end_d = _parse_date(end, "end") or date.today()
    start_d = _parse_date(start, "start") or end_d.fromordinal(
        end_d.toordinal() - 83)  # ~12 weeks
    return service.trends(conn, property, start_d, end_d)


@app.get("/api/insights")
def insights(conn=Depends(get_conn),
             property: str | None = None,
             start: str | None = None,
             end: str | None = None):
    end_d = _parse_date(end, "end") or date.today()
    start_d = _parse_date(start, "start") or end_d.fromordinal(
        end_d.toordinal() - 6)
    result = service.topic_insights(conn, property, start_d, end_d)
    return {"range": {"start": start_d.isoformat(), "end": end_d.isoformat()},
            **result}


@app.get("/api/reviews")
def reviews(conn=Depends(get_conn),
            property: str | None = None,
            start: str | None = None,
            end: str | None = None,
            topic: str | None = None,
            sentiment: str | None = Query(
                None, pattern="^(positive|neutral|negative)$"),
            search: str | None = None,
            sort: str = Query("newest",
                              pattern="^(newest|oldest|worst|best)$"),
            page: int = Query(1, ge=1),
            size: int = Query(20, ge=1, le=100)):
    return service.query_reviews(
        conn, property=property,
        start=_parse_date(start, "start"), end=_parse_date(end, "end"),
        topic=topic, sentiment=sentiment, search=search,
        sort=sort, page=page, size=size)


_dist = pathlib.Path(__file__).resolve().parents[3] / "frontend" / "dist"
if (_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
else:  # dev fallback so / still responds
    @app.get("/")
    def root():
        return {"app": "Azzurro Hotels Review Dashboard",
                "api": "/api/meta", "note": "frontend not built; run `npm run dev`"}
