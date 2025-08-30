"""
Rate Limiting and Bot Protection Middleware for InstaFit
Provides IP-based rate limiting and bot detection capabilities
"""

import time
import re
import logging
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, g
from config import RATE_LIMIT_CONFIG, BOT_PROTECTION_CONFIG

logger = logging.getLogger(__name__)

class RateLimiter:
    """In-memory rate limiter with multiple time windows"""
    
    def __init__(self):
        self.storage = defaultdict(lambda: {
            'minute': deque(),
            'hour': deque(),
            'day': deque()
        })
        self.config = RATE_LIMIT_CONFIG
        
    def _get_client_ip(self):
        """Get the real client IP address"""
        # Check for forwarded headers (common with proxies/load balancers)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr
    
    def _cleanup_old_requests(self, client_ip, window_type):
        """Remove old requests outside the time window"""
        current_time = time.time()
        window_seconds = self.config[f"{window_type}_window"]
        
        # Remove requests older than the window
        while (self.storage[client_ip][window_type] and 
               current_time - self.storage[client_ip][window_type][0] > window_seconds):
            self.storage[client_ip][window_type].popleft()
    
    def is_rate_limited(self, client_ip):
        """Check if the client is rate limited"""
        current_time = time.time()
        
        # Check each time window
        for window_type in ['minute', 'hour', 'day']:
            self._cleanup_old_requests(client_ip, window_type)
            
            limit = self.config[f"requests_per_{window_type}"]
            current_requests = len(self.storage[client_ip][window_type])
            
            if current_requests >= limit:
                return True, window_type, limit, current_requests
        
        return False, None, None, None
    
    def record_request(self, client_ip):
        """Record a new request for the client"""
        current_time = time.time()
        
        for window_type in ['minute', 'hour', 'day']:
            self.storage[client_ip][window_type].append(current_time)
    
    def get_remaining_requests(self, client_ip):
        """Get remaining requests for each time window"""
        self._cleanup_old_requests(client_ip, 'minute')
        self._cleanup_old_requests(client_ip, 'hour')
        self._cleanup_old_requests(client_ip, 'day')
        
        return {
            'minute': self.config['requests_per_minute'] - len(self.storage[client_ip]['minute']),
            'hour': self.config['requests_per_hour'] - len(self.storage[client_ip]['hour']),
            'day': self.config['requests_per_day'] - len(self.storage[client_ip]['day'])
        }

class BotProtector:
    """Bot detection and protection"""
    
    def __init__(self):
        self.config = BOT_PROTECTION_CONFIG
    
    def _get_user_agent(self):
        """Get user agent string"""
        return request.headers.get('User-Agent', '').lower()
    
    def _is_bot_user_agent(self, user_agent):
        """Check if user agent indicates a bot"""
        if not self.config['block_bot_user_agents']:
            return False
        
        # Check whitelist first
        for allowed_agent in self.config['allowed_user_agents']:
            if allowed_agent.lower() in user_agent:
                return False
        
        # Check bot patterns
        for pattern in self.config['bot_user_agent_patterns']:
            if pattern.lower() in user_agent:
                return True
        
        return False
    
    def _is_known_bot_ip(self, client_ip):
        """Check if IP is in known bot list"""
        if not self.config['block_known_bot_ips']:
            return False
        
        return client_ip in self.config['known_bot_ips']
    
    def _has_required_headers(self):
        """Check if request has required headers"""
        if not self.config['require_user_agent']:
            return True
        
        user_agent = request.headers.get('User-Agent')
        return user_agent is not None and user_agent.strip() != ''
    
    def is_bot(self, client_ip):
        """Check if the request is from a bot"""
        user_agent = self._get_user_agent()
        
        # Check for missing required headers
        if not self._has_required_headers():
            logger.warning(f"Request missing required headers from IP: {client_ip}")
            return True, "Missing required headers"
        
        # Check for bot user agent
        if self._is_bot_user_agent(user_agent):
            logger.warning(f"Bot user agent detected from IP: {client_ip}, UA: {user_agent}")
            return True, f"Bot user agent detected: {user_agent}"
        
        # Check for known bot IP
        if self._is_known_bot_ip(client_ip):
            logger.warning(f"Known bot IP detected: {client_ip}")
            return True, "Known bot IP"
        
        return False, None

# Global instances
rate_limiter = RateLimiter()
bot_protector = BotProtector()

def rate_limit_and_protect(f):
    """Decorator to apply rate limiting and bot protection"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = rate_limiter._get_client_ip()
        
        # Bot protection check
        is_bot, bot_reason = bot_protector.is_bot(client_ip)
        if is_bot:
            logger.warning(f"Bot request blocked from {client_ip}: {bot_reason}")
            return jsonify({
                "error": "Access denied",
                "reason": "Bot detection",
                "details": bot_reason
            }), 403
        
        # Rate limiting check
        is_limited, window_type, limit, current = rate_limiter.is_rate_limited(client_ip)
        if is_limited:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {current}/{limit} requests per {window_type}")
            
            response = jsonify({
                "error": "Rate limit exceeded",
                "limit_type": window_type,
                "limit": limit,
                "current": current,
                "retry_after": RATE_LIMIT_CONFIG[f"{window_type}_window"]
            })
            
            # Add rate limit headers if enabled
            if RATE_LIMIT_CONFIG['enable_headers']:
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(time.time() + RATE_LIMIT_CONFIG[f"{window_type}_window"]))
                response.headers['Retry-After'] = str(RATE_LIMIT_CONFIG[f"{window_type}_window"])
            
            return response, 429
        
        # Record the request
        rate_limiter.record_request(client_ip)
        
        # Add rate limit info to request context
        g.client_ip = client_ip
        g.rate_limit_info = rate_limiter.get_remaining_requests(client_ip)
        
        # Add rate limit headers to response if enabled
        if RATE_LIMIT_CONFIG['enable_headers']:
            remaining = rate_limiter.get_remaining_requests(client_ip)
            response = f(*args, **kwargs)
            
            # If response is a tuple (response, status_code)
            if isinstance(response, tuple):
                flask_response, status_code = response
                if hasattr(flask_response, 'headers'):
                    flask_response.headers['X-RateLimit-Limit-Minute'] = str(RATE_LIMIT_CONFIG['requests_per_minute'])
                    flask_response.headers['X-RateLimit-Limit-Hour'] = str(RATE_LIMIT_CONFIG['requests_per_hour'])
                    flask_response.headers['X-RateLimit-Limit-Day'] = str(RATE_LIMIT_CONFIG['requests_per_day'])
                    flask_response.headers['X-RateLimit-Remaining-Minute'] = str(remaining['minute'])
                    flask_response.headers['X-RateLimit-Remaining-Hour'] = str(remaining['hour'])
                    flask_response.headers['X-RateLimit-Remaining-Day'] = str(remaining['day'])
                return flask_response, status_code
            else:
                # If response is just the response object
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit-Minute'] = str(RATE_LIMIT_CONFIG['requests_per_minute'])
                    response.headers['X-RateLimit-Limit-Hour'] = str(RATE_LIMIT_CONFIG['requests_per_hour'])
                    response.headers['X-RateLimit-Limit-Day'] = str(RATE_LIMIT_CONFIG['requests_per_day'])
                    response.headers['X-RateLimit-Remaining-Minute'] = str(remaining['minute'])
                    response.headers['X-RateLimit-Remaining-Hour'] = str(remaining['hour'])
                    response.headers['X-RateLimit-Remaining-Day'] = str(remaining['day'])
                return response
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_rate_limit_info(client_ip):
    """Get current rate limit information for a client"""
    return rate_limiter.get_remaining_requests(client_ip)

def reset_rate_limit(client_ip):
    """Reset rate limit for a client (admin function)"""
    if client_ip in rate_limiter.storage:
        del rate_limiter.storage[client_ip]
        logger.info(f"Rate limit reset for IP: {client_ip}")
        return True
    return False 