from ..extensions import db

# Price ORM model
class Price(db.Model):
    __tablename__ = 'prices'
    query = db.session.query_property()
    id = db.Column(db.String(40), primary_key=True)
    pdate = db.Column(db.Date, nullable=False, unique=False)
    prices = db.Column(db.String(100), nullable=False, unique=False)
    
    def to_json(self):
        return {
            'id': self.id,
            'date': self.pdate,
            'price': self.prices,
        }