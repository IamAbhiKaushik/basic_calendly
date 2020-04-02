from flask import Flask, request
from pymongo import MongoClient
from bson.json_util import dumps
from datetime import datetime
import jwt

app = Flask(__name__)
# db = MongoClient('mongodb://mongo/test').db # docker
db = MongoClient('mongodb://localhost:27017').db # Local runs
BASE_URL = "http://localhost:5000"
PRIVATE_TOKEN = 'calendly_2020'


@app.route("/")
def home():
	return dumps(db.user_table.find())

@app.route('/signup', methods=['POST'])
def signup():
	request_data = request.get_json()
	existing_user = db.users.find_one({"email": request_data['email']})
	if existing_user is not None:
		return alert_message(False, f"User already exists for email:{request_data['email']}")
	insert_response = db.users.insert_one({
		'created_at': datetime.utcnow(),
		'name': request_data['name'],
		'email': request_data['email'],
		'password': request_data['password']
		})
	return alert_message(True, f"User registered successfully for email:{request_data['email']}")

@app.route('/login', methods=['POST'])
def login():
	request_data = request.get_json()
	if (not 'email' in request_data) or (not 'password' in request_data):
		return alert_message(False, "Bad Request. Required variables missing")

	user = db.users.find_one({'email': request_data['email'], 'password': request_data['password']})
	if not user:
		return alert_message(False, "Bad Credentials. User do not exists.")
	
	# return dumps(user)
	token_data = {
	'email': user.get('email'),
	'id': str(user.get('_id'))
	}
	PUBLIC_TOKEN = jwt.encode(token_data, PRIVATE_TOKEN, algorithm='HS256')
	# return alert_message(True, "Login Successful", auth_token=PUBLIC_TOKEN)
	return dumps(token_data)

def alert_message(code, message, auth_token=None):
	data = {
	'status': code,
	'message': message,
	'auth_token': auth_token
	}
	return dumps(data)

if __name__ == "__main__":
	app.run(debug=True, host='0.0.0.0')

