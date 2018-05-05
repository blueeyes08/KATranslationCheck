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

def findCommonPatterns(lang, orderBy='num_untranslated'):
    query = client.query(kind='Pattern', namespace=lang)
    query.add_filter('num_untranslated', '>', 0)
    query.order = ['-' + orderBy]
    query_iter = query.fetch(100)
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        print(result)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()

    findCommonPatterns(args.lang)

