"""
Configuration file for InstaFit backend
All settings can be easily modified here for quick updates
"""

# Rate Limiting Configuration
RATE_LIMIT_CONFIG = {
    # Requests per minute
    "requests_per_minute": 3,
    
    # Requests per hour
    "requests_per_hour": 15,
    
    # Requests per day
    "requests_per_day": 30,
    
    # Rate limit window in seconds
    "minute_window": 60,
    "hour_window": 3600,
    "day_window": 86400,
    
    # Rate limit headers
    "enable_headers": True,
    
    # Storage configuration (in-memory for now, can be changed to Redis later)
    "storage_type": "memory",  # Options: "memory", "redis"
    
    # Redis configuration (if using Redis storage)
    "redis_config": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None
    }
}

# Bot Protection Configuration
BOT_PROTECTION_CONFIG = {
    # Block common bot user agents
    "block_bot_user_agents": True,
    
    # Block requests without proper headers
    "require_user_agent": True,
    
    # Block requests from known bot IPs (optional)
    "block_known_bot_ips": False,
    
    # List of bot user agent patterns to block
    "bot_user_agent_patterns": [
        "bot", "crawler", "spider", "scraper", "scraper", "crawler",
        "python", "curl", "wget", "http", "java", "perl", "ruby",
        "go-http-client", "okhttp", "apache-httpclient", "requests",
        "urllib", "mechanize", "scrapy", "selenium", "phantomjs",
        "headless", "chrome-lighthouse", "googlebot", "bingbot",
        "yandex", "baiduspider", "facebookexternalhit", "twitterbot",
        "linkedinbot", "whatsapp", "telegrambot", "slackbot",
        "discordbot", "redditbot", "tumblr", "instagram", "pinterest"
    ],
    
    # List of known bot IPs (optional)
    "known_bot_ips": [
        # Add known bot IPs here if needed
    ],
    
    # Allow specific user agents (whitelist)
    "allowed_user_agents": [
        "instafit-extension",  # Your Chrome extension
        "instafit-mobile",     # Your mobile app if any
    ]
}

# API Configuration
API_CONFIG = {
    # API keys (moved from app.py for better organization)
    "api_keys": {
        # These will be loaded from environment variables
    },
    
    # CORS settings
    "cors_origins": [
        "chrome-extension://*",  # Chrome extensions
        "http://localhost:*",    # Local development
        "https://yourdomain.com" # Your production domain
    ],
    
    # Request timeout settings
    "request_timeout": 30,  # seconds
    
    # Max file size for image uploads (in bytes)
    "max_image_size": 10 * 1024 * 1024,  # 10MB
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "instafit.log",
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# Development/Production Configuration
ENVIRONMENT = "development"  # Options: "development", "production"

# Debug settings
DEBUG = ENVIRONMENT == "development"

# Server configuration
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": DEBUG,
    "threaded": True
} 