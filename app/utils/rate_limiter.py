import time
from collections import defaultdict


class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(list)
    
    def can_attempt_reset(self, email, max_attempts=5, window_hours=1):
        """Check if user can attempt password reset"""
        now = time.time()
        window_seconds = window_hours * 3600
        
        # Clean old attempts
        self.attempts[email] = [
            attempt_time for attempt_time in self.attempts[email]
            if now - attempt_time < window_seconds
        ]
        
        # Check if under limit
        if len(self.attempts[email]) >= max_attempts:
            return False
        
        # Record this attempt
        self.attempts[email].append(now)
        return True
    
    def get_remaining_attempts(self, email, max_attempts=5):
        """Get remaining attempts for email"""
        return max(0, max_attempts - len(self.attempts.get(email, [])))


rate_limiter = RateLimiter()
