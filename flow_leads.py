from prefect import flow, task

@task(retries=3)
def fetch_new_leads(): 
    return ["lead-1", "lead-2"]

@flow(name="lead_ingest")
def lead_ingest():
    leads = fetch_new_leads()
    print(f"Ingested {len(leads)} leads")

if __name__ == "__main__":
    lead_ingest()
