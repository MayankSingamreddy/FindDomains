#!/usr/bin/env python3
import subprocess
import json
import time
import random
from tqdm import tqdm
import concurrent.futures
import threading
import os
import requests  # use the library instead of spawning curl

# Map TLDs to known RDAP bases or fall back to IANA bootstrap
RDAP_ENDPOINTS = {
    'com': 'https://rdap.verisign.com/com/v1/domain/{}',
    'ai' : 'https://rdap.identitydigital.services/rdap/domain/{}',
    'dev': 'https://rdap.googleapis.com/rdap/v1/domain/{}',
}

def is_domain_available(domain: str, timeout=10) -> bool:
    tld = domain.split('.')[-1].lower()

    # Resolve RDAP URL
    if tld in RDAP_ENDPOINTS:
        url = RDAP_ENDPOINTS[tld].format(domain)
    else:                              # last-resort: IANA bootstrap
        url = f'https://rdap.iana.org/domain/{domain}'

    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True,
                         headers={'Accept': 'application/rdap+json, application/json'})
    except requests.exceptions.RequestException:
        return False  # network hiccup ⇒ assume unavailable

    # Identity-Digital (and a few other registries) always return 200,
    # so we must inspect the body for errorCode 4xx.
    if r.status_code == 404:
        return True # 404 means AVAILABLE (reverted based on testing available .dev domains)
    if r.status_code == 200:
        try:
            j = r.json()
            if isinstance(j, dict) and j.get('errorCode') in (400, 404):
                return True            # JSON-level not-found
        except ValueError:
            pass                       # not JSON → treat as registered
    return False                       # anything else → assume taken

# Function to check a domain with timeout handling for the overall check
def check_domain(domain):
    try:
        available = is_domain_available(domain)
        return domain, available
    except Exception as e:
        # Log the error and mark as unavailable
        tqdm.write(f"Error in check_domain wrapper for {domain}: {e}")
        return domain, False

# --- List of Base Names to Check ---
# Replace this list with the names you want to check
base_names_to_check = [
    "soil",
]

# Generate the full list of domains (.com and .ai versions)
domains_to_check = []
prefixes = ["", "try", "get", "use", "my", "the"]
tlds = ["com", "ai", "dev"]

for name in base_names_to_check:
    if name and isinstance(name, str): # Basic validation
        cleaned_name = name.strip().lower()
        if not cleaned_name: # Skip empty names after stripping
            continue
        for prefix in prefixes:
            # Construct base name with prefix (handle empty prefix)
            base_with_prefix = f"{prefix}{cleaned_name}" if prefix else cleaned_name
            for tld in tlds:
                domains_to_check.append(f"{base_with_prefix}.{tld}")

if not domains_to_check:
    print("No valid base names provided to generate domains. Exiting.")
    exit()

print(f"Checking {len(domains_to_check)} domain variations (.com and .ai) for {len(base_names_to_check)} base names.")

available_domains = []
# Lock for thread-safe updates to available_domains
lock = threading.Lock()

# Number of parallel workers (adjust based on network and RDAP server limits)
MAX_WORKERS = 10 # Start with a moderate number

# Process the domains in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Submit all tasks
    future_to_domain = {executor.submit(check_domain, domain): domain for domain in domains_to_check}

    # Process results as they complete
    for future in tqdm(concurrent.futures.as_completed(future_to_domain),
                       total=len(domains_to_check),
                       desc="Checking domains",
                       unit="domain"):
        try:
            # Set a timeout for getting the result from the future
            domain, available = future.result(timeout=25)
            with lock:
                if available:
                    available_domains.append(domain)
                    # Make the available notification more visible
                    tqdm.write(f"\n✨🟢 AVAILABLE: {domain} 🟢✨\n")
                # else:
                    # Optional: Log unavailable domains if needed for debugging
                    # tqdm.write(f"🔴 UNAVAILABLE: {domain}")
        except concurrent.futures.TimeoutError:
            # This timeout is for future.result(), not the curl command itself
            domain = future_to_domain[future]
            tqdm.write(f"⚠️ CHECK TIMEOUT: Task for {domain} exceeded timeout - skipping result")
        except Exception as e:
            domain = future_to_domain[future]
            # Log errors during result processing
            tqdm.write(f"Error processing result for {domain}: {str(e)}")

# Sort the available domains alphabetically for readability
available_domains.sort()

# Display summary of results
print("\n--- Summary of Available Domains ---")
if available_domains:
    for domain in available_domains:
        print(f"- {domain}")
else:
    print("No domains from the list were found to be available.")

print(f"\nTotal available domains found: {len(available_domains)}")
print(f"Total domain variations checked: {len(domains_to_check)}")

# Write results to file for reference
output_filename = "com_ai_available_domains.txt"
try:
    with open(output_filename, "w") as f:
        f.write(f"Checked {len(domains_to_check)} domain variations (.com and .ai) for {len(base_names_to_check)} base names.\n")
        f.write(f"Total available domains found: {len(available_domains)}\n\n")
        f.write("Available domains:\n")
        if available_domains:
            for domain in available_domains:
                f.write(f"{domain}\n")
        else:
            f.write("None\n")
    print(f"Results written to {output_filename}")
except IOError as e:
    print(f"Error writing results to file {output_filename}: {e}") 