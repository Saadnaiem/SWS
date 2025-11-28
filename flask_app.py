from flask import Flask, render_template, request, send_file
import pandas as pd
import io
import os
import time
import re
from scraper_lib import get_driver, scrape_nahdi, scrape_aldawaa

app = Flask(__name__)
app.secret_key = os.urandom(24)

def generate_filename_from_url(url):
    try:
        # Remove protocol
        name = url.split('://')[-1]
        # Remove query params
        name = name.split('?')[0]
        # Replace non-alphanumeric characters with underscores
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        # Limit length
        name = name[:50]
        # Remove trailing underscores
        name = name.strip('_')
        return f"{name}.csv"
    except:
        return "scraped_products.csv"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    headless_mode = request.form.get('headless') == 'true'
    
    if not url:
        return "URL is required", 400

    driver = get_driver(headless=headless_mode)
    
    try:
        data = []
        if "nahdi" in url.lower():
            data = scrape_nahdi(driver, url)
        elif "al-dawaa" in url.lower():
            data = scrape_aldawaa(driver, url)
        
        if not data:
            return "No data found or scraping failed.", 500
            
        # Add numbering
        enriched_data = []
        for i, item in enumerate(data, 1):
            new_item = {'No.': i}
            new_item.update(item)
            enriched_data.append(new_item)
            
        df = pd.DataFrame(enriched_data)
        
        # Create buffer
        buffer = io.BytesIO()
        # Write with BOM for Excel compatibility
        df.to_csv(buffer, index=False, encoding='utf-8-sig')
        buffer.seek(0)
        
        filename = generate_filename_from_url(url)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return f"An error occurred: {str(e)}", 500
    finally:
        driver.quit()

if __name__ == '__main__':
    app.run(debug=True)
