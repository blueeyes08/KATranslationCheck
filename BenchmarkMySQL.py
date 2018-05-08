#!/usr/bin/env python3
import pymysql
from collections import namedtuple
import time

# Connect
with open("mysql-rootpw.txt") as pwfile:
    password = pwfile.read().strip()

"""
CREATE TABLE `strings` (
  `id` int(11) NOT NULL,
  `pattern` text,
  `source` text NOT NULL,
  `target` text,
  `translated` tinyint(4) DEFAULT NULL,
  `approved` tinyint(4) DEFAULT NULL,
  `target_source` varchar(45) DEFAULT NULL,
  `file` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
"""

db = pymysql.connect(host="35.227.106.167",
                     user="root",
                     passwd=password,
                     db="babelfish")

def add_string(sref):
    with db.cursor() as cursor:
        # Create a new record
        sql = "INSERT INTO `strings` (`id`, `pattern`, `source`, `target`, `translated`, `approved`, `target_source`, `file`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
        cursor.execute(sql, (sref["id"], sref["pattern"], sref["source"], sref["target"], sref["translated"], sref["approved"], sref["target_source"], sref["file"]))
    db.commit()

s1 = {
    "id": 123,
    "source": "$1$",
    "target": "$1$",
    "pattern": "$formula$",
    "target_source": "universal",
    "translated": False,
    "approved": False,
    "file": "learn.drafts.xliff"
}

t0 = time.time()
for i in range(1000):
    s1["id"] = i
    add_string(s1)
db.close()
t1 = time.time()
print((t1 - t0))
