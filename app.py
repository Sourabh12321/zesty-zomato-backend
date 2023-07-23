from pymongo import MongoClient
from flask import Flask, render_template, request, redirect, jsonify
from flask_cors import CORS
from bson.json_util import dumps
from flask_socketio import SocketIO
from bson import ObjectId 
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
import bcrypt

# Load environment variables from .env
load_dotenv()


URL = os.getenv("URL")

app = Flask(__name__)
CORS(app)
client = MongoClient(URL)
db = client['zomato']

app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app)

menu_collection = db['menu']


# Load orders
orders_collection = db['orders']

cart_collection = db['cart']

users = db['user']


@app.route("/register", methods=["POST"])
def register():
    # Get the registration data from the request
    registration_data = request.get_json()
    name = registration_data.get("name")
    email = registration_data.get("email")
    password = registration_data.get("password")

    print(name,email,password)
    # Check if the required fields are provided
    if not name or not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    # Check if the user already exists in the database
    existing_user = users.find_one({"email": email})
    if existing_user:
        return jsonify({"message": "User already exists"}), 409

    # Create a new user document
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    new_user = {
        "name": name,
        "email": email,
        "password": hashed_password
    }
    print(new_user)

    
    users.insert_one(new_user)

    return jsonify({"message": "Registration successful"}), 200


@app.route("/login", methods=["POST"])
def login():
    # Get the login data from the request
    login_data = request.get_json()
    email = login_data.get("email")
    password = login_data.get("password")

    # Check if the required fields are provided
    if not email or not password:
        return jsonify({"message": "Missing required fields"}), 400

    # Check if the user exists in the database
    user = users.find_one({"email": email})
    if not user:
        return jsonify({"message": "Invalid email or password"}), 401

    # Check if the password is correct
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"message": "Invalid email or password"}), 401

    # Generate a JWT token
    
    
    # Get the user's id
    user_id = str(user["_id"])

    # Return the response with the id included
    return jsonify({"message": "Login successful", "name": user["name"], "id": user_id, "email":email}), 200







@app.route("/")
def home():
    return jsonify({"msg":"Home Page"})

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/chatbot_msg",methods=['GET','POST'])
def chatbot_msg():
    if request.method == "POST":
        dish_data = request.get_json()
        message = dish_data.get("messageInput")
        
        if message =="hii" or message=="hello":
            return jsonify({"message": "hello sir, how may i help you"})
        elif message =="how to order food" or message=="order food":
            return jsonify({"message": "Sir you can click on order now"})
        else:
            return jsonify({"message": "Sir you can explore our website"})
        
    
@app.route("/menu", methods=["GET"])
def get_menu():
    menu = list(menu_collection.find())

    # Convert ObjectId to string for serialization
    for item in menu:
        item["_id"] = str(item["_id"])

    return jsonify(menu)





@app.route("/add_dish", methods=["GET", "POST"])
def add_dish():
    if request.method == "POST":
        dish_data = request.get_json()
        
        dish_image = dish_data.get("image")
        dish_name = dish_data.get("name")
        dish_price = dish_data.get("price")

        new_dish = {
            
            "name": dish_name,
            "image":dish_image,
            "price": dish_price,
            "availability": True
        }

        menu_collection.insert_one(new_dish)

        return jsonify({"message": "Dish added successfully"})

    
    return render_template("add_dish.html")


@app.route("/update_dish", methods=["GET", "POST"])
def update_dish():
    if request.method == "POST":
        dish_data = request.get_json()
        dish_id = dish_data.get("id")
        availability = dish_data.get("availability")
        price = dish_data.get("price")
        image = dish_data.get("image")
        print(dish_id)
        # Convert dish_id to ObjectId
        dish_id = ObjectId(dish_id)
        print(dish_data,dish_id,availability,price,image)


        # Update the dish in the MongoDB collection
        result = menu_collection.update_one(
            {"_id": dish_id},
            {"$set": {"availability": availability, "price": price, "image": image}}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Dish updated successfully"})
        else:
            return jsonify({"message": "Invalid dish ID"})

    return render_template("update_dish.html")


@app.route("/delete_dish", methods=["GET", "POST"])
def delete_dish():
    if request.method == "POST":
        dish_data = request.get_json()
        dish_id = dish_data.get("id")

        # Convert dish_id to ObjectId
        dish_id = ObjectId(dish_id)

        # Delete the dish from the MongoDB collection
        result = menu_collection.delete_one({"_id": dish_id})

        if result.deleted_count > 0:
            return jsonify({"message": "Dish deleted successfully"})
        else:
            return jsonify({"message": "Invalid dish ID"})

    return render_template("delete_dish.html")

@app.route("/update_order", methods=["GET", "POST"])
def update_order():
    if request.method == "POST":
        dish_data = request.get_json()
        order_id = dish_data.get("order_id")
        new_status = dish_data.get("new_status")

        print(order_id,new_status)
        # Convert order_id to ObjectId
        order_id = ObjectId(order_id)

        result = orders_collection.update_one(
            {"_id": order_id},
            {"$set": {"status": new_status}}
        )

        if result.modified_count > 0:
            # Emit the status update event to all connected clients
            print("modified")
            socketio.emit("status_update", {"order_id": str(order_id), "new_status": new_status}, namespace="/")

            return jsonify({"message": "Order status updated successfully"})
        else:
            return jsonify({"message": "Invalid order ID"})
    orders = list(orders_collection.find())
    return render_template("update_order.html", orders=orders)





@app.route("/new_order", methods=["GET", "POST"])
def new_order():
    if request.method == "POST":
        data = request.get_json()
        customer_name = data.get("customer_name")
        dish_ids = data.get("dish_ids")
        customer_id = data.get("c_id")

        

        print(customer_name, dish_ids)
        print("customer data is here")

        ordered_dishes = []
        for dish_id in dish_ids:
            dish = db.menu.find_one({"_id": ObjectId(dish_id)})
            print(dish)
            ordered_dishes.append(dish)

        if len(ordered_dishes) == len(dish_ids):
            order_status = "received"
            print("main")
            new_order = {
                "customer_name": customer_name,
                "dishes": ordered_dishes,
                "status": order_status,
                "customer_id":customer_id,
            }
            print(new_order)
            orders_collection.insert_one(new_order)
            cart_collection.delete_many({"customer_id": customer_id})

            return jsonify({"message": "Order placed successfully"})
        else:
            return jsonify({"message": "Invalid order"})

    # Handle the GET method
    menu = db.menu.find()  # Retrieve the menu from MongoDB
    return render_template("new_order.html", menu=menu)




@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    customer_id = request.form.get("customer_id")
    dish_id = request.form.get("dish_id")
    print(f"Customer ID: {customer_id}, Dish ID: {dish_id}")

    # Retrieve the dish details from the menu collection
    dish = db.menu.find_one({"_id": ObjectId(dish_id)})
    if dish and dish.get("availability"):
        # Create a new order document
        print(dish)
        new_order = {
            "customer_id": customer_id,
            "image":dish["image"],
            "name":dish["name"],
            "price":dish["price"],
            "dish_id":dish_id,
            "quantity":1,
        }
        # Insert the new order into the orders collection
        cart_collection.insert_one(new_order)

        return jsonify({"message": "Item added to cart"}), 200
    else:
        return jsonify({"message": "Invalid dish"}), 400
    








@app.route("/cart/<customer_id>", methods=["GET", "POST", "DELETE"])
def manage_cart(customer_id):
    if request.method == "GET":
        cart_items = cart_collection.find({"customer_id": customer_id})
        if cart_items:
            cart_items_json = json_util.dumps(list(cart_items))
            return jsonify({"msg": cart_items_json})
        else:
            return jsonify({"msg": "No cart items found for the customer ID"})

    if request.method == "POST":
        quantity = request.json.get("quantity")
        item_id = ObjectId(request.json.get("id"))
        # Update the cart item with the given item_id and customer_id
        cart_collection.update_one({"_id": item_id},{"$set": {"quantity": quantity}},)

        return jsonify({"msg": "Cart item updated successfully"})

    if request.method == "DELETE":
        item_id = ObjectId(customer_id)
        print(item_id)
        # Remove the cart item with the given item_id and customer_id
        cart_collection.delete_one({"_id": item_id})
        return jsonify({"msg": "Cart item removed successfully"})



@app.route("/review_orders/<customer_id>")
def review_orders(customer_id):
    print(customer_id)
    print("data")
    orders = list(orders_collection.find({"customer_id": customer_id}))  # Convert Cursor to a list
    
    # Convert ObjectId values to string representation
    for order in orders:
        order["_id"] = str(order["_id"])
        for dish in order["dishes"]:
            dish["_id"] = str(dish["_id"])
    
    return jsonify(orders)  # Serialize the list of orders to JSON





from bson import json_util

@app.route("/review_orders_data")
def review_orders_data():
    orders = list(orders_collection.find())

    # Convert ObjectId to string for serialization
    for item in orders:
        item["_id"] = str(item["_id"])

    return json_util.dumps(orders)






@app.route("/exit")
def exit_app():
    return "Thank you for using Zesty Zomato! See you soon."


@app.errorhandler(404)
def page_not_found(e):
    return "404 - Page not found"


@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('status_update')
def handle_status_update(data):
    order_id = data.get('order_id')
    new_status = data.get('new_status')

    if order_id and new_status:
        order = orders_collection.find_one({"_id": ObjectId(order_id)})
        if order:
            orders_collection.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": new_status}})
            emit_status_update(order_id, new_status)

def emit_status_update(order_id, new_status):
    socketio.emit('status_update', {'order_id': order_id, 'new_status': new_status}, broadcast=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port,debug=True)