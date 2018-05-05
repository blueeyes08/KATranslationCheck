#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import sys
import simplejson as json
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer
from bottle import route, run, template

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(512)

def populate(lang, pattern):
    all_ids = pattern.get("translated", []) + pattern.get("untranslated", [])
    # Convert IDs to keys
    all_keys = [client.key('String', kid, namespace=lang) for kid in all_ids]
    entries = client.get_multi(all_keys)
    # Convert entity list to ID-to-dict map
    entryMap = {entry.key.id: dict(entry) for entry in entries}
    # Map pattern
    return {
        "pattern": pattern.key.name,
        "translated": [entryMap[kid] for kid in pattern.get("translated", []) if kid in entryMap],
        "untranslated": [entryMap[kid] for kid in pattern.get("untranslated", []) if kid in entryMap]
    }

def findCommonPatterns(lang, orderBy='num_unapproved', n=10, offset=0):
    query = client.query(kind='Pattern', namespace=lang)
    query.add_filter('num_unapproved', '>', 0)
    query.order = ['-' + orderBy]
    query_iter = query.fetch(n, offset=offset)
    count = 0
    futures = []
    # Populate entries with strings
    return list(executor.map(lambda result: populate(lang, result), query_iter))

@route('/api/patterns/<lang>')
def index(lang):
    return json.dumps(findCommonPatterns(lang))

run(host='localhost', port=12091)