import requests
from bs4 import BeautifulSoup
import nltk
import re
import smtplib
import os
import logging
import openai
import schedule
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client
from flask import Flask, render_template
import telegram
from slack_sdk import WebClient
from datetime import datetime

# Configure Logging
logging.basicConfig(filename="job_scraper.log", level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# AI Setup (OpenAI)
openai.api_key = "your_openai_api_key"

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('english'))

# AI Function to analyze job postings
def ai_job_analysis(job_description):
    logging.info("AI analyzing job description...")
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=f"Analyze the following job description and provide key insights:\n\n{job_description}\n\nInsights:",
      max_tokens=500,
      temperature=0.7,
    )
    return response.choices[0].text.strip()

# Function to pull job page and get AI insights
def ai_pull_and_analyze_job_page(job_link):
    logging.info(f"AI pulling job page: {job_link}")
    response = requests.get(job_link)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the main job description on the page
    job_description = soup.get_text(separator=" ").strip()
    
    # Let AI analyze the job page
    insights = ai_job_analysis(job_description)
    
    return insights

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
    
    logging.info(f"Scraped {len(jobs)} jobs from Indeed.")
    return jobs

# AI-driven scam filtering
def filter_scams(jobs):
    logging.info("AI filtering scam jobs...")
    scam_keywords = ['no experience needed', 'quick money', 'cash', 'pyramid', 'work from home']
    filtered_jobs = []
    
    for job in jobs:
        tokens = re.findall(r'\b\w+\b', job['summary'].lower())
        tokens = [word for word in tokens if word not in stop_words]
        if not any(keyword in job['summary'].lower() for keyword in scam_keywords):
            filtered_jobs.append(job)
    
    logging.info(f"Filtered {len(filtered_jobs)} jobs after AI scam detection.")
    return filtered_jobs

# Logging and email notification functions
def send_email_notification(jobs, user_email, user_password):
    logging.info(f"Sending email notifications to {user_email}")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(user_email, user_password)
    
    for job in jobs:
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = user_email
        msg['Subject'] = f"New Job: {job['title']}"
        body = f"Company: {job['company']}\nSummary: {job['summary']}\nLink: {job['link']}"
        msg.attach(MIMEText(body, 'plain'))
        server.sendmail(user_email, user_email, msg.as_string())
    
    server.quit()
    logging.info("Email notifications sent successfully.")

# AI-powered job insights via Telegram
def ai_job_insights_via_telegram(jobs, bot, chat_id):
    if bot:
        logging.info("Sending AI insights via Telegram.")
        for job in jobs:
            insights = ai_pull_and_analyze_job_page(job['link'])
            message = f"Job: {job['title']}\nCompany: {job['company']}\nInsights: {insights}\nLink: {job['link']}"
            bot.send_message(chat_id=chat_id, text=message)

# Flask Web Interface
app = Flask(__name__)

@app.route('/')
def home():
    indeed_jobs = scrape_indeed("cybersecurity internship", "")
    filtered_jobs = filter_scams(indeed_jobs)
    return render_template('index.html', jobs=filtered_jobs)

# Main job search function with AI control and logging
def find_jobs():
    logging.info("Starting job search...")

    job_query = "cybersecurity internship"
    location = ""
    
    indeed_jobs = scrape_indeed(job_query, location)
    all_jobs = indeed_jobs  # Add more job boards if needed
    
    # Filter scam jobs with AI
    filtered_jobs = filter_scams(all_jobs)

    # Send notifications via Email
    send_email_notification(filtered_jobs, "your_email@gmail.com", "your_email_password")

    # AI-driven Telegram notifications
    ai_job_insights_via_telegram(filtered_jobs, None, None)  # Add bot and chat_id
    
    logging.info(f"Job search completed. {len(filtered_jobs)} jobs found.")

# Schedule the job search and logging
def schedule_jobs():
    logging.info("Scheduling job search every 3 hours.")
    schedule.every(3).hours.do(find_jobs)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    logging.info("AI Job Scraper started.")
    schedule_jobs()
    app.run(debug=True)
