#!/usr/bin/env python3
"""
Script to fix certain errors in the DB.
This script will only fix the latest error, not old errors.
"""
from google.cloud import datastore
from collections import namedtuple
import time
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from ansicolor import black

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(4096)

def delete(key):
    try:
        client.delete(key)
    except Exception as ex:
        traceback.print_exc()

def delete_selective(lang, kind):
    query = client.query(kind=kind, namespace=lang)
    query.projection = []
    query.keys_only()
    query_iter = query.fetch()
    count = 0
    count_ok = 0
    futures = []
    for result in query_iter:
        name = result.key.id_or_name
        if name.startswith("live#") or name.startswith("all"):
            count_ok += 1
            print("OK: ", name)
            continue
        else: # Key not OK
            print("NOK: ", name)
            count += 1
            futures.append(executor.submit(delete, result.key))
            if count % 5000 == 0:
                print("Deleted {} {}s".format(count, kind))
    # Wait for futures to finish
    for future in concurrent.futures.as_completed(futures):
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()

    delete_selective(args.lang, 'Pattern')

