# Amazon Scraper – Automated Best Deals Finder

This project automatically scrapes Amazon Canada for **women's shoes/sneakers**, identifies the best deals under $50, and emails those deals. 
---

## **Project Overview**

- **Scraper:** Python script (`amazon_scraper.py`) using `requests` and `BeautifulSoup`.
- **Data Extracted:**
  - Product title
  - Price (numeric)
  - Rating
  - Number of reviews
  - Availability
- **Output:** `amazon_data.csv` stores 
- **Email Notification:** Sends email only for **deals under $50**.

---

## **Automation Using GitHub Actions**

1. **Workflow File:** `.github/workflows/amazon_scraper.yml`
2. **Schedule:** Runs every 10 minutes (cron: `*/10 * * * *`) or manually via the Actions tab.
3. **Secrets Used:**
   - `EMAIL_SENDER` → Gmail address
   - `EMAIL_PASSWORD` → App password
   - `EMAIL_RECEIVER` → Receiver email
4. **Workflow Steps:**
   - Checkout the repository
   - Setup Python environment
   - Install dependencies from `requirements.txt`
   - Run `amazon_scraper.py`
   - Commit updated `amazon_data.csv` only if changes exist
