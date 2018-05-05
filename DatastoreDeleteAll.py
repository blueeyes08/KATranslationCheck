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

def delete(key):
    try:
        client.delete(key)
    except Exception as ex:
        traceback.print_exc()

def delete_all(lang, kind):
    query = client.query(kind=kind, namespace=lang)
    query.projection = []
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        futures.append(executor.submit(delete, result.key))
    # Wait for futures to finish
    for future in concurrent.futures.as_completed(futures):
        pass
    print("Deleted {} {}s".format(count, kind))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()

    delete_all(args.lang, 'String')
    delete_all(args.lang, 'Pattern')

