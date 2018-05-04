#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
client = datastore.Client(project="watts-198422")

# Create & store an entity
query = client.query(kind='MyKind')

StringRef = namedtuple("StringRef", [])


def add_string_to_pattern(pattern, sref):
    key = client.key('Pattern', pattern)
    entity = client.get(key)
    # Update entity
    if "strings" not in entity:
        entity.update({"strings": []})
    # Is string already present
    for existingSref in entity["strings"]:
        if existingSref["id"] == sref["id"]:
            return # No need to update
    # Add string
    entity["strings"].append(sref)
    # Save
    client.put(entity)

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
add_string_to_pattern("$formula$", s1)
add_string_to_pattern("$formula$", s2)