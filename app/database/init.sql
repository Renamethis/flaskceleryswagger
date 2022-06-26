CREATE DATABASE IF NOT EXISTS prices;
USE prices;
CREATE TABLE IF NOT EXISTS prices(id int not null primary key,
    pdate datetime not null,
    price float not null);