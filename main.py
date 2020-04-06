from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.json_util import dumps
from datetime import datetime
import jwt

app = Flask(__name__)
# db = MongoClient('mongodb://mongo/test').db # docker
db = MongoClient('mongodb://localhost:27017').db # Local runs
BASE_URL = "http://localhost:5000"
PRIVATE_TOKEN = 'calendly'
MEETING_HOURS = [ [9, 16] ] # last slot will be [16-17]

@app.route("/")
def home():
	return dumps(db.users.find())
# @app.route('/fetch_all_users')
# def fetch_all_user():
	# response = 
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
		'password': request_data['password'],
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
	token_data = {
	'email': user.get('email'),
	'id': str(user.get('_id'))
	}
	PUBLIC_TOKEN = jwt.encode(token_data, PRIVATE_TOKEN, algorithm='HS256')
	return PUBLIC_TOKEN

@app.route('/add_available_slots', methods=['POST'])
def add_available_slots():
	auth = user_auth(request.headers)
	request_data = request.get_json()
	if not auth['status'] or not request_data:
		return alert_message(False, "User not logged in, Login Please.")
	request_data['free_slots'] = request_data.get('free_slots', MEETING_HOURS)  
	request_data['day_month_year'] = request_data.get('day_month_year', get_current_day_month_year())
	request_data['force_update'] = request_data.get('force_update', False)

	record = db.user_meeting_table.find_one({'owner': auth['email'], 'day_month_year': request_data['day_month_year']})
	if record:
		if request_data['force_update']:
			record['updated_at'] = datetime.utcnow()
			record['free_slots'] = request_data['free_slots']
			db.user_meeting_table.update({'owner': auth['email']}, record)
			return dumps(record)
		else:
			return alert_message(False, "Entry already exists for current datetime. To force update, pass variable `force_update: true`")
	else:
		day_slot_entry = db.user_meeting_table.insert_one({
			'owner': auth['email'],
			'day_month_year': request_data['day_month_year'],
			'free_slots': request_data['free_slots'], # This will be a list of timings like -> [[9, 11], [13, 17]]
			'meeting_slots': dict(),
			'created_at': datetime.utcnow(),
			'updated_at': datetime.utcnow()	
		}) 
		if day_slot_entry.acknowledged:
			return alert_message(True, f"Successfully updated your meeting timings for the day: {request_data['day_month_year']}.")
		return alert_message(False, "Error updating database entry. Try again.")


@app.route('/fetch_meeting_slots', methods=['GET'])
def fetch_meeting_slots():
	auth = user_auth(request.headers)
	if not auth['status']:
		return alert_message(False, "User not logged in, Login Please.")
	response = db.user_meeting_table.find_one({'owner': auth['email']}).get('meeting_slots') 
	return dumps(response)


@app.route('/request_meeting_slot', methods=['POST'])
def request_meeting_slot():
	auth = user_auth(request.headers)
	request_data = request.get_json()
	if not auth['status'] or not request_data:
		return alert_message(False, "User not logged in, Login Please.")
	if ('slot' not in request_data) or ('participant' not in request_data) or ('day_month_year' not in request_data):
		return alert_message(False, "variables missing. try again with proper infromation.")
	
	return validate_available_meeting_slot(request_data['slot'], auth['email'], request_data['participant'], request_data['day_month_year'])


def validate_available_meeting_slot(slot, user, participant, day_month_year):
	participant_data = db.user_meeting_table.find_one({'owner': participant, 'day_month_year': day_month_year})
	check_1 = False	
	for user_slot in participant_data.get('free_slots'):
		if (user_slot[0] <= slot <= user_slot[1]):
			check_1 = True
	# TODO -- CHECK IF USER HAS A FREE SLOT at booking time
	if not check_1 or (slot in participant_data.get('meeting_slots')):
		return alert_message(False, "Requested time slot not available for meeting. Book another slot.")
	
	participant_data['meeting_slots'][slot] = [user, False]
	response = db.user_meeting_table.update({'owner': participant, 'day_month_year': day_month_year}, participant_data)
	if response.acknowledged:
		user_data = db.user_meeting_table.find_one({'owner': user, 'day_month_year': day_month_year})
		if not user_data:
			meeting_slot = {}
			meeting_slot[slot] = [participant, True]
			user_data = {'owner': user,
				'day_month_year': day_month_year,
				'free_slots': MEETING_HOURS, # This will be a list of timings like -> [[9, 11], [13, 17]]
				'meeting_slots': meeting_slot,
				'created_at': datetime.utcnow(),
				'updated_at': datetime.utcnow()	
				}
		else:
			user_data['meeting_slots'][slot] = [participant, True]
			db.user_meeting_table.update({'owner': user, 'day_month_year': day_month_year}, user_data)
		
		

	# TODO- modify user table with this detail as well.
	# user['meeting_slots'][slot] = [participant, True]
	return response


@app.route('/fetch_available_slots', methods=['GET'])
def fetch_available_slots():
	auth = user_auth(request.headers)
	# request_data = request.get_json()
	# request_data['day_month_year'] = request_data.get('day_month_year', )
	user_old_record = db.user_meeting_table.find({'owner': auth['email']})
	return dumps(user_old_record)


@app.route('/filter_user', methods=['GET'])
def filter_user():
	auth = user_auth(request.headers)
	if auth['status']:
		return dumps(auth)
	else:
		return alert_message("False", "User not Authorized. Login again.")
	# auth_header = request.headers['Authorization']
	# auth_token = jwt.decode(auth_header, PRIVATE_TOKEN, algorithm='HS256')
	
	# jwt.decode(token, 'secret', audience='urn:foo', algorithms=['HS256'])
	return dumps(auth_token)

	filter_text = request.args.get('user')
	#	TODO Add remaining functions here
	# 1. FETCH ALL USER FROM TABLE, MATCH FOR RELEVENT USERS AND RETURN A LIST OF USERS MATCHING THE SUBSTRING
	return filter_text









def user_auth(headers):
	if 'Authorization' not in headers:
		return {'status': False}
	auth_token = jwt.decode(headers['Authorization'], PRIVATE_TOKEN, algorithms=['HS256'])
	auth_token['status'] = True
	return auth_token

def get_current_day_month_year():
	return datetime.today().strftime('%d-%m-%Y')

def alert_message(code, message, auth_token=None):
	# TODO- add response varable here only. 
	data = {
	'status': code,
	'message': message,
	'auth_token': auth_token
	}
	return dumps(data)

if __name__ == "__main__":
	app.run(debug=True, host='0.0.0.0')


