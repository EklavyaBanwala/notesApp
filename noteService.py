#redis code
from functools import wraps
import jwt
from flask import Flask, jsonify, request, abort
import redis  # Added: Redis client import to replace in-memory dicts

app = Flask(__name__)

secretKey = "my-super‑secret‑key"
algorithm = "HS256"

# Changed: removed the old in-memory stores
# noteDict = {}
# noteCounters = {}

# Added: connect to local Redis (persistent, shared across restarts)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


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
            abort(401, description="Invalid token")

        request.current_user = payload["sub"]
        return fn(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET"])
def home():
    print("server is running")
    return "Welcome to the Notes ", 200


@app.route("/notes", methods=["GET"])
@token_required
def getNotes():
    userId = request.current_user
    # Changed: fetch all Redis keys for this user's notes
    keys = r.keys(f"user:{userId}:note:*")
    notes = [r.hgetall(key) for key in keys]
    return jsonify(notes), 200


@app.route("/notes/<int:noteId>", methods=["GET"])
@token_required
def getNote(noteId: int):
    userId = request.current_user
    key = f"user:{userId}:note:{noteId}"
    # Changed: fetch the hash; r.hgetall returns {} if not found
    note = r.hgetall(key)
    if not note:
        abort(404, description="Note not found")
    return jsonify(note), 200


@app.route("/notes", methods=["POST"])
@token_required
def createNote():
    userId = request.current_user
    data = request.get_json()
    title = data.get("title")
    content = data.get("content")

    if not title or not content:
        abort(400, description="Both 'title' and 'content' are required")

    # Changed: use Redis INCR to get a unique per-user note ID
    noteId = r.incr(f"user:{userId}:nextId")

    # Changed: store note fields in a Redis hash
    r.hset(f"user:{userId}:note:{noteId}", mapping={
        "id": noteId,
        "title": title,
        "content": content
    })

    return jsonify({"id": noteId, "title": title, "content": content}), 201


@app.route("/notes/<int:noteId>", methods=["PUT"])
@token_required
def updateNote(noteId: int):
    userId = request.current_user
    key = f"user:{userId}:note:{noteId}"
    # Changed: ensure the note exists in Redis
    if not r.exists(key):
        abort(404, description="Note not found")

    data = request.get_json()
    mapping = {}
    # Changed: only update provided fields
    if "title" in data:
        mapping["title"] = data["title"]
    if "content" in data:
        mapping["content"] = data["content"]

    r.hset(key, mapping=mapping)
    note = r.hgetall(key)
    return jsonify(note), 200


@app.route("/notes/<int:noteId>", methods=["DELETE"])
@token_required
def delete_note(noteId):
    userId = request.current_user
    key = f"user:{userId}:note:{noteId}"
    # Changed: delete the key; r.delete returns number of keys removed
    deleted = r.delete(key)
    if deleted == 0:
        abort(404, description="Note not found")

    return jsonify({"note deleted": {"id": noteId}}), 200


if __name__ == "__main__":
    print("server is running")
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


