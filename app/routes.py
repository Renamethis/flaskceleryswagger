from flask import jsonify, abort, request
from flask.views import View
from .database.models import Price
from .__init__ import create_app
from flasgger import Swagger
from . import db
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
    "description": "API for prices managing prices in database",
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
    prices = Price.query.all()
    data = [price.to_json() for price in prices]
    return jsonify(data), 200

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
      datetime.strptime(request.form.get('date'), "%Y-%m-%d")
    except ValueError:
      abort(400)
    id = prev = 0
    for row in Price.query.all():
      json = row.to_json()
      id = json['id']
      if(id - prev > 1):
        break
      else:
        prev = id
        id = id + 1
    price = Price(
        id=id,
        pdate=request.form.get('date'),
        price=request.form.get('price')
    )
    db.session.add(price)
    db.session.commit()
    return jsonify(price.to_json()), 201

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
    price = Price.query.get(id)
    if price is None:
        abort(404)
    return jsonify(price.to_json()), 200

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
    price = Price.query.get(id)
    if price is None:
        abort(404)
    local_object = db.session.merge(price)
    db.session.delete(local_object)
    db.session.commit()
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
    if not request.json:
        abort(400)
    price = Price.query.get(id)
    if price is None:
        abort(404)
    price.pdate = request.json.get('date', price.pdate)
    price.price = request.json.get('price', price.port)
    db.session.commit()
    Price.query.all()
    return jsonify(price.to_json()), 200