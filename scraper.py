"""
What: Use Apify API to communicate with curious_coder/linkedin-jobs-scraper
Return: Document inside google doc with job details from linkedin
"""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient
import openai
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# load environment variables
load_dotenv()
APIFY_TOKEN = os.getenv("MY-APIFY-TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
PARENT_FOLDER_ID = "1b1EEcEIlO3IR6njyzcBrCQRdxyeYWGLz"

if not APIFY_TOKEN:
    client = None
else:
    client = ApifyClient(APIFY_TOKEN)


def job_scraper():
    # Prepare the Actor input
    run_input = {
        "urls": ["https://www.linkedin.com/jobs/search/?currentJobId=4428356248&distance=25.0&f_E=1%2C2%2C3&f_TPR=r604800&geoId=101282230&keywords=Machine%20Learning%20Engineer&origin=JOB_SEARCH_PAGE_JOB_FILTER"],
        "scrapeCompany": True,
        "count": 10,
        "splitByLocation": False,
        "splitCountry": "DE",
    }

    # Ensure client is available
    if client is None:
        print("APIFY token missing. Set MY-APIFY-TOKEN in your .env file.")
        return []

    # Run the Actor and wait for it to finish
    try:
        run = client.actor("hKByXkMQaC5Qt9UMN").call(run_input=run_input)
    except Exception as e:
        print("Actor call failed:", e)
        return []

    # Fetch and print Actor results from the run's dataset (if there are any)
    # The `run` may be a resource object, so try multiple ways to obtain the dataset id
    dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None) or getattr(run, "id", None)
    if not dataset_id:
        try:
            run_dict = run.to_dict()
            dataset_id = run_dict.get("defaultDatasetId") or run_dict.get("default_dataset_id") or run_dict.get("id")
        except Exception:
            pass

    if not dataset_id:
        print("Could not determine dataset id from run:", run)
        return []

    # Collect all items into a list
    items = []
    for item in client.dataset(dataset_id).iterate_items():
        items.append(item)
    
    return items

def authenticate():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def create_google_sheet(creds, title):
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets().create(body={
        'properties': {'title': title}
    }).execute()
    return sheet['spreadsheetId']


if __name__ == "__main__":
    items = job_scraper()

    if items:
        df = pd.DataFrame(items)
        print(df.head())

        csv_filename = f"linkedin_jobs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Saved scraped jobs to CSV: {csv_filename}")

        creds = authenticate()
        try:
            sheet_id = create_google_sheet(creds, "LinkedIn Job Scraper Results")
            print(f"Google Sheet created with ID: {sheet_id}")
        except HttpError as e:
            print("Google Sheets API error:", e)
            print("Please enable the Google Sheets API for your project, or check your service account permissions.")
            print("The data was still saved to CSV.")
    else:
        print("No items found from the scraper.")
        
        