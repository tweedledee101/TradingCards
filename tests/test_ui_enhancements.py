"""
Tests for buy zone calculation and UI enhancements
"""
import pytest


class TestBuyZoneCalculation:
    """Test buy zone calculation logic"""
    
    def get_buy_zone(self, avg_price: float, velocity: float) -> float:
        """
        Calculate buy zone based on velocity
        Matches frontend logic in TrendingTable.jsx
        """
        if velocity > 70:
            multiplier = 0.85  # Hot card - buy at 85%
        elif velocity > 40:
            multiplier = 0.75  # Moderate - buy at 75%
        else:
            multiplier = 0.65  # Cold - buy at 65%
        return round(avg_price * multiplier, 2)
    
    def test_hot_card_buy_zone(self):
        """Hot cards (velocity > 70) should have 85% buy zone"""
        avg_price = 100.0
        velocity = 80.0
        buy_zone = self.get_buy_zone(avg_price, velocity)
        assert buy_zone == 85.0
    
    def test_moderate_card_buy_zone(self):
        """Moderate cards (velocity 40-70) should have 75% buy zone"""
        avg_price = 100.0
        velocity = 50.0
        buy_zone = self.get_buy_zone(avg_price, velocity)
        assert buy_zone == 75.0
    
    def test_cold_card_buy_zone(self):
        """Cold cards (velocity < 40) should have 65% buy zone"""
        avg_price = 100.0
        velocity = 30.0
        buy_zone = self.get_buy_zone(avg_price, velocity)
        assert buy_zone == 65.0
    
    def test_boundary_velocity_70(self):
        """Test boundary at velocity = 70"""
        avg_price = 100.0
        
        # Just above 70 = hot
        buy_zone_hot = self.get_buy_zone(avg_price, 70.1)
        assert buy_zone_hot == 85.0
        
        # At 70 = moderate
        buy_zone_moderate = self.get_buy_zone(avg_price, 70.0)
        assert buy_zone_moderate == 75.0
    
    def test_boundary_velocity_40(self):
        """Test boundary at velocity = 40"""
        avg_price = 100.0
        
        # Just above 40 = moderate
        buy_zone_moderate = self.get_buy_zone(avg_price, 40.1)
        assert buy_zone_moderate == 75.0
        
        # At 40 = cold
        buy_zone_cold = self.get_buy_zone(avg_price, 40.0)
        assert buy_zone_cold == 65.0
    
    def test_real_world_prices(self):
        """Test with realistic card prices"""
        # Wembanyama hot card
        assert self.get_buy_zone(450.0, 85.0) == 382.5
        
        # Mid-tier card
        assert self.get_buy_zone(75.0, 55.0) == 56.25
        
        # Budget card
        assert self.get_buy_zone(15.0, 25.0) == 9.75
    
    def test_zero_velocity(self):
        """Cards with zero velocity should use cold multiplier"""
        avg_price = 100.0
        velocity = 0.0
        buy_zone = self.get_buy_zone(avg_price, velocity)
        assert buy_zone == 65.0
    
    def test_extreme_velocity(self):
        """Cards with very high velocity should still use hot multiplier"""
        avg_price = 100.0
        velocity = 150.0
        buy_zone = self.get_buy_zone(avg_price, velocity)
        assert buy_zone == 85.0


class TestRowColorCoding:
    """Test row color coding logic"""
    
    def get_row_color(self, avg_price: float, velocity: float) -> str:
        """
        Determine row color based on price vs buy zone
        Matches frontend logic in TrendingTable.jsx
        """
        # Calculate buy zone
        if velocity > 70:
            multiplier = 0.85
        elif velocity > 40:
            multiplier = 0.75
        else:
            multiplier = 0.65
        buy_zone = avg_price * multiplier
        
        # Determine color
        if avg_price <= buy_zone * 1.05:
            return 'bg-green-50'  # In buy zone
        elif avg_price <= buy_zone * 1.15:
            return 'bg-yellow-50'  # Close to buy zone
        else:
            return ''  # Overpriced
    
    def test_in_buy_zone_green(self):
        """Cards at or below buy zone should be green"""
        # Exactly at buy zone
        assert self.get_row_color(85.0, 80.0) == 'bg-green-50'
        
        # 5% above buy zone (still green)
        assert self.get_row_color(89.25, 80.0) == 'bg-green-50'
    
    def test_close_to_buy_zone_yellow(self):
        """Cards 5-15% above buy zone should be yellow"""
        # 10% above buy zone
        assert self.get_row_color(93.5, 80.0) == 'bg-yellow-50'
        
        # 15% above buy zone (edge)
        assert self.get_row_color(97.75, 80.0) == 'bg-yellow-50'
    
    def test_overpriced_white(self):
        """Cards >15% above buy zone should be white"""
        # 20% above buy zone
        assert self.get_row_color(102.0, 80.0) == ''
        
        # Way overpriced
        assert self.get_row_color(150.0, 80.0) == ''
    
    def test_different_velocity_tiers(self):
        """Test color coding across velocity tiers"""
        # Hot card (85% buy zone)
        assert self.get_row_color(85.0, 80.0) == 'bg-green-50'
        
        # Moderate card (75% buy zone)
        assert self.get_row_color(75.0, 50.0) == 'bg-green-50'
        
        # Cold card (65% buy zone)
        assert self.get_row_color(65.0, 30.0) == 'bg-green-50'


class TestFocusMode:
    """Test focus mode filtering logic"""
    
    def filter_focus_mode(self, cards: list, focus_mode: bool) -> list:
        """
        Filter cards for focus mode
        Matches frontend logic in Home.jsx
        """
        if focus_mode:
            return [c for c in cards if c['hotness_score'] >= 60][:10]
        return cards
    
    def test_focus_mode_filters_by_hotness(self):
        """Focus mode should only show cards with hotness >= 60"""
        cards = [
            {'hotness_score': 85.0, 'player_name': 'Player A'},
            {'hotness_score': 65.0, 'player_name': 'Player B'},
            {'hotness_score': 45.0, 'player_name': 'Player C'},
            {'hotness_score': 70.0, 'player_name': 'Player D'},
        ]
        
        filtered = self.filter_focus_mode(cards, focus_mode=True)
        assert len(filtered) == 3
        assert all(c['hotness_score'] >= 60 for c in filtered)
    
    def test_focus_mode_limits_to_10(self):
        """Focus mode should limit to top 10 cards"""
        cards = [{'hotness_score': 70.0 + i} for i in range(15)]
        
        filtered = self.filter_focus_mode(cards, focus_mode=True)
        assert len(filtered) == 10
    
    def test_focus_mode_off_shows_all(self):
        """When focus mode is off, show all cards"""
        cards = [{'hotness_score': i * 10} for i in range(5)]
        
        filtered = self.filter_focus_mode(cards, focus_mode=False)
        assert len(filtered) == 5
    
    def test_focus_mode_boundary_60(self):
        """Test boundary at hotness = 60"""
        cards = [
            {'hotness_score': 60.1},
            {'hotness_score': 60.0},
            {'hotness_score': 59.9},
        ]
        
        filtered = self.filter_focus_mode(cards, focus_mode=True)
        assert len(filtered) == 2  # Only >= 60


class TestQuickActions:
    """Test quick action button logic"""
    
    def test_watchlist_payload(self):
        """Test watchlist API payload structure"""
        card = {
            'card_id': 123,
            'avg_price': 100.0,
            'velocity_score': 80.0,
            'hotness_score': 75.0
        }
        
        # Calculate buy zone
        buy_zone = 85.0  # 85% for hot card
        
        payload = {
            'card_id': card['card_id'],
            'target_price': buy_zone,
            'alert_threshold': 5.0,
            'notes': f"Auto-added from trending (hotness: {card['hotness_score']:.1f})"
        }
        
        assert payload['card_id'] == 123
        assert payload['target_price'] == 85.0
        assert payload['alert_threshold'] == 5.0
        assert 'hotness: 75.0' in payload['notes']
    
    def test_inventory_payload(self):
        """Test inventory API payload structure"""
        card = {'card_id': 456, 'player_name': 'Test Player'}
        purchase_price = 75.50
        
        payload = {
            'card_id': card['card_id'],
            'purchase_price': purchase_price,
            'purchase_date': '2024-01-15',
            'quantity': 1,
            'condition': 'raw',
            'storage_location': 'home'
        }
        
        assert payload['card_id'] == 456
        assert payload['purchase_price'] == 75.50
        assert payload['quantity'] == 1
        assert payload['condition'] == 'raw'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
