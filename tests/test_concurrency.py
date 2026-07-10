import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from main import app

def test_concurrent_reads():
    client = TestClient(app)
    res = client.post("/drop", json={"payload": "concurrency_test"})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]

    def read_drop():
        # Create a new client per thread, disabling exception raising so we get a 500 instead of a crash on deadlock
        c = TestClient(app, raise_server_exceptions=False)
        return c.get(f"/x/{drop_id}", params={"key": key})

    # Spawn 10 concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(read_drop) for _ in range(10)]
        results = [f.result() for f in futures]

    status_codes = [r.status_code for r in results]
    
    # Due to race conditions, exactly 1 request should succeed.
    # The others will get 409, 403, or 500 (SQLite lock deadlock).
    assert status_codes.count(200) == 1
    assert status_codes.count(409) + status_codes.count(403) + status_codes.count(500) == 9

def test_concurrent_revoke_and_read():
    client = TestClient(app)
    res = client.post("/drop", json={"payload": "concurrency_test_2"})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]
    revoke_token = data["revoke_token"]

    def read_drop():
        c = TestClient(app, raise_server_exceptions=False)
        return c.get(f"/x/{drop_id}", params={"key": key})
        
    def revoke_drop():
        c = TestClient(app, raise_server_exceptions=False)
        return c.post(f"/revoke/{drop_id}", params={"revoke_token": revoke_token})

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_read = executor.submit(read_drop)
        f_revoke = executor.submit(revoke_drop)
        
        read_res = f_read.result()
        revoke_res = f_revoke.result()
    
    # Either read succeeded and revoke failed, OR revoke succeeded and read failed.
    # It cannot be that both succeed.
    read_success = read_res.status_code == 200
    revoke_success = revoke_res.status_code == 200
    
    assert read_success != revoke_success
