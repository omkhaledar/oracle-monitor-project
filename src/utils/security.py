import time
import asyncio
from collections import deque
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    A circuit breaker to prevent repeated calls to a failing service.
    """
    def __init__(self, failure_threshold: int, reset_timeout: int):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # Can be CLOSED, OPEN, or HALF_OPEN

    def record_failure(self):
        """Record a failure and open the circuit if threshold is met."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened. Failing fast for {self.reset_timeout}s.")

    def record_success(self):
        """Reset the circuit on success."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker closed successfully.")

    async def __aenter__(self):
        """Check the circuit state before allowing an operation."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker is now HALF_OPEN. Allowing one test call.")
            else:
                raise ConnectionAbortedError("Circuit breaker is open. Call is blocked.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Update circuit state based on operation outcome."""
        if exc_type:
            self.record_failure()
        else:
            self.record_success()


class RateLimiter:
    """
    A simple token bucket rate limiter for async operations.
    """
    def __init__(self, rate: int, per: int):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()

    async def acquire(self):
        """Wait until a token is available."""
        while True:
            now = time.monotonic()
            time_passed = now - self.last_check
            self.last_check = now
            self.allowance += time_passed * (self.rate / self.per)

            if self.allowance > self.rate:
                self.allowance = self.rate  # Cap the allowance

            if self.allowance >= 1:
                self.allowance -= 1
                return
            
            # Calculate sleep time to wait for the next token
            sleep_time = (1 - self.allowance) * (self.per / self.rate)
            await asyncio.sleep(sleep_time)
