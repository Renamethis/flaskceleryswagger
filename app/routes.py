import io
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
from datetime import datetime

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
  "schemes": [
    "http",
    "https"
  ],
}

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
swagger = Swagger(app, config=swagger_config, template=template)

@celery.task()
def get(id):
  if(id == None):
    prices = Price.query.all()
    data = [price.to_json() for price in prices]
    return data
  else:
    price = Price.query.get(id)
    if(price is None):
      return None
    else:
      return price.to_json()
  
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
      price=form.get('price')
  )
  db.session.add(price)
  db.session.commit()
  return price.to_json()

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
    price.pdate = form.get('date', price.pdate)
    price.price = form.get('price', price.price)
    db.session.commit()
    return price.to_json()

@app.route("/prices", methods=["GET"])
def get_trackers():
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
def get_tracker(id):
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
        description: Current date in such format - YYYY-MM-DD H:M:S
      - name: price
        in: formData
        type: number
        required: true
        minimum: 0.0
        description: Given price
    responses:
      201:
        description: Price entry was sucessfully created
      400:
        description: Entry(ies) are not correct
    """
    app.logger.info(request.form)
    if not request.form:
        abort(400)
    try:
      datetime.strptime(request.form.get('date'), "%Y-%m-%d %H:%M:%S")
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
        description: Current date in such format - YYYY-MM-DD H:M:S
      - name: price
        in: formData
        type: number
        required: false
        minimum: 0.0
        description: Given price
    responses:
      200:
        description: Price entry was sucessfully updated
      400:
        description: Entry(ies) are not correct
    """
    if not request.form:
        abort(400)
    try:
      datetime.strptime(request.form.get('date'), "%Y-%m-%d %H:%M:%S")
    except ValueError:
      abort(400)
    task = update.delay(id, request.form)
    result = task.wait(timeout=None)
    if result is None:
        abort(404)
    return jsonify(result), 200

@app.route('/prices/history', methods=['GET'])
def draw_history():
  """Endpoint which returns matplotlib chart
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
  prices = [entry.price for entry in Price.query.order_by(Price.price).all()]
  if(not dates or not prices):
    abort(404)
  fig = Figure()
  axis = fig.add_subplot(1, 1, 1)
  axis.plot(dates, prices, "go-")
  fmt = mdates.DateFormatter('%d %B %Y')
  axis.xaxis.set_major_formatter(fmt)
  for tick in axis.get_xticklabels():
    tick.set_rotation(30)
    tick.set_fontsize(5)
  output = io.BytesIO()
  FigureCanvas(fig).print_png(output)
  return Response(output.getvalue(), mimetype='image/png')
