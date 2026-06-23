# scripts/import_opening_dirs.py
import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def post_json(url, payload):
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def get_json(url):
    with urlopen(url, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_job(server, job_id, interval):
    while True:
        job = get_json(f"{server}/api/openings/import-directory/jobs/{job_id}")
        status = job.get("status")
        print(f"  job {job_id}: {status}")

        if status in {"completed", "failed", "cancelled", "canceled"}:
            return job

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--source", default="professional")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    base = Path(args.base_dir)
    dirs = sorted([p for p in base.iterdir() if p.is_dir()])

    if args.end is not None:
        dirs = dirs[args.start:args.end]
    else:
        dirs = dirs[args.start:]

    print(f"target dirs: {len(dirs)}")

    for index, directory in enumerate(dirs, start=args.start):
        print(f"[{index}] import: {directory}")

        try:
            payload = post_json(
                f"{args.server}/api/openings/import-directory",
                {
                    "path": str(directory),
                    "recursive": args.recursive,
                    "source": args.source,
                    "async": True,
                },
            )

            job_id = payload.get("id")
            if not job_id:
                raise RuntimeError(f"job id not found: {payload}")

            result = wait_job(args.server, job_id, args.interval)

            if result.get("status") != "completed":
                raise RuntimeError(result)

        except (HTTPError, URLError, RuntimeError) as e:
            print(f"ERROR: {directory}: {e}")
            if not args.continue_on_error:
                raise

    print("done")


if __name__ == "__main__":
    main()
