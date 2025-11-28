from flask import Flask, render_template, request, send_file, jsonify
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
    return render_template('index.html')

@app.route('/progress/<req_id>')
def progress(req_id):
    return jsonify(SCRAPE_STATUS.get(req_id, {'page': 0, 'count': 0, 'status': 'unknown'}))

@app.route('/download/<req_id>')
def download(req_id):
    filename = SCRAPE_RESULTS.get(req_id)
    if not filename or not os.path.exists(filename):
        return "File not found", 404
    
    return send_file(
        filename,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

@app.route('/results/<req_id>')
def results(req_id):
    filename = SCRAPE_RESULTS.get(req_id)
    status = SCRAPE_STATUS.get(req_id, {})
    
    if not filename or not os.path.exists(filename):
        return "File not found", 404
    
    try:
        df = pd.read_csv(filename)
        # Convert NaN to empty string for better display
        df = df.fillna('')
        products = df.to_dict('records')
        columns = df.columns.tolist()
        
        return render_template(
            'results.html',
            products=products,
            columns=columns,
            count=status.get('count', 0),
            pages=status.get('page', 0),
            time_elapsed=status.get('elapsed', '0s'),
            req_id=req_id
        )
    except Exception as e:
        return f"Error reading results: {str(e)}", 500

def run_scrape_task(req_id, url, headless_mode):
    print(f"Task started for {req_id}")
    start_time = time.time()
    try:
        driver = get_driver(headless=headless_mode)
        
        def update_status(page, count):
            print(f"Req {req_id}: Page {page}, Count {count}")
            SCRAPE_STATUS[req_id] = {'page': page, 'count': count, 'status': 'scraping'}

        data = []
        if "nahdi" in url.lower():
            data = scrape_nahdi(driver, url, status_callback=update_status)
        elif "al-dawaa" in url.lower():
            data = scrape_aldawaa(driver, url, status_callback=update_status)
        
        driver.quit()
        
        end_time = time.time()
        elapsed_seconds = int(end_time - start_time)
        mins, secs = divmod(elapsed_seconds, 60)
        elapsed_str = f"{mins}m {secs}s"
        
        # Save results
        if data:
            # Add numbering
            enriched_data = []
            for i, item in enumerate(data, 1):
                new_item = {'No.': i}
                new_item.update(item)
                enriched_data.append(new_item)
                
            df = pd.DataFrame(enriched_data)
            filename = generate_filename_from_url(url)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            SCRAPE_RESULTS[req_id] = filename
            SCRAPE_STATUS[req_id] = {
                'status': 'completed',
                'count': len(data),
                'page': SCRAPE_STATUS.get(req_id, {}).get('page', 0),
                'elapsed': elapsed_str
            }
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
    headless_mode = request.form.get('headless') == 'true'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    req_id = str(uuid.uuid4())
    SCRAPE_STATUS[req_id] = {'page': 0, 'count': 0, 'status': 'starting'}
    
    thread = threading.Thread(target=run_scrape_task, args=(req_id, url, headless_mode))
    thread.start()
    
    return jsonify({'req_id': req_id})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5500))
    host = os.environ.get('HOST', '127.0.0.1')
    print(f"Starting Flask server on http://{host}:{port}")
    app.run(debug=True, host=host, port=port)
