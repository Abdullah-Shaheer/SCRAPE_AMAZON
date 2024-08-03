import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

proxy_username = "your_username"
proxy_password = "your_password"

proxies = [
    f"http://{proxy_username}:{proxy_password}@45.127.248.127:5128",
    f"http://{proxy_username}:{proxy_password}@207.244.217.165:6712",
    f"http://{proxy_username}:{proxy_password}@134.73.69.7:5997",
    f"http://{proxy_username}:{proxy_password}@64.64.118.149:6732",
    f"http://{proxy_username}:{proxy_password}@157.52.253.244:6204",
    f"http://{proxy_username}:{proxy_password}@167.160.180.203:6754",
    f"http://{proxy_username}:{proxy_password}@166.88.58.10:5735",
    f"http://{proxy_username}:{proxy_password}@173.0.9.70:5653",
    f"http://{proxy_username}:{proxy_password}@204.44.69.89:6342",
    f"http://{proxy_username}:{proxy_password}@173.0.9.209:5792"
]


def get_user_agents():
    ua = UserAgent()
    header = {
        "User-Agent": ua.random,
        "Language": 'en-US,en;q=0.9',
        "Encoding": 'gzip, deflate, br',
        "Referer": 'http://www.google.com',
        "DNT": '1',
        "Connection": 'keep-alive'
    }
    return header


def setup_selenium_with_proxy_and_user_agent(proxy):
    options = Options()

    # Set up user agent
    user_agent = get_user_agents()
    options.add_argument(f'user-agent={user_agent["User-Agent"]}')

    # Set proxy
    options.add_argument(f'--proxy-server={proxy}')

    # Preventing bot detection
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    # Set language, encoding, and other headers
    prefs = {
        "intl.accept_languages": "en-US,en",
        "disable-web-security": True,
        "allow-running-insecure-content": True
    }
    options.add_experimental_option("prefs", prefs)
    s = Service("D:/Python Files/WebScraping/chromedriver-win64/chromedriver-win64/chromedriver.exe")
    driver = webdriver.Chrome(service=s, options=options)

    # To further prevent detection, you can execute JavaScript to remove WebDriver flag
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def get_product_details(driver, url):
    driver.get(url)
    details = {"URL": url}  # Add the URL to the details dictionary
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'a-keyvalue prodDetTable')]"))
        )
    except TimeoutException:
        print("There is a timeout error inside finding the table to fetch the content")
    try:
        details["Title"] = driver.find_element(By.XPATH, "//span[@class='a-size-large product-title-word-break']").text
    except (TimeoutException, NoSuchElementException):
        details["Title"] = " "
    try:
        details['Price'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr/td/span/span[@class='a-offscreen']"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['Price'] = " "

    try:
        details['Processor'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Processor')]]/td"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['Processor'] = " "

    try:
        details['RAM'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'RAM')]]/td"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['RAM'] = " "

    try:
        details['Memory Speed'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Memory Speed')]]/td"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['Memory Speed'] = " "

    try:
        details['Storage'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Hard Drive')]]/td"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['Storage'] = " "

    try:
        details['GPU'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Graphics Coprocessor')]]/td"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['GPU'] = " "

    try:
        details['GPU RAM Size'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tr[th[contains(text(), 'Graphics Card Ram Size')]]/td"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['GPU RAM Size'] = " "

    try:
        details['Rating'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span/a/span[@class='a-size-base a-color-base']"))
        ).text
    except (TimeoutException, NoSuchElementException):
        details['Rating'] = " "
    try:
        time.sleep(2)
        details["Complete Product Description"] = driver.find_element(By.XPATH, "//div/div/div/p/span").text
    except (TimeoutException, NoSuchElementException):
        details['Complete Product Description'] = " "

    return details


def amazon_main(page_number, proxy):
    h = get_user_agents()
    url = f"https://www.amazon.com/s?k=gaming+laptops&page={page_number}&qid=1719630661&ref=sr_pg_{page_number}"

    # Setup retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.proxies = {"http": proxy, "https": proxy}

    try:
        response = session.get(url, headers=h, timeout=10)
        response.raise_for_status()
    except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
        print(f"Failed to retrieve page {page_number} using proxy {proxy}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all product containers
    product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})

    product_links = []

    for container in product_containers:
        # Check if the product is sponsored
        sponsored_label = container.find('span', class_='puis-label-popover-default')
        is_sponsored = False
        if sponsored_label:
            for i in sponsored_label:
                text = sponsored_label.find('span', class_="a-color-secondary").text
                if 'sponsored' in text.lower():
                    is_sponsored = True
                    break
        if not is_sponsored:
            # Extract product link
            link_element = container.find('a')
            link = 'https://www.amazon.com' + link_element['href'] if link_element else "N/A"
            product_links.append(link)

    return product_links


if __name__ == '__main__':
    all_product_details = []
    for page_number in range(1, 11):  # Loop through the first 10 pages
        print(f"Processing page {page_number}...")
        proxy = proxies[page_number % len(proxies)]
        product_links = amazon_main(page_number, proxy)
        d = setup_selenium_with_proxy_and_user_agent(proxy)
        for link in product_links:
            details = get_product_details(d, link)
            all_product_details.append(details)
        d.quit()

    # Save to CSV
    df = pd.DataFrame(all_product_details)
    df.to_csv('amazon_product_details.csv', index=False)
    print("Data saved to amazon_product")
