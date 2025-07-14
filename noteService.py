# database branch
from functools import wraps
import jwt
from flask import Flask, jsonify, request, abort
from dbConnection import get_dbConnection

app = Flask(__name__)

secretKey = "my-super‑secret‑key"
algorithm = "HS256"


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        authHeader = request.headers.get("Authorization", "")
        if not authHeader.startswith("Bearer "):
            abort(401, description="Missing or malformed Authorization header")
        token = authHeader.split(" ", 1)[1]

        try:
            payload = jwt.decode(token, secretKey, algorithms=[algorithm])
        except jwt.ExpiredSignatureError:
            abort(401, description="Token expired – log in again")
        except jwt.InvalidTokenError:
            abort(401, description="Invalid or malformed token")

        request.current_user = payload["sub"]
        return fn(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET"])
def home():
    return "Welcome to the Notes service", 200


@app.route("/notes", methods=["GET"])
@token_required
def get_notes():
    userId = request.current_user
    conn = get_dbConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, title, content FROM notes WHERE user_id = %s",
        (userId,)
    )
    notes = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(notes), 200


@app.route("/notes/<int:noteId>", methods=["GET"])
@token_required
def get_note(noteId):
    userId = request.current_user
    conn = get_dbConnection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, title, content FROM notes WHERE id = %s AND user_id = %s",
        (noteId, userId)
    )
    note = cursor.fetchone()
    cursor.close()
    conn.close()
    if note is None:
        abort(404, description="Note not found")
    return jsonify(note), 200


@app.route("/notes", methods=["POST"])
@token_required
def create_note():
    userId = request.current_user
    data = request.get_json()
    title = data.get("title")
    content = data.get("content")

    if not title or not content:
        abort(400, description="Both 'title' and 'content' are required")

    conn = get_dbConnection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)",
        (userId, title, content)
    )
    conn.commit()
    note_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"id": note_id, "title": title, "content": content}), 201


@app.route("/notes/<int:noteId>", methods=["PUT"])
@token_required
def update_note(noteId):
    userId = request.current_user
    data = request.get_json()

    fields = []
    values = []
    if "title" in data:
        fields.append("title = %s")
        values.append(data["title"])
    if "content" in data:
        fields.append("content = %s")
        values.append(data["content"])
    if not fields:
        abort(400, description="No fields to update")

    values.extend([noteId, userId])
    query = f"UPDATE notes SET {', '.join(fields)} WHERE id = %s AND user_id = %s"

    conn = get_dbConnection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(values))
    conn.commit()
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        abort(404, description="Note not found or no change made")

    # fetch updated note
    cursor.close()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, title, content FROM notes WHERE id = %s AND user_id = %s",
        (noteId, userId)
    )
    note = cursor.fetchone()
    cursor.close()
    conn.close()

    return jsonify(note), 200


@app.route("/notes/<int:noteId>", methods=["DELETE"])
@token_required
def delete_note(noteId):
    userId = request.current_user
    conn = get_dbConnection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM notes WHERE id = %s AND user_id = %s",
        (noteId, userId)
    )
    conn.commit()
    deleted = cursor.rowcount
    cursor.close()
    conn.close()

    if deleted == 0:
        abort(404, description="Note not found")
    return jsonify({"note deleted": {"id": noteId}}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)


# from functools import wraps
# import jwt
# from flask import Flask, jsonify, request, abort
# 
# app = Flask(__name__)
# 
# secretKey = "my-super‑secret‑key"
# algorithm = "HS256"
# 
# 
# noteDict = {}
# noteCounters = {}
# 
# 
# def token_required(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         authHeader = request.headers.get("Authorization", "")
#         if not authHeader.startswith("Bearer "):
#             abort(401, description="Missing or malformed Authorization header")
#         token = authHeader.split(" ", 1)[1]
# 
#         try:
#             payload = jwt.decode(token, secretKey, algorithms=[algorithm])
#         except jwt.ExpiredSignatureError:
#             abort(401, description="Token expired – log in again")
#         except jwt.InvalidTokenError:
#             abort(401, description="Invalid token")
# 
#         request.current_user = payload["sub"]
#         return fn(*args, **kwargs)
#     return wrapper
# 
# 
# @app.route("/", methods=["GET"])
# def home():
#     print("server is running")
#     return "Welcome to the Notes ", 200
# 
# 
# @app.route("/notes", methods=["GET"])
# @token_required
# def getNotes():
#     userId = request.current_user
#     return jsonify(list(noteDict.get(userId, {}).values())), 200
# 
# 
# @app.route("/notes/<int:noteId>", methods=["GET"])
# @token_required
# def getNote(noteId: int):
#     userId = request.current_user
#     note = noteDict.get(userId, {}).get(noteId)
#     if note is None:
#         abort(404, description="Note not found")
#     return jsonify(note), 200
# 
# 
# @app.route("/notes", methods=["POST"])
# @token_required
# def createNote():
#     userId = request.current_user
#     data = request.get_json()
#     title = data.get("title")
#     content = data.get("content")
# 
#     if not title or not content:
#         abort(400, description="Both 'title' and 'content' are required")
# 
#     # Init user notes and counter if not present
#     if userId not in noteDict:
#         noteDict[userId] = {}
#         noteCounters[userId] = 1
# 
#     noteId = noteCounters[userId]
#     note = {"id": noteId, "title": title, "content": content}
#     noteDict[userId][noteId] = note
#     noteCounters[userId] += 1
# 
#     return jsonify(note), 201
# 
# 
# @app.route("/notes/<int:noteId>", methods=["PUT"])
# @token_required
# def updateNote(noteId: int):
#     userId = request.current_user
#     note = noteDict.get(userId, {}).get(noteId)
#     if note is None:
#         abort(404, description="Note not found")
# 
#     data = request.get_json()
#     note["title"] = data.get("title", note["title"])
#     note["content"] = data.get("content", note["content"])
# 
#     return jsonify(note), 200
# 
# 
# @app.route("/notes/<int:noteId>", methods=["DELETE"])
# @token_required
# def delete_note(noteId):
#     userId = request.current_user
#     userNotes = noteDict.get(userId, {})
#     note = userNotes.pop(noteId, None)
#     if note is None:
#         abort(404, description="Note not found")
# 
#     return jsonify({"note deleted": note}), 200
# 
# 
# if __name__ == "__main__":
#     print("server is running")
#     app.run(debug=True, port=5000)
