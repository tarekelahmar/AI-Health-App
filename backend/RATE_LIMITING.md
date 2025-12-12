# Rate Limiting Guide

## Overview

The application uses **slowapi** for lightweight, in-memory rate limiting. This is designed for **abuse prevention**, not high-scale distributed systems. For production scaling, consider migrating to Redis-backed rate limiting later.

## Configuration

Rate limiting can be enabled/disabled via settings:

```env
ENABLE_RATE_LIMITING=true
RATE_LIMIT_INSIGHTS=10/minute
RATE_LIMIT_LLM=5/minute
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_GENERAL=100/hour
```

## Rate Limits Applied

### Insight Endpoints
- **`POST /api/v1/insights/sleep`**: 10 requests per minute (per user)
- **`GET /api/v1/insights/*`**: No specific limit (general API limit applies)

### LLM-Backed Endpoints
- **`POST /api/v1/protocols/{user_id}`**: 5 requests per minute (per user)
- Future LLM endpoints will use the same `RATE_LIMIT_LLM` setting

### Authentication Endpoints
- **`POST /api/v1/auth/login`**: 5 requests per minute (per IP address)
- Prevents brute force attacks

### General Endpoints
- All other endpoints: 100 requests per hour (per IP/user)

## How It Works

### IP-Based Limiting
Used for unauthenticated endpoints (like login):
```python
@rate_limit_ip("5/minute")
def login(...):
    ...
```

### User-Based Limiting
Used for authenticated endpoints (like insights):
```python
@rate_limit_user("10/minute")
def generate_insights(...):
    ...
```

## Rate Limit Format

Rate limits use the format: `"number/period"`

Examples:
- `"10/minute"` - 10 requests per minute
- `"100/hour"` - 100 requests per hour
- `"1000/day"` - 1000 requests per day

## Rate Limit Exceeded Response

When a rate limit is exceeded, the API returns:

```json
{
    "error": "Rate limit exceeded: 10 per 1 minute"
}
```

HTTP Status: `429 Too Many Requests`

## Disabling Rate Limiting

### For Development
Set in `.env`:
```env
ENABLE_RATE_LIMITING=false
```

### For Specific Endpoints
The decorators check `settings.ENABLE_RATE_LIMITING` and fall back to a very high limit if disabled:
```python
@rate_limit_user(settings.RATE_LIMIT_INSIGHTS if settings.ENABLE_RATE_LIMITING else "1000/minute")
```

## Storage

Rate limiting uses **in-memory storage** (`memory://`). This means:
- ✅ Fast and lightweight
- ✅ No external dependencies
- ❌ Limits reset on server restart
- ❌ Not shared across multiple server instances

For production with multiple instances, consider Redis-backed storage.

## Adding Rate Limits to New Endpoints

### For User-Based Limiting
```python
from app.config.rate_limiting import rate_limit_user
from app.config.settings import get_settings

settings = get_settings()

@router.post("/my-endpoint")
@rate_limit_user(settings.RATE_LIMIT_LLM if settings.ENABLE_RATE_LIMITING else "1000/minute")
def my_endpoint(...):
    ...
```

### For IP-Based Limiting
```python
from app.config.rate_limiting import rate_limit_ip
from app.config.settings import get_settings

settings = get_settings()

@router.post("/public-endpoint")
@rate_limit_ip(settings.RATE_LIMIT_AUTH if settings.ENABLE_RATE_LIMITING else "1000/minute")
def public_endpoint(...):
    ...
```

## Testing Rate Limits

### Test with curl
```bash
# Make 11 requests quickly (limit is 10/minute)
for i in {1..11}; do
  curl -X POST http://localhost:8000/api/v1/insights/sleep \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json"
  echo "Request $i"
done

# 11th request should return 429
```

### Test with Python
```python
import requests

token = "your_token"
headers = {"Authorization": f"Bearer {token}"}

# Make requests until rate limited
for i in range(15):
    response = requests.post(
        "http://localhost:8000/api/v1/insights/sleep",
        headers=headers
    )
    print(f"Request {i+1}: {response.status_code}")
    if response.status_code == 429:
        print("Rate limited!")
        break
```

## Monitoring

Rate limit information is logged when limits are exceeded. Check application logs for:
```
Rate limit exceeded for key: user:123
```

## Future Enhancements

1. **Redis Backend**: For distributed rate limiting across multiple instances
2. **Per-Endpoint Configuration**: More granular control per endpoint
3. **Rate Limit Headers**: Return remaining requests in response headers
4. **Whitelist**: Allow certain users/IPs to bypass limits
5. **Sliding Window**: More sophisticated rate limiting algorithms

## Troubleshooting

### Rate limits not working
1. Check `ENABLE_RATE_LIMITING=true` in settings
2. Verify slowapi is installed: `pip install slowapi`
3. Check application logs for errors

### Too restrictive
- Adjust limits in `.env` file
- Or disable for development: `ENABLE_RATE_LIMITING=false`

### Need higher limits for specific users
- Currently not supported (all users have same limits)
- Future: Add whitelist or tiered limits

