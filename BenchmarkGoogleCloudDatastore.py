#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
client = datastore.Client(project="watts-198422")

# Create & store an entity
def write_string(sref):
    key = client.key('String', "{}-{}".format(sref["lang"], sref["id"]))
    entity = client.get(key)
    entity.update(sref)
    # Save
    client.put(entity)

s1 = {
    "id": 123,
    "lang": "sv-SE",
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
    s1["id"] = i;
    write_string(s1)
t1 = time.time()
print((t1 - t0))