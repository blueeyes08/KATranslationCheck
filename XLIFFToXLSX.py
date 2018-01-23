#!/usr/bin/env python3
from XLIFFReader import parse_xliff_file
import itertools
import bs4
import os

import xlsxwriter
from collections import namedtuple

def xlsx_write_rows(filename, rows):
    """
    Write XLSX rows from an iterable of rows.
    Each row must be an iterable of writeable values.

    Returns the number of rows written
    """
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    # Write values
    nrows = 0
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            worksheet.write(i, j, val)
        nrows += 1
    # Cleanup
    workbook.close()
    return nrows

def namedtuples_to_xlsx(filename, values):
    """
    Convert a list or generator of namedtuples to an XLSX file.
    Returns the number of rows written.
    """
    try:
        # Use first row to generate header
        peek = next(values)
        header = list(peek.__class__._fields)
        return xlsx_write_rows(filename, itertools.chain([header], [peek], values))
    except StopIteration: # Empty generator
        # Write empty xlsx
        return xlsx_write_rows(filename, [])


XLIFFEntry = namedtuple("XLIFFEntry", ["ID", "Source", "Translated"])

def process_xliff_soup(soup):
    """
    Remove both untranslated and notes from the given soup.
    For the untranslated elements, in
    """
    overall_count = 0
    untranslated_count = 0
    translated_count = 0
    autotranslated_count = 0
    # Iterate over all translatable strings
    body = soup.xliff.file.body

    # Resulting elements
    results = []

    for trans_unit in body.children:  # body.find_all("trans-unit"):
        # Ignore strings
        if not isinstance(trans_unit, bs4.element.Tag):
            continue

        # Ignore other tags
        if trans_unit.name != "trans-unit":
            print("Encountered wrong tag: {}".format(trans_unit.name))
            continue

        overall_count += 1
        source = trans_unit.source
        target = trans_unit.target
        # Broken XLIFF?
        if target is None:
            print(trans_unit.prettify())
            continue
        trans_id = trans_unit.attrs["id"]
        note = trans_unit.note
        is_untranslated = (
            "state" in target.attrs and target["state"] == "needs-translation")
        is_approved = (
            "approved" in trans_unit.attrs and trans_unit["approved"] == "yes")

        if not is_approved:
            yield XLIFFEntry(trans_id, source.text, target.text)


def convertXLIFFToXLSX(src, target):
    soup = parse_xliff_file(src)
    n = namedtuples_to_xlsx(target, process_xliff_soup(soup))
    print("{}: {} entries".format(src, n - 1)) # n - 1: header included

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('indir', help='Directory with XLIFFs to convert, like 2_high_priority')
    parser.add_argument('outdir', help='Directory to save XLSXs to (auto-created)')
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    for filename in os.listdir(args.indir):
        if not filename.endswith(".xliff"):
            continue
        inpath = os.path.join(args.indir, filename)
        outpath = os.path.join(args.outdir, filename)
        convertXLIFFToXLSX(inpath, outpath)
