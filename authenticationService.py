import os
from datetime import datetime, timedelta
from typing import Dict

import jwt  
from flask import Flask, request, jsonify, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

secretKey = "my-super‑secret‑key"
algorithm = "HS256"
accessTokenExpiryMinutes = 60  

usersDb = {}


def createAccessToken(username: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(minutes=accessTokenExpiryMinutes),
    }
    token = jwt.encode(payload, secretKey, algorithm=algorithm)
    # print(token)
    return token


def verifyJWT(token):
    try:
        decoded = jwt.decode(token, secretKey, algorithms=[algorithm])
        return decoded
    except jwt.ExpiredSignatureError:
        abort(401, description="Token expired – log in again")
    except jwt.InvalidTokenError:
        abort(401, description="Invalid or malformed token")


@app.route("/register", methods=["POST"])
def registerUser():
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if not username or not password:
        abort(400, description="Both 'username' and 'password' are required")

    if username in usersDb:
        abort(409, description="Username already taken")

    usersDb[username] = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
    return jsonify({"message": "User registered successfully."}), 201


@app.route("/login", methods=["POST"])
def loginUser():
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    storedHash = usersDb.get(username)
    if storedHash is None or not check_password_hash(storedHash, password):
        abort(401, description="Invalid username or password")

    token = createAccessToken(username)
    response = make_response(jsonify({"message": "login successful"}))
    response.headers['Authorization'] = f"Bearer {token}"
    return response, 200


@app.route("/debug", methods=["POST"])
def debug_decode():
    token = request.json.get("token", "")
    payload = verifyJWT(token)
    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)