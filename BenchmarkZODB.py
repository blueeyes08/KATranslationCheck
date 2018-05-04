#!/usr/bin/env python3
# DOES NOT WORK - NOT ALL VALUES ARE COMMITTED
from collections import namedtuple
import time
import transaction
import ZODB, ZODB.FileStorage

storage = ZODB.FileStorage.FileStorage('mydata.fs')
db = ZODB.DB(storage)
# Create & store an entity

conn = db.open()
conn.root()["patterns"] = {}

def add_string_to_pattern(pattern, sref):
    with db.transaction() as conn:
        patterns = conn.root()["patterns"]
        try:
            entity = patterns[pattern]
            # Is string already present?
            for existingSref in entity["strings"]:
                if existingSref["id"] == sref["id"]:
                    pass # return # No need to update
            entity["strings"].append(sref)
        except KeyError: # Not present yet
            entity = {"strings": [sref]}
        # Save
        patterns[pattern] = entity
        transaction.commit()

s1 = {
    "id": 123,
    "source": "$1$",
    "target": "$1$",
    "target_source": "universal",
    "state": "untranslated",
    "file": "learn.drafts.xliff"
}

s2 = {
    "id": 345,
    "source": "$1$",
    "target": "$1$",
    "target_source": "universal",
    "state": "untranslated",
    "file": "learn.drafts.xliff"
}

t0 = time.time()
for i in range(1000):
    s1["id"] = i
    add_string_to_pattern("$formula$", s1.copy())
conn.close()
t1 = time.time()
print((t1 - t0))
