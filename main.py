from flask import Flask, request, redirect
from pymongo import MongoClient
from bson.json_util import dumps
from datetime import datetime
import jwt

app = Flask(__name__)
db = MongoClient('mongodb://mongo/test').db  # docker
# db = MongoClient('mongodb://localhost:27017').db  # Local runs
BASE_URL = "http://localhost:5000"
PRIVATE_TOKEN = 'calendly'
MEETING_HOURS = [[9, 16]]  # last slot will be [16-17]


@app.route("/")
def home():
    return "Welcome to Calendly App Test App"
    # return dumps(db.users.find())


@app.route('/signup', methods=['POST'])
def signup():
    """
    Register new user
    """
    request_data = request.get_json()
    existing_user = db.users.find_one({"email": request_data['email']})
    if existing_user is not None:
        return alert_message(False, f"User already exists for email:{request_data['email']}")
    # TODO -- Store password in hashed format.
    response = db.users.insert_one({
        'created_at': datetime.utcnow(),
        'name': request_data['name'],
        'email': request_data['email'],
        'password': request_data['password']
    })
    if response.acknowledged:
        return alert_message(True, f"User registered successfully for email:{request_data['email']}")
    return alert_message(False, "User registration Failed. Please try again.")


@app.route('/login', methods=['POST'])
def login():
    """
     Login Function
    """
    request_data = request.get_json()
    if ('email' not in request_data) or ('password' not in request_data):
        return alert_message(False, "Bad Request. Required variables missing")
    # TODO -- Compare the hashed format of password. Do this once signup is implemented.
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
    """
    API for user to define his/her available meeting slots for the given day.
    """
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
            response = db.user_meeting_table.update({'owner': auth['email'], 'day_month_year': request_data['day_month_year']}, record)
            return alert_message(True, f"Successfully updated meeting timings for : {request_data['day_month_year']}.")
        else:
            return alert_message(
                False, "Entry already exists for current datetime. To force update, pass variable `force_update: true`"
            )
    else:
        day_slot_entry = db.user_meeting_table.insert_one({
            'owner': auth['email'],
            'day_month_year': request_data['day_month_year'],
            'free_slots': request_data['free_slots'],  # This will be a list of timings like -> [[9, 11], [13, 17]]
            'meeting_slots': dict(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        if day_slot_entry.acknowledged:
            return alert_message(True, f"Successfully updated meeting timings for : {request_data['day_month_year']}.")
        return alert_message(False, "Error updating database entry. Try again.")


@app.route('/fetch_all_meetings', methods=['GET'])
def fetch_all_meetings():
    """
    Fetch all meetings of User
    :return:
    """
    auth = user_auth(request.headers)
    if not auth['status']:
        return alert_message(False, "User not logged in, Login Please.")
    responses = db.user_meeting_table.find({'owner': auth['email']})
    # return dumps(responses)
    if responses is not None:
        data = []
        for resp in responses:
            data.append({'day':resp.get('day_month_year'), 'meetings':resp.get('meeting_slots')})
        return dumps(data)
    return alert_message(False, "User has no meeting scheduled.")


@app.route('/meeting_slots/<day>', methods=['GET'])
def meeting_slots(day):
    """
    Fetch all meetings scheduled for a particular day
    :param day: Day value in datetime.today().strftime('%d-%m-%Y') format
    """
    auth = user_auth(request.headers)
    if not auth['status']:
        return alert_message(False, "User not logged in, Login Please.")
    response = db.user_meeting_table.find_one({'owner': auth['email'], 'day_month_year': day})
    if response is not None:
        return dumps(response.get('meeting_slots'))
    return alert_message(False, "User has no meeting scheduled.")


@app.route('/meetings_today', methods=['GET'])
def meetings_today():
    """
    Fetch all meetings that are scheduled for today
    """
    auth = user_auth(request.headers)
    if not auth['status']:
        return alert_message(False, "User not logged in, Login Please.")
    return redirect(f'/meeting_slots/{get_current_day_month_year()}')


@app.route('/request_meeting_slot', methods=['POST'])
def request_meeting_slot():
    """
    Request a meeting with participant for a particular date and time
    """
    auth = user_auth(request.headers)
    request_data = request.get_json()
    if not auth['status'] or not request_data:
        return alert_message(False, "User not logged in, Login Please.")
    if ('slot' not in request_data) or ('participant' not in request_data):
        return alert_message(False, "Variables missing. Try again with proper information.")
    if not is_user_registered(request_data['participant']):
        return alert_message(False, "No User associated with the email ID provided.")
    request_data['day_month_year'] = request_data.get('day_month_year', get_current_day_month_year())
    return book_meeting_slot(int(request_data['slot']),
                             auth['email'],
                             request_data['participant'],
                             request_data['day_month_year'])


def book_meeting_slot(slot, user, participant, day_month_year):
    """
    Function to book a meeting slot between user and participant for given day and time.
    """
    participant_data = db.user_meeting_table.find_one({'owner': participant, 'day_month_year': day_month_year})
    user_data = db.user_meeting_table.find_one({'owner': user, 'day_month_year': day_month_year})
    if user_data and (str(slot) in user_data.get('meeting_slots')):
        return alert_message(False, "You already have meeting in this slot. Choose some diffent time slot.")
    if not participant_data:
        return alert_message(False, "Participant has no free time for the meeting day Requested.")
    check_1 = False
    for user_slot in participant_data.get('free_slots'):
        if user_slot[0] <= slot <= user_slot[1]:
            check_1 = True
    if not check_1 or (str(slot) in participant_data.get('meeting_slots')):
        return alert_message(False, "Requested time slot not available for meeting. Book another slot.")

    participant_data['meeting_slots'][str(slot)] = [user,
                                               False]  # Second element of list helps in defining who fixed the meeting.
    response = db.user_meeting_table.update({'owner': participant, 'day_month_year': day_month_year}, participant_data)
    # if response.acknowledged:
    if not user_data:
        user_data = {
            'owner': user,
            'day_month_year': day_month_year,
            'free_slots': MEETING_HOURS,  # This will be a list of timings like -> [[9, 11], [13, 17]]
            'meeting_slots': {str(slot): [participant, True]},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    else:
        user_data['meeting_slots'][str(slot)] = [participant, True]

    user_response = db.user_meeting_table.update({'owner': user, 'day_month_year': day_month_year}, user_data)

    return dumps(user_response)


@app.route('/user_check', methods=['GET'])
def user_check():
    auth = user_auth(request.headers)
    user = request.args.get('user', None)
    if not auth['status']:
        return alert_message(False, "User not logged in, Login Please.")
    if (user is None):
        return alert_message("Request not correct. Add argument 'user' to request.")
    return dumps(is_user_registered(user))


@app.route('/test')
def test():
    return dumps(is_user_registered('abcd@gmail'))

def is_user_registered(user):
    user_data = db.users.find_one({'email': user})
    return user_data is not None


def user_auth(headers):
    failed_status = {'status': False}
    if 'Authorization' not in headers:
        return failed_status
    try:
        auth_token = jwt.decode(headers['Authorization'], PRIVATE_TOKEN, algorithms=['HS256'])
    except:
        return failed_status
    if 'email' not in auth_token or 'id' not in auth_token:
        return failed_status
    user = db.users.find_one({'email': auth_token['email']})
    if not user:
        return failed_status
    auth_token['status'] = True
    return auth_token


def get_current_day_month_year():
    return datetime.today().strftime('%d-%m-%Y')


def alert_message(code, message):
    data = {
        'status': code,
        'message': message,
    }
    return dumps(data)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
