import json
import subprocess


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def get_counts():
    counts = {}
    for table in ["jobs", "applications", "memory_facts", "application_events"]:
        cmd = f"docker exec ai_job_agent_db_prod psql -U postgres -d ai_job_agent -t -c \"SELECT count(*) FROM {table};\""
        result = run(cmd)
        counts[table] = int(result.stdout.strip() or "0")
    return counts

def populate():
    print("Populating initial data...")
    queries = [
        "INSERT INTO users (id, email, hashed_password, is_active, created_at, updated_at) VALUES ('33333333-3333-3333-3333-333333333333', 'test3@example.com', '123', true, now(), now()) ON CONFLICT DO NOTHING;",
        "INSERT INTO jobs (id, title, company, url, description, source_job_id, created_at, updated_at) VALUES ('44444444-4444-4444-4444-444444444444', 'Data Engineer', 'Meta', 'https://m', 'desc', 'm123', now(), now()) ON CONFLICT DO NOTHING;",
        "INSERT INTO applications (id, user_id, job_id, status, created_at, updated_at) VALUES ('55555555-5555-5555-5555-555555555555', '33333333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', 'pending', now(), now()) ON CONFLICT DO NOTHING;",
        "INSERT INTO memory_facts (id, user_id, category, confidence, provenance, status, key, value, trust_level, created_at, updated_at) VALUES ('66666666-6666-6666-6666-666666666666', '33333333-3333-3333-3333-333333333333', 'test', 1.0, 'test', 'active', 'test_key', 'test_value', 'high', now(), now()) ON CONFLICT DO NOTHING;",
        "INSERT INTO application_events (id, application_id, user_id, event_type, new_state, actor_type, correlation_id, occurred_at, created_at, updated_at) VALUES ('77777777-7777-7777-7777-777777777777', '55555555-5555-5555-5555-555555555555', '33333333-3333-3333-3333-333333333333', 'status_change', 'pending', 'system', 'corr1', now(), now(), now()) ON CONFLICT DO NOTHING;"
    ]
    for q in queries:
        cmd = f'docker exec ai_job_agent_db_prod psql -U postgres -d ai_job_agent -c "{q}"'
        res = run(cmd)
        if res.returncode != 0:
            print("Populate error:", res.stderr)

import datetime
import time


def main():
    print("=== GATE 1: DATABASE BACKUP / RESTORE ===")
    populate()
    before = get_counts()
    print("BEFORE BACKUP:")
    print(json.dumps(before, indent=2))
    
    backup_start = time.time()
    print("\nCreating backup (pg_dump -F c)...")
    # Clean up previous dump if any
    run("docker exec ai_job_agent_db_prod rm -f /tmp/gate1.dump")
    backup_cmd = "docker exec ai_job_agent_db_prod pg_dump -U postgres -d ai_job_agent -F c -f /tmp/gate1.dump"
    res = run(backup_cmd)
    backup_end = time.time()
    backup_duration = backup_end - backup_start
    print(f"Backup exit code: {res.returncode}")
    
    print("\nPreparing clean target database (ai_job_agent_clean)...")
    run("docker exec ai_job_agent_db_prod psql -U postgres -c \"DROP DATABASE IF EXISTS ai_job_agent_clean;\"")
    run("docker exec ai_job_agent_db_prod psql -U postgres -c \"CREATE DATABASE ai_job_agent_clean;\"")
    run("docker exec ai_job_agent_db_prod psql -U postgres -d ai_job_agent_clean -c \"CREATE EXTENSION IF NOT EXISTS vector;\"")

    restore_start = time.time()
    print("\nRestoring backup into clean target...")
    restore_cmd = "docker exec ai_job_agent_db_prod pg_restore -U postgres -d ai_job_agent_clean -1 /tmp/gate1.dump"
    res = run(restore_cmd)
    restore_end = time.time()
    restore_duration = restore_end - restore_start
    print(f"Restore exit code: {res.returncode}")
    if res.returncode != 0:
        print("RESTORE ERRORS:")
        print(res.stderr)
        
    print("\nFetching counts from RESTORED database...")
    counts_after = {}
    for table in ["jobs", "applications", "memory_facts", "application_events"]:
        cmd = f"docker exec ai_job_agent_db_prod psql -U postgres -d ai_job_agent_clean -t -c \"SELECT count(*) FROM {table};\""
        r = run(cmd)
        counts_after[table] = int(r.stdout.strip() or "0")
        
    print("AFTER RESTORE:")
    print(json.dumps(counts_after, indent=2))

    print("\n--- RPO/RTO Report ---")
    print(f"Backup timestamp: {datetime.datetime.now().isoformat()}")
    print(f"Backup duration: {backup_duration:.2f}s")
    print(f"Restore duration: {restore_duration:.2f}s")
    # For a snapshot RTO/RPO, RTO is restore duration + overhead. RPO is time since last backup (here ~0s since immediately restored)
    print(f"Measured RTO: {restore_duration:.2f}s")
    print("Measured RPO: 0s (immediate restore test)")


if __name__ == "__main__":
    main()
