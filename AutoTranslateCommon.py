#!/usr/bin/env python3
import cffi_re2 as re
import json
import os
import xlsxwriter
from bs4 import BeautifulSoup
import urllib.parse
import hashlib

def get_text_regex():
    exceptions = ["cm", "m", "g", "kg", "s", "min", "max", "h", "cm"]
    exc_clause = "".join([r"(?! ?" + ex + r"\})" for ex in exceptions])
    regex = r"(\\(text|mathrm|textit|textbf)\s*\{" + exc_clause + r")"
    return re.compile(regex)

def get_end_invariant_regex():
    # Apply to reversed string
    return re.compile(r"^((n\\|[\.\?,!\s]+|\]\]\d*\s*[a-z-]+\s+☃\s*\[\[)*)\s*", re.UNICODE)

def get_start_invariant_regex():
    return re.compile(r"^((>|\s+|-|\\n)*)\s*", re.UNICODE)

def hash_string(s):
    m = hashlib.md5() 
    m.update(s.encode("utf-8"))
    return m.digest()[:4] # need to be short, not secure => take only the first half = 64 bits

def get_text_content_regex():
    return re.compile(r"(\\text\s*\{\s*)([^\}]+?)(\s*\})") 

def get_formula_re():
    return re.compile(r"\$[^\$]+\$") 

def get_image_regex():
    return re.compile(r"((!\[([^\]]+)?\]\()?\s*(http|https|web\+graphie):\/\/(ka-perseus-(images|graphie)\.s3\.amazonaws\.com|fastly\.kastatic\.org\/ka-perseus-graphie)\/[0-9a-f]+(\.(svg|png|jpg))?\)?)")

def get_input_re():
    return re.compile(r"\[\[☃\s+[a-z-]+\s*\d*\]\]")

def transmap_filename(lang, identifier, extension="json"):
    return os.path.join("transmap", "{}.{}.{}".format(
        lang, identifier, extension))

def read_patterns(lang, identifier):
    with open(transmap_filename(lang, identifier)) as infile:
        return json.load(infile)

def save_patterns(lang, identifier, patterns):
    with open(transmap_filename(lang, identifier), "w") as outfile:
        json.dump(patterns, outfile)

def read_ifpattern_index(lang):
    try:
        ifpatterns = read_patterns(lang, "ifpatterns")
        return {
            v["english"]: v["translated"]
            for v in ifpatterns
            if v["translated"] # Ignore empty string == untranslated
            and v["english"].count("$formula$") == v["translated"].count("$formula$")
        }
    except FileNotFoundError:
        return {}

def read_texttag_index(lang):
    try:
        texttags = read_patterns(lang, "texttags")
        return {
            v["english"]: v["translated"]
            for v in texttags
             # Ignore empty string == untranslated
            if (v["translated"] or (v["english"] == "" and v["translated"] == ""))
        }
    except FileNotFoundError:
        return {}

import re
_numeric_only_re = re.compile(r"^\d+(\.\d+)?$", re.UNICODE)
def is_numeric_only(s):
    if s is None:
        return False
    return _numeric_only_re.match(s) is not None

def pattern_list_to_xliff(patterns):
    """
    Convert a JSON list to a XLIFF soup
    """
    # Read template XLIFF
    with open("template.xliff") as infile:
        soup = BeautifulSoup(infile, "lxml-xml")
    body = soup.xliff.file.body
    
    for pattern in patterns:
        trans = soup.new_tag("trans-unit")
        # Source
        source = soup.new_tag("source")
        source.append(pattern["english"])
        # Target
        target = soup.new_tag("target")
        target.append(pattern["translated"] if pattern["translated"] else pattern["english"])
        target.attrs["state"] = "needs-translations" \
            if pattern["translated"] == "" else "translated"
        # Assembly
        trans.append(source)
        trans.append(target)
        body.append(trans)
    return soup

def to_crowdin_search_string(entry):
    s = entry.translated[:100].replace('*', ' ')
    s = s.replace('$', ' ').replace('\\', ' ').replace(',', ' ')
    s = s.replace('.', ' ').replace('?', ' ').replace('!', ' ')
    s = s.replace("-", " ").replace(":", " ")
    #Remove consecutive spaces
    s = _multiSpace.sub(" ", s)
    return urllib.parse.quote(s.replace('☃', ' ').replace("|", " "))

def to_xlsx(tags, filename):
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()

    # Header
    worksheet.write(0, 0, "Count")
    worksheet.write(0, 1, "Untranslated count")
    worksheet.write(0, 2, "English")
    worksheet.write(0, 3, "Translated")
    worksheet.write(0, 4, "Translated is proofread")
    worksheet.write(0, 5, "Unapproved count")

    # Content
    for i, tag in enumerate(tags):
        worksheet.write(i + 1, 0, tag["count"])
        worksheet.write(i + 1, 1, tag["untranslated_count"])
        worksheet.write(i + 1, 2, tag["english"])
        worksheet.write(i + 1, 3, tag["translated"])
        if "translation_is_proofread" in tag:
            worksheet.write(i + 1, 4, tag["translation_is_proofread"])
        if "unapproved_count" in tag:
            worksheet.write(i + 1, 5, tag["unapproved_count"])

    workbook.close()

def from_xlsx(tags, filename):
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()

    # Header
    worksheet.write(0, 0, "Count")
    worksheet.write(0, 1, "English")
    worksheet.write(0, 2, "Translated")

    # Content
    for i, tag in enumerate(tags):
        worksheet.write(i + 1, 0, tag["count"])
        worksheet.write(i + 1, 1, tag["english"])
        worksheet.write(i + 1, 2, tag["translated"])

    workbook.close()
