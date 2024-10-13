import requests
from bs4 import BeautifulSoup
import nltk
import re
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client
from flask import Flask, render_template
import telegram
from slack_sdk import WebClient
import schedule
import time

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('english'))

# Ask user for their notification preferences
def get_user_input():
    print("Welcome to the AI-powered Job Scraper Setup!")
    use_temp_email = input("Do you want to use a temporary email (y/n)?: ").lower()
    if use_temp_email == 'y':
        temp_email = "your_temp_email@domain.com"  # Replace with a temp email provider setup or use API
        email_password = "temp_email_password"  # Add a logic to generate or provide a temp email service
        to_email = temp_email
        print(f"Temporary email set: {temp_email}")
    else:
        to_email = input("Please enter your email address for notifications: ")
        email_password = input("Enter your email password: ")

    use_telegram = input("Would you like to enable Telegram notifications (y/n)?: ").lower()
    if use_telegram == 'y':
        bot_token = input("Enter your Telegram Bot Token: ")
        chat_id = input("Enter your Telegram Chat ID: ")
        bot = telegram.Bot(token=bot_token)
    else:
        bot_token, chat_id, bot = None, None, None

    use_slack = input("Would you like to enable Slack notifications (y/n)?: ").lower()
    if use_slack == 'y':
        slack_token = input("Enter your Slack Token: ")
        slack_channel = input("Enter your Slack Channel ID (e.g., #job-alerts): ")
        slack_client = WebClient(token=slack_token)
    else:
        slack_client, slack_channel = None, None

    use_sms = input("Would you like to enable SMS notifications via Twilio (y/n)?: ").lower()
    if use_sms == 'y':
        twilio_account_sid = input("Enter your Twilio Account SID: ")
        twilio_auth_token = input("Enter your Twilio Auth Token: ")
        twilio_phone_number = input("Enter your Twilio Phone Number: ")
        recipient_phone_number = input("Enter your phone number to receive SMS: ")
        sms_client = Client(twilio_account_sid, twilio_auth_token)
    else:
        sms_client, twilio_phone_number, recipient_phone_number = None, None, None

    return {
        "email": to_email,
        "email_password": email_password,
        "bot": bot,
        "chat_id": chat_id,
        "slack_client": slack_client,
        "slack_channel": slack_channel,
        "sms_client": sms_client,
        "twilio_phone_number": twilio_phone_number,
        "recipient_phone_number": recipient_phone_number
    }

# Scraper for Indeed
def scrape_indeed(query, location):
    url = f'https://www.indeed.com/jobs?q={query}&l={location}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    job_cards = soup.find_all('div', class_='jobsearch-SerpJobCard')
    
    jobs = []
    for card in job_cards:
        title = card.find('a', class_='jobtitle').text.strip()
        company = card.find('span', class_='company').text.strip()
        summary = card.find('div', class_='summary').text.strip()
        link = "https://www.indeed.com" + card.find('a', class_='jobtitle')['href']
        job = {
            'title': title,
            'company': company,
            'summary': summary,
            'link': link
        }
        jobs.append(job)
    
    return jobs

# AI Filtering for Scams
def filter_scams(jobs):
    scam_keywords = ['no experience needed', 'quick money', 'cash', 'pyramid', 'work from home']
    filtered_jobs = []
    
    for job in jobs:
        tokens = re.findall(r'\b\w+\b', job['summary'].lower())
        tokens = [word for word in tokens if word not in stop_words]
        if not any(keyword in job['summary'].lower() for keyword in scam_keywords):
            filtered_jobs.append(job)
    
    return filtered_jobs

# Notification Functions
def send_email_notification(jobs, user_prefs):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(user_prefs['email'], user_prefs['email_password'])
    
    for job in jobs:
        msg = MIMEMultipart()
        msg['From'] = user_prefs['email']
        msg['To'] = user_prefs['email']
        msg['Subject'] = f"New Job: {job['title']}"
        body = f"Company: {job['company']}\nSummary: {job['summary']}\nLink: {job['link']}"
        msg.attach(MIMEText(body, 'plain'))
        server.sendmail(user_prefs['email'], user_prefs['email'], msg.as_string())
    
    server.quit()

def notify_via_telegram(jobs, user_prefs):
    if user_prefs['bot']:
        for job in jobs:
            message = f"Job: {job['title']}\nCompany: {job['company']}\nSummary: {job['summary']}\nLink: {job['link']}"
            user_prefs['bot'].send_message(chat_id=user_prefs['chat_id'], text=message)

def notify_via_slack(jobs, user_prefs):
    if user_prefs['slack_client']:
        for job in jobs:
            message = f"Job: {job['title']} at {job['company']}\nLink: {job['link']}"
            user_prefs['slack_client'].chat_postMessage(channel=user_prefs['slack_channel'], text=message)

def notify_via_sms(jobs, user_prefs):
    if user_prefs['sms_client']:
        for job in jobs:
            message = f"Job: {job['title']} at {job['company']}\nLink: {job['link']}"
            user_prefs['sms_client'].messages.create(
                body=message,
                from_=user_prefs['twilio_phone_number'],
                to=user_prefs['recipient_phone_number']
            )

# Flask Web Interface
app = Flask(__name__)

@app.route('/')
def home():
    indeed_jobs = scrape_indeed("cybersecurity internship", "")
    filtered_jobs = filter_scams(indeed_jobs)
    return render_template('index.html', jobs=filtered_jobs)

# Scheduler to Run Job Scraping and Notifications
def job_scraper(user_prefs):
    jobs = scrape_indeed("cybersecurity internship", "")
    filtered_jobs = filter_scams(jobs)
    
    send_email_notification(filtered_jobs, user_prefs)
    notify_via_telegram(filtered_jobs, user_prefs)
    notify_via_slack(filtered_jobs, user_prefs)
    notify_via_sms(filtered_jobs, user_prefs)

# Run scraper every 3 hours
def schedule_jobs(user_prefs):
    schedule.every(3).hours.do(job_scraper, user_prefs)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    user_prefs = get_user_input()
    schedule_jobs(user_prefs)
    app.run(debug=True)
