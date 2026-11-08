"""Tiny Supabase client for the local scripts: reads .env, talks to the REST + Storage APIs
with the secret key (bypasses the database rules, so keep .env off git)."""
import json, re, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
ENV = dict(re.findall(r"^(\w+)=(.*)$", (HERE / ".env").read_text(), re.M))
URL = re.search(r'SUPABASE_URL = "([^"]+)"', (HERE / "index.html").read_text()).group(1)
KEY = ENV["SUPABASE_SECRET_KEY"]
BUCKET = "item-photos"


def call(method, path, body=None, content_type="application/json", headers=None):
    data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"{URL}{path}", data=data, method=method, headers={
        "apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": content_type,
        "Prefer": "return=representation", **(headers or {})})
    with urllib.request.urlopen(req) as r:
        out = r.read()
    return json.loads(out) if out else None


def items():
    return call("GET", "/rest/v1/items?select=*&order=created_at")


def insert(rows):
    return call("POST", "/rest/v1/items", rows)


def update(item_id, fields):
    return call("PATCH", f"/rest/v1/items?id=eq.{item_id}", fields)


def upload(path, data, content_type):
    call("POST", f"/storage/v1/object/{BUCKET}/{path}", data, content_type, {"cache-control": "max-age=31536000"})


def photo_exists(path):
    try:
        urllib.request.urlopen(urllib.request.Request(f"{URL}/storage/v1/object/public/{BUCKET}/{path}", method="HEAD"))
        return True
    except urllib.error.HTTPError:
        return False
