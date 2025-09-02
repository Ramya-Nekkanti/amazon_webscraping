from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import os
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

        # Clean up accidental extra dots
        price_str = f"{price_whole}.{price_fraction}".replace("..", ".").strip()

        return float(price_str)
    except AttributeError:
        try:
            price = soup.find("span", attrs={'id': 'priceblock_dealprice'}).string.strip()
            return float(price.replace("$", "").replace(",", ""))
        except (AttributeError, ValueError):
            return np.nan

def get_rating(soup):
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
        return "Not Available"

# ------------------- Email Function -------------------

def send_email(new_data):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Amazon Deals Under $50"
    msg["From"] = sender
    msg["To"] = receiver

    html_table = new_data.to_html(index=False, escape=False)
    body = MIMEText(f"<h3>Amazon Deals (Under $50)</h3>{html_table}", "html")
    msg.attach(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())

# ------------------- Main Scraper -------------------

if __name__ == '__main__':

    url = "https://www.amazon.ca/s?k=shoes+for+women+sneakers"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
        'Referer': 'https://www.amazon.ca/',
        'Accept-Language': 'en-CA, en;q=0.5'
    }

    # Request search page
    webpage = requests.get(url, headers=headers)
    soup = BeautifulSoup(webpage.content, "html.parser")

    # Collect product links
    links = soup.find_all("a", attrs={"class" :"a-link-normal s-line-clamp-2 s-line-clamp-3-for-col-12 s-link-style a-text-normal"})
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

    # ------------------- Filter Best Deals -------------------
    best_deals = amazon_df[(amazon_df["price"].notna()) & (amazon_df["price"] < 50)]

    if not best_deals.empty:
        send_email(best_deals[["title", "price", "rating", "reviews", "availability"]])
        print(f"✅ Email sent with {len(best_deals)} deals under $50")
    else:
        print("ℹ️ No deals under $50 found today. Email skipped.")
