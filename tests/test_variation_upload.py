"""
Small script to try NCBI Variation API VCF upload / rsID annotation endpoint.
It will try a couple of plausible endpoints, POST the VCF, and poll for results.

Usage:
  python tests/test_variation_upload.py /path/to/input.vcf

Notes:
- NCBI Variation API docs: https://api.ncbi.nlm.nih.gov/variation/v0
- Endpoints and response shapes can vary; this script prints raw responses and is defensive.
"""
import sys
import time
import requests
from pathlib import Path

# Candidate endpoints to try (defensive list based on docs variations)
ENDPOINTS = [
    "https://api.ncbi.nlm.nih.gov/variation/v0/vcf/file",
    "https://api.ncbi.nlm.nih.gov/variation/v0/vcf/file_set_rsids",
    "https://api.ncbi.nlm.nih.gov/variation/v0/vcf/file_set/rsids",
]

TIMEOUT = 30
POLL_INTERVAL = 3


def try_upload(endpoint, vcf_path):
    print(f"Trying endpoint: {endpoint}")
    try:
        with open(vcf_path, 'rb') as fh:
            files = { 'file': (Path(vcf_path).name, fh, 'text/vcf') }
            # Some endpoints expect multipart/form-data with a file field
            resp = requests.post(endpoint, files=files, timeout=TIMEOUT)

        print(f"  -> status: {resp.status_code}")
        # Print response headers for clues (Location etc.)
        for k in ('Location', 'location', 'Content-Type'):
            if k in resp.headers:
                print(f"  header {k}: {resp.headers[k]}")

        # Print JSON or text body (truncated)
        try:
            j = resp.json()
            print("  json:", j)
        except Exception:
            text = resp.text.strip()
            print("  body:", (text[:1000] + '...') if len(text) > 1000 else text)

        return resp
    except Exception as e:
        print(f"  Error posting to {endpoint}: {e}")
        return None


def poll_status(url, timeout=300):
    print(f"Polling status: {url}")
    start = time.time()
    while True:
        try:
            r = requests.get(url, timeout=TIMEOUT)
            print(f"  poll status: {r.status_code}")
            try:
                j = r.json()
                print("  json:", j)
            except Exception:
                print("  body:", r.text[:1000])

            if r.status_code in (200, 201):
                return r
            # If 202 Accepted, keep polling
            if time.time() - start > timeout:
                print("  Timeout waiting for job result")
                return None
        except Exception as e:
            print(f"  Poll error: {e}")
        time.sleep(POLL_INTERVAL)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_variation_upload.py /path/to/input.vcf")
        sys.exit(1)

    vcf_path = sys.argv[1]
    if not Path(vcf_path).exists():
        print("VCF file not found:", vcf_path)
        sys.exit(1)

    for ep in ENDPOINTS:
        resp = try_upload(ep, vcf_path)
        if not resp:
            continue

        # If endpoint returned a Location header, poll it
        loc = resp.headers.get('Location') or resp.headers.get('location')
        if loc:
            print("Found Location header, will poll")
            final = poll_status(loc)
            if final:
                print("Final response:", final.status_code)
                try:
                    print(final.json())
                except Exception:
                    print(final.text[:2000])
                return
            else:
                print("Polling failed or timed out")
                continue

        # Some APIs return a JSON job id / status object
        try:
            j = resp.json()
        except Exception:
            j = None

        if j:
            # Look for common fields: job, status_url, results_url, id
            for key in ('status', 'job', 'job_id', 'status_url', 'results_url', 'id', 'task'):
                if key in j:
                    print(f"Found key '{key}' in response -> {j[key]}")
                    val = j[key]
                    # If it's a URL, poll it
                    if isinstance(val, str) and val.startswith('http'):
                        final = poll_status(val)
                        if final:
                            print('Done')
                            return
        
        # If response code 200 and contains annotated VCF, print sample
        if resp.status_code == 200:
            print("200 OK - response body (first 2000 chars):")
            print(resp.text[:2000])
            return

    print("All endpoints tried, nothing returned a usable job/result.")


if __name__ == '__main__':
    main()
