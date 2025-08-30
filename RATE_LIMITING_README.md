# InstaFit Rate Limiting & Bot Protection

This document describes the IP-based rate limiting and bot protection system implemented for the InstaFit backend.

## Features

### Rate Limiting
- **3 requests per minute**
- **15 requests per hour** 
- **30 requests per day**
- Configurable limits via `config.py`
- Real-time rate limit headers in responses
- Automatic cleanup of expired requests

### Bot Protection
- Blocks requests without User-Agent headers
- Blocks common bot User-Agent patterns
- Whitelist for legitimate clients (Chrome extension, mobile app)
- Optional blocking of known bot IPs
- Comprehensive logging of blocked requests

## Configuration

All settings are easily configurable in `config.py`:

### Rate Limiting Settings
```python
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 3,
    "requests_per_hour": 15,
    "requests_per_day": 30,
    "minute_window": 60,
    "hour_window": 3600,
    "day_window": 86400,
    "enable_headers": True,
    "storage_type": "memory",  # Can be changed to "redis" later
}
```

### Bot Protection Settings
```python
BOT_PROTECTION_CONFIG = {
    "block_bot_user_agents": True,
    "require_user_agent": True,
    "block_known_bot_ips": False,
    "bot_user_agent_patterns": [
        "bot", "crawler", "spider", "python", "curl", "wget",
        # ... more patterns
    ],
    "allowed_user_agents": [
        "instafit-extension",
        "instafit-mobile",
    ]
}
```

## Usage

### Applying Rate Limiting to Routes

Simply add the `@rate_limit_and_protect` decorator to any route:

```python
from rate_limiter import rate_limit_and_protect

@app.route('/api/endpoint')
@rate_limit_and_protect
def my_endpoint():
    return jsonify({"message": "Success"})
```

### Rate Limit Headers

When rate limiting is enabled, responses include these headers:

- `X-RateLimit-Limit-Minute`: Requests allowed per minute
- `X-RateLimit-Limit-Hour`: Requests allowed per hour  
- `X-RateLimit-Limit-Day`: Requests allowed per day
- `X-RateLimit-Remaining-Minute`: Remaining requests this minute
- `X-RateLimit-Remaining-Hour`: Remaining requests this hour
- `X-RateLimit-Remaining-Day`: Remaining requests this day

### Rate Limit Responses

When rate limit is exceeded, the API returns:

```json
{
    "error": "Rate limit exceeded",
    "limit_type": "minute",
    "limit": 3,
    "current": 3,
    "retry_after": 60
}
```

With HTTP status code `429 Too Many Requests`.

### Bot Protection Responses

When a bot is detected, the API returns:

```json
{
    "error": "Access denied",
    "reason": "Bot detection",
    "details": "Bot user agent detected: python-requests/2.31.0"
}
```

With HTTP status code `403 Forbidden`.

## API Endpoints

### Rate Limit Status
```
GET /rate-limit/status
```
Returns current rate limit information for the requesting IP.

### Admin Reset Rate Limit
```
GET /rate-limit/reset/<ip_address>
```
Resets rate limit for a specific IP (admin function).

### Health Check
```
GET /health
```
Includes rate limit information in the response.

## Testing

Run the test script to verify the implementation:

```bash
python test_rate_limiting.py
```

This will test:
- Rate limiting functionality
- Bot protection
- API endpoint integration
- Rate limit headers

## Monitoring

### Logs
All rate limiting and bot protection events are logged to `instafit.log`:

```
2024-01-15 10:30:15 - rate_limiter - WARNING - Rate limit exceeded for IP 192.168.1.100: 3/3 requests per minute
2024-01-15 10:30:20 - rate_limiter - WARNING - Bot request blocked from 192.168.1.101: Bot user agent detected: python-requests/2.31.0
```

### Metrics
You can monitor rate limiting by:
1. Checking the `/rate-limit/status` endpoint
2. Monitoring response headers
3. Reviewing application logs

## Future Enhancements

### Redis Storage
For production use with multiple server instances, you can switch to Redis storage:

1. Update `config.py`:
```python
"storage_type": "redis"
```

2. Install Redis dependencies:
```bash
pip install redis
```

3. Update the `RateLimiter` class in `rate_limiter.py` to use Redis.

### Advanced Bot Detection
- Implement CAPTCHA for suspicious requests
- Add IP reputation checking
- Implement behavioral analysis
- Add machine learning-based bot detection

### Rate Limit Tiers
- Different limits for different user types
- Premium user higher limits
- API key-based rate limiting

## Security Considerations

1. **IP Spoofing**: The system checks multiple headers (`X-Forwarded-For`, `X-Real-IP`) to get the real client IP
2. **User Agent Spoofing**: Bot detection includes multiple patterns and can be enhanced
3. **Rate Limit Bypass**: Consider implementing additional measures like CAPTCHA for repeated violations
4. **Admin Endpoints**: The reset endpoint should be protected with proper authentication in production

## Troubleshooting

### Common Issues

1. **Rate limiting not working**: Check if the decorator is applied correctly
2. **Bot protection too strict**: Adjust the `allowed_user_agents` list in config
3. **Memory usage high**: Consider switching to Redis storage for high-traffic applications
4. **False positives**: Review and adjust bot detection patterns

### Debug Mode
Enable debug logging by setting the log level in `config.py`:
```python
"level": "DEBUG"
```

## Performance

- In-memory storage is fast but doesn't persist across server restarts
- Redis storage is recommended for production with multiple instances
- Rate limiting adds minimal overhead (~1-2ms per request)
- Automatic cleanup prevents memory leaks 