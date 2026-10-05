import asyncio
import sys
import time

import aiohttp


async def fetch(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            return response.status
    except Exception:
        return 500

async def bound_fetch(sem, session, url):
    async with sem:
        return await fetch(session, url)

async def main():
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    requests_count = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    url = "http://localhost/ready"
    
    sem = asyncio.Semaphore(concurrency)
    
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.ensure_future(bound_fetch(sem, session, url)) for _ in range(requests_count)]
        responses = await asyncio.gather(*tasks)
    end_time = time.time()
    
    success = sum(1 for r in responses if r == 200)
    failed = requests_count - success
    duration = end_time - start_time
    req_per_sec = requests_count / duration if duration > 0 else 0
    
    print(f"Concurrency: {concurrency}")
    print(f"Total Requests: {requests_count}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"Req/Sec: {req_per_sec:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
