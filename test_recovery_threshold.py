#!/usr/bin/env python3
"""
Test to verify recovery_threshold parameter is working correctly
"""
import unittest
from datetime import datetime, timedelta
from main import LayoffTracker

class TestRecoveryThreshold(unittest.TestCase):
    
    def setUp(self):
        self.tracker = LayoffTracker()
        
    def create_test_price_history(self, base_price=100.0, drop_date='2025-11-01', recovery_date='2025-11-05'):
        """Create a test price history with a drop and recovery"""
        price_history = []
        
        # Create prices for 10 days before drop
        for i in range(10, 0, -1):
            date = (datetime.strptime(drop_date, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
            price_history.append({
                'date': date,
                'price': base_price + (i * 0.5)  # Slight upward trend
            })
        
        # Drop date - 5% drop
        drop_price = base_price * 0.95
        price_history.append({
            'date': drop_date,
            'price': drop_price
        })
        
        # Days after drop
        recovery_dt = datetime.strptime(recovery_date, '%Y-%m-%d')
        drop_dt = datetime.strptime(drop_date, '%Y-%m-%d')
        days_after = (recovery_dt - drop_dt).days
        
        for i in range(1, days_after + 1):
            date = (drop_dt + timedelta(days=i)).strftime('%Y-%m-%d')
            # Gradually recover
            recovery_progress = i / days_after
            price = drop_price + (base_price - drop_price) * recovery_progress
            price_history.append({
                'date': date,
                'price': price
            })
        
        return price_history
    
    def test_recovery_threshold_2_percent(self):
        """Test with 2% recovery threshold - should find recovery"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history where stock drops to $95 and recovers to $97 (2% recovery)
        price_history = []
        # Day before drop
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        # Drop date - 5% drop
        price_history.append({'date': drop_date, 'price': 95.0})
        # Recovery date - 2% recovery from drop (95 * 1.02 = 96.9)
        price_history.append({'date': '2025-11-05', 'price': 97.0})  # 2.1% recovery
        
        pct_threshold = -5.0
        recovery_threshold = 2.0
        
        result = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=recovery_threshold
        )
        
        self.assertIsInstance(result, dict)
        items = result.get('items', [])
        
        # Should find the drop and recovery
        self.assertGreater(len(items), 0, "Should find at least one recovery item with 2% threshold")
        
        # Check that recovery was found
        found_recovery = False
        for item in items:
            if item.get('drop_date') == drop_date:
                self.assertIsNotNone(item.get('recovery_date'), 
                                   f"Should find recovery for drop on {drop_date} with 2% threshold")
                self.assertIsNotNone(item.get('recovery_pct'), 
                                   f"Should have recovery_pct for drop on {drop_date}")
                recovery_pct = item.get('recovery_pct')
                self.assertGreaterEqual(recovery_pct, 2.0, 
                                      f"Recovery percentage should be >= 2% (got {recovery_pct}%)")
                found_recovery = True
                break
        
        self.assertTrue(found_recovery, f"Should find recovery for drop on {drop_date}")
    
    def test_recovery_threshold_6_percent(self):
        """Test with 6% recovery threshold - should NOT find recovery if only 2% recovered"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history where stock drops to $95 and only recovers to $97 (2% recovery, not 6%)
        price_history = []
        # Day before drop
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        # Drop date - 5% drop
        price_history.append({'date': drop_date, 'price': 95.0})
        # Recovery date - only 2% recovery from drop (95 * 1.02 = 96.9)
        price_history.append({'date': '2025-11-05', 'price': 97.0})  # 2.1% recovery
        
        pct_threshold = -5.0
        recovery_threshold = 6.0
        
        result = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=recovery_threshold
        )
        
        self.assertIsInstance(result, dict)
        items = result.get('items', [])
        
        # Should find the drop but NOT the recovery (since only 2% recovered, not 6%)
        found_drop = False
        found_recovery = False
        for item in items:
            if item.get('drop_date') == drop_date:
                found_drop = True
                recovery_date = item.get('recovery_date')
                if recovery_date is not None:
                    found_recovery = True
                break
        
        self.assertTrue(found_drop, f"Should find drop on {drop_date}")
        self.assertFalse(found_recovery, 
                        f"Should NOT find recovery for drop on {drop_date} with 6% threshold when only 2% recovered")
    
    def test_recovery_threshold_6_percent_with_6_percent_recovery(self):
        """Test with 6% recovery threshold - SHOULD find recovery if 6% recovered"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history where stock drops to $95 and recovers to $100.7 (6% recovery)
        price_history = []
        # Day before drop
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        # Drop date - 5% drop
        price_history.append({'date': drop_date, 'price': 95.0})
        # Recovery date - 6% recovery from drop (95 * 1.06 = 100.7)
        price_history.append({'date': '2025-11-05', 'price': 100.7})  # 6% recovery
        
        pct_threshold = -5.0
        recovery_threshold = 6.0
        
        result = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=recovery_threshold
        )
        
        self.assertIsInstance(result, dict)
        items = result.get('items', [])
        
        # Should find the drop AND recovery
        found_recovery = False
        for item in items:
            if item.get('drop_date') == drop_date:
                self.assertIsNotNone(item.get('recovery_date'), 
                                   f"Should find recovery for drop on {drop_date} with 6% threshold when 6% recovered")
                self.assertIsNotNone(item.get('recovery_pct'), 
                                   f"Should have recovery_pct for drop on {drop_date}")
                recovery_pct = item.get('recovery_pct')
                self.assertGreaterEqual(recovery_pct, 6.0, 
                                      f"Recovery percentage should be >= 6% (got {recovery_pct}%)")
                found_recovery = True
                break
        
        self.assertTrue(found_recovery, f"Should find recovery for drop on {drop_date} with 6% recovery")
    
    def test_recovery_threshold_calculation(self):
        """Test that recovery_target is calculated correctly"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        drop_price = 95.0
        
        # Test with 2% threshold
        recovery_threshold_2 = 2.0
        expected_target_2 = drop_price * (1 + recovery_threshold_2 / 100)  # 95 * 1.02 = 96.9
        
        # Test with 6% threshold
        recovery_threshold_6 = 6.0
        expected_target_6 = drop_price * (1 + recovery_threshold_6 / 100)  # 95 * 1.06 = 100.7
        
        # Create price history
        price_history = []
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        price_history.append({'date': drop_date, 'price': drop_price})
        
        # Test 2% threshold - price at 97.0 should recover (above 96.9)
        price_history_2 = price_history.copy()
        price_history_2.append({'date': '2025-11-05', 'price': 97.0})
        
        result_2 = self.tracker.analyze_recovery_history(
            price_history_2, 
            -5.0, 
            bearish_date, 
            None, 
            recovery_threshold=recovery_threshold_2
        )
        
        items_2 = result_2.get('items', [])
        found_recovery_2 = False
        for item in items_2:
            if item.get('drop_date') == drop_date and item.get('recovery_date') is not None:
                found_recovery_2 = True
                break
        
        self.assertTrue(found_recovery_2, f"Price 97.0 should recover with 2% threshold (target: {expected_target_2:.2f})")
        
        # Test 6% threshold - price at 97.0 should NOT recover (below 100.7)
        result_6 = self.tracker.analyze_recovery_history(
            price_history_2, 
            -5.0, 
            bearish_date, 
            None, 
            recovery_threshold=recovery_threshold_6
        )
        
        items_6 = result_6.get('items', [])
        found_recovery_6 = False
        for item in items_6:
            if item.get('drop_date') == drop_date and item.get('recovery_date') is not None:
                found_recovery_6 = True
                break
        
        self.assertFalse(found_recovery_6, f"Price 97.0 should NOT recover with 6% threshold (target: {expected_target_6:.2f})")
        
        # Test 6% threshold - price at 101.0 should recover (above 100.7)
        price_history_6 = price_history.copy()
        price_history_6.append({'date': '2025-11-05', 'price': 101.0})
        
        result_6_recovered = self.tracker.analyze_recovery_history(
            price_history_6, 
            -5.0, 
            bearish_date, 
            None, 
            recovery_threshold=recovery_threshold_6
        )
        
        items_6_recovered = result_6_recovered.get('items', [])
        found_recovery_6_recovered = False
        for item in items_6_recovered:
            if item.get('drop_date') == drop_date and item.get('recovery_date') is not None:
                found_recovery_6_recovered = True
                break
        
        self.assertTrue(found_recovery_6_recovered, f"Price 101.0 should recover with 6% threshold (target: {expected_target_6:.2f})")
    
    def test_recovery_threshold_parameter_passing(self):
        """Test that recovery_threshold parameter is actually being used"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history with drop and partial recovery (3% recovery)
        price_history = []
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        price_history.append({'date': drop_date, 'price': 95.0})  # 5% drop
        price_history.append({'date': '2025-11-05', 'price': 97.85})  # 3% recovery (95 * 1.03 = 97.85)
        
        pct_threshold = -5.0
        
        # Test with 2% threshold - should find recovery (3% > 2%)
        result_2 = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=2.0
        )
        
        items_2 = result_2.get('items', [])
        recovery_found_2 = False
        for item in items_2:
            if item.get('drop_date') == drop_date and item.get('recovery_date') is not None:
                recovery_found_2 = True
                break
        
        # Test with 6% threshold - should NOT find recovery (3% < 6%)
        result_6 = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=6.0
        )
        
        items_6 = result_6.get('items', [])
        recovery_found_6 = False
        for item in items_6:
            if item.get('drop_date') == drop_date and item.get('recovery_date') is not None:
                recovery_found_6 = True
                break
        
        self.assertTrue(recovery_found_2, "With 2% threshold, should find recovery (3% recovered)")
        self.assertFalse(recovery_found_6, "With 6% threshold, should NOT find recovery (only 3% recovered)")

if __name__ == '__main__':
    unittest.main()
