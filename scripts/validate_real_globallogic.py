import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.application.workflow.graph import build_application_graph
from packages.db.models.application import Application
from packages.db.models.candidate import Profile, User
from packages.db.models.jobs import Job
from packages.db.models.memory import MemoryFact
from packages.db.session import SessionLocal
from packages.schemas.enums import ApplicationStatus


async def main():
    print("Initializing Database Session...")
    db = SessionLocal()
    
    # 1. Create User
    user = User(
        email=f"e2e-globallogic-{uuid.uuid4()}@example.com",
        hashed_password="test-hash",
        is_active=True,
    )
    db.add(user)
    db.flush()

    # 2. Create Profile
    profile = Profile(
        user_id=user.id,
        full_name="Alex Demo",
        phone="+91 90000 00000",
        location="Bhopal, India",
        summary="Technical Support Engineer - AIML with 1-2 years experience.",
        links={"linkedin": "https://www.linkedin.com/in/alex-demo", "github": "https://github.com/alex-demo"}
    )
    db.add(profile)
    db.flush()
    
    # 3. Create Memory Facts
    facts = {
        "email": "alex.demo@example.com",
        "target role": "ML Engineer / AIML",
        "experience level": "1-2 years",
        "relocation": "Yes",
        "work authorization": "Yes",
        "sponsorship required": "No",
        "expected salary": "10 LPA",
        "notice period": "0 days / immediate",
        "gender": "Male",
        "previously worked at GlobalLogic": "No",
        "how heard about job": "LinkedIn"
    }

    for key, value in facts.items():
        fact = MemoryFact(
            user_id=user.id,
            category="profile",
            key=key,
            value=value,
            normalized_value=value,
            confidence=1.0,
            provenance="USER_PROVIDED",
            trust_level="EXPLICIT_PROFILE",
            status="CONFIRMED",
            source="manual",
            version=1,
            is_current=True,
            content_hash=str(uuid.uuid4())
        )
        db.add(fact)
    db.flush()

    # 4. Create Job
    job = Job(
        source_job_id="IRC300786",
        title="Technical Support Engineer - AIML",
        company="GlobalLogic",
        location="Gurugram",
        description="GlobalLogic Role",
        url="https://www.globallogic.com/careers/technical-support-engineer-aiml-gurugram-irc300786/",
    )
    db.add(job)
    db.flush()

    # 5. Create Application
    application = Application(
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.STARTED.value,
    )
    db.add(application)
    db.commit()

    print(f"Created Application ID: {application.id}")

    # 6. Build and invoke Workflow
    workflow_id = str(uuid.uuid4())
    initial_state = {
        "workflow_id": workflow_id,
        "application_id": str(application.id),
        "user_id": str(user.id),
        "status": ApplicationStatus.STARTED.value,
        "is_approved": False,
        "pre_submission_snapshot_id": None,
        "validation_errors": [],
    }

    print("Building application graph...")
    app = build_application_graph().compile()
    
    print("Invoking graph...")
    final_state = await app.ainvoke(initial_state)

    print("\n===============================")
    print(f"Final Status: {final_state.get('status')}")
    print(f"Browser Session ID: {final_state.get('browser_session_id')}")
    print("Pending Fields:", final_state.get("pending_field_ids", []))
    print("Waiting Fields:", final_state.get("waiting_field_ids", []))
    print("Validation Errors:", final_state.get("validation_errors", []))
    
    # Save the output to a file
    with open("real_validation_output.json", "w") as f:
        # Convert set or unsupported types to string or omit them
        try:
            json.dump(final_state, f, indent=2, default=str)
        except TypeError as e:
            print("Warning: JSON serialization error", e)

if __name__ == "__main__":
    asyncio.run(main())
