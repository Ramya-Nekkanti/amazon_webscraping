# Amazon Scraper – Automated Best Deals Finder

This project automatically scrapes Amazon Canada for **women's shoes/sneakers**, identifies the best deals under $50, and emails only the new or updated deals. Historical data is stored for reporting and auditing.

---

## **Project Overview**

- **Scraper:** Python script (`amazon_scraper.py`) using `requests` and `BeautifulSoup`.
- **Data Extracted:**
  - Product title
  - Price (numeric)
  - Rating
  - Number of reviews
  - Availability
- **Output:** `amazon_data.csv` stores historical data with a `scraped_date` column.
- **Email Notification:** Sends email only for **new or changed deals under $50**.

---

## **Automation Using GitHub Actions**

1. **Workflow File:** `.github/workflows/amazon_scraper.yml`
2. **Schedule:** Runs every 10 minutes (cron: `*/10 * * * *`) or manually via the Actions tab.
3. **Secrets Used:**
   - `EMAIL_SENDER` → Gmail address
   - `EMAIL_PASSWORD` → App password
   - `EMAIL_RECEIVER` → Receiver email
   - `GH_PAT` → Personal Access Token for committing CSV updates
4. **Workflow Steps:**
   - Checkout the repository
   - Setup Python environment
   - Install dependencies from `requirements.txt`
   - Run `amazon_scraper.py`
   - Commit updated `amazon_data.csv` only if changes exist
