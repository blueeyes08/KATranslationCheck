#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
from ansicolor import black
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(512)

def index(lang):
    query = client.query(kind='String')
    query.add_filter('lang', '=', lang)
    query.distinct_on = ['ifpattern']
    query_iter = query.fetch()
    for result in query_iter:
        print(result)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()

    index(args.lang)

