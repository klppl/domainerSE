import requests
from datetime import datetime
import os
import sys
import argparse
from openai import OpenAI, OpenAIError

# ===========================
# ===== CONFIGURATION =======
# ===========================

# Embed your OpenAI API key directly into the script
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# URL to fetch the domains data
DOMAIN_DATA_URL = "https://data.internetstiftelsen.se/bardate_domains.txt"

# Output filenames
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SORTED_FILE = os.path.join(SCRIPT_DIR, "sorted_domains.txt")


# ===========================
# ======= FUNCTIONS =========
# ===========================

def download_and_process_data(url):
    """
    Downloads the domain data and processes it (parsing and sorting).

    Args:
        url (str): URL to download the data.

    Returns:
        list of tuples: Sorted list of (domain, date).
    """
    content = download_file(url)
    if content is None:
        sys.exit("Error: Unable to download data.")

    entries = parse_file_content(content)
    if not entries:
        sys.exit("Error: No valid entries found.")

    return sort_entries_by_date(entries)


def download_file(url):
    """
    Downloads the content of the file from the given URL.

    Args:
        url (str): The URL to download the file from.

    Returns:
        str: The content of the file as a string.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
        return None


def parse_file_content(content):
    """
    Parses the content of the file into a list of tuples (domain, date).

    Args:
        content (str): The content of the file.

    Returns:
        list of tuples: Each tuple contains (domain, date as datetime.date object).
    """
    entries = []
    for line in content.strip().splitlines():
        parts = line.split('\t')
        if len(parts) != 2:
            print(f"Skipping malformed line: {line}")
            continue

        domain, date_str = parts
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            entries.append((domain, date))
        except ValueError:
            print(f"Skipping invalid date format: {line}")
    return entries


def sort_entries_by_date(entries):
    """
    Sorts the list of entries by date in ascending order.

    Args:
        entries (list of tuples): Each tuple contains (domain, date).

    Returns:
        list of tuples: Sorted list of entries.
    """
    return sorted(entries, key=lambda x: x[1])


def save_to_file(filename, header, rows):
    """
    Saves the given data to a file.

    Args:
        filename (str): File path to save the data.
        header (str): Header line for the file.
        rows (list of str): List of rows to write.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(header + '\n')
            file.writelines(f"{row}\n" for row in rows)
        print(f"Data successfully saved to {filename}")
    except IOError as e:
        print(f"Error writing to file: {e}")


def load_sorted_entries(filename):
    """
    Loads sorted entries from a file.

    Args:
        filename (str): Path to the sorted domains file.

    Returns:
        list of tuples: Each tuple contains (domain, date as datetime.date object).
    """
    entries = []
    try:
        with open(filename, mode='r', encoding='utf-8') as file:
            next(file)  # Skip header
            for line in file:
                parts = line.strip().split(', ')
                if len(parts) != 2:
                    print(f"Skipping malformed line: {line}")
                    continue
                domain, date_str = parts
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    entries.append((domain, date))
                except ValueError:
                    print(f"Skipping invalid date format: {line}")
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
    except IOError as e:
        print(f"Error reading file: {e}")
    return entries


def get_available_domains(entries, target_date):
    """
    Filters and returns domains available on the specified date.

    Args:
        entries (list of tuples): List of (domain, date) tuples.
        target_date (datetime.date): The date to filter domains.

    Returns:
        list of str: Domains available on the specified date.
    """
    return [domain for domain, date in entries if date == target_date]


def analyze_domains_with_chatgpt(domains):
    """
    Sends the list of domains to OpenAI's GPT API for detailed analysis.

    Args:
        domains (list of str): List of domain names.

    Returns:
        str: GPT's analysis and recommendations.
    """
    if not domains:
        return "No domains provided for analysis."

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = (
        "Analyze the following domain names based on their potential value and provide a specific recommendation for each. "
        "Consider factors like brandability, relevance to industries or trends, commercial potential, and any risks. "
        "Format the response as a numbered list with a brief explanation for each domain.\n\n"
        "Domains:\n" + "\n".join(domains) + "\n\n"
        "Provide concise recommendations for each domain:"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that provides in-depth domain name analysis and recommendations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.5,
        )

        # Extract and format the analysis
        analysis = response.choices[0].message.content.strip()
        return analysis
    except OpenAIError as e:
        return f"OpenAI API Error: {e}"
    except Exception as e:
        return f"Unexpected Error: {e}"


def display_analysis(domains, analysis):
    """
    Display and format the analysis for better clarity.

    Args:
        domains (list): List of domains analyzed.
        analysis (str): ChatGPT's analysis response.
    """
    if not domains:
        print("No domains available for analysis.")
        return

    print("\nChatGPT Analysis and Recommendations:")
    print("-" * 50)
    print(analysis)
    print("-" * 50)
    print("Analysis complete. Use the insights to evaluate domain potential.")


# ===========================
# ========= MAIN ============
# ===========================

def main():
    parser = argparse.ArgumentParser(description="Download, sort domains, and filter by date.")
    parser.add_argument('-d', '--date', type=str, help='Date to filter available domains (YYYY-MM-DD)')
    parser.add_argument('-c', '--chatgpt', action='store_true', help='Analyze domains using ChatGPT')
    args = parser.parse_args()

    # Download and process data if sorted file is missing
    if not os.path.exists(SORTED_FILE):
        print("Downloading and processing domain data...")
        sorted_entries = download_and_process_data(DOMAIN_DATA_URL)
        save_to_file(SORTED_FILE, "domain, date", [f"{domain}, {date}" for domain, date in sorted_entries])
    else:
        print("Loading sorted data from file...")
        sorted_entries = load_sorted_entries(SORTED_FILE)

    # Filter and process based on the provided date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            sys.exit("Error: Invalid date format. Use YYYY-MM-DD.")

        available_domains = get_available_domains(sorted_entries, target_date)
        if available_domains:
            print(f"Domains available on {target_date}:")
            print("\n".join(available_domains))

            # Save available domains to a file
            available_file = os.path.join(SCRIPT_DIR, f"available_domains_{target_date}.txt")
            save_to_file(available_file, "domain", available_domains)

            if args.chatgpt:
                print("Analyzing domains with ChatGPT...")
                analysis = analyze_domains_with_chatgpt(available_domains)
                display_analysis(available_domains, analysis)
        else:
            print(f"No domains available on {target_date}.")
    else:
        print("Data successfully downloaded and sorted.")


if __name__ == "__main__":
    main()
