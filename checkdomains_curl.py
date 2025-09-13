#!/usr/bin/env python3
import subprocess
import json
import time
import random
from tqdm import tqdm
import concurrent.futures
import threading
import os
# Get all 6-letter words from the English words set
import random
import string

# Function to check if a .com domain is available via RDAP
def is_domain_available(domain):
    # Use curl to check domain availability via RDAP
    try:
        # Determine RDAP endpoint based on TLD
        tld = domain.split('.')[-1].lower()
        if tld == 'com':
            rdap_url = f"https://rdap.verisign.com/com/v1/domain/{domain}"
        elif tld == 'ai':
            rdap_url = f"https://rdap.whois.ai/rdap/domain/{domain}"
        else:
            # Add more TLDs and their RDAP servers here if needed
            tqdm.write(f"Unsupported TLD: {tld} for domain {domain}. Assuming unavailable.")
            return False

        # Execute curl command and get response headers
        result = subprocess.run(
            ["curl", "-s", "-I", rdap_url],
            capture_output=True,
            text=True,
            timeout=10 # Increased timeout slightly
        )

        # Get the status code from the response
        status_line = result.stdout.split('\n')[0] if result.stdout else ""

        # Check if domain is available (404 means domain not found, thus available)
        if "404" in status_line:
            return True
        # 200 means domain exists, thus not available
        elif "200" in status_line:
            return False
        # Handle other responses
        else:
            # If we got a 429 (Too Many Requests), we should wait and consider unavailable
            if "429" in status_line:
                time.sleep(2)  # Wait longer for rate limiting
                return False
            # Log unexpected status for debugging
            # tqdm.write(f"Debug: Domain {domain} got status: {status_line.strip()} from {rdap_url}")
            # For any other ambiguous response, assume unavailable to be safe
            return False

    except subprocess.TimeoutExpired:
        tqdm.write(f"⚠️ TIMEOUT checking {domain} via {rdap_url}")
        return False # Assume unavailable on timeout
    except Exception as e:
        # Log the error more specifically
        tqdm.write(f"Error checking {domain} via RDAP: {e}")
        # For errors, assume the domain is not available to be safe
        return False

# Function to check a domain with timeout
def check_domain(domain):
    try:
        available = is_domain_available(domain)
        return domain, available
    except Exception as e:
        # Log the error and mark as unavailable
        tqdm.write(f"Error in check_domain wrapper for {domain}: {e}")
        return domain, False

# Function to load words from a dictionary file
# def load_words_from_file(filepath, length):
#     words = set()
#     if not os.path.exists(filepath):
#         print(f"Warning: Dictionary file not found at {filepath}")
#         return list(words)
#     try:
#         with open(filepath, 'r') as f:
#             for line in f:
#                 word = line.strip().lower()
#                 # Ensure the word is exactly the desired length and contains only letters
#                 if len(word) == length and word.isalpha():
#                     words.add(word)
#     except Exception as e:
#         print(f"Error reading dictionary file {filepath}: {e}")
#     return list(words)

# List of domains to check
domains_to_check = [
    # Existing
    "MCPManage.com",
    "MCPControl.com",
    "MCPAdmin.com",
    "MCPOps.com",
    "MCPMaestro.com",
    "MCPPilot.com",
    "MCPHelm.com",
    "MCPNexus.com",
    "MCPCore.com",
    "MCPHub.com",
    "MCPCenter.com",
    "ManageMCP.com",
    "ControlMCP.com",
    "SimpleMCP.com",
    "EasyMCP.com",
    "TotalMCP.com",
    "FullMCP.com",
    "MCPComplete.com",
    "MCPManager.com",
    "MCPConsole.com",

    # Added based on request
    "MCPView.com",
    "MCPDash.com",
    "MCPBoard.com",
    "MCPPanel.com",
    "MCPGuard.com",
    "MCPSecure.com",
    "MCPAccess.com",
    "MCPDesk.com",
    "MCPCentral.com",
    "MCPMaster.com",
    "MCPKey.com",
    "MCPGate.com",
    "MCPPort.com", # Short for Portal
    "MCPApp.com",
    "MCPTool.com",
    "MCPKit.com",
    "MCPMon.com", # Short for Monitor
    "MCPWatch.com",
    "MCPHQ.com",
    "MCPZone.com",
]


print(f"Checking {len(domains_to_check)} specific domains.")

available_domains = []
# Lock for thread-safe updates to available_domains
lock = threading.Lock()

# Number of parallel workers (adjust as needed)
MAX_WORKERS = 10 # Reduced workers slightly for potentially slower RDAP servers

# Process the domains in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Submit all tasks
    future_to_domain = {executor.submit(check_domain, domain): domain for domain in domains_to_check}

    # Process results as they complete
    for future in tqdm(concurrent.futures.as_completed(future_to_domain),
                       total=len(domains_to_check),
                       desc="Checking domains",
                       unit="domain"): # Changed unit to domain
        try:
            domain, available = future.result(timeout=25) # Slightly increased result timeout
            with lock:
                if available:
                    available_domains.append(domain)
                    tqdm.write(f"\n🟢 AVAILABLE: {domain} 🟢\n")
                # else:
                    # Optional: Log unavailable domains if needed
                    # tqdm.write(f"🔴 UNAVAILABLE: {domain}")
        except concurrent.futures.TimeoutError:
            # This timeout is for future.result(), not the curl command itself
            domain = future_to_domain[future]
            tqdm.write(f"⚠️ FUTURE TIMEOUT: Check for {domain} took too long - skipping result")
        except Exception as e:
            domain = future_to_domain[future]
            tqdm.write(f"Error processing result for {domain}: {str(e)}")

# Display summary of results
print("\nSummary of Available Domains:")
if available_domains:
    for domain in available_domains:
        print(f"- {domain}")
else:
    print("No domains from the list were found to be available.")

print(f"\nTotal available domains found: {len(available_domains)}")
print(f"Total domains checked: {len(domains_to_check)}")

# Write results to file for reference
output_filename = "specific_available_domains.txt" # Changed filename
with open(output_filename, "w") as f:
    f.write(f"Checked {len(domains_to_check)} specific domains.\n")
    f.write(f"Total available domains found: {len(available_domains)}\n\n")
    f.write("Available domains:\n")
    if available_domains:
        for domain in available_domains:
            f.write(f"{domain}\n")
    else:
        f.write("None\n")
print(f"Results written to {output_filename}")



# Removed commented out vowel alteration code

# # Generate random combinations of 6-letter words
# # four_letter_words = []
# # for _ in range(1000):
# #     letters = random.sample(string.ascii_lowercase, 3)
# #     digit = random.choice(string.digits)
# #     insert_pos = random.randint(0, 3)
# #     word = letters[:insert_pos] + [digit] + letters[insert_pos:]
# #     four_letter_words.append(''.join(word))

# # four_letter_words = [''.join(random.choices(string.ascii_lowercase, k=5)) for _ in range(1000)]
# # four_letter_words = [word.lower() for word in get_english_words_set(['web2'], lower=True) if len(word) == 6]


# # # Mapping of digits to similar-looking letters
# # substitution_map = {
# #     # 'a': '4',
# #     # 'e': '3',
# #     # 'i': '1',
# #     'o': '0',
# #     # 's': '5',
# #     # 't': '7',
# #     # 'b': '8',
# #     # 'g': '9',
# #     # 'z': '2',
# # }

# # Get all lowercase 5-letter English words
# # four_letter_words = [word.lower() for word in get_english_words_set(['web2'], lower=True) if len(word) == 6]


# ## Get all lowercase 3-letter base words
# # Use /usr/share/dict/words as the source
# dict_path = '/usr/share/dict/words'
# base_words = load_words_from_file(dict_path, 4) # Filter for 4-letter words
# print(f"Found {len(base_words)} base words to check")

# ## Prefix expansion using 3-4 letter words
# small_words = ["get", "try"]
# expanded_candidates = []
# for word in base_words:
#     # include the base word
#     expanded_candidates.append(word)
#     # add prefix variants
#     for sw in small_words:
#         expanded_candidates.append(sw + word)
# four_letter_words = list(set(expanded_candidates))
# print(f"Total candidate domain names after expansion: {len(four_letter_words)}")



# # Replace one eligible letter with corresponding digit
# # leetified_words = []
# # for word in temp_words:
# #     # Only consider the 2nd place for replacement
# #     eligible_indices = [1] if len(word) > 1 and word[1] in substitution_map else []
# #     if eligible_indices:
# #         # Choose the letter to replace (always the 2nd place)
# #         idx = eligible_indices[0]
# #         new_char = substitution_map[word[idx]]
# #         # Create new word with the substitution
# #         leetified = word[:idx] + new_char + word[idx+1:]
# #         leetified_words.append(leetified)

# # four_letter_words = leetified_words

# # Shuffle the list to avoid checking only words starting with 'a'
# # random.shuffle(four_letter_words)

# print(f"Found {len(four_letter_words)} 5-letter words to check")

# available_domains = []
# # Lock for thread-safe updates to available_domains
# lock = threading.Lock()

# # Number of parallel workers (higher than WHOIS since curl requests are faster)
# MAX_WORKERS = 20

# # Process the words in parallel
# with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#     # Submit all tasks
#     future_to_domain = {executor.submit(check_domain, word): word for word in four_letter_words}
    
#     # Process results as they complete
#     for future in tqdm(concurrent.futures.as_completed(future_to_domain), 
#                        total=len(four_letter_words), 
#                        desc="Checking domains", 
#                        unit="word"):
#         try:
#             domain, available = future.result(timeout=20) # Add a 20 second timeout to result retrieval
#             with lock:
#                 if available:
#                     available_domains.append(domain)
#                     tqdm.write(f"\n🟢 AVAILABLE: {domain} 🟢\n")
#                 else:
#                     # tqdm.write(f"\n🔴 UNAVAILABLE: {domain} 🔴\n")
#                     pass
#         except concurrent.futures.TimeoutError:
#             word = future_to_domain[future]
#             tqdm.write(f"⚠️ TIMEOUT: {word}.com - skipping")
#         except Exception as e:
#             word = future_to_domain[future]
#             tqdm.write(f"Error processing {word}.com: {str(e)}")

# # Display summary of results
# print("\nSummary of Available Domains:")
# for domain in available_domains:
#     print(f"- {domain}")

# print(f"\nTotal available domains found: {len(available_domains)}")
# print(f"Total words checked: {len(four_letter_words)}")

# # Write results to file for reference
# with open("available_domains_dict.txt", "w") as f:
#     f.write(f"Total available domains found: {len(available_domains)}\n")
#     f.write(f"Total words checked: {len(four_letter_words)}\n\n")
#     f.write("Available domains:\n")
#     for domain in available_domains:
#         f.write(f"{domain}\n")


# ## Vowel Alteration / Removal (Commented Out)
# # def vowel_alterations(word):
# #     vowels = "aeiou"
# #     variations = []
# #     # Variation: remove vowels entirely
# #     no_vowel = ''.join([c for c in word if c not in vowels])
# #     if no_vowel != word:
# #         variations.append(no_vowel)
# #     # Variation: remove each vowel one at a time
# #     for i, c in enumerate(word):
# #         if c in vowels:
# #             variation = word[:i] + word[i+1:]
# #             if variation not in variations and variation != word:
# #                 variations.append(variation)
# #     return variations
# #
# # # Uncomment to generate additional candidates using vowel alterations
# # # additional_candidates = []
# # # for word in list(candidates):
# # #     additional_candidates.extend(vowel_alterations(word))
# # # candidates.extend(additional_candidates) 