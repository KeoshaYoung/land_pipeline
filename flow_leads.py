from prefect import flow, task, get_run_logger

@task(retries=3)
def fetch_new_leads():
    return ["lead-1", "lead-2"]

@flow(name="lead_ingest")
def lead_ingest():
    log = get_run_logger()
    leads = fetch_new_leads()
    log.info("Ingested %d leads", len(leads))

if __name__ == "__main__":
    lead_ingest()
