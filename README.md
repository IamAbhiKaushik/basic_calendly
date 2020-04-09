# Basic Calendly backend service 
A backend service based on python and flask

How to Run:

1. git clone git@github.com:IamAbhiKaushik/flask-backend.git
2. cd basic_calendly
3. `docker build -t basic_calendly:latest .`
4. `docker run -d -p 5000:5000 basic_calendly`
5. Go to `http://localhost:5000` in your browser for accessing backend API services.

## To Run the APIS in POSTMAN,
[![Run in Postman](https://run.pstmn.io/button.svg)](https://app.getpostman.com/run-collection/a36c05549f50fcd64aec)

## To run a mongo container, run the below command:
```
docker run -d \
  -e MONGO_INITDB_DATABASE=db \
  -p 27017:27017 mongo
```

## To go inside any running docker container: `docker exec -it <container ID> /bin/bash`


# New Update: V02
1. Added docker-compose file and mongo db base code
2. To run the code.. 
`docker-compse build`
`docker-compose up` 

Visit http://0.0.0.0:5000/ or http://localhost:5000 to verify Flask running


#	Error Issues while running locally:
while running python main.py, if you get an error that something else is running at port 5000, 
you can check that using <br>
`sudo lsof -i:5000`
and stop that service or <br>
`python -m SimpleHTTPServer 8910 main.py` run on different port. 


## Helpful URLs: 
1. https://medium.com/datadriveninvestor/writing-a-simple-flask-web-application-in-80-lines-cb5c386b089a
2. https://www.freecodecamp.org/news/how-to-build-a-web-application-using-flask-and-deploy-it-to-the-cloud-3551c985e492/
3. https://runnable.com/docker/python/dockerize-your-flask-application
4. https://scotch.io/bar-talk/processing-incoming-request-data-in-flask
5. https://docs.mongodb.com/manual/core/index-unique/


## APIs Exposed -- (Instructions for running from POSTMAN)
Base URL: http://localhost:5000

1. /signup -- POST
`URL: http://127.0.0.1:5000/signup
Request Body(raw, type=json):
{
    "name": "Abhinav",
    "email": "abhi@gmail",
    "password": "password@abc"
}
Expected Response:
{"status": true, "message": "User registered successfully for email:abhi@gmail"}
`

2. /login -- POST
`URL: http://127.0.0.1:5000/login
Request Body(raw, json):
{
    "email": "abhi@gmail",
    "password": "password@abc"
}
Expected Response:  <auth token>
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6InVzZXIzQGdtYWlsIiwiaWQiOiI1ZThkZjNkMjQ0YTJlNWI5NmU4YTIzYTQifQ.k55h8uKJYdeklJ-8P35R5ba-Ug3v1KX9PcRcXKzWUu0
`

3. /add_available_slots -- POST
`URL: http://127.0.0.1:5000/add_available_slots
Request Body:(raw, JSON)
{
    "force_update": true,
    "free_slots": [[9, 17]],
    'day_month_year': '08-04-2020' 
}
* Create the user before requesting to add available time slots
Force Update parameter will overrite if there was an old entry for the given date. 
If no date provided, current date will be taken as default. date format: datetime.today().strftime('%d-%m-%Y')
`

4. /fetch_all_meetings -- GET
`URL: http://127.0.0.1:5000/fetch_all_meetings
Request Body: 
headers = {
  'Authorization': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6InVzZXIxQGdtYWlsIiwiaWQiOiI1ZThkZDg0NDQ0YTJlNWI4YmNhOTU5OGIifQ.rI3a74z-TlACQ1drPvgGyjuzl4ABc04Moow1in3-FwQ'
}
`

ALl postman collections can be found here: 
[![Run in Postman](https://run.pstmn.io/button.svg)](https://app.getpostman.com/run-collection/a36c05549f50fcd64aec)
