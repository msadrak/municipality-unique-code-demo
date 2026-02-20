"""Sprint 1 Verification Script — Tests Phase 2 endpoints."""
import urllib.request
import urllib.error
import http.cookiejar
import json
import sys

BASE = "http://localhost:8000"

# Cookie-based auth (matches the app's session system)
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

def req(method, path, data=None):
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = opener.open(r)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            return e.code, json.loads(body_bytes)
        except:
            return e.code, {"raw": body_bytes.decode()[:500]}

def main():
    ok = 0
    fail = 0

    # 1. Login (cookie-based)
    status, body = req("POST", "/auth/login", {"username": "admin", "password": "admin"})
    if status == 200 and body.get("status") == "success":
        print(f"[PASS] Login: {status} - {body['message']}")
        ok += 1
    else:
        print(f"[FAIL] Login: {status} -> {body}")
        fail += 1
        sys.exit(1)

    # 2. GET /contractors (empty list)
    status, body = req("GET", "/contractors")
    if status == 200 and "items" in body:
        print(f"[PASS] GET /contractors: {status}, items={len(body['items'])}, total={body['total']}")
        ok += 1
    else:
        print(f"[FAIL] GET /contractors: {status} -> {body}")
        fail += 1

    # 3. POST /contractors (create)
    contractor_data = {
        "national_id": "99887766554",
        "company_name": "شرکت آزمایشی",
        "ceo_name": "تست",
        "phone": "021-12345678",
        "source_system": "MANUAL"
    }
    status, body = req("POST", "/contractors", contractor_data)
    cid = body.get("id", 0)
    if status == 200 and cid:
        print(f"[PASS] POST /contractors: created id={cid}, name={body['company_name']}")
        ok += 1
    else:
        print(f"[FAIL] POST /contractors: {status} -> {body}")
        fail += 1

    # 4. GET /contractors/{id}
    if cid:
        status, body = req("GET", f"/contractors/{cid}")
        if status == 200 and body.get("national_id") == "99887766554":
            print(f"[PASS] GET /contractors/{cid}: {body['company_name']}")
            ok += 1
        else:
            print(f"[FAIL] GET /contractors/{cid}: {status} -> {body}")
            fail += 1

    # 5. POST /contractors/fetch-from-setad (mock)
    status, body = req("POST", "/contractors/fetch-from-setad", {"national_id": "10320894567"})
    if status == 200 and body.get("source_system") == "SETAD":
        print(f"[PASS] Setad fetch: {body['company_name']} (source={body['source_system']})")
        ok += 1
    else:
        print(f"[FAIL] Setad fetch: {status} -> {body}")
        fail += 1

    # 6. GET /contract-templates (empty list)
    status, body = req("GET", "/contract-templates")
    if status == 200 and "items" in body:
        print(f"[PASS] GET /contract-templates: {status}, items={len(body['items'])}")
        ok += 1
    else:
        print(f"[FAIL] GET /contract-templates: {status} -> {body}")
        fail += 1

    # 7. POST /contract-templates (create)
    template_data = {
        "code": "CIVIL_TYPE_A",
        "title": "قرارداد عمرانی نوع الف",
        "category": "CIVIL",
        "schema_definition": {
            "type": "object",
            "properties": {
                "project_location": {"type": "string", "title": "محل پروژه"},
                "duration_days": {"type": "integer", "title": "مدت (روز)"},
                "penalty_rate": {"type": "number", "title": "نرخ جریمه روزانه"}
            },
            "required": ["project_location", "duration_days"]
        },
        "default_values": {"duration_days": 90},
        "approval_workflow_config": {"required_levels": 3, "requires_legal_review": True}
    }
    status, body = req("POST", "/contract-templates", template_data)
    tid = body.get("id", 0)
    if status == 200 and tid:
        print(f"[PASS] POST /contract-templates: created id={tid}, code={body['code']}")
        ok += 1
    else:
        print(f"[FAIL] POST /contract-templates: {status} -> {body}")
        fail += 1

    # 8. GET /contract-templates/{id}
    if tid:
        status, body = req("GET", f"/contract-templates/{tid}")
        if status == 200 and "schema_definition" in body:
            props = list(body["schema_definition"]["properties"].keys())
            print(f"[PASS] GET /contract-templates/{tid}: schema props={props}")
            ok += 1
        else:
            print(f"[FAIL] GET /contract-templates/{tid}: {status} -> {body}")
            fail += 1

    print(f"\n{'='*40}")
    print(f"Results: {ok} passed, {fail} failed")
    if fail == 0:
        print("ALL Sprint 1 tests PASSED!")
    else:
        print("Some tests FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
