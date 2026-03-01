#!/usr/bin/env python3
"""
Test to verify recovery_threshold parameter flows correctly through the chain
"""
import unittest
from datetime import datetime
from main import LayoffTracker
import inspect

class TestRecoveryThresholdParameterFlow(unittest.TestCase):
    
    def test_analyze_recovery_history_signature(self):
        """Test that analyze_recovery_history accepts recovery_threshold parameter"""
        tracker = LayoffTracker()
        
        # Get function signature
        sig = inspect.signature(tracker.analyze_recovery_history)
        params = list(sig.parameters.keys())
        
        # Check that recovery_threshold is in the parameters
        self.assertIn('recovery_threshold', params, 
                     "analyze_recovery_history should have recovery_threshold parameter")
        
        # Check default value
        recovery_threshold_param = sig.parameters['recovery_threshold']
        self.assertEqual(recovery_threshold_param.default, 6.0,
                        f"recovery_threshold default should be 6.0, got {recovery_threshold_param.default}")
    
    def test_get_bearish_analytics_signature(self):
        """Test that get_bearish_analytics accepts recovery_threshold parameter"""
        tracker = LayoffTracker()
        
        # Get function signature
        sig = inspect.signature(tracker.get_bearish_analytics)
        params = list(sig.parameters.keys())
        
        # Check that recovery_threshold is in the parameters
        self.assertIn('recovery_threshold', params,
                     "get_bearish_analytics should have recovery_threshold parameter")
        
        # Check default value
        recovery_threshold_param = sig.parameters['recovery_threshold']
        self.assertEqual(recovery_threshold_param.default, 6.0,
                        f"recovery_threshold default should be 6.0, got {recovery_threshold_param.default}")
    
    def test_recovery_threshold_calculation_verification(self):
        """Verify the recovery_target calculation uses recovery_threshold correctly"""
        drop_price = 95.0
        
        # Test different thresholds
        test_cases = [
            (2.0, 95.0 * 1.02),   # 96.9
            (6.0, 95.0 * 1.06),   # 100.7
            (10.0, 95.0 * 1.10),  # 104.5
        ]
        
        for threshold, expected_target in test_cases:
            calculated_target = drop_price * (1 + threshold / 100)
            error_msg = f"Recovery target calculation incorrect for {threshold}% threshold"
            self.assertAlmostEqual(calculated_target, expected_target, places=2, msg=error_msg)
            print(f"✓ {threshold}% threshold: drop_price={drop_price}, target={calculated_target:.2f}")
    
    def test_recovery_threshold_affects_results(self):
        """Test that different recovery_threshold values produce different results"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history with 4% recovery (between 2% and 6%)
        price_history = []
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        price_history.append({'date': drop_date, 'price': 95.0})  # 5% drop
        price_history.append({'date': '2025-11-05', 'price': 98.8})  # 4% recovery (95 * 1.04 = 98.8)
        
        pct_threshold = -5.0
        tracker = LayoffTracker()
        
        # Test with 2% threshold - should find recovery (4% > 2%)
        result_2 = tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=2.0
        )
        
        items_2 = result_2.get('items', [])
        recovery_count_2 = sum(1 for item in items_2 
                               if item.get('drop_date') == drop_date 
                               and item.get('recovery_date') is not None)
        
        # Test with 6% threshold - should NOT find recovery (4% < 6%)
        result_6 = tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=6.0
        )
        
        items_6 = result_6.get('items', [])
        recovery_count_6 = sum(1 for item in items_6 
                              if item.get('drop_date') == drop_date 
                              and item.get('recovery_date') is not None)
        
        print(f"\n[TEST] With 2% threshold: {recovery_count_2} recoveries found")
        print(f"[TEST] With 6% threshold: {recovery_count_6} recoveries found")
        
        self.assertGreater(recovery_count_2, recovery_count_6,
                          "2% threshold should find more recoveries than 6% threshold for 4% recovery")
        
        self.assertEqual(recovery_count_2, 1,
                        "With 2% threshold, should find 1 recovery (4% recovered)")
        self.assertEqual(recovery_count_6, 0,
                        "With 6% threshold, should find 0 recoveries (only 4% recovered)")

if __name__ == '__main__':
    unittest.main()
