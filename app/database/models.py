from ..extensions import db

class Price(db.Model):
    __tablename__ = 'prices'
    query = db.session.query_property()
    id = db.Column(db.String(40), primary_key=True)
    pdate = db.Column(db.DateTime, nullable=False, unique=False)
    price = db.Column(db.Float, nullable=False, unique=False)
    
    def to_json(self):
        return {
            'id': self.id,
            'date': self.pdate,
            'price': self.price,
        }