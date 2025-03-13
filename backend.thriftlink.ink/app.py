from flask import Flask, request, jsonify
import bcrypt
from common import sql_connect
import json
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def authorize_user(email: str, password: str):
    """
    Checks if the (email, password) combo is valid.
    If valid, returns the user_id (int).
    If invalid, returns None.
    """
    db, cur = sql_connect()
    sql = "SELECT user_id, password FROM users WHERE email = %s"
    cur.execute(sql, (email,))
    row = cur.fetchone()

    if not row:
        cur.close()
        db.close()
        return None

    user_id, hashed_password = row

    # Compare the incoming password with the stored (hashed) password
    if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
        cur.close()
        db.close()
        return user_id
    else:
        cur.close()
        db.close()
        return None


@app.route('/')
def hello():
    return "Hello from Flask on backend.thriftlink.ink!"


@app.route("/createUser", methods=["POST"])
def create_user():
    """
    Create a new user (no authorization required here).
    Expects JSON:
      {
        "username": "...",
        "password": "...",
        "email": "...",  # Must be unique
        "profile_picture_url": "..." (optional)
      }
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    profile_picture_url = data.get("profile_picture_url")

    # Basic validation
    if not username or not password or not email:
        return jsonify({"error": "Missing required fields"}), 400

    # Hash the password before storing
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    db, cur = sql_connect()

    # Check if email already exists
    check_sql = "SELECT user_id FROM users WHERE email = %s"
    cur.execute(check_sql, (email,))
    existing_user = cur.fetchone()
    if existing_user:
        cur.close()
        db.close()
        return jsonify({"error": "Email already in use"}), 400

    # Create the new user
    insert_sql = """
        INSERT INTO users (username, password, email, profile_picture_url)
        VALUES (%s, %s, %s, %s)
    """
    val = (username, hashed_password, email, profile_picture_url)
    cur.execute(insert_sql, val)
    db.commit()

    user_id = cur.lastrowid
    cur.close()
    db.close()

    return jsonify({"message": "User created", "user_id": user_id}), 201


@app.route("/updateUser", methods=["PUT"])
def update_user():
    """
    Allows a user to update their own username and/or profile picture URL.

    Expects JSON:
      {
        "email": "user_email@example.com",     # required for authorization
        "password": "user_password",          # required for authorization
        "username": "New Username",           # optional
        "profile_picture_url": "http://..."   # optional
      }

    Returns:
      401 Unauthorized if email/password are invalid
      400 if neither username nor profile_picture_url is provided
      200 on successful update
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    username = data.get("username")
    profile_picture_url = data.get("profile_picture_url")

    # Must have email and password for authentication
    if not email or not password:
        return jsonify({"error": "Missing required authentication fields"}), 400

    # Authorize the user (this function should return the user's ID if valid, or None if invalid)
    authorized_user_id = authorize_user(email, password)
    if not authorized_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # If neither field to update was provided, there's nothing to change
    if username is None and profile_picture_url is None:
        return jsonify({"error": "Nothing to update"}), 400

    db, cur = sql_connect()

    # Build a dynamic SQL update based on the fields provided
    update_fields = []
    update_values = []

    if username is not None:
        update_fields.append("username = %s")
        update_values.append(username)
    if profile_picture_url is not None:
        update_fields.append("profile_picture_url = %s")
        update_values.append(profile_picture_url)

    update_sql = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
    update_values.append(authorized_user_id)

    cur.execute(update_sql, tuple(update_values))
    db.commit()

    cur.close()
    db.close()

    return jsonify({"message": "User updated successfully"}), 200


@app.route("/createListing", methods=["POST"])
def create_listing():
    """
    Create a listing.
    Expects JSON:
      {
        "email": "user_email@example.com",   # for authentication
        "password": "user_password",         # for authentication
        "title": "My Product",
        "price": 123.45
      }

    Returns:
      401 if unauthorized
      400 if missing required fields
      201 on success
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    title = data.get("title")
    price = data.get("price")
    description = data.get("description")


    # Basic checks
    if not email or not password:
        return jsonify({"error": "Missing authentication fields"}), 400
    if not title or price is None:
        return jsonify({"error": "Missing required listing fields"}), 400

    # Authorize user
    authorized_user_id = authorize_user(email, password)
    if not authorized_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    db, cur = sql_connect()

    # Insert new listing
    insert_sql = """
        INSERT INTO listings (user_id, title, price, description)
        VALUES (%s, %s, %s, %s)
    """
    cur.execute(insert_sql, (authorized_user_id, title, price, description))
    db.commit()

    listing_id = cur.lastrowid
    cur.close()
    db.close()

    return jsonify({"message": "Listing created successfully", "listing_id": listing_id}), 201


@app.route("/updateListing", methods=["PUT"])
def update_listing():
    """
    Update an existing listing.
    Expects JSON:
      {
        "listing_id": 123,
        "email": "user_email@example.com",   # must match listing's owner
        "password": "user_password",
        "title": "Updated Title",            # optional
        "price": 99.99                       # optional
      }

    Returns:
      400 if listing_id missing
      401 if unauthorized
      403 if user doesn't own the listing
      200 on success
    """
    data = request.get_json()
    listing_id = data.get("listing_id")
    email = data.get("email")
    password = data.get("password")
    new_title = data.get("title")
    new_price = data.get("price")
    description = data.get("description")


    # Must provide listing_id, email, password
    if not listing_id or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    # Authorize user
    authorized_user_id = authorize_user(email, password)
    if not authorized_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Make sure at least one field to update was provided
    if new_title is None and new_price is None and description is None:
        return jsonify({"error": "Nothing to update"}), 400

    db, cur = sql_connect()

    # Check that the listing exists and belongs to the authenticated user
    check_sql = "SELECT user_id FROM listings WHERE listing_id = %s"
    cur.execute(check_sql, (listing_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        db.close()
        return jsonify({"error": "Listing not found"}), 404

    owner_id = row[0]
    if owner_id != authorized_user_id:
        cur.close()
        db.close()
        return jsonify({"error": "You do not own this listing"}), 403

    # Build an update statement dynamically for provided fields
    update_fields = []
    update_values = []

    if new_title is not None:
        update_fields.append("title = %s")
        update_values.append(new_title)
    if new_price is not None:
        update_fields.append("price = %s")
        update_values.append(new_price)
    if description is not None:
        update_fields.append("description = %s")
        update_values.append(description)


    update_sql = f"UPDATE listings SET {', '.join(update_fields)} WHERE listing_id = %s"
    update_values.append(listing_id)

    cur.execute(update_sql, tuple(update_values))
    db.commit()

    cur.close()
    db.close()

    return jsonify({"message": "Listing updated successfully"}), 200


@app.route("/deleteListing", methods=["DELETE"])
def delete_listing():
    """
    Soft-delete (inactivate) an existing listing by changing its status to 'inactive'.
    Expects JSON:
      {
        "listing_id": 123,
        "email": "user_email@example.com",
        "password": "user_password"
      }

    Returns:
      400 if missing required fields
      401 if unauthorized
      403 if listing is not owned by the user
      404 if listing is not found
      200 if inactivation is successful
    """
    data = request.get_json()
    listing_id = data.get("listing_id")
    email = data.get("email")
    password = data.get("password")

    # Basic validation
    if not listing_id or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    # Authenticate the user
    authorized_user_id = authorize_user(email, password)
    if not authorized_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    db, cur = sql_connect()

    # Verify the listing exists and belongs to the authenticated user
    check_sql = "SELECT user_id, status FROM listings WHERE listing_id = %s"
    cur.execute(check_sql, (listing_id,))
    row = cur.fetchone()
    
    if not row:
        cur.close()
        db.close()
        return jsonify({"error": "Listing not found"}), 404

    owner_id, current_status = row
    if owner_id != authorized_user_id:
        cur.close()
        db.close()
        return jsonify({"error": "You do not own this listing"}), 403

    # If already inactive, return success without making changes
    if current_status == "inactive":
        cur.close()
        db.close()
        return jsonify({"message": "Listing is already inactive"}), 200

    # Soft delete by updating status to 'inactive'
    update_sql = "UPDATE listings SET status = 'inactive' WHERE listing_id = %s"
    cur.execute(update_sql, (listing_id,))
    db.commit()

    cur.close()
    db.close()

    return jsonify({"message": "Listing status changed to 'inactive'"}), 200



@app.route("/addListingPhoto", methods=["PUT"])
def add_listing_photo():
    """
    Add a photo to a listing.
    Expects JSON:
      {
        "email": "user_email@example.com",   # for authentication
        "password": "user_password",         # for authentication
        "listing_id": 123,
        "photo_url": "https://example.com/image.jpg"
      }

    Returns:
      400 if missing required fields
      401 if unauthorized
      403 if listing is not owned by the user
      404 if listing does not exist
      201 if photo is successfully added
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    listing_id = data.get("listing_id")
    photo_url = data.get("photo_url")

    # Basic validation
    if not email or not password or not listing_id or not photo_url:
        return jsonify({"error": "Missing required fields"}), 400

    # Authenticate user
    authorized_user_id = authorize_user(email, password)
    if not authorized_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    db, cur = sql_connect()

    # Ensure the listing exists and is owned by the authenticated user
    check_sql = "SELECT user_id FROM listings WHERE listing_id = %s"
    cur.execute(check_sql, (listing_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        db.close()
        return jsonify({"error": "Listing not found"}), 404

    owner_id = row[0]
    if owner_id != authorized_user_id:
        cur.close()
        db.close()
        return jsonify({"error": "You do not own this listing"}), 403

    # Insert photo record
    insert_sql = """
        INSERT INTO listing_photos (listing_id, photo_url)
        VALUES (%s, %s)
    """
    cur.execute(insert_sql, (listing_id, photo_url))
    db.commit()

    photo_id = cur.lastrowid
    cur.close()
    db.close()

    return jsonify({"message": "Photo added successfully", "photo_id": photo_id}), 201


@app.route("/deleteListingPhoto", methods=["DELETE"])
def delete_listing_photo():
    """
    Delete a photo from a listing.
    Expects JSON:
      {
        "email": "user_email@example.com",   # for authentication
        "password": "user_password",         # for authentication
        "photo_id": 456
      }

    Returns:
      400 if missing required fields
      401 if unauthorized
      403 if user does not own the listing
      404 if photo does not exist
      200 if photo is deleted
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    photo_id = data.get("photo_id")

    # Basic validation
    if not email or not password or not photo_id:
        return jsonify({"error": "Missing required fields"}), 400

    # Authenticate user
    authorized_user_id = authorize_user(email, password)
    if not authorized_user_id:
        return jsonify({"error": "Unauthorized"}), 401

    db, cur = sql_connect()

    # Ensure the photo exists and belongs to a listing owned by the user
    check_sql = """
        SELECT lp.listing_id, l.user_id 
        FROM listing_photos lp
        JOIN listings l ON lp.listing_id = l.listing_id
        WHERE lp.photo_id = %s
    """
    cur.execute(check_sql, (photo_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        db.close()
        return jsonify({"error": "Photo not found"}), 404

    listing_id, owner_id = row
    if owner_id != authorized_user_id:
        cur.close()
        db.close()
        return jsonify({"error": "You do not own this listing's photo"}), 403

    # Delete the photo
    delete_sql = "DELETE FROM listing_photos WHERE photo_id = %s"
    cur.execute(delete_sql, (photo_id,))
    db.commit()

    cur.close()
    db.close()

    return jsonify({"message": "Photo deleted successfully"}), 200




@app.route("/getListings", methods=["GET"])
def get_listings():
    """
    Retrieve all active listings within a given time range.
    Expects query parameters:
      - startTime: YYYY-MM-DD HH:MM:SS
      - endTime: YYYY-MM-DD HH:MM:SS

    Returns:
      - 400 if missing or invalid parameters.
      - 200 with a JSON array of listings.
    """
    start_time = request.args.get("startTime")
    end_time = request.args.get("endTime")

    # Validate parameters
    if not start_time or not end_time:
        return jsonify({"error": "Missing required query parameters: startTime, endTime"}), 400

    db, cur = sql_connect()

    # Fetch listings with full photo details
    sql = """
        SELECT 
            l.listing_id, l.title, l.price, l.description, l.status, l.created_at,
            u.user_id, u.username, u.email, u.profile_picture_url,
            COALESCE(lp.photos, '[]') AS photos
        FROM listings l
        JOIN users u ON l.user_id = u.user_id
        LEFT JOIN (
            SELECT listing_id, 
                   JSON_ARRAYAGG(JSON_OBJECT(
                       'photo_id', photo_id,
                       'photo_url', photo_url,
                       'uploaded_at', uploaded_at
                   )) AS photos
            FROM listing_photos
            GROUP BY listing_id
        ) lp ON l.listing_id = lp.listing_id
        WHERE l.status = 'active'
        AND l.created_at BETWEEN %s AND %s
        ORDER BY l.created_at DESC;
    """
    
    cur.execute(sql, (start_time, end_time))
    listings = cur.fetchall()

    cur.close()
    db.close()

    # Format the response
    result = []
    for row in listings:
        result.append({
            "listing_id": row[0],
            "title": row[1],
            "price": row[2],
            "description": row[3],
            "status": row[4],
            "created_at": row[5],
            "user": {
                "user_id": row[6],
                "username": row[7],
                "email": row[8],
                "profile_picture_url": row[9]
            },
            "photos": json.loads(row[10]) if row[10] and row[10] != 'null' else []
        })

    return jsonify(result), 200





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
