#!/usr/bin/env python3
"""
Test to verify recovery_threshold affects the summary metrics correctly
"""
import unittest
from datetime import datetime
from main import LayoffTracker

class TestRecoveryThresholdSummary(unittest.TestCase):
    
    def setUp(self):
        self.tracker = LayoffTracker()
        
    def test_recovery_threshold_affects_summary_metrics(self):
        """Test that different recovery_threshold values produce different summary metrics"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history with multiple drops and recoveries
        # Drop 1: 5% drop, recovers 3% (should recover with 2%, not with 6%)
        # Drop 2: 5% drop, recovers 7% (should recover with both 2% and 6%)
        price_history = []
        
        # Day before first drop
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        
        # First drop - 5% drop
        price_history.append({'date': '2025-10-25', 'price': 100.0})
        price_history.append({'date': '2025-10-26', 'price': 95.0})  # 5% drop
        price_history.append({'date': '2025-10-28', 'price': 97.85})  # 3% recovery
        
        # Second drop - 5% drop  
        price_history.append({'date': drop_date, 'price': 100.0})
        price_history.append({'date': '2025-11-02', 'price': 95.0})  # 5% drop
        price_history.append({'date': '2025-11-05', 'price': 101.65})  # 7% recovery
        
        pct_threshold = -5.0
        
        # Test with 2% threshold
        result_2 = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=2.0
        )
        
        summary_2 = result_2.get('summary', {})
        within_7_2 = summary_2.get('within_7_trading_days', {})
        count_7_2 = within_7_2.get('count_recovered', 0)
        
        # Test with 6% threshold
        result_6 = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=6.0
        )
        
        summary_6 = result_6.get('summary', {})
        within_7_6 = summary_6.get('within_7_trading_days', {})
        count_7_6 = within_7_6.get('count_recovered', 0)
        
        print(f"\n[TEST] With 2% threshold: {count_7_2} recoveries within 7 trading days")
        print(f"[TEST] With 6% threshold: {count_7_6} recoveries within 7 trading days")
        
        # With 2% threshold, both drops should recover (3% and 7% both > 2%)
        # With 6% threshold, only the second drop should recover (7% > 6%, but 3% < 6%)
        self.assertGreater(count_7_2, count_7_6,
                          "2% threshold should find more recoveries than 6% threshold")
        
        self.assertEqual(count_7_2, 2,
                        "With 2% threshold, should find 2 recoveries (both 3% and 7% recovered)")
        self.assertEqual(count_7_6, 1,
                        "With 6% threshold, should find 1 recovery (only 7% recovered, not 3%)")
    
    def test_recovery_threshold_affects_avg_recovery(self):
        """Test that recovery_threshold affects average recovery percentage"""
        drop_date = '2025-11-01'
        bearish_date = '2025-11-10'
        
        # Create price history with drops that recover different amounts
        price_history = []
        price_history.append({'date': '2025-10-31', 'price': 100.0})
        
        # Drop 1: recovers 3%
        price_history.append({'date': '2025-10-25', 'price': 100.0})
        price_history.append({'date': '2025-10-26', 'price': 95.0})  # 5% drop
        price_history.append({'date': '2025-10-28', 'price': 97.85})  # 3% recovery
        
        # Drop 2: recovers 8%
        price_history.append({'date': drop_date, 'price': 100.0})
        price_history.append({'date': '2025-11-02', 'price': 95.0})  # 5% drop
        price_history.append({'date': '2025-11-05', 'price': 102.6})  # 8% recovery
        
        pct_threshold = -5.0
        
        # Test with 2% threshold - both should recover
        result_2 = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=2.0
        )
        
        summary_2 = result_2.get('summary', {})
        within_40_2 = summary_2.get('within_40_days', {})
        avg_recovery_2 = within_40_2.get('avg_recovery_pct', 0.0)
        
        # Test with 6% threshold - only the 8% recovery should count
        result_6 = self.tracker.analyze_recovery_history(
            price_history, 
            pct_threshold, 
            bearish_date, 
            None, 
            recovery_threshold=6.0
        )
        
        summary_6 = result_6.get('summary', {})
        within_40_6 = summary_6.get('within_40_days', {})
        avg_recovery_6 = within_40_6.get('avg_recovery_pct', 0.0)
        
        print(f"\n[TEST] With 2% threshold: avg_recovery_pct = {avg_recovery_2}%")
        print(f"[TEST] With 6% threshold: avg_recovery_pct = {avg_recovery_6}%")
        
        # With 2% threshold: avg of 3% and 8% = 5.5%
        # With 6% threshold: only 8% (3% doesn't count)
        self.assertNotEqual(avg_recovery_2, avg_recovery_6,
                           "Average recovery should be different with different thresholds")
        msg_2 = f"With 2% threshold, avg should be ~5.5% (got {avg_recovery_2}%)"
        self.assertAlmostEqual(avg_recovery_2, 5.5, places=1, msg=msg_2)
        msg_6 = f"With 6% threshold, avg should be ~8.0% (got {avg_recovery_6}%)"
        self.assertAlmostEqual(avg_recovery_6, 8.0, places=1, msg=msg_6)

if __name__ == '__main__':
    unittest.main()
