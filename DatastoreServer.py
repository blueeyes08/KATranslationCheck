#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import os
import sys
from ansicolor import black
import itertools
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
from DatastoreIndexPatterns import index_pattern
from DatastoreImportStrings import string_update_rules
from DatastoreUtils import DatastoreChunkClient
from UliEngineering.SignalProcessing.Selection import *
from google.cloud import logging
logging_client = logging.Client()

logger = logging_client.logger("Babelfish")
client = datastore.Client(project="watts-198422")
executor = ThreadPoolExecutor(1024)
chunkClient = DatastoreChunkClient(client, executor)
default_string_projection = ['source', 'target', 'id', 'file', 'is_translated', 'is_approved', 'translation_source']
string_ignore_fields = set(["words", "words_cs", "words_ngrams", "words_ngrams_cs", "source_length", "relevant_for_live"])

currently_indexing = []

def get_all_filenames(lang):
    for file in findXLIFFFiles("cache/{}".format(lang)):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        yield "/".join(file.split("/")[2:])

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

def populate(lang, pattern, limit=250, alsoApproved=False):
    unapproved_ids = (pattern.get("untranslated", []) + pattern.get("translated", []))[:limit]
    approved_ids = pattern.get("approved", [])[:limit]
    all_ids = unapproved_ids + approved_ids
    all_keys = [client.key('String', kid, namespace=lang) for kid in all_ids]
    entries, _ = chunkClient.get_multi(all_keys)

    for entry in entries:
        entry["id"] = entry.key.id_or_name
        # Remove unneccessary fields
        for key in list(entry.keys()):
            if key.startswith("has_") or key in string_ignore_fields:
                del entry[key]
        # Add "original translation field"
        entry.update({
            "original_translation": entry["target"]
        })

    # Split into approved and non-approved strings
    nonApproved = [entry for entry in entries if not entry["is_approved"]]
    approved = [entry for entry in entries if entry["is_approved"]]

    # Try to find existing translation pattern

    translation = None
    if approved:
        translator = IFPatternAutotranslator(lang)
        # [0]: Only translation, ignore before and after strings
        normalized = [translator.normalize(entry["target"])[0] for entry in approved]
        translation = majority_vote(normalized)

    # If there are no leftover strings, reindex that pattern asynchronous
    if len(nonApproved) == 0 and not alsoApproved:
        print("Empty pattern, reindexing")
        # Reindex for both relevant_for_live settings
        executor.submit(index_pattern, client, lang, pattern["pattern"], True)
        executor.submit(index_pattern, client, lang, pattern["pattern"], False)
        return None
    # Map pattern
    return {
        "pattern": pattern["pattern"],
        "strings": nonApproved if not alsoApproved else (nonApproved + approved),
        "translation": translation
    }

def findCommonPatterns(lang, orderBy='num_unapproved', n=20, offset=0, total_limit=2500, onlyRelevantForLive=False):
    query = client.query(kind='Pattern', namespace=lang)
    query.add_filter('num_unapproved', '>', 0)
    if onlyRelevantForLive:
        query.add_filter('relevant_for_live', '=', True)

    query.order = ['-' + orderBy]
    query_iter = query.fetch(n, offset=offset)
    # Populate entries with strings

    # Limit number of strings to total_limit
    patterns = [v for v in executor.map(lambda result: populate(lang, result), query_iter)
            if v is not None]
    result = []
    string_count = 0
    for pattern in patterns:
        result.append(pattern)
        string_count += len(pattern["strings"])
        if string_count > total_limit:
            break

    return result

@route('/apiv3/filenames/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    all_filenames = list(get_all_filenames("de"))
    return json.dumps(all_filenames)


# Single pattern
@route('/apiv3/pattern/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    pattern = request.query.pattern[:500]
    onlyRelevantForLive = request.query.onlyRelevantForLive == "true"
    limit = int(request.query.limit or "250")
    # fetch pattern
    prefix = "live" if onlyRelevantForLive else "all"
    key = client.key('Pattern', "{}#{}".format(prefix, pattern), namespace=lang)
    patternInfo = client.get(key)
    if not patternInfo:
        return "{}"
    # Populate pattern
    populated = populate(lang, patternInfo, alsoApproved=True)
    return json.dumps(populated) if populated else "{}"


@route('/apiv3/patterns/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = int(request.query.offset) or 0
    n = int(request.query.n) or 20
    onlyRelevantForLive = request.query.onlyRelevantForLive == "true"
    return json.dumps(findCommonPatterns(lang, offset=offset, n=n, onlyRelevantForLive=onlyRelevantForLive))

@route('/apiv3/extract-texttags-from-strings/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    info = json.load(request.body)
    strings = info["strings"]
    # Index texttags for pattern
    tti = TextTagIndexer(lang)
    for string in strings:
        tti.add(string["source"])
    del tti.index[""]
    # Fetch texttags
    keys = [client.key('Texttag', engl, namespace=lang) for engl in tti.index.keys()]
    texttags = client.get_multi(keys)
    # Map texttags to number of occurences
    result = []
    for texttag in texttags:
        texttag["count"] = tti.index[texttag["english"]]
        result.append(texttag)
    return json.dumps(texttags)


@route('/apiv3/long-strings/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = 0 # Maybe TODO later
    onlyRelevantForLive = request.query.onlyRelevantForLive == "true"
    filenameFilter = request.query.file or None
    sortAsc = request.query.sort == "asc"
    # Stage 1: Find 
    query = client.query(kind='String', namespace=lang)
    query.add_filter('is_approved', '=', False)
    if filenameFilter:
        query.add_filter('file', '=', filenameFilter)
    if onlyRelevantForLive:
        query.add_filter('relevant_for_live', '=', onlyRelevantForLive)
    query.order = ['source_length' if sortAsc else '-source_length']
    print(query.filters)
    query_iter = query.fetch(100, offset=offset)

    longStrings = []
    for entity in query_iter:
        string = dict(entity)
        string["id"] = entity.key.id_or_name
        # Remove unneccessary fields
        for key in list(string.keys()):
            if key.startswith("has_") or key in string_ignore_fields:
                del string[key]
        # Add "original translation field"
        string.update({
            "original_translation": string["target"]
        })
        longStrings.append(string)
    # Ignore the patterns, put ALL the strings into a list
    return json.dumps(longStrings)

def updateStringTranslation(lang, sid, newTranslation, src="SmartTranslation", just_translated=False, just_approved=False):
    """
    Update translation of string in datastore.
    If just_... is Tur
    """
    try:
        key = client.key('String', sid, namespace=lang)
        value = client.get(key)
        value.update({
            "target": newTranslation,
            "translation_source": src
        })
        if just_translated:
            value.update({
                "is_translated": True
            })
        if just_approved:
            value.update({
                "is_approved": True
            })
        # Update rules
        string_update_rules(lang, value)
        print(value)
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
    # Either those two ...
    english = info.get("english", None)
    translated = info.get("translated", None)
    # ... or those two
    englPattern = info.get("englishPattern", None)
    translatedPattern = info.get("translatedPattern", None)
    # this one always
    strings = info["strings"]
    # Create a single pattern / pattern translation pair from the string
    # (unless the user already supplied a translated pattern)
    if translatedPattern is None:
        tmp = IFPatternAutotranslator(lang)
        englPattern, _, _ = tmp.normalize(english)
        translatedPattern, _, _ = tmp.normalize(translated)
    # Generate 
    ifpatterns = {
        englPattern: translatedPattern
    }
    texttags = GoogleCloudDatastoreTexttagSrc(lang, client)
    translator = IFPatternAutotranslator(lang, 1000000, ifpatterns, texttags)
    # Update all strings
    def _translate_string(string):
        # Do not "throw away" an old translation
        oldTarget = string["target"]
        autotranslated = translator.translate(string["source"])
        if autotranslated is None:
            return None
        string["target"] = autotranslated or oldTarget
        # Update string in DB (async)
        if string["target"] != oldTarget or string["translation_source"] != "SmartTranslation":
            executor.submit(updateStringTranslation, lang, string["id"], string["target"])
        return string
    strings = [s for s in executor.map(_translate_string, strings) if s is not None]
    # Return translated strin
    return json.dumps({
        "pattern": englPattern,
        "translation": translatedPattern,
        "strings": strings,
        "missing_texttags": dict(translator.pattern_missing_tags[englPattern])
    })


def submitTexttag(lang, engl, transl):
    print("Submitting texttag '{}' for {}".format(engl, lang))
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
    query_iter = query.fetch(250, offset=offset)
    # Populate entries with strings
    return list(query_iter)

def delayedIndexPattern(lang, pattern, delay=15):
    if pattern in currently_indexing:
        print(black("Ignoring index request for '{}', already in queue".format(pattern), bold=True))
        return
    # Avoid duplicate indexing
    currently_indexing.append(pattern)
    # Delay
    time.sleep(delay) # Allow DB to sync
    # Index with both relevant_for_live settings
    executor.submit(index_pattern, client, lang, pattern, True)
    executor.submit(index_pattern, client, lang, pattern, False)
    # Remove from queue
    try:
        currently_indexing.remove(pattern)
    except ValueError:
        pass

def update_string(lang, string):
    engl = string['source']
    transl = string['target']
    fileid = string['fileid']
    pattern = string['normalized']
    stringid = string['id']
    approve = string['approve']
    nickname = string.get('nickname') or 'Anonymous'
    # Upload to Crowdin
    executor.submit(upload_string, fileid, lang, stringid, engl, transl, approve)
    # Update in Datastore
    executor.submit(updateStringTranslation, lang, stringid, transl, just_translated=True, just_approved=approve)
    # Index pattern after allowing the DB to sync
    executor.submit(delayedIndexPattern, lang, pattern, delay=0)
    # Log
    executor.submit(logger.log_struct, {
        "type": "string",
        "lang": lang,
        "stringid": stringid,
        "approve": approve,
        "english": engl,
        "translated": transl,
        "nickname": nickname,
        "original_translation": string.get('original_translation', None),
        "was_translated": string["is_translated"],
        "was_approved": string["is_approved"]
    })


@route('/apiv3/upload-string/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    string = json.load(request.body)
    update_string(lang, string)
    return json.dumps({"status": "ok"})


@route('/apiv3/upload-strings/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang): # multi string upload
    strings = json.load(request.body)
    for string in strings:
        update_string(lang, string)
    return json.dumps({"status": "ok"})

@route('/apiv3/texttag/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    texttag = request.query.texttag or ""
    texttag = client.get(client.key('Texttag', texttag, namespace=lang))
    return json.dumps(texttag or {})

@route('/apiv3/texttags/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = request.query.offset or 0
    return json.dumps(findTexttags(lang, offset))

@route('/apiv3/correctable-strings/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    offset = int(request.query.offset or '0')
    rule = request.query.rule or "has_decimal_point"
    query = client.query(kind='String', namespace=lang)
    query.add_filter(rule, '=', True)
    query.add_filter('is_approved', '=', True)
    query.add_filter(rule + '_override', '=', False)
    query.order = ['source_length']
    query_iter = query.fetch(150, offset=offset)

    entries = list(query_iter)
    for entry in entries:
        entry["id"] = entry.key.id_or_name
        # Add "original translation field"
        entry.update({
            "original_translation": entry["target"]
        })
    return json.dumps([dict(entry) for entry in entries])

# Mark string as correct i.e. ignore rule for that string in the future
@route('/apiv3/override-rule/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    stringid = int(request.query.id)
    rule = request.query.rule or "has_decimal_point"
    if rule != 'word_search': # Ignore word search ignore, dont add useless field
        key = client.key('String', stringid, namespace=lang)
        string = client.get(key)
        string.update({
            rule + "_override": True
        })
        client.put(string)
    return json.dumps({"status": "ok"})

@route('/apiv3/save-texttag/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    info = json.load(request.body)
    engl = info['english']
    transl = info['translated']
    submitTexttag(lang, engl, transl)
    return json.dumps({"status": "ok"})


@route('/apiv3/beast-translate/<lang>', method=['OPTIONS', 'POST'])
@enable_cors
def index(lang):
    info = json.load(request.body)
    engl = info['english']
    translator = FullAutoTranslator(lang)
    transl = translator.translate(engl)
    if transl is None:
        return json.dumps({"status": "error"})
    else: # Success
        return json.dumps({"status": "ok", "translation": transl})


# Mark string as correct i.e. ignore rule for that string in the future
@route('/apiv3/word-search/<lang>', method=['OPTIONS', 'GET'])
@enable_cors
def index(lang):
    word = request.query.word
    offset = int(request.query.offset or '0')
    caseSensitive = request.query.cs == 'true'
    
    searchNgrams = " " in word

    # Preproc
    if not caseSensitive:
        word = word.lower()

    field = "words_ngrams"
    if caseSensitive:
        field += "_cs"

    query = client.query(kind='String', namespace=lang)
    query.add_filter(field, '=', word)
    #query.add_filter('is_approved', '=', True)
    #query.add_filter(rule + '_override', '=', False)
    query.order = ['source_length']
    print(query.filters)
    query_iter = query.fetch(150, offset=offset)

    strings = [doc for doc in query_iter]

    for string in strings:
        string["id"] = string.key.id_or_name
        # Remove unneccessary fields
        for key in list(string.keys()):
            if key.startswith("has_") or key in string_ignore_fields:
                del string[key]
        # Add "original translation field"
        string.update({
            "original_translation": string["target"]
        })
    return json.dumps(strings)

run(host='localhost', port=int(os.getenv('PORT', 9921)), server='paste')