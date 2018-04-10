from flask import Flask
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
import redis

app = Flask(__name__)
cache = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
engine = create_engine('postgresql://postgres@postgresql/postgres', echo=True)


@app.route("/")
def hello():
    return "Hello World!"
