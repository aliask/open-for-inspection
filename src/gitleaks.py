from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import logging

if os.getenv("LAMBDA_TASK_ROOT"):
    import boto3

    os.environ["PATH"] = os.environ["LAMBDA_TASK_ROOT"] + "/bin:" + os.environ["PATH"]
from git import Repo

from util import slugify

logger = logging.getLogger()
logger.setLevel("INFO")


def run_gitleaks(clone_dir: str, report_path: str) -> str:
    result = subprocess.run(
        [
            "gitleaks",
            "--no-color",
            "--no-banner",
            "detect",
            "-f",
            "json",
            "-r",
            report_path,
            "--source",
            clone_dir,
        ],
        text=True,
        capture_output=True,
    )
    return result.stderr


def transform_report(report_path, repo_url):
    with open(report_path, "r") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Report should be an array of results")
    for obj in data:
        if not isinstance(obj, dict):
            raise ValueError("Report should be an array of results")
        obj["Repository"] = repo_url
    with open(report_path, "w") as file:
        json.dump(data, file, indent=4)


def checkout_and_scan(repo_url: str, report_path: str) -> str:
    clone_dir = tempfile.mkdtemp()
    results = ""
    try:
        logger.info(f"Cloning {repo_url}...")
        Repo.clone_from(repo_url, clone_dir)
        logger.info(f"Repository cloned to {clone_dir}")
        results = run_gitleaks(clone_dir, report_path=report_path)
        transform_report(report_path=report_path, repo_url=repo_url)
    finally:
        shutil.rmtree(clone_dir)
    return results


def lambda_handler(event, context):
    repo_url = event.get("repo_url")
    if not repo_url:
        return {
            "statusCode": 400,
            "body": "Error: repo_url not provided in the event",
        }

    try:
        out_file = slugify(urlparse(repo_url).path) + ".json"
        report_path = Path("/tmp") / out_file
        log = checkout_and_scan(repo_url=repo_url, report_path=report_path)

        s3 = boto3.client("s3")
        bucket = os.environ["DESTINATION_BUCKET"]
        datestamp = datetime.now().date().isoformat()
        s3.upload_file(report_path, bucket, f"{datestamp}/{out_file}")
        logger.info(
            f"Upload Successful: {report_path} to s3://{bucket}/{datestamp}/{out_file}"
        )
        return {"statusCode": 200, "body": json.dumps(log)}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps(e, default=str)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_url", type=str)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    if args.output:
        out_file = args.output
        out_dir = Path(out_file).parent
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        datestamp = datetime.now().date().isoformat()
        out_dir = Path(f"results/{datestamp}").absolute().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        repo_name = urlparse(args.repo_url).path
        out_file = str(out_dir / f"{slugify(repo_name)}.json")

    out = checkout_and_scan(args.repo_url, out_file)
    logger.info(out)
