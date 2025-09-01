from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ------------------- Extraction Functions -------------------

def get_title(soup):
    try:
        return soup.find("span", attrs={"id": 'productTitle'}).text.strip()
    except AttributeError:
        return np.nan

def get_price(soup):
    try:
        price_whole = soup.find("span", {"class": "a-price-whole"}).text.replace(",", "").strip()
        price_fraction = soup.find("span", {"class": "a-price-fraction"}).text.strip()
        return float(f"{price_whole}.{price_fraction}")
    except AttributeError:
        try:
            price = soup.find("span", attrs={'id': 'priceblock_dealprice'}).string.strip()
            return float(price.replace("$", "").replace(",", ""))
        except (AttributeError, ValueError):
            return np.nan

def get_rating(soup):
    try:
        return soup.find("i", attrs={'class': 'a-icon a-icon-star a-star-4-5'}).string.strip()
    except AttributeError:
        try:
            return soup.find("span", attrs={'class': 'a-icon-alt'}).string.strip()
        except:
            return np.nan

def get_review_count(soup):
    try:
        return soup.find("span", attrs={'id': 'acrCustomerReviewText'}).string.strip()
    except AttributeError:
        return np.nan

def get_availability(soup):
    try:
        available = soup.find("div", attrs={'id': 'availability'})
        return available.find("span").string.strip()
    except AttributeError:
        try:
            return soup.find("span", attrs={'id': 'twisterAvailability'}).text.strip()
        except:
            return "Not Available"

# ------------------- Email Function -------------------

def send_email(new_data):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "New Amazon Deals Under $50"
    msg["From"] = sender
    msg["To"] = receiver

    html_table = new_data.to_html(index=False, escape=False)
    body = MIMEText(f"<h3>New Amazon Deals (Under $50)</h3>{html_table}", "html")
    msg.attach(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())

# ------------------- Main Scraper -------------------

if __name__ == '__main__':

    url = "https://www.amazon.ca/s?k=shoes+for+women+sneakers"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Accept-Language': 'en-CA, en;q=0.5'
    }

    # Request search page
    webpage = requests.get(url, headers=headers)
    soup = BeautifulSoup(webpage.content, "html.parser")

    # Collect product links
    links = soup.find_all("a", attrs={'class':'a-link-normal s-no-outline'})
    links_list = ["https://www.amazon.ca" + link.get('href') for link in links if link.get('href')]

    # Prepare storage
    d = {"title": [], "price": [], "rating": [], "reviews": [], "availability": []}

    for link in links_list:
        new_webpage = requests.get(link, headers=headers)
        new_soup = BeautifulSoup(new_webpage.content, "html.parser")

        d['title'].append(get_title(new_soup))
        d['price'].append(get_price(new_soup))
        d['rating'].append(get_rating(new_soup))
        d['reviews'].append(get_review_count(new_soup))
        d['availability'].append(get_availability(new_soup))

    amazon_df = pd.DataFrame.from_dict(d)
    amazon_df["scraped_date"] = datetime.today().date()

    # ------------------- Merge with Old Data -------------------

    if os.path.exists("amazon_data.csv"):
        old_df = pd.read_csv("amazon_data.csv")

        if "scraped_date" not in old_df.columns:
            old_df["scraped_date"] = pd.NaT
    else:
        old_df = pd.DataFrame(columns=["title", "price", "rating", "reviews", "availability", "scraped_date"])

    combined_df = pd.concat([old_df, amazon_df]).drop_duplicates(subset=["title", "scraped_date"])
    combined_df.to_csv("amazon_data.csv", index=False)

    # ------------------- Compare with Yesterday -------------------

    yesterday = (datetime.today() - timedelta(days=1)).date()
    yesterday_df = old_df[old_df["scraped_date"] == str(yesterday)]

    if old_df.empty or yesterday_df.empty:
        new_or_changed = amazon_df  # first run → all products are new
    else:
        merged = amazon_df.merge(yesterday_df, on="title", how="left", suffixes=("", "_y"))
        new_or_changed = merged[(merged["price"] != merged["price_y"]) | merged["price_y"].isna()]

    # ------------------- Send Email if Needed -------------------

    best_deals = new_or_changed[(new_or_changed["price"].notna()) & (new_or_changed["price"] < 50)]

    if not best_deals.empty:
        send_email(best_deals[["title", "price", "rating", "reviews", "availability"]])
        print(f"✅ Email sent with {len(best_deals)} new deals under $50")
    else:
        print("ℹ️ No new or changed deals under $50 today. Email skipped.")