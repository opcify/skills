#!/home/node/.openclaw-env/bin/python3
# SPDX-License-Identifier: MIT
"""
_yf.py — shared helpers for the yahoo-finance skill scripts.

Centralizes:
  - yfinance/pandas/numpy import guards with actionable install hints
  - JSON encoding for pandas Timestamps, numpy scalars, NaN, DataFrames
  - DataFrame -> records conversion that survives non-JSON types
  - Stderr error formatting + a single error contract for --json mode
  - Common argparse boilerplate (--json flag, ticker positionals)
  - A "fetched_at" ISO timestamp helper

Every script in this skill imports from here. Keep it dependency-free
beyond yfinance / pandas / numpy.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Import guards
# ---------------------------------------------------------------------------

def require_yf():
    """Import yfinance, exit 1 with a clear pip hint if missing."""
    try:
        import yfinance as yf  # noqa: F401
        return yf
    except ImportError:
        print(
            "ERROR: yfinance is not installed. Run: pip install yfinance",
            file=sys.stderr,
        )
        sys.exit(1)


def require_pd():
    try:
        import pandas as pd  # noqa: F401
        return pd
    except ImportError:
        print(
            "ERROR: pandas is not installed. Run: pip install pandas",
            file=sys.stderr,
        )
        sys.exit(1)


def require_np():
    try:
        import numpy as np  # noqa: F401
        return np
    except ImportError:
        print(
            "ERROR: numpy is not installed. Run: pip install numpy",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# JSON encoding
# ---------------------------------------------------------------------------

def json_default(obj: Any) -> Any:
    """
    Default encoder for json.dumps that handles pandas/numpy types.
    Use as: json.dumps(data, default=json_default)
    """
    # Lazy import — _yf.py must stay importable even if pandas isn't installed yet
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        return str(obj)

    if obj is None:
        return None
    if isinstance(obj, (pd.Timestamp, datetime)):
        if getattr(obj, "tzinfo", None) is None:
            return obj.isoformat()
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, pd.Timedelta):
        return str(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, pd.DataFrame):
        return df_to_records(obj)
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return str(obj)


def safe_num(v: Any) -> Any:
    """Convert NaN/inf -> None; pass through other values unchanged."""
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return v


def round_num(v: Any, ndigits: int = 4) -> Any:
    """Round numerics to ndigits, preserving None/NaN as None."""
    n = safe_num(v)
    if n is None or not isinstance(n, (int, float)):
        return n
    return round(n, ndigits)


def df_to_records(df) -> list[dict]:
    """
    Convert a DataFrame to JSON-safe records, preserving the index as
    a 'date' column when the index is a DatetimeIndex (the common yfinance case).
    """
    pd = require_pd()
    if df is None or df.empty:
        return []

    work = df.copy()

    # Index → column
    if isinstance(work.index, pd.DatetimeIndex):
        work = work.reset_index()
        # Common yfinance index name is "Date" or "Datetime"; normalize
        first_col = work.columns[0]
        work = work.rename(columns={first_col: "date"})
    elif work.index.name:
        work = work.reset_index()

    records = []
    for _, row in work.iterrows():
        rec = {}
        for col, val in row.items():
            col_str = str(col) if not isinstance(col, str) else col
            if isinstance(val, pd.Timestamp):
                rec[col_str] = val.isoformat() if val is not pd.NaT else None
            elif isinstance(val, float):
                rec[col_str] = None if math.isnan(val) else round(val, 4)
            elif val is None or (hasattr(val, "__class__") and val.__class__.__name__ == "NaTType"):
                rec[col_str] = None
            else:
                try:
                    json.dumps(val)
                    rec[col_str] = val
                except (TypeError, ValueError):
                    rec[col_str] = str(val)
        records.append(rec)
    return records


def df_to_columnar(df) -> dict:
    """
    Convert a DataFrame to a columnar dict suitable for financial statements:
    { columns: [iso dates], rows: { "Total Revenue": [...], ... } }
    yfinance financial statements have row labels (line items) and column dates.
    """
    pd = require_pd()
    if df is None or df.empty:
        return {"columns": [], "rows": {}}

    columns = []
    for c in df.columns:
        if isinstance(c, pd.Timestamp):
            columns.append(c.isoformat())
        else:
            columns.append(str(c))

    rows = {}
    for label, series in df.iterrows():
        rows[str(label)] = [round_num(v) for v in series.tolist()]
    return {"columns": columns, "rows": rows}


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def emit_json(data: Any) -> None:
    """Print a JSON object to stdout. Always succeeds (uses json_default)."""
    print(json.dumps(data, default=json_default, ensure_ascii=False, indent=2))


def emit_error_json(ticker: str | None, message: str) -> None:
    """
    Emit a structured error to stdout in JSON mode. Writes ONLY to stdout
    (not stderr) so consumers using `2>&1` don't see the same payload twice.
    Callers should still `sys.exit(0)` after this — the contract is that
    `--json` mode always exits 0 and surfaces failures inside the payload.
    """
    payload: dict[str, Any] = {"error": message}
    if ticker:
        payload["ticker"] = ticker
    print(json.dumps(payload, ensure_ascii=False))


def now_iso() -> str:
    """UTC ISO timestamp for freshness banners."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def banner(ticker: str, note: str = "delayed ~15min") -> str:
    return f"# {ticker}  ·  fetched {now_iso()}  ·  {note}"


# ---------------------------------------------------------------------------
# Argparse helpers
# ---------------------------------------------------------------------------

def add_common_args(parser: argparse.ArgumentParser, multi: bool = False) -> None:
    """Add --json flag and ticker positional(s)."""
    if multi:
        parser.add_argument(
            "tickers",
            nargs="+",
            help="One or more ticker symbols (e.g. AAPL MSFT BTC-USD)",
        )
    else:
        parser.add_argument("ticker", help="Ticker symbol (e.g. AAPL)")
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit machine-readable JSON to stdout",
    )


def get_ticker_obj(symbol: str):
    """Wrap yf.Ticker(symbol). Raises on yfinance errors."""
    yf = require_yf()
    return yf.Ticker(symbol)
