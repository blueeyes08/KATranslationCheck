#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import sys
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from ansicolor import black
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(512)

def index_pattern(lang, pattern):
    key = client.key('Pattern', pattern, namespace=lang)
    patternInfo = datastore.Entity(key)
    print("Indexing '{}'".format(pattern))
    patternInfo.update({
        "pattern": pattern,
        "lang": lang,
        # Lists of String IDs
        "approved": [],
        "translated": [],
        "untranslated": []
    })
    # Find all strings 
    query = client.query(kind='String', namespace=lang)
    query.add_filter('ifpattern', '=', pattern)
    query.projection = []
    query_iter = query.fetch()
    # ... and add them to the list
    for result in query_iter:
        if result["is_approved"]:
            patternInfo["approved"].append(result.key.id_or_name)
        elif result["is_translated"]:
            patternInfo["translated"].append(result.key.id_or_name)
        else:
            patternInfo["untranslated"].append(result.key.id_or_name)
    # Complete stats
    patternInfo["num_approved"] = len(patternInfo["approved"])
    patternInfo["num_translated"] = len(patternInfo["translated"])
    patternInfo["num_untranslated"] = len(patternInfo["untranslated"])
    patternInfo["num_total"] = patternInfo["num_approved"] + patternInfo["num_translated"] + patternInfo["num_untranslated"]
    # Write to DB
    client.put(patternInfo)

def index(lang):
    query = client.query(kind='String')
    query.distinct_on = ['ifpattern']
    query.projection = ['ifpattern']
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        futures.append(executor.submit(index_pattern, lang, result["ifpattern"]))
    # Wait for futures to finish
    for future in concurrent.futures.as_completed(futures):
        pass
    print("Total {} patterns".format(count))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()

    index(args.lang)

