# services

Reserved area from an earlier design. No separate orchestrator or edge-filter service is implemented here.

The current release keeps Redis/Celery in `apps/api/app/tasks/celery_app.py`; Node.js/BullMQ and the C++ filter are excluded by the [product plan](../docs/FINAL_PRODUCT_PLAN.md). Do not implement those earlier proposals without an explicit scope change. See [actual architecture](../ARCHITECTURE.md).
