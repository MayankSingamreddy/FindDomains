#!/usr/bin/env python3
import subprocess
import time
import random
from tqdm import tqdm
import concurrent.futures
import threading
from english_words import get_english_words_set
# import string

# Function to check if a domain is available via RDAP
def is_domain_available(domain):
    try:
        rdap_url = f"https://rdap.verisign.com/com/v1/domain/{domain}"
        
        result = subprocess.run(
            ["curl", "-s", "-I", rdap_url],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        status_line = result.stdout.split('\n')[0]
        
        if "404" in status_line:
            return True
        elif "200" in status_line:
            return False
        else:
            if "429" in status_line:
                time.sleep(2)
            return False
            
    except Exception:
        return False

# Function to check a domain with timeout
def check_domain(word):
    domain = f"{word}.com"
    try:
        available = is_domain_available(domain)
        return domain, available
    except Exception:
        return domain, False

# Get input from user for word length
# word_length = int(input("Enter the length of domain names to check (e.g. 5): "))
word_length = 6

# Get all lowercase English words of specified length
words_to_check = [word.lower() for word in get_english_words_set(['web2'], lower=True) if len(word) == word_length]

# Shuffle the list for more random checking
random.shuffle(words_to_check)

print(f"Found {len(words_to_check)} {word_length}-letter words to check")

available_domains = []
lock = threading.Lock()

# Number of parallel workers
MAX_WORKERS = 20

# Process the words in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_domain = {executor.submit(check_domain, word): word for word in words_to_check}
    
    for future in tqdm(concurrent.futures.as_completed(future_to_domain), 
                      total=len(words_to_check), 
                      desc="Checking domains", 
                      unit="word"):
        try:
            domain, available = future.result(timeout=20)
            with lock:
                if available:
                    available_domains.append(domain)
                    tqdm.write(f"\n🟢 AVAILABLE: {domain} 🟢\n")
                # else:
                #     tqdm.write(f"\n🔴 UNAVAILABLE: {domain} 🔴\n")
        except concurrent.futures.TimeoutError:
            word = future_to_domain[future]
            tqdm.write(f"⚠️ TIMEOUT: {word}.com - skipping")
        except Exception as e:
            word = future_to_domain[future]
            tqdm.write(f"Error processing {word}.com: {str(e)}")

# Display summary of results
print("\nSummary of Available Domains:")
for domain in available_domains:
    print(f"- {domain}")

print(f"\nTotal available domains found: {len(available_domains)}")
print(f"Total words checked: {len(words_to_check)}")

# Write results to file for reference
with open("available_domains.txt", "w") as f:
    f.write(f"Total available domains found: {len(available_domains)}\n")
    f.write(f"Total words checked: {len(words_to_check)}\n\n")
    f.write("Available domains:\n")
    for domain in available_domains:
        f.write(f"{domain}\n") 
        f.write(f"{domain}\n") 