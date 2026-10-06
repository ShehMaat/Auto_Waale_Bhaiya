import os
import subprocess
import sys
import time

import pytest
import requests


def run_cmd(cmd):
    print(f"Executing: {cmd}")
    is_shell = isinstance(cmd, str)
    res = subprocess.run(cmd, shell=is_shell, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0:
        print(f"Error output stdout: {res.stdout}")
        print(f"Error output stderr: {res.stderr}")
        raise Exception(f"Command failed: {cmd}\nStdout: {res.stdout}\nStderr: {res.stderr}")
    return res

@pytest.fixture(scope="module", autouse=True)
def setup_infrastructure():
    # Make sure we're in the right directory
    compose_file = "deployment/docker-compose.prod.yml"

    # Tear down existing
    subprocess.run(f"docker compose -f {compose_file} down -v", shell=True)

    # Reset upstream to blue
    os.makedirs("deployment/nginx/conf.d", exist_ok=True)
    with open("deployment/nginx/conf.d/upstream.conf", "w") as f:
        f.write("upstream api_upstream {\n    server api_blue:8000;\n}\nupstream frontend_upstream {\n    server frontend_blue:3000;\n}\n")

    # Start basic infrastructure and Release N (Blue)
    run_cmd(f"docker compose -f {compose_file} up -d --build nginx db redis api_blue celery_worker_blue browser_worker_blue frontend_blue")

    # Wait for API to become healthy
    retries = 30
    while retries > 0:
        try:
            r = requests.get("http://localhost/ready", timeout=2)
            if r.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
        retries -= 1

    yield

    # Teardown
    subprocess.run(f"docker compose -f {compose_file} down -v", shell=True)

def test_actual_production_runtime_deployment():
    compose_file = "deployment/docker-compose.prod.yml"

    # 1. Verify Release N is healthy
    ps_output = run_cmd(f"docker compose -f {compose_file} ps").stdout
    assert "api_blue" in ps_output
    assert "nginx" in ps_output
    assert "frontend_blue" in ps_output

    # 2. Check traffic routing initially
    # For testing, we would verify the X-Release-Id header or similar, but /health on NGINX returns 200 OK directly.
    # We can check upstream conf
    with open("deployment/nginx/conf.d/upstream.conf", "r") as f:
        conf = f.read()
        assert "api_blue" in conf
        assert "frontend_blue" in conf

    # Check NGINX routing rules
    r = requests.get("http://localhost/", timeout=5)
    assert r.status_code == 200
    assert "html" in r.text.lower()

    # Check API routing rules - positively prove request reaches FastAPI
    r = requests.get("http://localhost/api/v1/auth/login", timeout=5)
    # FastAPI returns 405 Method Not Allowed for a GET to a POST route
    assert r.status_code == 405
    assert "detail" in r.json()
    assert r.json()["detail"] == "Method Not Allowed"

    r = requests.get("http://localhost/health", timeout=5)
    assert r.status_code == 200
    assert r.text == "OK"

    r = requests.get("http://localhost/ready", timeout=5)
    assert r.status_code == 200
    assert "ready" in r.json().get("status", "")

    # Check Frontend configuration
    ps_output_blue = run_cmd(f"docker compose -f {compose_file} ps").stdout
    assert "frontend_blue" in ps_output_blue

    res = run_cmd("docker exec ai_job_agent_frontend_blue sh -c \"grep -r 'http://localhost:8000/api/v1' .next/ || echo 'NOT_FOUND'\"")
    assert "NOT_FOUND" in res.stdout

    # 3. Start deployment Script (N+1)
    # We use subprocess to run the python script deploy.py
    deploy_output = run_cmd([sys.executable, "deployment/scripts/deploy.py"]).stdout

    # 4. Verify N+1 is running and N is terminated
    ps_output_after = run_cmd(f"docker compose -f {compose_file} ps").stdout
    assert "api_green" in ps_output_after
    assert "frontend_green" in ps_output_after
    assert "api_blue" not in ps_output_after

    # Verify NGINX traffic transition
    with open("deployment/nginx/conf.d/upstream.conf", "r") as f:
        conf = f.read()
        assert "api_green" in conf
        assert "frontend_green" in conf

    # Verify rollback works
    run_cmd([sys.executable, "deployment/scripts/rollback.py"])

    with open("deployment/nginx/conf.d/upstream.conf", "r") as f:
        conf = f.read()
        assert "api_blue" in conf
        assert "frontend_blue" in conf

def test_frontend_readiness_prevents_switch():
    compose_file = "deployment/docker-compose.prod.yml"
    with open(compose_file, "r") as f:
        original_compose = f.read()

    try:
        # inject a breaking command into frontend_green so it fails healthchecks
        broken_compose = original_compose.replace(
            "container_name: ai_job_agent_frontend_green",
            "container_name: ai_job_agent_frontend_green\n    command: [\"sleep\", \"1\"]"
        )
        with open(compose_file, "w") as f:
            f.write(broken_compose)

        # Run deploy, expect it to fail and exit 1
        env = os.environ.copy()
        env["DEPLOY_RETRIES"] = "5"
        res = subprocess.run([sys.executable, "deployment/scripts/deploy.py"], capture_output=True, text=True, env=env)

        assert res.returncode != 0

        # Verify NGINX still points to blue and wasn't changed to green
        with open("deployment/nginx/conf.d/upstream.conf", "r") as f:
            conf = f.read()
            assert "api_blue" in conf
            assert "frontend_blue" in conf
            assert "api_green" not in conf
    finally:
        with open(compose_file, "w") as f:
            f.write(original_compose)
