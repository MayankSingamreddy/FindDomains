#!/usr/bin/env python3
import concurrent.futures
import threading
import time
import random
import requests
import argparse
from tqdm import tqdm
import os

# RDAP endpoint for .ai domains
RDAP_AI_ENDPOINT = 'https://rdap.identitydigital.services/rdap/domain/{}'

def is_domain_available(domain: str, timeout=10) -> bool:
    """Checks if a domain is available using RDAP."""
    tld = domain.split('.')[-1].lower()
    if tld != 'ai':
        # This script only checks .ai
        return False

    url = RDAP_AI_ENDPOINT.format(domain)

    try:
        # Add a User-Agent header
        headers = {
            'Accept': 'application/rdap+json, application/json',
            'User-Agent': 'Python RDAP Client (https://github.com/your-repo-or-name)' # Be polite
        }
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers)

        # Add a small delay to avoid rate limiting
        time.sleep(random.uniform(0.1, 0.3))

    except requests.exceptions.Timeout:
        tqdm.write(f"Timeout checking {domain}")
        return False # Treat timeout as unavailable
    except requests.exceptions.RequestException as e:
        tqdm.write(f"Network error checking {domain}: {e}")
        return False # Network hiccup ⇒ assume unavailable

    # Identity-Digital (and others) often return 200 even for available domains,
    # using an errorCode in the JSON body.
    if r.status_code == 404:
        return True # Standard RDAP: 404 means AVAILABLE
    if r.status_code == 200:
        try:
            j = r.json()
            # Check for specific error codes indicating non-existence/availability
            if isinstance(j, dict) and j.get('errorCode') in (400, 404):
                 # Example: {"errorCode":404,"title":"Domain Not Found","description":["Domain not found"]}
                return True # JSON-level not-found means AVAILABLE
        except ValueError:
            # Response wasn't valid JSON, treat as registered/unavailable
            tqdm.write(f"Non-JSON 200 response for {domain}")
            pass
    elif r.status_code == 429:
        tqdm.write(f"Rate limited checking {domain}. Consider reducing workers or adding delays.")
        # Optionally, implement retry logic here or treat as unavailable for now
        return False
    # Log unexpected status codes
    elif r.status_code not in [200, 404]:
         tqdm.write(f"Unexpected status code {r.status_code} for {domain}")


    # Any other case means the domain is likely registered or there's an issue
    return False

def check_domain_wrapper(domain):
    """Wrapper for concurrent execution and error handling."""
    try:
        available = is_domain_available(domain)
        return domain, available
    except Exception as e:
        # Log unexpected errors within the check function itself
        tqdm.write(f"Error in check_domain_wrapper for {domain}: {e}")
        return domain, False # Mark as unavailable on error

def load_words(dictionary_path):
    """Loads words from the specified dictionary file."""
    words = set()
    try:
        with open(dictionary_path, 'r') as f:
            for line in f:
                # Basic cleaning: lower, strip whitespace, check if alphabetic
                word = line.strip().lower()
                if word.isalpha():
                    words.add(word)
    except FileNotFoundError:
        print(f"Error: Dictionary file not found at {dictionary_path}")
        return None
    except IOError as e:
        print(f"Error reading dictionary file {dictionary_path}: {e}")
        return None
    return list(words)

def main():
    parser = argparse.ArgumentParser(description="Check availability of 5 or 6 letter .ai domains from a dictionary.")
    parser.add_argument(
        "-d", "--dictionary",
        default="/usr/share/dict/words",
        help="Path to the dictionary file (default: /usr/share/dict/words)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=10,
        help="Number of parallel workers (default: 10)"
    )
    parser.add_argument(
        "-o", "--output",
        default="available_ai_domains.txt",
        help="Output file for available domains (default: available_ai_domains.txt)"
    )
    args = parser.parse_args()

    print(f"Loading words from: {args.dictionary}")
    all_words = load_words(args.dictionary)

    if all_words is None:
        return # Error message already printed in load_words

    print(f"Loaded {len(all_words)} unique words.")

    # Filter for 5 or 6 letter words
    filtered_words = [word for word in all_words if 4 == len(word)]
    print(f"Found {len(filtered_words)} words with 5 or 6 letters.")

    if not filtered_words:
        print("No 5 or 6 letter words found in the dictionary. Exiting.")
        return

    # Generate .ai domain names
    domains_to_check = [f"{word}.ai" for word in filtered_words]

    print(f"Checking {len(domains_to_check)} potential .ai domains with {args.workers} workers...")

    available_domains = []
    lock = threading.Lock() # For thread-safe list appends

    # Process domains in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_domain = {executor.submit(check_domain_wrapper, domain): domain for domain in domains_to_check}

        for future in tqdm(concurrent.futures.as_completed(future_to_domain),
                           total=len(domains_to_check),
                           desc="Checking domains",
                           unit="domain"):
            try:
                # Increased result timeout slightly
                domain, available = future.result(timeout=30)
                if available:
                    with lock:
                        available_domains.append(domain)
                        # Make available notification clearer in logs
                        tqdm.write(f"✨🟢 AVAILABLE: {domain} 🟢✨")
            except concurrent.futures.TimeoutError:
                domain = future_to_domain[future]
                tqdm.write(f"⚠️ CHECK TIMEOUT for {domain} (future.result) - skipping")
            except Exception as e:
                domain = future_to_domain[future]
                tqdm.write(f"Error processing result for {domain}: {str(e)}")

    # Sort results
    available_domains.sort()

    # --- Output ---
    print("\n--- Summary ---")
    print(f"Checked {len(domains_to_check)} potential domains.")
    print(f"Found {len(available_domains)} available .ai domains:")

    if available_domains:
        for domain in available_domains:
            print(f"- {domain}")
    else:
        print("None found.")

    # Write to file
    print(f"\nWriting available domains to {args.output}...")
    try:
        with open(args.output, "w") as f:
            f.write(f"Checked {len(domains_to_check)} potential .ai domains (5-6 letters) from {args.dictionary}.\n")
            f.write(f"Found {len(available_domains)} available domains.\n\n")
            if available_domains:
                for domain in available_domains:
                    f.write(f"{domain}\n")
            else:
                f.write("None\n")
        print(f"Successfully wrote results to {args.output}")
    except IOError as e:
        print(f"Error writing results to file {args.output}: {e}")

if __name__ == "__main__":
    main() 