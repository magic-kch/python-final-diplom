import flask
from flask import send_file

app = flask.Flask(__name__)
# app.config["DEBUG"] = True

@app.route('/', methods=['GET'])
def home():
    return """
    <a href="/download_shop_yaml">Скачать shop1.yaml</a>
    """
@app.route('/download_shop_yaml')
def download_shop1_yaml():
    return send_file('data/shop1.yaml', as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
