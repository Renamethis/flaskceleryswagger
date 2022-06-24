from flask import jsonify, abort, request
from flask.views import View
from .database.models import Price
from .__init__ import create_app
from flasgger import Swagger
from . import db
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
swagger = Swagger(app)

@app.route("/prices", methods=["GET"])
def get_trackers():
    """Example endpoint returning a list of colors by palette
    This is using docstrings for specifications.
    ---
    parameters:
      - name: palette
        in: path
        type: string
        enum: ['all', 'rgb', 'cmyk']
        required: true
        default: all
    definitions:
      Palette:
        type: object
        properties:
          palette_name:
            type: array
            items:
              $ref: '#/definitions/Color'
      Color:
        type: string
    responses:
      200:
        description: A list of colors (may be filtered by palette)
        schema:
          $ref: '#/definitions/Palette'
        examples:
          rgb: ['red', 'green', 'blue']
    """
    prices = Price.query.all()
    data = [price.to_json() for price in prices]
    return jsonify(data)

@app.route("/prices/<int:isbn>", methods=["GET"])
def get_tracker(isbn):
    price = Price.query.get(isbn)
    if price is None:
        abort(404)
    return jsonify(price.to_json())

@app.route("/prices/<int:isbn>", methods=["DELETE"])
def delete_price(isbn):
    price = Price.query.get(isbn)
    if price is None:
        abort(404)
    db.session.delete(price)
    db.session.commit()
    return jsonify({'result': True})

@app.route('/prices', methods=['POST'])
def create_price():
    if not request.json:
        abort(400)
    price = Price(
        id=request.json.get('id'),
        pdate=request.json.get('date'),
        price=request.json.get('price')
    )
    db.session.add(price)
    db.session.commit()
    return jsonify(price.to_json()), 201

@app.route('/prices/<int:isbn>', methods=['PUT'])
def update_price(isbn):
    if not request.json:
        abort(400)
    price = Price.query.get(isbn)
    if price is None:
        abort(404)
    price.id = request.json.get('id', price.room)
    price.pdate = request.json.get('date', price.pdate)
    price.price = request.json.get('price', price.port)
    db.session.commit()
    Price.query.all()
    return jsonify(price.to_json())