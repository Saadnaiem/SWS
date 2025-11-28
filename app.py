from flask import Flask, render_template, request, send_file, session, jsonify
import pandas as pd
import io
import os
import time
import re
import threading
import uuid
from scraper_lib import get_driver, scrape_nahdi, scrape_aldawaa

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global dictionary to store progress and results
SCRAPE_STATUS = {}
SCRAPE_RESULTS = {}

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
    try:
        return render_template('index.html')
    except Exception as e:
        import traceback
        return f"<h1>Internal Server Error</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/health')
def health():
    return "OK", 200

@app.route('/progress/<req_id>')
def progress(req_id):
    return jsonify(SCRAPE_STATUS.get(req_id, {'page': 0, 'count': 0, 'status': 'unknown'}))

def run_scrape_task(req_id, url, headless_mode):
    print(f"Task started for {req_id}")
    try:
        driver = get_driver(headless=headless_mode)
        
        def update_status(page, count):
            SCRAPE_STATUS[req_id] = {'page': page, 'count': count, 'status': 'scraping'}

        data = []
        if "nahdi" in url.lower():
            data = scrape_nahdi(driver, url, status_callback=update_status)
        elif "al-dawaa" in url.lower():
            data = scrape_aldawaa(driver, url, status_callback=update_status)
        
        driver.quit()
        
        # Save results
        if data:
            # Add numbering
            enriched_data = []
            for i, item in enumerate(data, 1):
                new_item = {'No.': i}
                new_item.update(item)
                enriched_data.append(new_item)
                
            df = pd.DataFrame(enriched_data)
            # Save to a unique file for this request
            filename = f"scraped_results_{req_id}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            SCRAPE_RESULTS[req_id] = filename
            SCRAPE_STATUS[req_id]['status'] = 'completed'
            SCRAPE_STATUS[req_id]['count'] = len(data)
            print(f"Task {req_id} completed. Saved to {filename}")
        else:
            SCRAPE_STATUS[req_id]['status'] = 'failed'
            SCRAPE_STATUS[req_id]['error'] = 'No data found'
            
    except Exception as e:
        print(f"Task {req_id} failed: {e}")
        SCRAPE_STATUS[req_id]['status'] = 'failed'
        SCRAPE_STATUS[req_id]['error'] = str(e)

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    req_id = request.form.get('req_id')
    headless_mode = request.form.get('headless') == 'true'
    
    if not url:
        return jsonify({'error': "Please enter a valid URL"}), 400
    
    if not req_id:
        req_id = f"req_{int(time.time())}"
    
    # Initialize status
    SCRAPE_STATUS[req_id] = {'page': 0, 'count': 0, 'status': 'starting'}
    
    # Start background thread
    thread = threading.Thread(target=run_scrape_task, args=(req_id, url, headless_mode))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started', 'req_id': req_id})

@app.route('/download/<req_id>')
def download_file(req_id):
    filename = SCRAPE_RESULTS.get(req_id)
    if filename and os.path.exists(filename):
        # Get original URL to generate a nice name if possible, or just use default
        download_name = "scraped_products.csv" 
        return send_file(filename, as_attachment=True, download_name=download_name)
    else:
        return "File not found or expired", 404

@app.route('/results/<req_id>')
def show_results(req_id):
    filename = SCRAPE_RESULTS.get(req_id)
    if filename and os.path.exists(filename):
        df = pd.read_csv(filename)
        data = df.to_dict('records')
        columns = df.columns.values
        return render_template('results.html', 
                               products=data, 
                               columns=columns, 
                               count=len(data),
                               pages=SCRAPE_STATUS.get(req_id, {}).get('page', 0),
                               time_elapsed="N/A", # We didn't store time, but that's fine for now
                               filename="scraped_products.csv",
                               req_id=req_id) # Pass req_id for download link
    else:
        return "Results not found or expired", 404

@app.route('/download')
def download():
    filename = request.args.get('name', 'scraped_products.csv')
    try:
        return send_file("scraped_results.csv", as_attachment=True, download_name=filename)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
