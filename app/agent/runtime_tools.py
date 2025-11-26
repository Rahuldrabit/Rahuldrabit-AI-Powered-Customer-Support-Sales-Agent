"""Runtime tools executed by the Tool Runner node (async-capable)."""

from typing import Any, Dict
import hashlib

from app.utils.logger import log
from app.integrations.tiktok import TikTokClient
from app.integrations.linkedin import LinkedInClient


def lookup_order_status(order_number: str) -> Dict[str, Any]:
    """Mock order status lookup. Deterministic based on hash for dev."""
    if not order_number:
        return {"found": False}
    h = int(hashlib.sha256(order_number.encode("utf-8")).hexdigest(), 16)
    stages = [
        {"status": "processing", "detail": "Your order is being prepared."},
        {"status": "shipped", "detail": "Your order is on the way."},
        {"status": "in_transit", "detail": "Carrier has your package."},
        {"status": "out_for_delivery", "detail": "Out for delivery today."},
        {"status": "delivered", "detail": "Delivered at destination."},
    ]
    rec = stages[h % len(stages)]
    return {"found": True, "order_number": order_number, **rec}


async def fetch_profile(platform: str, user_id: str) -> Dict[str, Any]:
    """Fetch profile from platform clients (mock implementations)."""
    try:
        if not platform or not user_id:
            return {"ok": False, "error": "missing platform or user_id"}
        if platform.lower() == "tiktok":
            client = TikTokClient()
            data = await client.get_user_info(user_id)
            return {"ok": True, "platform": platform, "profile": data}
        elif platform.lower() == "linkedin":
            client = LinkedInClient()
            data = await client.get_user_profile(user_id)
            return {"ok": True, "platform": platform, "profile": data}
        return {"ok": False, "error": f"unsupported platform: {platform}"}
    except Exception as e:
        log.error(f"fetch_profile error: {e}")
        return {"ok": False, "error": str(e)}
