## 2024-03-24 - Unblocking /remote/metrics endpoint
**Learning:** Using `psutil.cpu_percent(interval=0.1)` inside a Flask route handler blocked the thread for 0.1s for every request. Under load, this caused severe latency and thread starvation because Flask's dev server handles requests sequentially or with a limited thread pool, meaning a 100ms blocking call heavily degraded throughput.
**Action:** Use `psutil.cpu_percent(interval=None)` for non-blocking instantaneous measurements in route handlers.
