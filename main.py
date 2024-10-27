import time
import random
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
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import zipfile
import os
import pytesseract
from PIL import Image
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Proxy authentication details
proxy_username = proxy username
proxy_password = proxy password

# Proxy list with authentication
proxies = [
    "45.127.248.127:5128",
    "64.64.118.149:6732",
    "157.52.253.244:6204",
    "167.160.180.203:6754",
    "166.88.58.10:5735",
    "173.0.9.70:5653",
    "45.151.162.198:6600",
    "204.44.69.89:6342",
    "173.0.9.209:5792",
    "206.41.172.74:6634"
]

# CAPTCHA solving with Tesseract
def solve_captcha(image_path):
    # Load the image using OpenCV for preprocessing
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    cv2.imwrite(image_path, thresh)  # Save the preprocessed image for Tesseract
    captcha_text = pytesseract.image_to_string(Image.open(image_path), config='--psm 8')
    return captcha_text.strip()

def get_user_agents():
    # Randomized user agent generation
    ua = UserAgent()
    header = {"User-Agent": ua.random,
              "Language": 'en-US,en;q=0.9',
              "Encoding": 'gzip, deflate, br',
              "Referer": 'http://www.google.com',
              "DNT": '1',
              "Connection": 'keep-alive'}
    return header

def create_proxy_extension(proxy_host, proxy_port, proxy_username, proxy_password):
    """Create a Chrome extension to handle proxy authentication."""
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
              }},
              bypassList: ["localhost"]
            }}
          }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_username}",
                password: "{proxy_password}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    """

    pluginfile = 'proxy_auth_plugin.zip'

    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return pluginfile

def setup_selenium_with_proxy_and_user_agent(proxy):
    proxy_host, proxy_port = proxy.split(":")
    proxy_extension = create_proxy_extension(proxy_host, proxy_port, proxy_username, proxy_password)

    options = Options()

    # Set up user agent
    user_agent = get_user_agents()
    options.add_argument(f'user-agent={user_agent["User-Agent"]}')

    # Load proxy extension
    options.add_extension(proxy_extension)

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

    # Execute JavaScript to prevent detection by WebDriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

def handle_captcha(driver):
    # Check if CAPTCHA is present
    try:
        captcha_image = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'captcha')]"))
        )
        captcha_src = captcha_image.get_attribute("src")
        captcha_image_path = "captcha_image.png"

        # Download the CAPTCHA image directly
        captcha_image_response = requests.get(captcha_src)
        with open(captcha_image_path, 'wb') as f:
            f.write(captcha_image_response.content)

        # Solve the CAPTCHA using OCR (e.g., Tesseract)
        captcha_text = solve_captcha(captcha_image_path)
        logging.info(f"CAPTCHA Solved: {captcha_text}")

        # Enter the CAPTCHA text
        captcha_input = driver.find_element(By.XPATH, "//input[@class='a-span12']")
        captcha_input.send_keys(captcha_text)

        # Click on the "Continue" button
        continue_button = driver.find_element(By.XPATH, "//button[@class='a-button-text']")
        continue_button.click()

        # Give time for the page to reload
        time.sleep(3)

        # Recheck for CAPTCHA - if still present, consider it a failure
        if driver.find_elements(By.XPATH, "//img[contains(@src, 'captcha')]"):
            logging.warning("Failed to solve CAPTCHA, skipping product.")
            return False
    except (TimeoutException, NoSuchElementException):
        logging.info("No CAPTCHA detected.")
        return True
    return True

def get_product_details(driver, url, title, price, rating):
    logging.info(f"Fetching product details from URL: {url}")
    driver.get(url)

    if not handle_captcha(driver):
        return None  # Skip the product if CAPTCHA fails

    details = {
        "URL": url,
        "Title": title,
        "Price": price,
        "Rating": rating,
    }
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'a-keyvalue prodDetTable')]")))
    except TimeoutException:
        logging.warning("Timeout error while waiting for product details table.")

    search_terms = {
        "Processor": ["Processor", "CPU"],
        "RAM": ["RAM", "Memory"],
        "Memory Speed": ["Memory Speed", "Speed"],
        "Storage": ["Hard Drive", "Storage"],
        "GPU": ["Graphics Coprocessor", "GPU", "Graphics Card"],
        "GPU RAM Size": ["Graphics Card Ram Size", "GPU RAM", "Graphics Memory"],
    }

    for key, terms in search_terms.items():
        found = False
        for term in terms:
            try:
                details[key] = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, f"//tr[th[contains(text(), '{term}')]]/td"))
                ).text
                found = True
                break
            except (TimeoutException, NoSuchElementException):
                continue
        if not found:
            details[key] = " "

    return details

def amazon_main(page_number):
    logging.info(f"Fetching Amazon search results from page {page_number}...")
    h = get_user_agents()
    url = f"https://www.amazon.com/s?k=gaming+laptops&page={page_number}&qid=1719630661&ref=sr_pg_{page_number}"
    response = requests.get(url, headers=h)
    if response.status_code != 200:
        logging.error(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})

    product_links = []
    product_data = []

    for container in product_containers:
        is_sponsored = False

        # More accurate detection for sponsored products
        sponsored_label = container.find('span', class_='a-color-secondary')
        if sponsored_label:
            label_text = sponsored_label.get_text().lower()
            if 'sponsored' in label_text:
                is_sponsored = True

        if not is_sponsored:
            link_element = container.find('a')
            link = 'https://www.amazon.com' + link_element['href'] if link_element else "N/A"
            product_links.append(link)

            title = container.find('span', class_='a-size-medium a-color-base a-text-normal').text if container.find(
                'span', class_='a-size-medium a-color-base a-text-normal') else "N/A"
            price = container.find('span', class_='a-color-base').text if container.find('span',
                                                                                         class_='a-color-base') else "N/A"
            rating = container.find('span', class_='a-icon-alt').text if container.find('span',
                                                                                        class_='a-icon-alt') else "N/A"

            product_data.append({
                "URL": link,
                "Title": title,
                "Price": price,
                "Rating": rating
            })
        else:
            logging.info("Sponsored product detected and skipped.")

    return product_links, product_data

def process_product(link, title, price, rating, proxy):
    logging.info(f"Processing product URL: {link}")
    driver = setup_selenium_with_proxy_and_user_agent(proxy)
    details = get_product_details(driver, link, title, price, rating)
    driver.quit()
    return details

if __name__ == '__main__':
    all_product_details = []

    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        future_to_url = {}
        for page_number in range(1, 11):
            product_links, product_data = amazon_main(page_number)
            for product in product_data:
                url = product["URL"]
                title = product["Title"]
                price = product["Price"]
                rating = product["Rating"]
                future = executor.submit(process_product, url, title, price, rating,
                                         proxies[len(future_to_url) % len(proxies)])
                future_to_url[future] = url

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                if data:
                    all_product_details.append(data)
            except Exception as e:
                logging.error(f"Error processing URL {url}: {e}")

    df = pd.DataFrame(all_product_details)
    df.to_csv('amazon_product_details.csv', index=False)

    logging.info("Data saved to amazon_product_details.csv")

    os.remove('proxy_auth_plugin.zip')

