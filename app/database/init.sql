CREATE DATABASE IF NOT EXISTS prices;
USE prices;
CREATE TABLE IF NOT EXISTS prices(id int not null primary key,
    pdate date not null,
    price float not null);