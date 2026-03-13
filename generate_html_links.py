#!/usr/bin/env python3
"""Generate HTML page with clickable eBay links"""
from backend.utils.database import SessionLocal
from backend.models import Card

db = SessionLocal()

# Get all cards with eBay URLs, sorted by price descending
cards = db.query(Card).filter(
    Card.ebay_search_url.isnot(None),
    Card.ungraded_price.isnot(None)
).order_by(Card.ungraded_price.desc()).all()

html = """<!DOCTYPE html>
<html>
<head>
    <title>Card Variations - eBay Links</title>
    <style>
        body {{ font-family: Arial; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; position: sticky; top: 0; }}
        tr:hover {{ background-color: #f5f5f5; }}
        tr.checked {{ background-color: #d4edda; text-decoration: line-through; opacity: 0.6; }}
        a {{ color: #1a0dab; text-decoration: none; margin-right: 10px; }}
        a:hover {{ text-decoration: underline; }}
        input[type="checkbox"] {{ transform: scale(1.5); cursor: pointer; }}
    </style>
    <script>
        function toggleRow(checkbox, rowId) {{
            const row = document.getElementById(rowId);
            if (checkbox.checked) {{
                row.classList.add('checked');
                localStorage.setItem(rowId, 'checked');
            }} else {{
                row.classList.remove('checked');
                localStorage.removeItem(rowId);
            }}
        }}
        
        window.onload = function() {{
            const rows = document.querySelectorAll('tr[id^="row-"]');
            rows.forEach(row => {{
                if (localStorage.getItem(row.id) === 'checked') {{
                    row.classList.add('checked');
                    row.querySelector('input[type="checkbox"]').checked = true;
                }}
            }});
        }};
    </script>
</head>
<body>
    <h1>Card Variations with eBay Links ({} cards)</h1>
    <table>
        <tr>
            <th>✓</th>
            <th>Player</th>
            <th>Year</th>
            <th>Set</th>
            <th>Card #</th>
            <th>Parallel</th>
            <th>Price</th>
            <th>Links</th>
        </tr>
""".format(len(cards))

for i, card in enumerate(cards):
    # Generate SportsCardsPro URL
    scp_query = f"{card.player_name} {card.card_year} {card.card_set} #{card.card_number}"
    scp_url = f"https://www.sportscardspro.com/search-products?q={scp_query.replace(' ', '+').replace('#', '%23')}&type=prices"
    
    html += f"""        <tr id="row-{i}">
            <td><input type="checkbox" onchange="toggleRow(this, 'row-{i}')"></td>
            <td>{card.player_name}</td>
            <td>{card.card_year}</td>
            <td>{card.card_set}</td>
            <td>{card.card_number}</td>
            <td>{card.parallel}</td>
            <td>${card.ungraded_price:.2f}</td>
            <td>
                <a href="{card.ebay_search_url}" target="_blank">eBay</a>
                <a href="{scp_url}" target="_blank">SCP</a>
            </td>
        </tr>
"""

html += """    </table>
</body>
</html>"""

with open('card_variations.html', 'w') as f:
    f.write(html)

db.close()

print(f"✓ Generated card_variations.html with {len(cards)} cards")
print("Open card_variations.html in your browser to view clickable links")
