#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import sys
import simplejson as json
from XLIFFUpload import *
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import traceback
from AutoTranslationIndexer import *
from AutoTranslationTranslator import *
from bottle import route, run, request, response

client = datastore.Client(project="watts-198422")
executor = ThreadPoolExecutor(512)

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

def populate(lang, pattern):
    all_ids = pattern.get("untranslated", []) + pattern.get("translated", [])
    all_keys = [client.key('String', kid, namespace=lang) for kid in all_ids]
    entries = client.get_multi(all_keys)

    for entry in entries:
        entry["id"] = entry.key.id_or_name
    # Map pattern
    return {
        "pattern": pattern.key.name,
        "strings": entries
    }

def findCommonPatterns(lang, orderBy='num_unapproved', n=10, offset=0):
    query = client.query(kind='Pattern', namespace=lang)
    query.add_filter('num_unapproved', '>', 0)
    query.order = ['-' + orderBy]
    query_iter = query.fetch(n, offset=offset)
    # Populate entries with strings
    return list(executor.map(lambda result: populate(lang, result), query_iter))


@route('/apiv3/patterns/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = request.query.offset or 0
    return json.dumps(findCommonPatterns(lang, offset=offset))

def updateStringTranslation(lang, sid, newTranslation, src="SmartTranslation"):
    try:
        key = client.key('String', sid, namespace=lang)
        value = client.get(key)
        value.update({
            "translation": newTranslation,
            "translation_source": src
        })
        client.put(value)
    except Exception as ex:
        traceback.print_exc()


@route('/apiv3/pattern-smart-translate/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    """
    POST a translated pattern and a list of strings adhering
    to that pattern and translate that string according to the
    patterns.
    """
    info = json.load(request.body)
    english = info["english"]
    translated = info["translated"]
    strings = info["strings"]
    # Create a single pattern / pattern translation pair from the string
    idxer = IgnoreFormulaPatternIndexer(lang)
    englPattern = idxer._normalize(english)
    translatedPattern = idxer._normalize(translated)
    # Generate 
    ifpatterns = {
        englPattern: translatedPattern
    }
    texttags = GoogleCloudDatastoreTexttagSrc(lang, client)
    translator = IFPatternAutotranslator(lang, 1000, ifpatterns, texttags)
    # Update all strings
    def _translate_string(string):
        # Do not "throw away" an old translation
        oldTarget = string["target"]
        string["target"] = translator.translate(string["source"]) or oldTarget
        # Update string in DB (async)
        if string["target"] != oldTarget or string["translation_source"] != "SmartTranslation":
            executor.submit(updateStringTranslation, lang, string["id"], string["target"])
        return string
    strings = list(executor.map(_translate_string, strings))
    # Return translated strin
    return json.dumps({
        "pattern": englPattern,
        "translation": translatedPattern,
        "strings": strings
    })


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


@route('/apiv3/upload-string/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    string = json.load(request.body)
    engl = string['source']
    transl = string['target']
    fileid = string['fileid']
    stringid = string['id']
    approve = string['approve']
    upload_string(fileid, lang, stringid, engl, transl, approve)
    return json.dumps({"status": "ok"})





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