# Родительский образ
FROM python:3.6.9-slim

# Обновляем pip
RUN pip install -U pip 

# Устанавливаем библиотеки
RUN pip3 install flask jsonify requests flask_sqlalchemy pymysql celery cryptography flasgger