import os
import subprocess


def run_cmd(cmd):
    print(f"Executing: {cmd}")
    return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

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
    return "api_blue"

def main():
    current_upstream = get_current_upstream()
    if current_upstream == "api_blue":
        broken_env = "blue"
        safe_env = "green"
    else:
        broken_env = "green"
        safe_env = "blue"
        
    print(f"Rolling back to {safe_env} (removing {broken_env})")
    
    # 1. Update NGINX to safe env
    os.makedirs("deployment/nginx/conf.d", exist_ok=True)
    with open("deployment/nginx/conf.d/upstream.conf", "w") as f:
        f.write(f"upstream api_upstream {{\n    server api_{safe_env}:8000;\n}}\n")
        
    try:
        run_cmd("docker exec ai_job_agent_nginx nginx -s reload")
    except Exception:
        print("Warning: NGINX reload failed, maybe container is not running.")
        
    # 2. Stop broken env
    compose_file = "deployment/docker-compose.prod.yml"
    try:
        run_cmd(f"docker compose -f {compose_file} stop frontend_{broken_env} api_{broken_env} celery_worker_{broken_env} browser_worker_{broken_env}")
        run_cmd(f"docker compose -f {compose_file} rm -f frontend_{broken_env} api_{broken_env} celery_worker_{broken_env} browser_worker_{broken_env}")
    except Exception as e:
        print(f"Warning: Failed to stop broken environment: {e}")
        
    print("Rollback complete.")

if __name__ == "__main__":
    main()
