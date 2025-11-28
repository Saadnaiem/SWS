from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "<h1>Minimal App Working</h1>"

if __name__ == '__main__':
    print("Running minimal app on http://127.0.0.1:5500")
    app.run(host='127.0.0.1', port=5500, debug=True)