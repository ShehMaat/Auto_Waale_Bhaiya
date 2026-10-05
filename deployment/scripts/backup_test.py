import os
import subprocess
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from packages.db.models.application import Application, ApplicationEvent
from packages.db.models.candidate import User
from packages.db.models.jobs import Job
from packages.db.models.memory import MemoryFact

DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_agent"
engine = create_engine(DATABASE_URL)

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def populate_data():
    with Session(engine) as session:
        user = session.query(User).filter_by(email="test@test.com").first()
        if not user:
            user = User(email="test@test.com", hashed_password="pwd")
            session.add(user)
            session.commit()
    
        job = Job(
            title="Software Engineer",
            company="Google",
            url="https://google.com/careers/123",
            description="Build cool things",
            source_job_id="g123"
        )
        session.add(job)
        session.commit()
        
        app = Application(
            user_id=user.id,
            job_id=job.id,
            status="WAITING_FOR_USER"
        )
        session.add(app)
        session.commit()
        
        event = ApplicationEvent(
            application_id=app.id,
            user_id=user.id,
            event_type="STATE_CHANGE",
            new_state="WAITING_FOR_USER",
            actor_type="system",
            correlation_id="corr_123"
        )
        session.add(event)
        session.commit()
        
        fact = MemoryFact(
            user_id=user.id,
            category="skill",
            key="language",
            value="Python",
            confidence=0.9,
            provenance="user",
            trust_level="high",
            status="active",
            source="user_input"
        )
        session.add(fact)
        session.commit()

def print_counts(title):
    with Session(engine) as session:
        jobs = session.query(Job).count()
        apps = session.query(Application).count()
        events = session.query(ApplicationEvent).count()
        facts = session.query(MemoryFact).count()
        
        print(f"\n{title}")
        print(f"jobs: {jobs}")
        print(f"applications: {apps}")
        print(f"memory_facts: {facts}")
        print(f"application_events: {events}")

def wipe_db():
    with Session(engine) as session:
        session.query(ApplicationEvent).delete()
        session.query(Application).delete()
        session.query(Job).delete()
        session.query(MemoryFact).delete()
        session.query(User).delete()
        session.commit()

if __name__ == "__main__":
    wipe_db()
    populate_data()
    print_counts("BEFORE")
    
    # Backup
    print("\nBACKUP")
    t0 = time.time()
    res = run_cmd("docker exec ai_job_agent_db_prod pg_dump -U postgres -d ai_job_agent -F c -f /tmp/db.dump")
    run_cmd("docker cp ai_job_agent_db_prod:/tmp/db.dump backup.dump")
    print(f"timestamp: {t0}")
    print("artifact: backup.dump")
    try:
        print(f"size: {os.path.getsize('backup.dump')}")
    except:
        pass
    print(f"exit code: {res.returncode}")
    
    wipe_db()
    print_counts("AFTER WIPE")
    
    # Restore
    print("\nRESTORE")
    run_cmd("docker cp backup.dump ai_job_agent_db_prod:/tmp/db_restore.dump")
    engine.dispose()
    t1 = time.time()
    
    # Drop and recreate
    run_cmd("docker exec ai_job_agent_db_prod psql -U postgres -c \"DROP DATABASE IF EXISTS ai_job_agent_temp;\"")
    run_cmd("docker exec ai_job_agent_db_prod psql -U postgres -c \"CREATE DATABASE ai_job_agent_temp;\"")
    
    res2 = run_cmd("docker exec ai_job_agent_db_prod pg_restore -U postgres -d ai_job_agent_temp -1 /tmp/db_restore.dump")
    t2 = time.time()
    
    print(f"duration: {t2 - t1:.2f}s")
    print(f"exit code: {res2.returncode}")
    print(f"stderr: {res2.stderr}")
    
    # Let's count from temp DB
    res3 = run_cmd("docker exec ai_job_agent_db_prod psql -U postgres -d ai_job_agent_temp -t -c \"SELECT count(*) FROM jobs;\"")
    print(f"RESTORED JOBS COUNT: {res3.stdout.strip()}")
    
    print_counts("AFTER RESTORE")
