#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import sys
import traceback
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from ansicolor import black
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(4096)

def delete(keys):
    try:
        client.delete_multi(keys)
    except Exception as ex:
        traceback.print_exc()

def delete_all(lang, kind):
    query = client.query(kind=kind, namespace=lang)
    query.projection = []
    query.keys_only()
    query_iter = query.fetch()
    count = 0
    futures = []

    current_queue = []
    futures = []
    for result in query_iter:
        count += 1
        current_queue.append(result.key)
        if len(current_queue) > 350:
            futures.append(executor.submit(delete, current_queue))
            current_queue = []
        if count % 5000 == 0:
            print("Deleted {} {}s".format(count, kind))
    # Wait for futures to finish
    for future in concurrent.futures.as_completed(futures):
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    parser.add_argument('-s', '--strings', action="store_true", help='Delete strings')
    parser.add_argument('-p', '--patterns', action="store_true", help='Delete patterns')
    parser.add_argument('-t', '--texttags', action="store_true", help='Delete texttags')
    parser.add_argument('--yes-i-want-to-delete-everything', action="store_true", help='...')
    args = parser.parse_args()

    if args.yes_i_want_to_delete_everything:
        if args.strings:
            delete_all(args.lang, 'String')
        if args.patterns:
            delete_all(args.lang, 'Pattern')
        if args.texttags:
            delete_all(args.lang, 'Texttag')
    else:
        print("--yes-i-want-to-delete-everything missing")

