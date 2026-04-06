# implement rate limiting w/ redis
# Endpoint	Identifier	Limit	Window	Redis Key Pattern
# /auth/sign-in	IP Address	5	15 min	rate_limit:sign-in:{ip}
# /auth/sign-up	IP Address	3	1 hour	rate_limit:sign-up:{ip}
# /auth/refresh	User ID	20	1 min	rate_limit:refresh:{user_id}
# /auth/logout	IP Address	20	1 min	rate_limit:logout:{ip}


from fastapi import Request, HTTPException
from redis.asyncio import Redis
from functools import wraps
import time
from ..utils.redis_client import get_redis_client


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check if behind a proxy/load balancer
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can be: "client, proxy1, proxy2"
        # We want the first IP (the client)
        return forwarded.split(",")[0].strip()

    # Direct connection
    if request.client:
        return request.client.host

    return "unknown"


async def check_rate_limit(
    redis: Redis, key: str, max_requests: int, window_seconds: int
) -> tuple[int, int, int]:
    """
    Validating the request to the redis db
    returns (current_count, remaining, reset_timestamp)
    """
    try:
        # incrementing the counter atomically in the db
        current = await redis.incr(key)

        # we need to set expiration if this is the first request because that value needs to be initialized in the db
        if current == 1:
            await redis.expire(key, window_seconds)

        ttl = await redis.ttl(key)
        reset_time = (
            int(time.time()) + ttl if ttl > 0 else int(time.time()) + window_seconds
        )

        remaining_requests = max(0, max_requests - current)

        return (current, remaining_requests, reset_time)
    except Exception as e:
        print(f"⚠️  Unable to check the rate limiting in Redis: {e}")
        return (0, max_requests, int(time.time()) + window_seconds)


def rate_limit(
    max_requests: int, window_seconds: int, identifier_type: str, key_prefix: str
):
    """
    Middleware rate limiter, defines how many requests can be made in a
    specific window of time. Doing this with redis.
    """

    def decorator(func):
        # *args = positional arguments represented as a tuple
        # **kwargs = keyword arguments represented as a dictionary
        @wraps(func)  # preserving the function metadata
        async def wrapper(*args, **kwargs):
            """
            # 1. Get Request object from kwargs
            # 2. Extract identifier (IP or user_id)
            # 3. Build Redis key
            # 4. Check rate limit in Redis
            # 5. If exceeded, raise HTTPException(429)
            # 6. If allowed, call original function
            # 7. Add rate limit headers to response
            """

            request = kwargs.get("request")
            if not request:
                raise ValueError("Request was not able to be grabbed")

            if identifier_type == "ip":
                identifier = get_client_ip(request)
            elif identifier_type == "user_id":
                body = kwargs.get("body")
                if not body:
                    raise ValueError("Body was not able to be found")

                try:
                    from ..auth.jwt_helpers import decode_token

                    decoded_token = decode_token(
                        body.refresh_token, token_type="refresh"
                    )
                    identifier = decoded_token["sub"]
                except:
                    identifier = get_client_ip(
                        request
                    )  # if no user_id, rate limit by ip address
            else:
                raise ValueError("Unknown identifier_type")

            redis_key = f"rate_limit:{key_prefix}:{identifier}"

            redis = await get_redis_client()
            current, remaining_requests, reset_time = await check_rate_limit(
                redis, redis_key, max_requests, window_seconds
            )

            if current > max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {reset_time - int(time.time())} seconds.",
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - int(time.time())),
                    },
                )

            # Call the original function and return its response
            response = await func(*args, **kwargs)
            return response

        return wrapper

    return decorator
