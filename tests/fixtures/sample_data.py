"""
Test fixtures for eBay API responses and sample data
"""

# Sample eBay API response for sold listings
EBAY_SOLD_RESPONSE = {
    "itemSummaries": [
        {
            "itemId": "123456789",
            "title": "2023 Panini Prizm Victor Wembanyama RC Rookie PSA 10",
            "price": {
                "value": "450.00",
                "currency": "USD"
            },
            "itemEndDate": "2025-02-10T15:30:00.000Z",
            "condition": "New",
            "buyingOptions": ["FIXED_PRICE"]
        },
        {
            "itemId": "987654321",
            "title": "2023 Topps Chrome Corbin Carroll Rookie Auto BGS 9.5",
            "price": {
                "value": "325.50",
                "currency": "USD"
            },
            "itemEndDate": "2025-02-09T20:15:00.000Z",
            "condition": "New",
            "buyingOptions": ["AUCTION"]
        },
        {
            "itemId": "555666777",
            "title": "2022 Bowman Chrome Julio Rodriguez RC PSA 9",
            "price": {
                "value": "89.99",
                "currency": "USD"
            },
            "itemEndDate": "2025-02-08T12:00:00.000Z",
            "condition": "New",
            "buyingOptions": ["FIXED_PRICE"]
        }
    ]
}

# Sample active listings response
EBAY_ACTIVE_RESPONSE = {
    "itemSummaries": [
        {
            "itemId": "111222333",
            "title": "2023 Panini Prizm Victor Wembanyama RC PSA 10",
            "price": {
                "value": "475.00",
                "currency": "USD"
            },
            "buyingOptions": ["FIXED_PRICE"]
        },
        {
            "itemId": "444555666",
            "title": "2023 Panini Prizm Victor Wembanyama Rookie",
            "price": {
                "value": "125.00",
                "currency": "USD"
            },
            "buyingOptions": ["AUCTION"]
        }
    ]
}

# Expected parsed results
EXPECTED_PARSED_SALES = [
    {
        'ebay_item_id': '123456789',
        'title': '2023 Panini Prizm Victor Wembanyama RC Rookie PSA 10',
        'price': 450.00,
        'currency': 'USD',
        'sale_date': '2025-02-10T15:30:00.000Z',
        'condition': 'New',
        'listing_type': 'buy_it_now',
        'is_rookie': True,
        'card_year': 2023,
        'graded': True,
        'grade_company': 'PSA',
        'grade_value': 10.0,
        'card_set': 'Panini Prizm'
    },
    {
        'ebay_item_id': '987654321',
        'title': '2023 Topps Chrome Corbin Carroll Rookie Auto BGS 9.5',
        'price': 325.50,
        'currency': 'USD',
        'sale_date': '2025-02-09T20:15:00.000Z',
        'condition': 'New',
        'listing_type': 'auction',
        'is_rookie': True,
        'card_year': 2023,
        'graded': True,
        'grade_company': 'BGS',
        'grade_value': 9.5,
        'card_set': 'Topps Chrome'
    },
    {
        'ebay_item_id': '555666777',
        'title': '2022 Bowman Chrome Julio Rodriguez RC PSA 9',
        'price': 89.99,
        'currency': 'USD',
        'sale_date': '2025-02-08T12:00:00.000Z',
        'condition': 'New',
        'listing_type': 'buy_it_now',
        'is_rookie': True,
        'card_year': 2022,
        'graded': True,
        'grade_company': 'PSA',
        'grade_value': 9.0,
        'card_set': 'Bowman Chrome'
    }
]

# Test cases for title parsing
TITLE_PARSING_TESTS = [
    {
        'title': '2023 Panini Prizm Victor Wembanyama RC PSA 10',
        'expected': {
            'is_rookie': True,
            'card_year': 2023,
            'graded': True,
            'grade_company': 'PSA',
            'grade_value': 10.0,
            'card_set': 'Panini Prizm'
        }
    },
    {
        'title': '2021 Topps Chrome Trevor Lawrence Rookie Auto',
        'expected': {
            'is_rookie': True,
            'card_year': 2021,
            'graded': False,
            'grade_company': None,
            'grade_value': None,
            'card_set': 'Topps Chrome'
        }
    },
    {
        'title': '1986 Fleer Michael Jordan #57 BGS 9',
        'expected': {
            'is_rookie': False,
            'card_year': 1986,
            'graded': True,
            'grade_company': 'BGS',
            'grade_value': 9.0,
            'card_set': 'Fleer'
        }
    },
    {
        'title': '2020 Bowman Chrome Jasson Dominguez 1st SGC 10',
        'expected': {
            'is_rookie': False,
            'card_year': 2020,
            'graded': True,
            'grade_company': 'SGC',
            'grade_value': 10.0,
            'card_set': 'Bowman Chrome'
        }
    },
    {
        'title': 'Luka Doncic Select Prizm Silver',
        'expected': {
            'is_rookie': False,
            'card_year': None,
            'graded': False,
            'grade_company': None,
            'grade_value': None,
            'card_set': 'Prizm'
        }
    }
]

# Sample database records
SAMPLE_CARDS = [
    {
        'id': 1,
        'player_name': 'Victor Wembanyama',
        'card_year': 2023,
        'card_set': 'Prizm',
        'card_number': '1',
        'is_rookie': True,
        'sport': 'Basketball'
    },
    {
        'id': 2,
        'player_name': 'Corbin Carroll',
        'card_year': 2023,
        'card_set': 'Topps Chrome',
        'card_number': '50',
        'is_rookie': True,
        'sport': 'Baseball'
    }
]

SAMPLE_SALES = [
    {
        'id': 1,
        'card_id': 1,
        'sale_price': 450.00,
        'sale_date': '2025-02-10',
        'ebay_item_id': '123456789',
        'graded': True,
        'grade_company': 'PSA',
        'grade_value': 10.0
    },
    {
        'id': 2,
        'card_id': 1,
        'sale_price': 425.00,
        'sale_date': '2025-02-09',
        'ebay_item_id': '123456790',
        'graded': True,
        'grade_company': 'PSA',
        'grade_value': 10.0
    },
    {
        'id': 3,
        'card_id': 1,
        'sale_price': 400.00,
        'sale_date': '2025-02-03',
        'ebay_item_id': '123456791',
        'graded': True,
        'grade_company': 'PSA',
        'grade_value': 10.0
    }
]

SAMPLE_ACTIVE_LISTINGS = [
    {
        'id': 1,
        'card_id': 1,
        'listing_price': 475.00,
        'listing_type': 'buy_it_now',
        'snapshot_date': '2025-02-10'
    },
    {
        'id': 2,
        'card_id': 1,
        'listing_price': 125.00,
        'listing_type': 'auction',
        'snapshot_date': '2025-02-10'
    }
]
