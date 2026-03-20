from bs4 import BeautifulSoup

import sys
fname = sys.argv[1] if len(sys.argv) > 1 else '/tmp/pc_test.html'
with open(fname) as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

tables = soup.find_all('table')
print(f"Found {len(tables)} tables\n")

for i, table in enumerate(tables):
    rows = table.find_all('tr')
    print(f"Table {i}: {len(rows)} rows")
    for row in rows[:6]:
        cells = row.find_all(['td', 'th'])
        texts = [c.get_text(strip=True)[:40] for c in cells]
        print(f"  {texts}")
    print()
