from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import sqlite3
import csv
import io
import os
import html
import json
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

DB_PATH = "data/civicresolve.db"
HOST = "127.0.0.1"
PORT = 8000

CATEGORIES = [
    "Roads & Transport",
    "Water Supply",
    "Waste Management",
    "Street Lighting",
    "Public Health",
    "Education",
    "Other",
]
STATUSES = ["Open", "In Progress", "Resolved", "Rejected"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            area TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL,
            due_at TEXT NOT NULL,
            resolved_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def seed():
    conn = db()
    count = conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]
    if count:
        conn.close()
        return

    now = datetime.now()
    rows = [
        ("Street light not working near campus gate",
         "A street light has remained off during the evening.",
         "Street Lighting", "Dayalbagh", "High", "Open",
         (now - timedelta(days=4)).isoformat(timespec="minutes"),
         (now - timedelta(days=1)).isoformat(timespec="minutes"), None),
        ("Overflowing waste bin at market road",
         "The public bin is overflowing and needs collection.",
         "Waste Management", "Agra Market", "Medium", "In Progress",
         (now - timedelta(days=2)).isoformat(timespec="minutes"),
         (now + timedelta(days=1)).isoformat(timespec="minutes"), None),
        ("Water supply interruption",
         "Water supply was interrupted for several hours.",
         "Water Supply", "Sikandra", "Critical", "Resolved",
         (now - timedelta(days=7)).isoformat(timespec="minutes"),
         (now - timedelta(days=5)).isoformat(timespec="minutes"),
         (now - timedelta(days=4)).isoformat(timespec="minutes")),
        ("Road surface damaged near school",
         "A damaged road surface is creating difficulty for local traffic.",
         "Roads & Transport", "Kamla Nagar", "High", "Open",
         (now - timedelta(days=1)).isoformat(timespec="minutes"),
         (now + timedelta(days=2)).isoformat(timespec="minutes"), None),
    ]
    conn.executemany("""
        INSERT INTO grievances
        (title, description, category, area, priority, status, created_at, due_at, resolved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()


def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()


def duplicate_matches(title, description, limit=3):
    query = normalize(title + " " + description)
    conn = db()
    rows = conn.execute(
        "SELECT id, title, category, area, status FROM grievances ORDER BY id DESC"
    ).fetchall()
    conn.close()

    matches = []
    for row in rows:
        candidate = normalize(row["title"])
        score = SequenceMatcher(None, normalize(title), candidate).ratio()
        if score >= 0.72:
            matches.append((score, dict(row)))
    matches.sort(reverse=True, key=lambda x: x[0])
    return matches[:limit]


def page(title, body):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · CivicResolve</title>
<style>
:root {{
  --bg:#f4f7fb; --card:#ffffff; --text:#162033; --muted:#64748b;
  --line:#dbe3ee; --accent:#2563eb; --dark:#0f172a;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;
       background:var(--bg); color:var(--text); }}
header {{ background:var(--dark); color:white; padding:18px 22px; }}
header .bar {{ max-width:1100px; margin:auto; display:flex; justify-content:space-between;
               align-items:center; gap:16px; }}
.brand {{ font-weight:800; letter-spacing:.2px; }}
nav a {{ color:#cbd5e1; text-decoration:none; margin-left:16px; font-size:14px; }}
main {{ max-width:1100px; margin:26px auto; padding:0 18px; }}
h1 {{ margin:0 0 8px; font-size:28px; }}
h2 {{ font-size:19px; margin-top:0; }}
p.sub {{ color:var(--muted); margin-top:0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
         padding:18px; box-shadow:0 4px 18px rgba(15,23,42,.04); }}
.metric {{ font-size:28px; font-weight:800; margin-top:8px; }}
.small {{ color:var(--muted); font-size:13px; }}
.toolbar {{ display:flex; gap:10px; flex-wrap:wrap; margin:18px 0; }}
input,select,textarea {{ width:100%; padding:10px 11px; border:1px solid #cbd5e1;
  border-radius:9px; background:white; font:inherit; }}
textarea {{ min-height:110px; resize:vertical; }}
button,.btn {{ border:0; background:var(--accent); color:white; padding:10px 14px;
  border-radius:9px; cursor:pointer; font:inherit; text-decoration:none; display:inline-block; }}
.btn.secondary {{ background:#e2e8f0; color:#172033; }}
.formgrid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.full {{ grid-column:1/-1; }}
table {{ width:100%; border-collapse:collapse; background:white; }}
th,td {{ padding:11px 10px; border-bottom:1px solid var(--line); text-align:left; font-size:14px; }}
th {{ background:#f8fafc; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#e2e8f0;
  font-size:12px; }}
.badge.high {{ background:#fee2e2; color:#991b1b; }}
.badge.critical {{ background:#fecaca; color:#7f1d1d; font-weight:700; }}
.badge.resolved {{ background:#dcfce7; color:#166534; }}
.alert {{ background:#fff7ed; border:1px solid #fed7aa; padding:13px; border-radius:10px;
  margin:14px 0; }}
.success {{ background:#ecfdf5; border:1px solid #a7f3d0; padding:13px; border-radius:10px;
  margin:14px 0; }}
@media(max-width:800px) {{
 .grid {{ grid-template-columns:1fr 1fr; }} .formgrid {{ grid-template-columns:1fr; }}
 .full {{ grid-column:auto; }} table {{ display:block; overflow:auto; white-space:nowrap; }}
}}
</style>
</head>
<body>
<header><div class="bar">
<div class="brand">CivicResolve</div>
<nav><a href="/">Dashboard</a><a href="/new">New Grievance</a><a href="/export">Export CSV</a></nav>
</div></header>
<main>{body}</main>
</body></html>"""


def dashboard(query=""):
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]
    open_count = conn.execute(
        "SELECT COUNT(*) FROM grievances WHERE status IN ('Open','In Progress')"
    ).fetchone()[0]
    resolved = conn.execute(
        "SELECT COUNT(*) FROM grievances WHERE status='Resolved'"
    ).fetchone()[0]
    overdue = conn.execute(
        """SELECT COUNT(*) FROM grievances
           WHERE status NOT IN ('Resolved','Rejected') AND due_at < ?""",
        (datetime.now().isoformat(timespec="minutes"),)
    ).fetchone()[0]

    if query:
        rows = conn.execute("""
            SELECT * FROM grievances
            WHERE title LIKE ? OR description LIKE ? OR area LIKE ? OR category LIKE ?
            ORDER BY id DESC
        """, tuple(f"%{query}%" for _ in range(4))).fetchall()
    else:
        rows = conn.execute("SELECT * FROM grievances ORDER BY id DESC").fetchall()
    conn.close()

    cards = f"""
    <h1>Public Service Issue Tracker</h1>
    <p class="sub">A local-first Python + SQLite system for recording, prioritising and analysing service grievances.</p>
    <div class="grid">
      <div class="card"><div class="small">Total</div><div class="metric">{total}</div></div>
      <div class="card"><div class="small">Active</div><div class="metric">{open_count}</div></div>
      <div class="card"><div class="small">Resolved</div><div class="metric">{resolved}</div></div>
      <div class="card"><div class="small">Overdue</div><div class="metric">{overdue}</div></div>
    </div>
    """
    if overdue:
        cards += f'<div class="alert"><b>Attention:</b> {overdue} active issue(s) have crossed their due date.</div>'

    cards += f"""
    <form class="toolbar" method="get" action="/">
      <input name="q" value="{html.escape(query)}" placeholder="Search title, area, category...">
      <button type="submit">Search</button>
      <a class="btn secondary" href="/">Clear</a>
    </form>
    <div class="card">
      <h2>Grievance records</h2>
      <table>
      <tr><th>ID</th><th>Issue</th><th>Category</th><th>Area</th><th>Priority</th><th>Status</th><th>Due</th></tr>
    """
    for r in rows:
        priority_class = r["priority"].lower()
        status_class = "resolved" if r["status"] == "Resolved" else ""
        cards += f"""
        <tr>
          <td>#{r['id']}</td>
          <td><a href="/view?id={r['id']}">{html.escape(r['title'])}</a></td>
          <td>{html.escape(r['category'])}</td>
          <td>{html.escape(r['area'])}</td>
          <td><span class="badge {priority_class}">{html.escape(r['priority'])}</span></td>
          <td><span class="badge {status_class}">{html.escape(r['status'])}</span></td>
          <td>{html.escape(r['due_at'])}</td>
        </tr>"""
    cards += "</table></div>"
    return page("Dashboard", cards)


def new_form(error=""):
    err = f'<div class="alert">{html.escape(error)}</div>' if error else ""
    options = lambda values: "".join(f'<option>{html.escape(v)}</option>' for v in values)
    body = f"""
    <h1>New Grievance</h1>
    <p class="sub">Create a structured service issue record. Demo data only; this app is not connected to any government portal.</p>
    {err}
    <div class="card">
    <form method="post" action="/new">
      <div class="formgrid">
        <div class="full"><label>Issue title<br><input name="title" required maxlength="120"></label></div>
        <div class="full"><label>Description<br><textarea name="description" required maxlength="1000"></textarea></label></div>
        <div><label>Category<br><select name="category">{options(CATEGORIES)}</select></label></div>
        <div><label>Area<br><input name="area" required maxlength="80"></label></div>
        <div><label>Priority<br><select name="priority">{options(PRIORITIES)}</select></label></div>
        <div><label>Due in days<br><input name="due_days" type="number" min="1" max="90" value="7" required></label></div>
        <div class="full"><button type="submit">Create record</button></div>
      </div>
    </form>
    </div>
    """
    return page("New Grievance", body)


def view_grievance(gid, message=""):
    conn = db()
    r = conn.execute("SELECT * FROM grievances WHERE id=?", (gid,)).fetchone()
    conn.close()
    if not r:
        return page("Not Found", "<h1>Record not found</h1>")
    msg = f'<div class="success">{html.escape(message)}</div>' if message else ""
    options = "".join(
        f'<option {"selected" if s == r["status"] else ""}>{html.escape(s)}</option>'
        for s in STATUSES
    )
    body = f"""
    <h1>Grievance #{r['id']}</h1>
    {msg}
    <div class="card">
      <h2>{html.escape(r['title'])}</h2>
      <p>{html.escape(r['description'])}</p>
      <p><b>Category:</b> {html.escape(r['category'])}<br>
         <b>Area:</b> {html.escape(r['area'])}<br>
         <b>Priority:</b> {html.escape(r['priority'])}<br>
         <b>Created:</b> {html.escape(r['created_at'])}<br>
         <b>Due:</b> {html.escape(r['due_at'])}<br>
         <b>Resolved:</b> {html.escape(r['resolved_at'] or "—")}</p>
    </div>
    <div class="card" style="margin-top:14px">
      <h2>Update status</h2>
      <form method="post" action="/status">
        <input type="hidden" name="id" value="{r['id']}">
        <select name="status">{options}</select><br><br>
        <button type="submit">Save status</button>
      </form>
    </div>
    """
    return page("Grievance", body)


class Handler(BaseHTTPRequestHandler):
    def send_html(self, content, status=200):
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_csv(self):
        conn = db()
        rows = conn.execute("SELECT * FROM grievances ORDER BY id").fetchall()
        conn.close()
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(rows[0].keys() if rows else
                        ["id","title","description","category","area","priority","status","created_at","due_at","resolved_at"])
        for row in rows:
            writer.writerow(tuple(row))
        data = out.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="civicresolve_export.csv"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/":
            self.send_html(dashboard(qs.get("q", [""])[0]))
        elif parsed.path == "/new":
            self.send_html(new_form())
        elif parsed.path == "/view":
            try:
                gid = int(qs.get("id", ["0"])[0])
            except ValueError:
                gid = 0
            self.send_html(view_grievance(gid))
        elif parsed.path == "/export":
            self.send_csv()
        else:
            self.send_html(page("404", "<h1>404 — Page not found</h1>"), 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = parse_qs(raw)

        if self.path == "/new":
            title = data.get("title", [""])[0].strip()
            description = data.get("description", [""])[0].strip()
            category = data.get("category", ["Other"])[0]
            area = data.get("area", [""])[0].strip()
            priority = data.get("priority", ["Medium"])[0]
            try:
                due_days = max(1, min(90, int(data.get("due_days", ["7"])[0])))
            except ValueError:
                due_days = 7

            if not title or not description or not area:
                self.send_html(new_form("Title, description and area are required."), 400)
                return

            matches = duplicate_matches(title, description)
            if matches and matches[0][0] >= 0.86:
                top = matches[0][1]
                msg = (
                    f"Possible duplicate of grievance #{top['id']}: "
                    f"{top['title']} (similarity {matches[0][0]:.0%}). "
                    f"Review it before creating another record."
                )
                body = f"""
                <h1>Possible duplicate detected</h1>
                <div class="alert">{html.escape(msg)}</div>
                <p><a class="btn" href="/view?id={top['id']}">Review existing record</a>
                <a class="btn secondary" href="/new">Back</a></p>
                """
                self.send_html(page("Duplicate Check", body))
                return

            now = datetime.now()
            due = now + timedelta(days=due_days)
            conn = db()
            cur = conn.execute("""
                INSERT INTO grievances
                (title, description, category, area, priority, status, created_at, due_at)
                VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
            """, (title, description, category, area, priority,
                  now.isoformat(timespec="minutes"), due.isoformat(timespec="minutes")))
            conn.commit()
            gid = cur.lastrowid
            conn.close()
            self.send_response(303)
            self.send_header("Location", f"/view?id={gid}")
            self.end_headers()

        elif self.path == "/status":
            try:
                gid = int(data.get("id", ["0"])[0])
            except ValueError:
                gid = 0
            status = data.get("status", ["Open"])[0]
            if status not in STATUSES:
                status = "Open"
            resolved_at = datetime.now().isoformat(timespec="minutes") if status == "Resolved" else None
            conn = db()
            conn.execute(
                "UPDATE grievances SET status=?, resolved_at=? WHERE id=?",
                (status, resolved_at, gid)
            )
            conn.commit()
            conn.close()
            self.send_response(303)
            self.send_header("Location", f"/view?id={gid}&updated=1")
            self.end_headers()
        else:
            self.send_html(page("404", "<h1>404 — Page not found</h1>"), 404)


if __name__ == "__main__":
    init_db()
    seed()
    print(f"CivicResolve running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
