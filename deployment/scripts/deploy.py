import os
import subprocess
import sys
import time


def run_cmd(cmd):
    print(f"Executing: {cmd}")
    try:
        return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except subprocess.CalledProcessError as e:
        print(f"Command failed with {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def get_current_upstream():
    try:
        with open("deployment/nginx/conf.d/upstream.conf", "r") as f:
            content = f.read()
            if "api_blue" in content:
                return "api_blue"
            elif "api_green" in content:
                return "api_green"
    except FileNotFoundError:
        pass
    return "api_blue" # Default fallback

def main():
    current_upstream = get_current_upstream()
    if current_upstream == "api_blue":
        next_env = "green"
        old_env = "blue"
    else:
        next_env = "blue"
        old_env = "green"
        
    print(f"Current environment: {old_env}. Deploying to: {next_env}")
    
    # 1. Start N+1 containers
    compose_file = "deployment/docker-compose.prod.yml"
    print("Starting next release containers...")
    run_cmd(f"docker compose -f {compose_file} up -d --build frontend_{next_env} api_{next_env} celery_worker_{next_env} browser_worker_{next_env}")
    
    # 2. Wait for N+1 readiness
    print(f"Waiting for api_{next_env} to become healthy...")
    retries = 60
    healthy = False
    while retries > 0:
        try:
            inspect_cmd = ["docker", "inspect", "--format={{json .State.Health.Status}}", f"ai_job_agent_api_{next_env}"]
            res = subprocess.run(inspect_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            status = res.stdout.strip().strip('"')
            if status == "healthy":
                healthy = True
                break
        except Exception:
            pass
        time.sleep(2)
        retries -= 1
        
    if not healthy:
        print(f"api_{next_env} failed to become healthy. Rolling back.")
        run_cmd(f"docker compose -f {compose_file} stop frontend_{next_env} api_{next_env} celery_worker_{next_env} browser_worker_{next_env}")
        sys.exit(1)
        
    print(f"api_{next_env} is healthy. Swapping NGINX traffic.")
    
    # 3. Update NGINX
    os.makedirs("deployment/nginx/conf.d", exist_ok=True)
    with open("deployment/nginx/conf.d/upstream.conf", "w") as f:
        f.write(f"upstream api_upstream {{\n    server api_{next_env}:8000;\n}}\n")
        
    run_cmd("docker exec ai_job_agent_nginx nginx -s reload")
    print(f"Traffic switched to {next_env}.")
    
    print("\n=== MEASURING BLUE+GREEN OVERLAP ===")
    subprocess.run([sys.executable, "deployment/scripts/measure_resources.py", "BLUE_PLUS_GREEN"], check=False)
    
    print("\n=== RUNNING BENCHMARK DURING OVERLAP ===")
    subprocess.run([sys.executable, "deployment/scripts/benchmark.py", "100", "500"], check=False)
    
    # 4. Drain old release
    print(f"Draining old release: {old_env}...")
    run_cmd(f"docker compose -f {compose_file} stop -t 30 frontend_{old_env} api_{old_env} celery_worker_{old_env} browser_worker_{old_env}")
    run_cmd(f"docker compose -f {compose_file} rm -f frontend_{old_env} api_{old_env} celery_worker_{old_env} browser_worker_{old_env}")
    
    print("Deployment complete.")

if __name__ == "__main__":
    main()
