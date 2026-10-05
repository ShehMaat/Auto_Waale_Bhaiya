import multiprocessing
import time
import uuid

import pytest
import uvicorn

from packages.application.workflow.graph import build_application_graph
from packages.browser.policies import BrowserSecurityPolicy
from packages.db.models.application import Application
from packages.db.models.candidate import Profile, User
from packages.db.models.jobs import Job
from packages.db.models.memory import MemoryFact
from packages.schemas.enums import ApplicationStatus

# Import our ATS app
from tests.fixtures.golden_ats.app import app as ats_app


def run_server():
    uvicorn.run(ats_app, host="127.0.0.1", port=8085, log_level="error")

@pytest.fixture(scope="module")
def ats_server():
    p = multiprocessing.Process(target=run_server)
    p.start()
    time.sleep(2) # Give it time to start
    yield
    p.terminate()
    p.join()

@pytest.fixture
def mock_security():
    original = BrowserSecurityPolicy.validate_navigation_url
    def validate(url: str):
        if url.startswith("http://127.0.0.1:8085"):
            return url
        return original(url)
    
    import unittest.mock

    from packages.common.storage import MinioStorageProvider
    
    orig_download = MinioStorageProvider.download_file
    def download_file(self, object_name: str, file_path: str):
        with open(file_path, "wb") as f:
            f.write(b"dummy pdf content")
        return True

    from packages.llm.gemini_provider import GeminiProvider
    orig_generate = GeminiProvider.generate
    
    mock_doc_id = str(uuid.uuid4())
    
    def mock_generate(self, prompt, system_prompt=""):
        if "Resume upload" in prompt or "CUSTOM_QUESTION" in prompt:
            return mock_doc_id
        return orig_generate(self, prompt, system_prompt)

    with unittest.mock.patch.object(
        BrowserSecurityPolicy, "validate_navigation_url", side_effect=validate
    ), unittest.mock.patch.object(
        MinioStorageProvider, "download_file", new=download_file
    ), unittest.mock.patch.object(
        GeminiProvider, "generate", new=mock_generate
    ):
        yield mock_doc_id
def seed_db_for_test(db, user_id, job_url, mock_doc_id, mode="HAPPY_PATH"):
    user = User(id=user_id, email=f"{uuid.uuid4()}@test.com", hashed_password="x", is_active=True)
    db.add(user)
    db.flush()
    
    profile = Profile(user_id=user_id, full_name="Alex Demo", phone="+91 90000 00000", location="Bhopal, India", summary="ML Engineer")
    db.add(profile)
    
    facts = {
        "first_name": "Alex",
        "last_name": "Demo",
        "email": "alex.demo@example.com",
        "phone": "+91 90000 00000",
        "city": "Bhopal",
        "country": "India",
        "preferred_location": "Gurugram",
        "degree": "Masters",
        "university": "Stanford",
        "grad_year": "2026",
        "cgpa": "3.9",
        "years_of_experience": "2",
        "current_company": "Google",
        "job_title": "ML Engineer",
        "responsibilities": "Developed large language models",
        "primary_language": "Python",
        "ml_frameworks": "PyTorch, TensorFlow",
        "llm_exp": "3 years",
        "rag_exp": "2 years",
        "has_cloud": "Yes",
        "cloud_platform": "GCP",
        "cloud_exp": "3",
        "project_description": "I worked on an AI Job Application Agent using LangGraph."
    }
    
    if mode == "HAPPY_PATH":
        facts["office_snack"] = "Almonds"
        
    for k, v in facts.items():
        db.add(MemoryFact(user_id=user_id, category=k.upper(), key=k, value=v, is_current=True, confidence=1.0, provenance="USER_CONFIRMED", status="ACTIVE", trust_level="HIGH"))
        
    # Also add the resume as a MemoryFact so decision_engine can find it
    db.add(MemoryFact(user_id=user_id, category="RESUME", key="resume", value=mock_doc_id, is_current=True, confidence=1.0, provenance="USER_CONFIRMED", status="ACTIVE", trust_level="HIGH"))
        
    from packages.db.models.candidate import Document
    doc = Document(id=uuid.UUID(mock_doc_id), user_id=user_id, filename="resume.pdf", file_size=1024, storage_key=mock_doc_id, mime_type="application/pdf")
    db.add(doc)
    
    job = Job(source_job_id=str(uuid.uuid4()), title="ML Engineer", company="Golden ATS", description="Test job", url=job_url)
    db.add(job)
    db.flush()
    
    app = Application(user_id=user_id, job_id=job.id, status=ApplicationStatus.STARTED.value)
    db.add(app)
    db.commit()
    db.refresh(app)
    return app

@pytest.mark.asyncio
async def test_golden_ats_happy_path(ats_server, mock_security, db_session):
    user_id = uuid.uuid4()
    app = seed_db_for_test(db_session, user_id, "http://127.0.0.1:8085/jobs/ml-engineer", mock_security, mode="HAPPY_PATH")
    app_id = app.id
        
    initial_state = {
        "workflow_id": str(uuid.uuid4()),
        "application_id": str(app_id),
        "user_id": str(user_id),
        "status": ApplicationStatus.STARTED.value,
        "is_approved": False,
        "pre_submission_snapshot_id": None,
        "validation_errors": [],
    }

    import unittest.mock
    
    def mock_download(self, key, local_path):
        if key == mock_security:
            with open(local_path, "wb") as f:
                f.write(b"dummy pdf content")
            return True
        return False
            
    with unittest.mock.patch("packages.common.storage.MinioStorageProvider.__init__", return_value=None), \
         unittest.mock.patch("packages.common.storage.MinioStorageProvider.download_file", new=mock_download):
        workflow = build_application_graph().compile()
        
        # We must run the workflow until it reaches READY_FOR_REVIEW
        # We will use a while loop in case it pauses, but it shouldn't pause on HAPPY_PATH
        final_state = await workflow.ainvoke(initial_state, {"recursion_limit": 150})
    
    if final_state["current_url"] != "http://127.0.0.1:8085/apply/ml-engineer/review":
        import pprint
        pprint.pprint({k: v for k, v in final_state.items() if k not in ["page_model", "form_model", "pre_submission_snapshot_id", "execution_result"]})
        
    assert final_state["status"] == ApplicationStatus.READY_FOR_REVIEW.value
    assert final_state["pre_submission_snapshot_id"] is not None
    assert final_state["current_url"] == "http://127.0.0.1:8085/apply/ml-engineer/review"
    
    from packages.browser.manager import BrowserManager
    manager = BrowserManager()
    await manager.stop()
    manager._initialized = False

@pytest.mark.asyncio
async def test_golden_ats_hitl_path(ats_server, mock_security, db_session):
    user_id = uuid.uuid4()
    app = seed_db_for_test(db_session, user_id, "http://127.0.0.1:8085/jobs/ml-engineer", mock_security, mode="HITL")
    app_id = app.id
        
    initial_state = {
        "workflow_id": str(uuid.uuid4()),
        "application_id": str(app_id),
        "user_id": str(user_id),
        "status": ApplicationStatus.STARTED.value,
        "is_approved": False,
        "pre_submission_snapshot_id": None,
        "validation_errors": [],
    }

    workflow = build_application_graph().compile(debug=True)
    final_state = await workflow.ainvoke(initial_state, {"recursion_limit": 150})
    
    # Should block because 'office_snack' is required but not in memory
    assert final_state["status"] == ApplicationStatus.WAITING_FOR_USER.value
    # 'office_snack' or similar should be in waiting_field_ids
    assert final_state.get("waiting_field_ids")
    
    from packages.browser.manager import BrowserManager
    manager = BrowserManager()
    await manager.stop()
    manager._initialized = False
