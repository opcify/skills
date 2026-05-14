#!/usr/bin/env python3
"""Quotation skill CLI.

Subcommands: create, send, status, list, convert.
All commands talk to the Opcify API using $OPCIFY_API_URL, $OPCIFY_API_KEY,
$OPCIFY_WORKSPACE_ID exported into the agent shell at container start.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


# --- HTTP helpers ----------------------------------------------------------

def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"error: ${name} is not set — are you running inside an Opcify gateway container?")
    return v


def _api(path: str) -> str:
    base = _env("OPCIFY_API_URL").rstrip("/")
    ws = _env("OPCIFY_WORKSPACE_ID")
    return f"{base}/workspaces/{ws}{path}"


def _request(method: str, url: str, body: Optional[dict] = None) -> Any:
    data = None
    headers = {
        "Authorization": f"Bearer {_env('OPCIFY_API_KEY')}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {e.code} on {method} {url}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error on {method} {url}: {e}")


# --- Quote metadata helpers ------------------------------------------------

def _load_meta(entry: dict) -> dict:
    raw = entry.get("metadata")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _store_meta(entry_id: str, meta: dict) -> dict:
    return _request(
        "PATCH",
        _api(f"/ledger/{entry_id}"),
        {"metadata": json.dumps(meta)},
    )


def _public_url(share_token: str) -> str:
    base = _env("OPCIFY_API_URL").rstrip("/")
    return f"{base}/public/quotes/{share_token}"


def _find_quote(quote_id: str) -> dict:
    entry = _request("GET", _api(f"/ledger/{quote_id}"))
    if entry.get("type") != "quote":
        sys.exit(f"error: ledger entry {quote_id} is not a quote (type={entry.get('type')})")
    return entry


def _gen_quote_number() -> str:
    return "Q-" + secrets.token_hex(3).upper()


# --- Client handling -------------------------------------------------------

def _upsert_client(args: argparse.Namespace) -> str:
    email = args.client_email
    if email:
        hits = _request("GET", _api(f"/clients?q={urllib.parse.quote(email)}"))
        for c in hits:
            if (c.get("email") or "").lower() == email.lower():
                return c["id"]

    name = args.client_name or email or "Unnamed client"
    body = {"name": name}
    if email:
        body["email"] = email
    if args.client_phone:
        body["phone"] = args.client_phone
    if args.client_company:
        body["company"] = args.client_company
    if args.client_address:
        body["address"] = args.client_address
    created = _request("POST", _api("/clients"), body)
    return created["id"]


# --- Subcommand: create ----------------------------------------------------

def cmd_create(args: argparse.Namespace) -> None:
    try:
        items = json.loads(args.items)
    except json.JSONDecodeError as e:
        sys.exit(f"error: --items must be JSON array: {e}")
    if not isinstance(items, list) or not items:
        sys.exit("error: --items must be a non-empty JSON array")

    normalised = []
    total = 0.0
    for raw in items:
        desc = raw.get("description") or raw.get("desc")
        qty = float(raw.get("qty", 1))
        unit = float(raw.get("unit_price", raw.get("unitPrice", 0)))
        if not desc:
            sys.exit("error: every line item needs a description")
        normalised.append({"description": desc, "qty": qty, "unitPrice": unit})
        total += qty * unit

    if total <= 0:
        sys.exit("error: quote total must be positive")

    client_id = _upsert_client(args)

    valid_until = None
    if args.valid_days and args.valid_days > 0:
        valid_until = (datetime.now(timezone.utc) + timedelta(days=args.valid_days)).isoformat()

    share_token = secrets.token_urlsafe(16)
    quote_number = _gen_quote_number()

    meta = {
        "status": "draft",
        "lineItems": normalised,
        "shareToken": share_token,
        "quoteNumber": quote_number,
    }
    if valid_until:
        meta["validUntil"] = valid_until
    if args.terms:
        meta["terms"] = args.terms

    body = {
        "type": "quote",
        "amount": round(total, 2),
        "currency": args.currency or "USD",
        "clientId": client_id,
        "description": args.description or f"Quote {quote_number}",
        "metadata": json.dumps(meta),
    }
    entry = _request("POST", _api("/ledger"), body)

    print(json.dumps({
        "quoteId": entry["id"],
        "quoteNumber": quote_number,
        "shareToken": share_token,
        "shareUrl": _public_url(share_token),
        "clientId": client_id,
        "total": round(total, 2),
        "currency": body["currency"],
        "status": "draft",
    }, indent=2))


# --- Subcommand: send ------------------------------------------------------

def _render_email_html(entry: dict, meta: dict) -> str:
    client = entry.get("client") or {}
    items = meta.get("lineItems", [])
    rows = "".join(
        f"<tr><td>{i['description']}</td><td style='text-align:right'>{i['qty']}</td>"
        f"<td style='text-align:right'>{entry['currency']} {i['unitPrice']:.2f}</td>"
        f"<td style='text-align:right'>{entry['currency']} {i['qty']*i['unitPrice']:.2f}</td></tr>"
        for i in items
    )
    valid = ""
    if meta.get("validUntil"):
        valid = f"<p style='color:#6b7280'>Valid until {meta['validUntil'][:10]}</p>"
    terms = f"<p style='background:#fafafa;padding:12px;border-radius:8px'>{meta.get('terms','')}</p>" if meta.get("terms") else ""
    share_url = _public_url(meta["shareToken"])
    return f"""
<div style="font-family:-apple-system,sans-serif;max-width:640px">
  <h2>Quote #{meta.get('quoteNumber', entry['id'][:8].upper())}</h2>
  <p>Hi {client.get('name','there')},</p>
  <p>{entry.get('description','')}</p>
  {valid}
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <thead><tr style="background:#fafafa"><th style="text-align:left;padding:8px">Description</th><th style="text-align:right;padding:8px">Qty</th><th style="text-align:right;padding:8px">Unit</th><th style="text-align:right;padding:8px">Amount</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="text-align:right;font-size:18px"><strong>Total: {entry['currency']} {entry['amount']:.2f}</strong></p>
  {terms}
  <p><a href="{share_url}" style="display:inline-block;background:#16a34a;color:white;padding:10px 18px;border-radius:8px;text-decoration:none">View and respond online</a></p>
  <p style="color:#6b7280;font-size:13px">Or copy this link: {share_url}</p>
</div>
"""


def _render_pdf(entry: dict, meta: dict, out_path: str) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
    except ImportError:
        sys.exit(
            "error: reportlab is not installed. Run once per workspace:\n"
            "  uv pip install --python /home/node/.openclaw-env/bin/python3 reportlab"
        )

    styles = getSampleStyleSheet()
    story: list = []
    client = entry.get("client") or {}
    client_name = client.get("name", "Client")
    quote_number = meta.get("quoteNumber", entry["id"][:8].upper())

    story.append(Paragraph(f"<b>Quote #{quote_number}</b>", styles["Title"]))
    story.append(Paragraph(f"For: {client_name}", styles["Normal"]))
    if meta.get("validUntil"):
        story.append(Paragraph(f"Valid until: {meta['validUntil'][:10]}", styles["Normal"]))
    story.append(Spacer(1, 12))
    if entry.get("description"):
        story.append(Paragraph(entry["description"], styles["Normal"]))
        story.append(Spacer(1, 12))

    header = ["Description", "Qty", "Unit", "Amount"]
    rows = [header]
    for i in meta.get("lineItems", []):
        rows.append([
            i["description"],
            f"{i['qty']}",
            f"{entry['currency']} {i['unitPrice']:.2f}",
            f"{entry['currency']} {i['qty']*i['unitPrice']:.2f}",
        ])
    rows.append(["", "", "Total", f"{entry['currency']} {entry['amount']:.2f}"])
    table = Table(rows, colWidths=[240, 60, 100, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fafafa")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("LINEBELOW", (0, -2), (-1, -2), 0.5, colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(table)

    if meta.get("terms"):
        story.append(Spacer(1, 16))
        story.append(Paragraph("<b>Terms</b>", styles["Normal"]))
        story.append(Paragraph(meta["terms"], styles["Normal"]))

    story.append(Spacer(1, 24))
    story.append(Paragraph(
        f"View online: {_public_url(meta['shareToken'])}",
        styles["Normal"],
    ))

    SimpleDocTemplate(out_path, pagesize=A4).build(story)


def _send_email(to: str, subject: str, html: str, pdf_path: Optional[str]) -> None:
    cmd = ["himalaya", "message", "send"]
    msg = f"To: {to}\nSubject: {subject}\nContent-Type: text/html; charset=utf-8\n\n{html}"
    if pdf_path:
        # himalaya supports attachments via `-a` flag on newer versions.
        cmd += ["-a", pdf_path]
    proc = subprocess.run(cmd, input=msg, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"email send failed: {proc.stderr.strip() or proc.stdout.strip()}")


def cmd_send(args: argparse.Namespace) -> None:
    channels = {c.strip() for c in args.channels.split(",") if c.strip()}
    if not channels:
        sys.exit("error: --channels must list at least one of: email,link,pdf")
    unknown = channels - {"email", "link", "pdf"}
    if unknown:
        sys.exit(f"error: unknown channels: {','.join(unknown)}")

    entry = _find_quote(args.id)
    meta = _load_meta(entry)
    if meta.get("status") in {"converted", "declined", "expired"}:
        sys.exit(f"error: quote is {meta.get('status')} — cannot resend")

    output: dict = {"quoteId": entry["id"], "channels": sorted(channels)}

    pdf_path: Optional[str] = None
    if "pdf" in channels or "email" in channels:
        pdf_path = os.path.join(tempfile.gettempdir(), f"quote-{entry['id']}.pdf")
        _render_pdf(entry, meta, pdf_path)
        if "pdf" in channels:
            output["pdfPath"] = pdf_path

    if "link" in channels:
        output["shareUrl"] = _public_url(meta["shareToken"])

    if "email" in channels:
        client = entry.get("client") or {}
        to = client.get("email")
        if not to:
            sys.exit("error: cannot email — client has no email on file")
        html = _render_email_html(entry, meta)
        subject = f"Quote #{meta.get('quoteNumber', entry['id'][:8].upper())} — {entry.get('description','')}"
        _send_email(to, subject, html, pdf_path)
        output["emailedTo"] = to

    if meta.get("status") == "draft":
        meta["status"] = "sent"
        _store_meta(entry["id"], meta)
    output["status"] = meta["status"]

    print(json.dumps(output, indent=2))


# --- Subcommand: status ----------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    entry = _find_quote(args.id)
    meta = _load_meta(entry)
    client = entry.get("client") or {}
    print(json.dumps({
        "quoteId": entry["id"],
        "quoteNumber": meta.get("quoteNumber"),
        "status": meta.get("status", "unknown"),
        "total": entry["amount"],
        "currency": entry["currency"],
        "client": {"id": client.get("id"), "name": client.get("name"), "email": client.get("email")},
        "validUntil": meta.get("validUntil"),
        "acceptedAt": meta.get("acceptedAt"),
        "declinedAt": meta.get("declinedAt"),
        "declineReason": meta.get("declineReason"),
        "convertedInvoiceId": meta.get("convertedInvoiceId"),
        "shareUrl": _public_url(meta["shareToken"]) if meta.get("shareToken") else None,
    }, indent=2))


# --- Subcommand: list ------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> None:
    q = "type=quote"
    if args.client_id:
        q += f"&clientId={urllib.parse.quote(args.client_id)}"
    entries = _request("GET", _api(f"/ledger?{q}"))

    out = []
    for e in entries:
        m = _load_meta(e)
        if args.status and m.get("status") != args.status:
            continue
        out.append({
            "quoteId": e["id"],
            "quoteNumber": m.get("quoteNumber"),
            "status": m.get("status"),
            "total": e["amount"],
            "currency": e["currency"],
            "client": (e.get("client") or {}).get("name"),
            "createdAt": e.get("createdAt"),
            "shareUrl": _public_url(m["shareToken"]) if m.get("shareToken") else None,
        })
        if args.limit and len(out) >= args.limit:
            break

    print(json.dumps(out, indent=2))


# --- Subcommand: convert ---------------------------------------------------

def cmd_convert(args: argparse.Namespace) -> None:
    entry = _find_quote(args.id)
    meta = _load_meta(entry)
    status = meta.get("status")
    if status not in {"accepted", "sent", "viewed"}:
        sys.exit(f"error: cannot convert quote in status '{status}'. Accept it first.")

    client = entry.get("client") or {}
    quote_number = meta.get("quoteNumber", entry["id"][:8].upper())

    invoice_body = {
        "type": "income",
        "amount": entry["amount"],
        "currency": entry["currency"],
        "description": f"Invoice for quote #{quote_number} — {entry.get('description','')}".strip(" —"),
        "attachmentType": "invoice",
        "metadata": json.dumps({
            "lineItems": meta.get("lineItems", []),
            "sourceQuoteId": entry["id"],
            "quoteNumber": quote_number,
        }),
    }
    if client.get("id"):
        invoice_body["clientId"] = client["id"]

    invoice = _request("POST", _api("/ledger"), invoice_body)

    meta["status"] = "converted"
    meta["convertedInvoiceId"] = invoice["id"]
    _store_meta(entry["id"], meta)

    print(json.dumps({
        "invoiceId": invoice["id"],
        "quoteId": entry["id"],
        "quoteNumber": quote_number,
        "amount": invoice["amount"],
        "currency": invoice["currency"],
        "clientId": invoice.get("clientId"),
    }, indent=2))


# --- Main ------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quote.py", description="Quotation skill CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Draft a new quote")
    c.add_argument("--client-email")
    c.add_argument("--client-name")
    c.add_argument("--client-phone")
    c.add_argument("--client-company")
    c.add_argument("--client-address")
    c.add_argument("--description", default="")
    c.add_argument("--items", required=True, help='JSON: [{"description":..,"qty":..,"unit_price":..}]')
    c.add_argument("--valid-days", type=int, default=14)
    c.add_argument("--terms", default="")
    c.add_argument("--currency", default="USD")
    c.set_defaults(func=cmd_create)

    s = sub.add_parser("send", help="Deliver a draft quote")
    s.add_argument("--id", required=True, dest="id")
    s.add_argument("--channels", default="email,link", help="Comma list: email,link,pdf")
    s.set_defaults(func=cmd_send)

    st = sub.add_parser("status", help="Inspect a quote")
    st.add_argument("--id", required=True, dest="id")
    st.set_defaults(func=cmd_status)

    ls = sub.add_parser("list", help="List quotes")
    ls.add_argument("--status")
    ls.add_argument("--client-id")
    ls.add_argument("--limit", type=int, default=50)
    ls.set_defaults(func=cmd_list)

    cv = sub.add_parser("convert", help="Convert accepted quote to an invoice")
    cv.add_argument("--id", required=True, dest="id")
    cv.set_defaults(func=cmd_convert)

    return p


def main(argv: Optional[list] = None) -> None:
    args = _build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
