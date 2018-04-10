#!/usr/bin/env python3
from bs4 import BeautifulSoup

def parse_xliff_file(filename):
    with open(filename) as infile:
        return BeautifulSoup(infile, "lxml-xml")
