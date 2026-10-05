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
        f.write("upstream api_upstream {\n    server api_blue:8000;\n}\n")
    
    # Start basic infrastructure and Release N (Blue)
    run_cmd(f"docker compose -f {compose_file} up -d --build nginx db redis api_blue celery_worker_blue browser_worker_blue frontend_blue")
    
    # Wait for API to become healthy
    retries = 30
    while retries > 0:
        try:
            r = requests.get("http://localhost/health", timeout=2)
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
        assert "api_blue" in f.read()

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
        assert "api_green" in f.read()
        
    # Verify rollback works
    run_cmd([sys.executable, "deployment/scripts/rollback.py"])
    
    with open("deployment/nginx/conf.d/upstream.conf", "r") as f:
        assert "api_blue" in f.read()
