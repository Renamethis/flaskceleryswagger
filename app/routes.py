import io
import json
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import numpy as np
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from crypt import methods
from flask import jsonify, abort, request,  Response
from flask.views import View
from .database.models import Price
from .__init__ import create_app
from flasgger import Swagger
from .extensions import db, celery
import os
from datetime import datetime, date
from sqlalchemy import extract  
from json import loads, dumps
import re
from random import random
import csv
from time import sleep
from celery.signals import worker_ready

# Load data from csv file
CSV_PATH = "app/database/init_values.csv"

data = []
with open(CSV_PATH) as File:
    rows = list(csv.reader(File))
    for row in rows:
        data.append(row)
COLUMNS = len(data[0]) - 2

# Swagger global configuration
swagger_config = {
    "headers": [
    ],
    "specs": [
        {
            "endpoint": 'api',
            "route": '/api',
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}

# Swagger template configuration
template = {
  "swagger": "2.0",
  "info": {
    "title": "Prices API",
    "description": "Price history monitoring and management system.",
    "contact": {
      "responsibleOrganization": "Ivan Gavrilov",
      "responsibleDeveloper": "Ivan Gavrilov",
      "email": "enderjoin@gmail.com",
    },
    "version": "0.0.1"
  },
}

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
swagger = Swagger(app, config=swagger_config, template=template)

# Initialize database
@worker_ready.connect
def at_start(sender, **k):
  sleep(10) # Wait database
  with app.app_context():
    prices = Price.query.all()
    if(not prices):
      i = 0
      for entry in data:
        new_entry = Price(
          id=i,
          pdate=datetime.strptime(entry[1], "%m/%d/%Y"),
          prices=','.join([price for price in entry[2:]])
        )
        db.session.add(new_entry)
        i+=1
      db.session.commit()

# CRUD celery tasks
@celery.task()
def get(id):
  if(id == None):
    prices = Price.query.all()
    data = [price.to_json() for price in prices]
    for d in data:
      d['date'] = d['date'].strftime("%Y-%m-%d")
    return data
  else:
    price = Price.query.get(id)
    if(price is None):
      return None
    else:
      price = price.to_json()
      price['date'] = price['date'].strftime("%Y-%m-%d")
      return price
  
@celery.task()
def create(form):
  id = prev = 0
  for row in Price.query.all():
    json = row.to_json()
    id = json['id']
    if(id - prev > 1):
      id = id - 1
      break
    else:
      prev = id
      id = id + 1
  price = Price(
      id=id,
      pdate=form.get('date'),
      prices=form.get('prices')
  )
  db.session.add(price)
  db.session.commit()
  price = price.to_json()
  price['date'] = price['date'].strftime("%Y-%m-%d")
  return price

@celery.task()
def delete(id):
    price = Price.query.get(id)
    if(price is None):
      return None
    db.session.delete(price)
    db.session.commit()
    return True

@celery.task()
def update(id, form):
    price = Price.query.get(id)
    if(price is None):
      return None
    if(form.get('date') is not None):
      price.pdate = form.get('date', price.pdate)
    price.prices = form.get('prices', price.prices)
    db.session.commit()
    price = price.to_json()
    price['date'] = price['date'].strftime("%Y-%m-%d")
    return price

# Flask endpoints
@app.route("/prices", methods=["GET"])
def get_entries():
    """Endpoint which returns all the prices history from database
    ---
    tags:
      - CRUD
    responses:
      200:
        description: A list of price entries
    """
    task = get.delay(None)
    result = task.wait(timeout=None)
    return jsonify(result), 200

@app.route("/prices/<id>", methods=["GET"])
def get_entry(id):
    """Endpoint which returns current price entry by given id from database
    ---
    tags:
      - CRUD
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        minimum: 0
        description: The ID value of price entry
    responses:
      200:
        description: Current price
      404:
        description: Entry with such id not found
    """
    task = get.delay(id)
    result = task.wait(timeout=None)
    if result is None:
        abort(404)
    return jsonify(result), 200

@app.route('/prices', methods=['POST'])
def create_price():
    """Endpoint which add price entry to database
    ---
    tags:
      - CRUD
    consumes:
      - application/x-www-form-urlencoded
    parameters:
      - name: date
        in: formData
        type: string
        required: true
        description: Current date in such format - YYYY-MM-DD
      - name: prices
        in: formData
        schema:
          type: string
          example: "[15, 30, 45, 60]"
        required: true
        description: Given prices
    responses:
      201:
        description: Price entry was sucessfully created
      400:
        description: Entry(ies) are not correct
    """
    prices = re.findall("(\d+(?:\.\d+)?)", request.form.get('prices'))
    if(not prices or len(prices) < COLUMNS):
      abort(400)
    if not request.form:
        abort(400)
    try:
      datetime.strptime(request.form.get('date'), "%Y-%m-%d")
    except ValueError:
      abort(400)
    task = create.delay(request.form)
    result = task.wait(timeout=None)
    return result, 201

@app.route("/prices/<id>", methods=["DELETE"])
def delete_price(id):
    """Endpoint which deletes current price entry by given id from database
    ---
    tags:
      - CRUD
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        minimum: 0
        description: The ID value of price entry
    responses:
      200:
        description: Price was deleted
      404:
        description: Entry with such id not found
    """
    task = delete.delay(id)
    result = task.wait(timeout=None)
    if(result is None):
      abort(404)
    return jsonify({'result': True}), 200

@app.route('/prices/<id>', methods=['PUT'])
def update_price(id):
    """Endpoint which update price entry to database by id
    ---
    tags:
      - CRUD
    consumes:
      - application/x-www-form-urlencoded
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        minimum: 0
        description: The ID value of price entry
      - name: date
        in: formData
        type: string
        required: false
        description: Current date in such format - YYYY-MM-DD
      - name: prices
        in: formData
        schema:
          type: string
          example: "[15, 30, 45, 60]"
        required: false
        description: Given price
    responses:
      200:
        description: Price entry was sucessfully updated
      400:
        description: Entry(ies) are not correct
    """
    if not request.form:
        abort(400)
    if(request.form.get('date') is not None):
      try:
        datetime.strptime(request.form.get('date'), "%Y-%m-%d")
      except ValueError:
        abort(400)
    task = update.delay(id, request.form)
    result = task.wait(timeout=None)
    if result is None:
        abort(404)
    return jsonify(result), 200

@app.route('/prices/history', methods=['GET'])
def draw_history():
  """Endpoint which returns matplotlib chart of prices history
  ---
  tags:
    - Charts
  responses:
    200:
      description: Chart successfully builded
    404:
      description: Price history is empty
  """
  dates = [entry.pdate for entry in Price.query.order_by(Price.pdate).all()]
  if(not dates):
    abort(404)
  prices = [[] for _ in re.findall("(\d+(?:\.\d+)?)", Price.query.first().prices)]
  for entry in Price.query.order_by(Price.pdate).all():
    splitted = re.findall("(\d+(?:\.\d+)?)", entry.prices)
    for i in range(len(prices)):
      prices[i].append(float(splitted[i]))
  fig = Figure()
  axis = fig.add_subplot(1, 1, 1)
  for price in prices:
    color = (random(), random(), random())
    axis.plot(dates, price, marker='o', color=color)
  fmt = mdates.DateFormatter('%d %B %Y')
  axis.xaxis.set_major_formatter(fmt)
  for tick in axis.get_xticklabels():
    tick.set_rotation(30)
    tick.set_fontsize(5)
  output = io.BytesIO()
  FigureCanvas(fig).print_png(output)
  return Response(output.getvalue(), mimetype='image/png')

@app.route('/prices/seasonality', methods=['GET'])
def draw_seasonality():
  """Endpoint which returns matplotlib chart or seasonality
  ---
  tags:
    - Charts
  responses:
    200:
      description: Chart successfully builded
    404:
      description: Price history is empty
  """
  dates = [entry.pdate for entry in Price.query.order_by(Price.pdate).all()]
  entries_amount = len(dates)
  if(not dates):
    abort(404)
  fig = Figure()
  axis = fig.add_subplot(1, 1, 1)
  entries = {}
  for date in dates:
    key = (date.year, date.month)
    if(key not in entries.keys()):
      entries[key] = 1
    else:
      entries[key] += 1
  coeffs = []
  for key in entries.keys():
    coeffs.append(entries[key]/entries_amount)
  color = (random(), random(), random())
  dates = [datetime(year=key[0], month=key[1], day=1) for key in entries.keys()]
  values = [entries[key]/entries_amount for key in entries.keys()]
  axis.plot(dates, values, marker='o', color=color)
  fmt = mdates.DateFormatter('%Y %B')
  axis.xaxis.set_major_formatter(fmt)
  for tick in axis.get_xticklabels():
    tick.set_rotation(30)
    tick.set_fontsize(5)
  output = io.BytesIO()
  FigureCanvas(fig).print_png(output)
  return Response(output.getvalue(), mimetype='image/png')
 