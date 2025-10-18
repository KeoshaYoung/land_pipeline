import json
from urllib.request import Request, urlopen
from prefect import flow, task, get_run_logger

@task
def call_make_webhook(webhook_url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode()

@flow(name="nightly_backup")
def nightly_backup(
    make_webhook_url: str,
    tables: list[str] = None,
    subfolder: str = ""
):
    log = get_run_logger()
    payload = {
        "source": "prefect",
        "flow": "nightly_backup",
        "tables": tables or ["Raw Leads", "Master CRM", "Properties"],
        "subfolder": subfolder,  # e.g., "2025-10-17" or leave blank to use Make's date
    }
    result = call_make_webhook(webhook_url=make_webhook_url, payload=payload)
    log.info("Triggered Make backup. Response: %s", result)

if __name__ == "__main__":
    # quick local smoke (paste your webhook URL)
    nightly_backup("https://hook.us2.make.com/t9gtkgg5idvtw10tf767d9u957v71dah")
