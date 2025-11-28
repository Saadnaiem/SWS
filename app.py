from flask import Flask, render_template, request, send_file, session, jsonify
import pandas as pd
import io
import os
import time
import re
from scraper_lib import get_driver, scrape_nahdi, scrape_aldawaa

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global dictionary to store progress
SCRAPE_STATUS = {}

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

@app.route('/progress/<req_id>')
def progress(req_id):
    return jsonify(SCRAPE_STATUS.get(req_id, {'page': 0, 'count': 0, 'status': 'unknown'}))

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    req_id = request.form.get('req_id')
    headless_mode = request.form.get('headless') == 'true' # Checkbox value
    
    if not url:
        return render_template('index.html', error="Please enter a valid URL")
    
    # Initialize status
    if req_id:
        SCRAPE_STATUS[req_id] = {'page': 0, 'count': 0, 'status': 'running'}
        
    def update_status(page, count):
        if req_id:
            SCRAPE_STATUS[req_id] = {'page': page, 'count': count, 'status': 'running'}

    try:
        # Use headless mode based on user selection
        print(f"Starting scrape for URL: {url}")
        print(f"Headless Mode: {headless_mode}")
        
        start_time = time.time()
        driver = get_driver(headless=headless_mode)
        
        data = []
        if "nahdi" in url.lower():
            print("Scraping Nahdi...")
            data = scrape_nahdi(driver, url, status_callback=update_status)
        elif "al-dawaa" in url.lower():
            print("Scraping Al-Dawaa...")
            data = scrape_aldawaa(driver, url, status_callback=update_status)
        else:
            driver.quit()
            return render_template('index.html', error="Unknown URL. Please use Nahdi or Al-Dawaa.")
            
        driver.quit()
        end_time = time.time()
        
        # Calculate stats
        elapsed_seconds = int(end_time - start_time)
        mins, secs = divmod(elapsed_seconds, 60)
        time_str = f"{mins}m {secs}s"
        
        pages_scraped = 0
        if req_id and req_id in SCRAPE_STATUS:
            pages_scraped = SCRAPE_STATUS[req_id].get('page', 0)
            SCRAPE_STATUS[req_id]['status'] = 'completed'
        
        print(f"Scraping finished. Found {len(data)} items in {time_str}.")
        
        if data:
            # Add numbering and reorder columns
            enriched_data = []
            for i, item in enumerate(data, 1):
                # Create new dict with 'No.' as first key
                new_item = {'No.': i}
                new_item.update(item)
                enriched_data.append(new_item)
            
            # Convert to DataFrame
            df = pd.DataFrame(enriched_data)
            
            # Save to a temporary CSV for download
            temp_file = "scraped_results.csv"
            df.to_csv(temp_file, index=False)
            
            # Generate filename
            download_filename = generate_filename_from_url(url)
            
            # Pass data and columns to template for custom rendering
            return render_template('results.html', 
                                   products=enriched_data, 
                                   columns=df.columns.values, 
                                   count=len(data),
                                   pages=pages_scraped,
                                   time_elapsed=time_str,
                                   filename=download_filename)
        else:
            return render_template('index.html', error="No data found.")
            
    except Exception as e:
        return render_template('index.html', error=f"An error occurred: {str(e)}")

@app.route('/download')
def download():
    filename = request.args.get('name', 'scraped_products.csv')
    try:
        return send_file("scraped_results.csv", as_attachment=True, download_name=filename)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
