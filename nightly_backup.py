# nightly_backup.py
from prefect import flow, task, get_run_logger

@task(retries=2, retry_delay_seconds=10)
def call_make_webhook(webhook_url: str, payload: dict) -> tuple[int, str]:
    """
    POST JSON to a Make webhook. Returns (status_code, body).
    Uses requests for reliable redirect/TLS handling.
    """
    import requests
    resp = requests.post(
        webhook_url,
        json=payload,
        timeout=30,
        allow_redirects=False  # surface any redirects instead of silently following
    )
    return resp.status_code, (resp.text or "")

@flow(name="nightly_backup")
def nightly_backup(
    make_webhook_url: str,
    tables: list[str] | None = None,
    subfolder: str = ""
):
    log = get_run_logger()
    payload = {
        "source": "prefect",
        "flow": "nightly_backup",
        "tables": tables or ["Raw Leads", "Master CRM", "Properties"],
        "subfolder": subfolder,  # e.g., "2025-10-17"; blank = Make will use its own date
    }
    status, body = call_make_webhook(webhook_url=make_webhook_url, payload=payload)
    log.info("Make webhook status=%s body=%s", status, (body[:500] if body else ""))

    # Fail the flow if Make rejects the request
    if status >= 400:
        raise RuntimeError(f"Make webhook failed: {status} :: {body[:500]}")

if __name__ == "__main__":
    # quick local smoke test: paste your real webhook URL here
    nightly_backup("https://hook.us2.make.com/t9gtkgg5idvtw10tf767d9u957v71dah")
