import random
import time
import asyncio
from datetime import datetime
import json

# Global state for monitoring
class MonitoringEngine:
    def __init__(self):
        self.is_active = False
        self.current_score = 0.95
        self.incidents = []
        self.history = []
        self.last_analysis_context = None
        self.drift_active = False

    def reset(self, context=None):
        self.is_active = True
        self.current_score = 0.95
        self.history = [{"time": datetime.now().strftime("%H:%M:%S"), "score": 0.95}]
        self.incidents = []
        self.last_analysis_context = context
        self.drift_active = False

    def generate_pulse(self):
        """Generates a single synthetic data point with occasional drift"""
        if not self.is_active:
            return None

        # Random walk for stability
        change = random.uniform(-0.02, 0.02)
        
        # Inject artificial drift every ~20 pulses if not already active
        if random.random() < 0.05 and not self.drift_active:
            self.drift_active = True
            print("[Monitoring] DRIFT DETECTED: Simulating bias anomaly...")

        if self.drift_active:
            # Rapidly drop score
            self.current_score -= random.uniform(0.01, 0.04)
            if self.current_score < 0.70: # Floor
                self.current_score = 0.70
        else:
            self.current_score += change
            # Clamp between 0.88 and 0.99 for "Healthy" state
            self.current_score = max(0.88, min(0.99, self.current_score))

        point = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "score": round(self.current_score, 3),
            "status": "Healthy" if self.current_score > 0.82 else "Critical",
            "drift_detected": self.drift_active
        }
        
        self.history.append(point)
        # Keep last 100 points
        if len(self.history) > 100:
            self.history.pop(0)

        return point

    async def trigger_incident(self):
        """Triggers a Gemini-powered audit of the current drift"""
        if not self.drift_active:
            return None

        incident_id = f"INC-{int(time.time() % 10000)}"
        
        # Simple local diagnosis for speed (to save credits for the big ones)
        reasons = [
            "Feature Drift: 'Income' proxy bias in North-India region.",
            "Historical Skew: Gender-coded language in resume screening.",
            "Sampling Bias: New user segment has 40% higher rejection rate.",
            "Algorithm Decay: Disparate impact ratio dropped below 0.80."
        ]
        diagnosis = random.choice(reasons)

        new_incident = {
            "id": incident_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "severity": "High",
            "score": round(self.current_score, 3),
            "diagnosis": diagnosis,
            "investigation_pending": True
        }

        self.incidents.append(new_incident)
        
        # Reset drift after incident is recorded
        self.drift_active = False
        
        return new_incident

# Singleton instance
engine = MonitoringEngine()
