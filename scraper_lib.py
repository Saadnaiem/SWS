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

    # Check for Render-specific Chrome path
    chrome_binary_path = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
    if not os.path.exists(chrome_binary_path):
        # Fallback for local testing or other paths
        chrome_binary_path = None

    # Method 0: Undetected Chromedriver (Best for bypassing blocks)
    try:
        print("Method 0: Undetected Chromedriver...")
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1920,1080")
        
        if chrome_binary_path:
            print(f"Setting binary location to: {chrome_binary_path}")
            options.binary_location = chrome_binary_path
        
        if headless:
            options.add_argument("--headless")
            
        driver = uc.Chrome(options=options, use_subprocess=True)
        return driver
    except Exception as e:
        print(f"Method 0 (UC) failed: {e}")

    # Standard Selenium Options
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3") # Suppress console logs
    
    if chrome_binary_path:
        options.binary_location = chrome_binary_path
    
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    
    # Anti-detection settings
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Update to a newer User-Agent (Chrome 131)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    
    # Stability settings
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")

    driver = None
    
    # Helper to try initializing with a service
    def try_init_driver(service_obj):
        return webdriver.Chrome(service=service_obj, options=options)
    
    err1 = "Not attempted"
    err2 = "Not attempted"
    err3 = "Not attempted"

    # Method 1: Selenium Manager (Built-in)
    # This is the standard way for Selenium 4.10+
    try:
        print("Method 1: Selenium Manager...")
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        err1 = str(e)
        print(f"Method 1 failed: {e}")

    # Method 2: WebDriver Manager (Auto-Detect) - MOVED UP
    # This is better at handling version mismatches (like Chrome 142 vs Driver 131)
    try:
        print("Method 2: WebDriver Manager (Auto-Detect)...")
        from webdriver_manager.chrome import ChromeDriverManager
        try:
             path = ChromeDriverManager().install()
        except TypeError:
             path = ChromeDriverManager().install()
             
        service = Service(path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        err2 = str(e)
        print(f"Method 2 failed: {e}")

    # Method 3: Manual Download (Fallback) - Windows Only
    if os.name == 'nt':
        try:
            print("Method 3: Manual Download of Chrome Driver (v131)...")
            import zipfile
            import requests
            import shutil
            
            # Define path for local driver
            base_dir = os.path.dirname(os.path.abspath(__file__))
            bin_dir = os.path.join(base_dir, "bin")
            driver_path = os.path.join(bin_dir, "chromedriver-win64", "chromedriver.exe")
            
            # Check if already exists
            if not os.path.exists(driver_path):
                print("Downloading driver manually...")
                os.makedirs(bin_dir, exist_ok=True)
                
                # URL for Chrome for Testing (Stable 131)
                url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.204/win64/chromedriver-win64.zip"
                zip_path = os.path.join(bin_dir, "driver.zip")
                
                # Download
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    with open(zip_path, 'wb') as f:
                        shutil.copyfileobj(response.raw, f)
                    
                    # Extract
                    print("Extracting driver...")
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(bin_dir)
                    
                    # Cleanup
                    os.remove(zip_path)
                else:
                    raise Exception(f"Failed to download driver. Status: {response.status_code}")
            
            if os.path.exists(driver_path):
                print(f"Using manually downloaded driver at: {driver_path}")
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=options)
                return driver
                
        except Exception as e:
            err3 = str(e)
            print(f"Method 3 failed: {e}")
    else:
        err3 = "Skipped (Not Windows)"
    
    raise Exception(f"Could not initialize Chrome Driver. \nMethod 1 Error: {err1}\nMethod 2 Error: {err2}\nMethod 3 Error: {err3}")

    # Remove navigator.webdriver flag (this code is unreachable if we return early, 
    # but we need to apply it to the driver instance before returning in the blocks above.
    # Refactoring to apply it inside the success blocks would be cleaner, but for now
    # let's just rely on the fact that we return 'driver' from the blocks.)


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
        time.sleep(random.uniform(5, 8))
        
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
        except:
            last_height = 0
            
        for _ in range(5): 
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 3))
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
            print(f"Strategy 1 found {len(cards1)} cards")
        
        # Strategy 2
        if not product_cards:
            print("Strategy 1 failed, trying Strategy 2...")
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
                    print(f"Strategy 2 found {len(unique_cards)} cards")
            except Exception as e:
                print(f"Strategy 2 error: {e}")

        if not product_cards:
            print("No product cards found on page.")
            # Save debug html
            try:
                with open("debug_nahdi_fail.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved debug_nahdi_fail.html")
            except:
                pass
            break
            
        new_products_count = 0
        for i, card in enumerate(product_cards):
            try:
                name = ""
                
                # Strategy A: Specific Selector (Most accurate)
                try:
                    name = card.find_element(By.CSS_SELECTOR, "span.line-clamp-3").text.strip()
                except:
                    pass

                # Strategy B: Image Alt Text (Very reliable for Nahdi)
                if not name:
                    try:
                        img = card.find_element(By.TAG_NAME, "img")
                        alt = img.get_attribute("alt")
                        if alt and len(alt) > 3:
                            name = alt
                    except:
                        pass
                
                # Strategy C: Aria Label on Anchor
                if not name:
                    try:
                        name = card.get_attribute("aria-label")
                    except:
                        pass

                # Strategy D: URL Fallback (Guaranteed to exist if it's a link)
                # Also use this if the found name looks like garbage (contains CSS or too long/short)
                if not name or len(name) < 3 or "{" in name or "sar_symbol" in name:
                    href = card.get_attribute("href")
                    if href:
                        # Extract slug from URL: /en-sa/product-name/pdp/123 -> product-name
                        parts = href.split("/")
                        for part in parts:
                            if part and part not in ["en-sa", "pdp", "https:", "", "www.nahdionline.com"]:
                                # Check if it looks like a product name (has hyphens)
                                if "-" in part:
                                    name = part.replace("-", " ").title()
                                    break
            except:
                name = "Unknown Product"
            
            if i == 0:
                print(f"DEBUG: First card name extracted: '{name}'")
                # print(f"DEBUG: First card full text: '{card.text}'")
                try:
                    print(f"DEBUG: First card HTML: {card.get_attribute('outerHTML')[:500]}...")
                except:
                    pass
            
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
                
            # Fallback: If prices are missing, try to parse from full text using Regex
            if (not regular_price and not price_after_discount and not price_without_discount):
                try:
                    full_text = card.get_attribute("innerText")
                    # Look for numbers like 123.45
                    found_prices = re.findall(r'(\d{1,5}\.\d{2})', full_text)
                    
                    if len(found_prices) >= 2:
                        # Convert to floats to sort
                        float_prices = sorted([float(p) for p in found_prices], reverse=True)
                        # Assumption: Higher price is Regular, Lower is Discounted
                        regular_price = str(float_prices[0])
                        price_after_discount = str(float_prices[1])
                    elif len(found_prices) == 1:
                        # Only one price found, assume it's the selling price
                        price_without_discount = str(found_prices[0])
                except Exception as e:
                    print(f"DEBUG: Price fallback failed: {e}")

            try:
                discount_percent = ""
                # Strategy 1: Look for the badge container (Red/Yellow background)
                try:
                    # Nahdi badges are usually in a rounded div with red or yellow background
                    badge = card.find_element(By.CSS_SELECTOR, "div[class*='bg-red'], div[class*='bg-yellow']")
                    # Get text content but replace newlines/multiple spaces with ' _ '
                    raw_text = badge.get_attribute("textContent").strip()
                    # Normalize whitespace
                    raw_text = " ".join(raw_text.split())
                    # If it looks like "ONLINE EXCLUSIVE Save 25%", insert the separator
                    # We can try to split by "Save" or just use the raw text if it's already good
                    # But the user specifically asked for " _ " separator.
                    # Let's try to detect if there are two distinct parts (e.g. text + number%)
                    if "Save" in raw_text and not " _ " in raw_text:
                         discount_percent = raw_text.replace("Save", " _ Save")
                    else:
                         discount_percent = raw_text
                except:
                    pass
                
                # Strategy 2: Look for white text (Old method)
                if not discount_percent:
                    discount_percent = card.find_element(By.CSS_SELECTOR, "span.text-white").text.strip()
            except:
                discount_percent = ""
            
            if i == 0:
                print(f"DEBUG: First card discount found: '{discount_percent}'")

            try:
                product_link = card.get_attribute("href")
                # Ensure absolute URL if it comes back relative (though Selenium usually gives absolute)
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
            
    # Deduplicate
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
        time.sleep(2) # Give driver a moment to settle
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
            time.sleep(random.uniform(3, 6))
        except:
            pass
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-detail-section, li.product-item")))
        except TimeoutException:
            pass
        
        # Strategy 1: Original Selector
        cards = driver.find_elements(By.CSS_SELECTOR, ".product-detail-section")
        
        # Strategy 2: Standard Magento Selector (Container)
        if not cards:
            cards = driver.find_elements(By.CSS_SELECTOR, "li.product-item")
            if cards:
                print(f"DEBUG: Strategy 2 (li.product-item) found {len(cards)} cards")

        # Strategy 3: Generic Product Container (Broadest)
        if not cards:
            cards = driver.find_elements(By.CSS_SELECTOR, "[class*='product-item-info']")
            if cards:
                print(f"DEBUG: Strategy 3 (product-item-info) found {len(cards)} cards")

        if not cards:
            print(f"DEBUG: No cards found on Al-Dawaa page {page_num}.")
            print(f"DEBUG: Page Title: {driver.title}")
            # Check for common blocking messages
            page_source = driver.page_source.lower()
            if "access denied" in page_source or "403 forbidden" in page_source or "security check" in page_source:
                print("DEBUG: POTENTIAL BLOCK DETECTED (403/Access Denied)")
            
            # Save debug HTML
            try:
                with open("debug_aldawaa_fail.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved debug_aldawaa_fail.html")
            except:
                pass
            break
            
        for card in cards:
            # Determine context for details (Name, Price)
            # If we found the container (li.product-item), we might need to look deeper
            context = card
            try:
                # Try to narrow down to detail section if it exists
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
                # Fallback price selector
                try:
                    selling_price = context.find_element(By.CSS_SELECTOR, "[data-price-type='finalPrice'] .price").text.strip()
                except:
                    selling_price = ""

            try:
                old_price = context.find_element(By.CSS_SELECTOR, ".price-section.total").text.strip()
            except:
                # Fallback old price selector
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
                
            try:
                card_text = context.text
                match = re.search(r"Ends in (\d+D \d+H \d+M \d+S)", card_text)
                if match:
                    promotion_ends = match.group(0)
                else:
                    promotion_ends = ""
            except:
                promotion_ends = ""
            
            # Extract Product Link (Image Link)
            product_link = ""
            try:
                # Try finding 'a' tag with href in the context
                links = context.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and "/p/" in href:
                        product_link = href
                        break
                
                # If not found in context, try the parent card if context was narrowed down
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
