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
from bottle import route, run, request, response

# the decorator
def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        if request.method != 'OPTIONS':
            # actual request; reply with the actual response
            return fn(*args, **kwargs)

    return _enable_cors

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(512)

def populate(lang, pattern):
    all_ids = pattern.get("translated", []) + pattern.get("untranslated", [])
    # Convert IDs to keys
    all_keys = [client.key('String', kid, namespace=lang) for kid in all_ids]
    entries = client.get_multi(all_keys)
    # Convert entity list to ID-to-dict map
    entryMap = {entry.key.id: dict(entry) for entry in entries}
    # Add 
    for key,value in entryMap.items():
        value["id"] = key
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


@route('/apiv3/patterns/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = request.query.offset or 0
    return json.dumps(findCommonPatterns(lang, offset=offset))

def submitTexttag(lang, engl, transl):
    key = client.key('Texttag', engl, namespace=lang)
    obj = client.get(key)
    obj.update({"translated": transl, "approved_in_ui": True})
    client.put(obj)
    print("Updated", obj)

def findTexttags(lang, offset=0):
    query = client.query(kind='Texttag', namespace=lang)
    query.add_filter('unapproved_count', '>', 0)
    query.add_filter('approved_in_ui', '=', False)
    query.order = ['-unapproved_count']
    query_iter = query.fetch(500, offset=offset)
    # Populate entries with strings
    return list(query_iter)

@route('/apiv3/texttags/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = request.query.offset or 0
    return json.dumps(findTexttags(lang, offset))

@route('/apiv3/save-texttag/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    info = json.load(request.body)
    engl = info['english']
    transl = info['translated']
    submitTexttag(lang, engl, transl)
    return json.dumps({"status": "ok"})

run(host='localhost', port=9921)