import subprocess
import sys


def get_stats():
    # Get stats for all running containers
    cmd = "docker stats --no-stream --format \"{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}\""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        return {}
    stats = {}
    for line in res.stdout.strip().split('\n'):
        if not line: continue
        parts = line.split('|')
        name = parts[0]
        cpu = parts[1]
        mem = parts[2].split('/')[0].strip() # e.g. "1.5GiB" or "500MiB"
        stats[name] = {"cpu": cpu, "mem": mem}
    return stats

def convert_to_mib(mem_str):
    if "GiB" in mem_str or "GB" in mem_str:
        return float(mem_str.replace("GiB", "").replace("GB", "").strip()) * 1024
    if "MiB" in mem_str or "MB" in mem_str:
        return float(mem_str.replace("MiB", "").replace("MB", "").strip())
    if "KiB" in mem_str or "KB" in mem_str:
        return float(mem_str.replace("KiB", "").replace("KB", "").strip()) / 1024
    if "B" in mem_str:
        return float(mem_str.replace("B", "").strip()) / (1024 * 1024)
    return 0.0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    stats = get_stats()
    total_mib = 0.0
    
    print(f"--- RESOURCES: {mode} ---")
    for name, data in stats.items():
        if "ai_job_agent_" in name:
            mem_mib = convert_to_mib(data["mem"])
            total_mib += mem_mib
            print(f"{name}: CPU {data['cpu']}, MEM {data['mem']} ({mem_mib:.2f} MiB)")
            
    print(f"TOTAL: {total_mib:.2f} MiB")
