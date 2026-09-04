import sys
sys.path.insert(0, r"c:\projects AI\campusAI")

from fastapi.testclient import TestClient
from backend.app.main import app

def test_routes():
    client = TestClient(app)
    
    # 1. Announcements
    r1 = client.get("/api/announcements")
    print(f"GET /api/announcements: {r1.status_code}, count={len(r1.json())}")
    assert r1.status_code == 200
    assert len(r1.json()) > 0
    
    # 2. Academic Calendar
    r2 = client.get("/api/academic-calendar")
    print(f"GET /api/academic-calendar: {r2.status_code}, count={len(r2.json())}")
    assert r2.status_code == 200
    assert len(r2.json()) > 0
    
    # 3. Examinations
    r3 = client.get("/api/examinations")
    print(f"GET /api/examinations: {r3.status_code}, count={len(r3.json())}")
    assert r3.status_code == 200
    assert len(r3.json()) > 0
    
    # 4. Departments
    r4 = client.get("/api/departments")
    print(f"GET /api/departments: {r4.status_code}, count={len(r4.json())}")
    assert r4.status_code == 200
    assert len(r4.json()) > 0
    
    # 5. Placements
    r5 = client.get("/api/placements")
    print(f"GET /api/placements: {r5.status_code}, count={len(r5.json())}")
    assert r5.status_code == 200
    assert len(r5.json()) > 0
    
    # 6. College Info & Links
    r6 = client.get("/api/college/info")
    print(f"GET /api/college/info: {r6.status_code}, count={len(r6.json())}")
    assert r6.status_code == 200
    
    r7 = client.get("/api/college/links")
    print(f"GET /api/college/links: {r7.status_code}, count={len(r7.json())}")
    assert r7.status_code == 200
    
    # 7. Global Search
    r8 = client.get("/api/search?q=B.Tech")
    print(f"GET /api/search?q=B.Tech: {r8.status_code}, total={r8.json()['total_results']}")
    assert r8.status_code == 200
    
    print("\nALL MITS REST API ROUTES TESTED AND PASSED!")

if __name__ == "__main__":
    test_routes()
