from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import re
import random
import sys
import os

def extract_category_from_url(url):
    try:
        # Remove query parameters
        url = url.split('?')[0]
        parts = url.split('/')
        
        # Filter out common non-category parts
        ignore_list = [
            "https:", "http:", "", "www.nahdionline.com", "www.al-dawaa.com", 
            "en-sa", "ar-sa", "english", "arabic", "pdp", "plp", "catalog", "product", "view", "id",
            "en", "ar", "c"
        ]
        
        categories = []
        for part in parts:
            if part and part not in ignore_list:
                # Check if it's a numeric ID (sometimes mixed with text, but usually pure numbers are IDs)
                if not re.match(r'^\d+$', part):
                    # Format: baby-care -> Baby Care
                    formatted = part.replace('-', ' ').title()
                    categories.append(formatted)
        
        if categories:
            return " > ".join(categories)
        return "Unknown Category"
    except:
        return "Unknown Category"

def get_driver(headless=False):
    print("Attempting to initialize Chrome Driver...")

    # Method 0: Undetected Chromedriver (Best for bypassing blocks)
    try:
        print("Method 0: Undetected Chromedriver...")
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        if headless:
            options.add_argument("--headless=new")
            
        # Try without version_main first, let UC detect it
        driver = uc.Chrome(options=options, use_subprocess=True)
        return driver
    except Exception as e:
        print(f"Method 0 (UC) failed: {e}")
        # Retry with version_main=131 as fallback
        try:
            print("Retrying Method 0 with version_main=131...")
            driver = uc.Chrome(options=options, use_subprocess=True, version_main=131)
            return driver
        except Exception as e2:
            print(f"Method 0 (UC) retry failed: {e2}")

    # Standard Selenium Options (Fallback)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")

    # Method 1: Selenium Manager
    try:
        print("Method 1: Selenium Manager...")
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2: WebDriver Manager
    try:
        print("Method 2: WebDriver Manager...")
        path = ChromeDriverManager().install()
        service = Service(path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Method 2 failed: {e}")

    raise Exception("Could not initialize Chrome Driver.")

def scrape_nahdi(driver, base_url, status_callback=None):
    products = []
    seen_signatures = set() 
    
    category_name = extract_category_from_url(base_url)

    if "?page=" not in base_url and "&page=" not in base_url:
        if "?" in base_url:
            base_url += "&page={}"
        else:
            base_url += "?page={}"
    else:
        base_url = re.sub(r'page=\d+', 'page={}', base_url)

    page = 1
    
    while True:
        url = base_url.format(page)
        if status_callback:
            status_callback(page=page, count=len(products))
        
        driver.get(url)
        
        # Wait for products to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.flex.h-full.flex-col"))
            )
        except:
            pass
            
        time.sleep(random.uniform(2, 4))
        
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
        except:
            last_height = 0
            
        for _ in range(3): 
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            except Exception:
                break
            
        product_cards = []
        
        # Strategy 1
        cards1 = driver.find_elements(By.CSS_SELECTOR, "a.flex.h-full.flex-col")
        if len(cards1) > 0:
            product_cards = cards1
        
        # Strategy 2
        if not product_cards:
            try:
                name_spans = driver.find_elements(By.CSS_SELECTOR, "span.line-clamp-3")
                unique_cards = []
                seen_links = set()
                for span in name_spans:
                    try:
                        parent_anchor = span.find_element(By.XPATH, "./ancestor::a")
                        link = parent_anchor.get_attribute("href")
                        if link and link not in seen_links:
                            unique_cards.append(parent_anchor)
                            seen_links.add(link)
                    except:
                        continue
                if unique_cards:
                    product_cards = unique_cards
            except Exception as e:
                pass

        if not product_cards:
            break
            
        new_products_count = 0
        for i, card in enumerate(product_cards):
            try:
                name = ""
                try:
                    name = card.find_element(By.CSS_SELECTOR, "span.line-clamp-3").text.strip()
                except:
                    pass

                if not name:
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        alt = img.get_attribute("alt")
                        if alt and len(alt) > 3:
                            name = alt
                    except:
                        pass
                
                if not name:
                    try:
                        name = card.get_attribute("aria-label")
                    except:
                        pass

                if not name or len(name) < 3 or "{" in name or "sar_symbol" in name:
                    href = card.get_attribute("href")
                    if href:
                        parts = href.split("/")
                        for part in parts:
                            if part and part not in ["en-sa", "pdp", "https:", "", "www.nahdionline.com"]:
                                if "-" in part:
                                    name = part.replace("-", " ").title()
                                    break
            except:
                name = "Unknown Product"
            
            try:
                price_without_discount = card.find_element(By.CSS_SELECTOR, "span.text-gray-dark").text.strip()
            except:
                price_without_discount = ""
                
            try:
                regular_price = card.find_element(By.CSS_SELECTOR, ".line-through").text.strip()
            except:
                regular_price = ""
                
            try:
                price_after_discount = card.find_element(By.CSS_SELECTOR, ".text-red").text.strip()
            except:
                price_after_discount = ""
                
            if (not regular_price and not price_after_discount and not price_without_discount):
                try:
                    full_text = card.get_attribute("innerText")
                    found_prices = re.findall(r'(\d{1,5}\.\d{2})', full_text)
                    
                    if len(found_prices) >= 2:
                        float_prices = sorted([float(p) for p in found_prices], reverse=True)
                        regular_price = str(float_prices[0])
                        price_after_discount = str(float_prices[1])
                    elif len(found_prices) == 1:
                        price_without_discount = str(found_prices[0])
                except Exception:
                    pass

            try:
                discount_percent = ""
                try:
                    badge = card.find_element(By.CSS_SELECTOR, "div[class*='bg-red'], div[class*='bg-yellow']")
                    raw_text = badge.get_attribute("textContent").strip()
                    raw_text = " ".join(raw_text.split())
                    if "Save" in raw_text and not " _ " in raw_text:
                         discount_percent = raw_text.replace("Save", " _ Save")
                    else:
                         discount_percent = raw_text
                except:
                    pass
                
                if not discount_percent:
                    discount_percent = card.find_element(By.CSS_SELECTOR, "span.text-white").text.strip()
            except:
                discount_percent = ""
            
            try:
                product_link = card.get_attribute("href")
                if product_link and product_link.startswith("/"):
                    product_link = "https://www.nahdionline.com" + product_link
            except:
                product_link = ""
            
            product_signature = (name, price_after_discount, regular_price)
            
            if product_signature not in seen_signatures:
                seen_signatures.add(product_signature)
                new_products_count += 1
                
            products.append({
                "Product Name": name,
                "Regular Price": regular_price,
                "Price After Discount": price_after_discount,
                "Price Without Discount": price_without_discount,
                "Discount %": discount_percent,
                "Category": category_name,
                "Image Link": product_link,
                "Source": "Nahdi"
            })
        
        if new_products_count == 0 and len(products) > 0:
            break
            
        page += 1
            
    unique_products = []
    seen = set()
    for p in products:
        sig = (p["Product Name"], p["Price After Discount"], p["Regular Price"])
        if sig not in seen:
            seen.add(sig)
            unique_products.append(p)
            
    return unique_products

def scrape_aldawaa(driver, start_url, status_callback=None):
    products = []
    
    category_name = extract_category_from_url(start_url)
    
    try:
        time.sleep(2)
        driver.get(start_url)
    except Exception:
        return []
        
    wait = WebDriverWait(driver, 20)
    page_num = 1
    
    while True:
        if status_callback:
            status_callback(page=page_num, count=len(products))
            
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3))
        except:
            pass
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-detail-section, li.product-item")))
        except TimeoutException:
            pass
        
        cards = driver.find_elements(By.CSS_SELECTOR, ".product-detail-section")
        
        if not cards:
            cards = driver.find_elements(By.CSS_SELECTOR, "li.product-item")

        if not cards:
            cards = driver.find_elements(By.CSS_SELECTOR, "[class*='product-item-info']")

        if not cards:
            break
            
        for card in cards:
            context = card
            try:
                context = card.find_element(By.CSS_SELECTOR, ".product-detail-section")
            except:
                pass

            try:
                name = context.find_element(By.CLASS_NAME, "product-name").text.strip()
            except:
                try:
                    name = context.find_element(By.CSS_SELECTOR, "a.product-item-link").text.strip()
                except:
                    name = ""
            
            selling_price = ""
            old_price = ""
            
            try:
                price_element = context.find_element(By.CSS_SELECTOR, ".icon-saudi_riyal")
                selling_price = price_element.find_element(By.XPATH, "..").text.strip()
            except:
                try:
                    selling_price = context.find_element(By.CSS_SELECTOR, "[data-price-type='finalPrice'] .price").text.strip()
                except:
                    selling_price = ""

            try:
                old_price = context.find_element(By.CSS_SELECTOR, ".price-section.total").text.strip()
            except:
                try:
                    old_price = context.find_element(By.CSS_SELECTOR, "[data-price-type='oldPrice'] .price").text.strip()
                except:
                    old_price = ""

            if old_price:
                regular_price = old_price
                price_after_discount = selling_price
            else:
                regular_price = selling_price
                price_after_discount = ""
                
            try:
                discount_percent = context.find_element(By.CSS_SELECTOR, ".promotion-style span").text.strip()
            except:
                discount_percent = ""
                
            product_link = ""
            try:
                links = context.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and "/p/" in href:
                        product_link = href
                        break
                
                if not product_link and context != card:
                     links = card.find_elements(By.TAG_NAME, "a")
                     for link in links:
                        href = link.get_attribute("href")
                        if href and "/p/" in href:
                            product_link = href
                            break
                            
                if product_link and not product_link.startswith("http"):
                    product_link = "https://www.al-dawaa.com" + product_link
            except:
                pass
                
            products.append({
                "Product Name": name,
                "Regular Price": regular_price,
                "Price After Discount": price_after_discount,
                "Discount %": discount_percent,
                "Image Link": product_link,
                "Category": category_name,
                "Source": "Al-Dawaa"
            })
            
        try:
            next_button = None
            selectors = [
                "//a[contains(@class, 'next')]",
                "//li[contains(@class, 'next')]/a",
                "//a[@title='Next']",
                "//a[contains(text(), 'Next')]",
                "//a[contains(text(), '›')]",
                "//a[contains(text(), '>')]",
                "//a[contains(@aria-label, 'Next')]"
            ]
            
            for xpath in selectors:
                try:
                    btn = driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed():
                        next_button = btn
                        break
                except NoSuchElementException:
                    continue
            
            if next_button:
                if "disabled" in next_button.get_attribute("class"):
                    break
                
                driver.execute_script("arguments[0].scrollIntoView();", next_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(random.uniform(5, 8))
                page_num += 1
            else:
                break
        except Exception:
            break
            
    return products
