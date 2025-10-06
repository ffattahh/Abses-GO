from flask import Flask
import ssl

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello HTTPS!"

if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host="0.0.0.0", port=5000, ssl_context=context)