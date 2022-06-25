# Родительский образ
FROM python:3.10.5

# Обновляем pip
RUN pip install -U pip 

# Устанавливаем библиотеки

RUN pip install pipenv
WORKDIR /code
COPY Pipfile* /code/
RUN pipenv install --system --deploy --ignore-pipfile
ADD app /code/