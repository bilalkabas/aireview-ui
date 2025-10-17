import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def download_pdf(remote_url, local_url):
    # Create directory structure for the local file if it doesn't exist
    local_dir = os.path.dirname(local_url)
    if local_dir:
        os.makedirs(local_dir, exist_ok=True)

    # Check if already downloaded
    if os.path.exists(local_url):
        return (local_url, "exists")

    # Download PDF
    try:
        req = urllib.request.Request(
            remote_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            pdf_content = response.read()

        # Save to file
        with open(local_url, 'wb') as f:
            f.write(pdf_content)

        return (local_url, "downloaded")

    except Exception as e:
        print(f"    ✗ Error downloading {os.path.basename(local_url)}: {e}")
        return (local_url, "failed")


def download_pdfs_batch(remote_urls, local_urls, max_workers=5):
    results = []
    total = len(remote_urls)

    if total == 0:
        return results

    downloaded = 0
    skipped = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_info = {
            executor.submit(download_pdf, remote_url, local_url): (remote_url, local_url)
            for remote_url, local_url in zip(remote_urls, local_urls)
        }

        # Process completed downloads with progress bar
        with tqdm(total=total, desc="Downloading PDFs", unit="file") as pbar:
            for future in as_completed(future_to_info):
                local_path, status = future.result()
                results.append(local_path)

                if status == "downloaded":
                    downloaded += 1
                elif status == "exists":
                    skipped += 1
                elif status == "failed":
                    failed += 1

                pbar.update(1)
                pbar.set_postfix({"downloaded": downloaded, "skipped": skipped, "failed": failed})

    print(f"✅ Download complete: {downloaded} new, {skipped} existing, {failed} failed")
    return results


if __name__ == "__main__":
    import dotenv
    import json

    # Load environment variables
    # When run from ./run script, WEBAPP_ENV_FILE will be set
    env_file = os.getenv("WEBAPP_ENV_FILE")
    if env_file and os.path.exists(env_file):
        dotenv.load_dotenv(env_file)
    else:
        dotenv.load_dotenv()

    # Get paths from environment (these are absolute paths set by ./run script)
    json_path = os.getenv("WEBAPP_REVIEWS_JSON")
    project_root = os.getenv("WEBAPP_PROJECT_ROOT", os.path.dirname(os.path.dirname(__file__)))

    if not json_path:
        print("Error: WEBAPP_REVIEWS_JSON environment variable not set")
        exit(1)

    if not os.path.exists(json_path):
        print(f"Error: Reviews JSON file not found at {json_path}")
        exit(1)

    # Get paper URLs
    remote_urls = []
    local_urls = []
    with open(json_path, "r") as f:
        data = json.load(f)
        for item in data:
            if "remote_url" in item and "url" in item:
                remote_urls.append(item["remote_url"])
                # Resolve local path relative to project root
                local_path = item["url"]
                if not os.path.isabs(local_path):
                    local_path = os.path.join(project_root, local_path)
                local_urls.append(local_path)

    if len(remote_urls) == 0:
        print("No PDFs to download (no items with 'remote_url' and 'url' found)")
        exit(0)

    pdf_paths = download_pdfs_batch(remote_urls, local_urls, max_workers=5)
