import schedule
import time
from datetime import datetime

# Function to scrape jobs, filter scams, and send notifications
def find_jobs():
    # Define the search term and job boards
    job_query = input("Enter the job title or query you'd like to search for: ")
    job_location = input("Enter the job location (leave blank for all locations): ")

    use_indeed = input("Would you like to scrape Indeed? (y/n): ").lower() == 'y'
    use_handshake = input("Would you like to scrape Handshake? (y/n): ").lower() == 'y'
    use_ziprecruiter = input("Would you like to scrape ZipRecruiter? (y/n): ").lower() == 'y'

    all_jobs = []
    
    # Scrape selected job boards
    if use_indeed:
        indeed_jobs = scrape_indeed(job_query, job_location)
        all_jobs += indeed_jobs
    
    if use_handshake:
        handshake_jobs = scrape_handshake(job_query, job_location)
        all_jobs += handshake_jobs

    if use_ziprecruiter:
        ziprecruiter_jobs = scrape_ziprecruiter(job_query, job_location)
        all_jobs += ziprecruiter_jobs

    # Filter scam jobs using AI filtering
    filtered_jobs = filter_scams(all_jobs)

    # Notifications
    notify = input("Do you want to receive notifications? (y/n): ").lower()
    if notify == 'y':
        notify_via_telegram(filtered_jobs)
        notify_via_slack(filtered_jobs)
        send_email_notification(filtered_jobs, "your_email@gmail.com")
        notify_via_sms(filtered_jobs)

    print(f"[{datetime.now()}] Job search completed. {len(filtered_jobs)} jobs found.")

# Helper function to ask for the scheduling interval
def setup_schedule():
    print("\nScheduler Setup")
    interval_type = input("Would you like to schedule the job search every (1) Minutes, (2) Hours, or (3) Daily at a specific time? Enter the number: ")

    if interval_type == '1':
        minutes = int(input("How many minutes should the search run? "))
        schedule.every(minutes).minutes.do(find_jobs)
        print(f"Scheduled every {minutes} minute(s).")

    elif interval_type == '2':
        hours = int(input("How many hours should the search run? "))
        schedule.every(hours).hours.do(find_jobs)
        print(f"Scheduled every {hours} hour(s).")

    elif interval_type == '3':
        time_of_day = input("Enter the time of day to run the search (e.g., 14:30 for 2:30 PM): ")
        schedule.every().day.at(time_of_day).do(find_jobs)
        print(f"Scheduled daily at {time_of_day}.")
    else:
        print("Invalid input. Defaulting to every 3 hours.")
        schedule.every(3).hours.do(find_jobs)

# Start the scheduler
if __name__ == "__main__":
    setup_schedule()

    print("\nScheduler is running... Press Ctrl+C to stop.")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)
