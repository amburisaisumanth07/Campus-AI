import httpx
from bs4 import BeautifulSoup

def inspect():
    try:
        resp = httpx.get("https://mits.ac.in/faculty-information", verify=False, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        tables = soup.find_all("table")
        print(f"Total tables found: {len(tables)}")
        for idx, table in enumerate(tables):
            rows = table.find_all("tr")
            print(f"\n--- Table {idx}: {len(rows)} rows ---")
            depts = {}
            for r in rows[:5]:
                tds = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
                print("Row sample:", tds[:5])
            for r in rows:
                tds = r.find_all("td")
                if len(tds) >= 5:
                    d = tds[4].get_text(strip=True)
                    depts[d] = depts.get(d, 0) + 1
            print(f"Departments in Table {idx}:", depts)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    inspect()
