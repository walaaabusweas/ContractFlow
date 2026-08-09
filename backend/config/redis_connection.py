import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
# Create Redis client
redis_client = redis.Redis(
    host="redis",   # 👈 اسم السيرفس في docker-compose
    port=6379,
    decode_responses=True
)
if redis_client.ping():
    print("Redis is connected ✅")
else:
    print("Redis connection failed ❌")