"""CLI entry point: python -m azzurro <command>.

Commands:
  scrape   Collect reviews from Booking.com (backfill or incremental update)
  classify Re-run classification (keyword) or LLM enrichment over stored reviews
  export   Dump the dataset to JSON (data/reviews_export.json)
  stats    Print a quick summary of the dataset
  serve    Run the FastAPI server (API + built frontend)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from . import config
from .classification.keyword import classify_record
from .database import connect, export_rows, init_db, iter_reviews


def cmd_scrape(args) -> int:
    from .classification.llm import classify_with_llm_fallback
    from .scraper.collector import run_scraper

    if args.max:
        config.BACKFILL_TARGET_PER_PROPERTY = args.max
    classify_fn = classify_with_llm_fallback if args.llm else classify_record

    conn = connect(config.DB_PATH)
    init_db(conn)
    slugs = args.property or None
    result = run_scraper(conn, args.mode, slugs, classify_fn=classify_fn,
                         fast=args.fast)
    conn.close()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] != "failed" else 1


def cmd_classify(args) -> int:
    from .classification.llm import enrich_unclassified

    conn = connect(config.DB_PATH)
    init_db(conn)
    if args.llm:
        n = enrich_unclassified(conn, limit=args.limit)
        print(f"LLM-enriched {n} reviews")
    else:
        n = 0
        for row in iter_reviews(conn):
            rec = dict(row)
            classify_record(rec)
            conn.execute(
                "UPDATE reviews SET sentiment=?, topics_json=?, classified_by=? "
                "WHERE id=?",
                (rec["sentiment"], rec["topics_json"], rec["classified_by"], rec["id"]),
            )
            n += 1
        conn.commit()
        print(f"Re-classified {n} reviews with keyword classifier")
    conn.close()
    return 0


def cmd_export(args) -> int:
    conn = connect(config.DB_PATH)
    rows = export_rows(conn)
    conn.close()
    out = args.out or config.EXPORT_PATH
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"Exported {len(rows)} reviews to {out}")
    return 0


def cmd_stats(_args) -> int:
    conn = connect(config.DB_PATH)
    init_db(conn)
    total = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    print(f"Total reviews: {total}")
    for row in conn.execute(
        "SELECT property_slug, COUNT(*), ROUND(AVG(rating),2), "
        "MIN(review_date), MAX(review_date) FROM reviews GROUP BY property_slug"
    ):
        print(f"  {row[0]:<20} n={row[1]:<5} avg={row[2]:<5} {row[3]} .. {row[4]}")
    runs = conn.execute(
        "SELECT mode, status, COUNT(*) FROM scrape_runs GROUP BY mode, status"
    ).fetchall()
    for r in runs:
        print(f"  runs: {r[0]}/{r[1]} x{r[2]}")
    conn.close()
    return 0


def cmd_serve(args) -> int:
    import uvicorn
    uvicorn.run(
        "azzurro.api.main:app",
        host=args.host, port=args.port, reload=args.reload,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="azzurro", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("scrape", help="Collect reviews from Booking.com")
    sp.add_argument("--mode", choices=["backfill", "update"], default="update")
    sp.add_argument("--property", action="append",
                    help="property slug (repeatable); default: all")
    sp.add_argument("--max", type=int, default=0,
                    help="override per-property review cap for backfill")
    sp.add_argument("--llm", action="store_true",
                    help="use LLM classification in-pipe when LLM_API_KEY is set")
    sp.add_argument("--fast", action="store_true",
                    help="trim polite delays (~3x faster; fine for daily refreshes, "
                         "slightly higher block risk)")
    sp.set_defaults(func=cmd_scrape)

    cp = sub.add_parser("classify", help="Re-run classification")
    cp.add_argument("--llm", action="store_true",
                    help="LLM-enrich reviews not yet LLM-classified")
    cp.add_argument("--limit", type=int, default=500)
    cp.set_defaults(func=cmd_classify)

    ep = sub.add_parser("export", help="Export dataset to JSON")
    ep.add_argument("--out", default=None)
    ep.set_defaults(func=cmd_export)

    st = sub.add_parser("stats", help="Dataset summary")
    st.set_defaults(func=cmd_stats)

    sv = sub.add_parser("serve", help="Run the API/frontend server")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--reload", action="store_true")
    sv.set_defaults(func=cmd_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
