from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime, timedelta

CSV_FILE = "amazon_data.csv"

# -------------------------------
# Functions for data extraction
# -------------------------------

def get_title(soup):
    try:
        return soup.find("span", attrs={"id": 'productTitle'}).text.strip()
    except AttributeError:
        return ""

def get_price(soup):
    try:
        price_whole = soup.find("span", {"class": "a-price-whole"}).text.replace(",", "").replace(".", "")
        price_fraction = soup.find("span", {"class": "a-price-fraction"}).text.strip()
        return float(f"{price_whole}.{price_fraction}")
    except (AttributeError, ValueError):
        try:
            price = soup.find("span", attrs={'id':'priceblock_dealprice'}).string.strip()
            return float(price.replace("$","").replace(",",""))
        except (AttributeError, ValueError):
            return np.nan

def get_rating(soup):
    try:
        rating = soup.find("i", attrs={'class': 'a-icon a-icon-star a-star-4-5'}).string.strip()
    except AttributeError:
        try:
            rating = soup.find("span", attrs={'class': 'a-icon-alt'}).string.strip()
        except:
            rating = ""
    return rating

def get_review_count(soup):
    try:
        return soup.find("span", attrs={'id': 'acrCustomerReviewText'}).string.strip()
    except AttributeError:
        return ""

def get_availability(soup):
    try:
        available = soup.find("div", attrs={'id': 'availability'})
        return available.find("span").string.strip()
    except AttributeError:
        try:
            return soup.find("span", attrs={'id':'twisterAvailability'}).text.strip()
        except AttributeError:
            return "Not Available"

# -------------------------------
# Email sender
# -------------------------------

def send_email(new_data):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = os.getenv("EMAIL_TO")

    if not sender or not password or not receiver:
        print("⚠️ Email not sent. Missing credentials.")
        return

    if new_data.empty:
        print("📭 No new deals under $50 today. No email sent.")
        return

    html_table = new_data.to_html(index=False)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Amazon Daily Best Deals (<$50)"
    msg["From"] = sender
    msg["To"] = receiver

    body = MIMEText(f"<h3>New Amazon Deals (Under $50)</h3>{html_table}", "html")
    msg.attach(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("✅ Email sent with new deals!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# -------------------------------
# Main Script
# -------------------------------

if __name__ == '__main__':

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    url = "https://www.amazon.ca/s?k=shoes+for+women+sneakers"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Referer': 'https://www.amazon.ca/',
        'Accept-Language': 'en-CA,en;q=0.5'
    }

    # Scrape product links
    webpage = requests.get(url, headers=headers)
    soup = BeautifulSoup(webpage.content, "html.parser")
    links = soup.find_all("a", attrs={"class": "a-link-normal s-line-clamp-2 s-line-clamp-3-for-col-12 s-link-style a-text-normal"})
    links_list = ["https://www.amazon.ca" + link.get('href') for link in links if link.get('href')]

    # Scrape product details
    d = {"title": [], "price": [], "rating": [], "reviews": [], "availability": [], "scraped_date": []}
    for link in links_list:
        new_webpage = requests.get(link, headers=headers)
        new_soup = BeautifulSoup(new_webpage.content, "html.parser")
        d['title'].append(get_title(new_soup))
        d['price'].append(get_price(new_soup))
        d['rating'].append(get_rating(new_soup))
        d['reviews'].append(get_review_count(new_soup))
        d['availability'].append(get_availability(new_soup))
        d['scraped_date'].append(today)

    amazon_df = pd.DataFrame.from_dict(d)
    amazon_df['title'] = amazon_df['title'].replace('', np.nan)
    amazon_df = amazon_df.dropna(subset=['title'])
    amazon_df = amazon_df.dropna(axis=1, how='all')  # remove empty columns

    # Load old data
    if os.path.exists(CSV_FILE):
        old_df = pd.read_csv(CSV_FILE).dropna(axis=1, how='all')
    else:
        old_df = pd.DataFrame(columns=amazon_df.columns)

    # Append new data safely
    combined_df = pd.concat([old_df, amazon_df], ignore_index=True).drop_duplicates(subset=["title", "scraped_date"])
    combined_df.to_csv(CSV_FILE, index=False)

    # Compare today vs yesterday
    yesterday_df = old_df[old_df['scraped_date'] == yesterday]
    merged = pd.merge(amazon_df, yesterday_df, on="title", how="left", suffixes=("", "_yesterday"))

    # New or price-changed products
    changes_mask = merged['price_yesterday'].isna() | (merged['price'] != merged['price_yesterday'])
    new_or_changed = merged[changes_mask]

    # Only deals under $50
    best_deals = new_or_changed[new_or_changed['price'] < 50]

    if not best_deals.empty:
        send_email(best_deals[['title', 'price', 'rating', 'reviews', 'availability']])
    else:
        print("ℹ️ No new or changed deals under $50 today. Email skipped.")
        