import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ---------------------------
# Scraper Helper Functions
# ---------------------------
def get_title(soup):
    try:
        return soup.find("span", class_="a-size-medium").text.strip()
    except AttributeError:
        return np.nan


def get_price(soup):
    try:
        price_whole = soup.find("span", {"class": "a-price-whole"}).text.replace(",", "").strip()
        price_fraction = soup.find("span", {"class": "a-price-fraction"}).text.strip()
        return float(f"{price_whole}.{price_fraction}")
    except AttributeError:
        try:
            price = soup.find("span", class_="a-offscreen").text.strip()
            return float(price.replace("$", "").replace(",", ""))
        except:
            return np.nan


def get_rating(soup):
    try:
        return soup.find("span", class_="a-icon-alt").text.split()[0]
    except AttributeError:
        return np.nan


def get_reviews(soup):
    try:
        return soup.find("span", {"class": "a-size-base"}).text.strip()
    except AttributeError:
        return np.nan


def get_availability(soup):
    try:
        return soup.find("span", {"class": "a-color-success"}).text.strip()
    except AttributeError:
        return "Not Available"


# ---------------------------
# Main Scraper
# ---------------------------
def scrape_amazon(search_query, max_pages=1):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    base_url = "https://www.amazon.com/s"
    products = {"title": [], "price": [], "rating": [], "reviews": [], "availability": []}

    for page in range(1, max_pages + 1):
        params = {"k": search_query, "page": page}
        res = requests.get(base_url, headers=headers, params=params)
        soup = BeautifulSoup(res.content, "html.parser")

        items = soup.find_all("div", {"data-component-type": "s-search-result"})
        if not items:
            print(f"⚠️ No results found on page {page}")
            continue

        for item in items:
            products["title"].append(get_title(item))
            products["price"].append(get_price(item))
            products["rating"].append(get_rating(item))
            products["reviews"].append(get_reviews(item))
            products["availability"].append(get_availability(item))

    df = pd.DataFrame(products)
    df["scraped_date"] = datetime.now().date()
    return df


# ---------------------------
# Email Sender
# ---------------------------
def send_email(new_data):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    msg = MIMEMultipart()
    msg["Subject"] = "New Amazon Deals Under $50"
    msg["From"] = sender
    msg["To"] = receiver

    html_table = new_data.to_html(index=False, justify="center")
    body = MIMEText(f"<h3>New/Updated Amazon Deals</h3>{html_table}", "html")
    msg.attach(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())


# ---------------------------
# Main Logic
# ---------------------------
if __name__ == "__main__":
    csv_file = "amazon_data.csv"

    # 1️⃣ Scrape fresh data
    amazon_df = scrape_amazon("shoes for women sneakers", max_pages=2)

    # 2️⃣ Filter best deals (< $50)
    amazon_df = amazon_df[pd.to_numeric(amazon_df["price"], errors="coerce") < 50].dropna(subset=["price"])

    # 3️⃣ Load old data (if exists)
    if os.path.exists(csv_file):
        old_df = pd.read_csv(csv_file)
        old_df["scraped_date"] = pd.to_datetime(old_df["scraped_date"]).dt.date
    else:
        old_df = pd.DataFrame(columns=amazon_df.columns)

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    today_df = amazon_df.copy()
    yesterday_df = old_df[old_df["scraped_date"] == yesterday] if not old_df.empty else pd.DataFrame(columns=amazon_df.columns)

    # 4️⃣ Find new/changed products (today vs yesterday)
    comparison_cols = ["title", "price", "rating", "reviews", "availability"]
    new_data = pd.concat([today_df, yesterday_df]).drop_duplicates(subset=comparison_cols, keep=False)

    # 5️⃣ Save updated data
    combined_df = pd.concat([old_df, today_df]).drop_duplicates(subset=["title", "scraped_date"], keep="last")
    combined_df.to_csv(csv_file, index=False)

    # 6️⃣ Send email only if new/changed deals exist
    if not new_data.empty:
        send_email(new_data[comparison_cols])
        print(f"📩 Email sent with {len(new_data)} new/changed deals.")
    else:
        print("ℹ️ No new or changed deals under $50 today. Email skipped.")