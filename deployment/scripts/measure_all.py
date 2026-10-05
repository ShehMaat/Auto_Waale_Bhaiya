import os
import subprocess
import sys
import time


def run_cmd(cmd):
    print(f"Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error output: {res.stderr}")
    return res

def wait_for_healthy(container_name):
    print(f"Waiting for {container_name} to be healthy...")
    retries = 30
    while retries > 0:
        res = subprocess.run(f"docker inspect --format='{{{{json .State.Health.Status}}}}' {container_name}", shell=True, capture_output=True, text=True)
        if "healthy" in res.stdout:
            print(f"{container_name} is healthy!")
            return True
        time.sleep(2)
        retries -= 1
    print(f"{container_name} did not become healthy.")
    return False

def measure(mode):
    print(f"=== MEASURING {mode} ===")
    subprocess.run([sys.executable, "deployment/scripts/measure_resources.py", mode])

def main():
    compose_file = "deployment/docker-compose.prod.yml"
    
    # Reset upstream to blue
    os.makedirs("deployment/nginx/conf.d", exist_ok=True)
    with open("deployment/nginx/conf.d/upstream.conf", "w") as f:
        f.write("upstream api_upstream {\n    server api_blue:8000;\n}\n")
    
    # Start BLUE
    print("Starting BLUE environment...")
    run_cmd(f"docker compose -f {compose_file} up -d nginx db redis api_blue celery_worker_blue browser_worker_blue")
    wait_for_healthy("ai_job_agent_api_blue")
    time.sleep(5) # Let things settle
    measure("BLUE_ONLY")
    
    # Start GREEN
    print("\nStarting GREEN environment...")
    run_cmd(f"docker compose -f {compose_file} up -d api_green celery_worker_green browser_worker_green")
    wait_for_healthy("ai_job_agent_api_green")
    
    # Swap traffic
    with open("deployment/nginx/conf.d/upstream.conf", "w") as f:
        f.write("upstream api_upstream {\n    server api_green:8000;\n}\n")
    run_cmd("docker exec ai_job_agent_nginx nginx -s reload")
    
    time.sleep(5)
    measure("BLUE_PLUS_GREEN")
    
    print("\n=== RUNNING BENCHMARK DURING OVERLAP ===")
    subprocess.run([sys.executable, "deployment/scripts/benchmark.py", "100", "500"])
    
    print("\nDraining BLUE environment...")
    run_cmd(f"docker compose -f {compose_file} stop -t 10 api_blue celery_worker_blue browser_worker_blue")
    
    time.sleep(5)
    measure("GREEN_ONLY")

if __name__ == "__main__":
    main()
