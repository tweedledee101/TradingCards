# Acquisition Data Flow Diagram

```mermaid
flowchart LR
    marketplaces[Marketplaces<br/>Facebook Marketplace, eBay, others] -->|Listings| intake[Acquisition Intake]
    intake -->|Normalize & scan| categorize[Card Categorization]
    categorize -->|Strategy fit| strategy[Buy Strategy (cash-aware)]
    strategy -->|Seller outreach| outreach[Negotiation & Purchase]
    outreach -->|Acquired inventory| database[Local Inventory Database]
    database -->|Ready for sales phase| sales[Sales Pipeline]
```
