#!/usr/bin/env python3
from webvtt import WebVTT, Caption
from io import StringIO
from TranslationDriver import TranslationDriver
from bs4 import BeautifulSoup
import subprocess
import argparse
import sys
import os
from ansicolor import red, green

parser = argparse.ArgumentParser(description='Translate subtitles')
parser.add_argument('lang', help='The lang code like "sv" to translate to')
parser.add_argument('yturl', help='The Youtube URL of the video with english subtitles')
args = parser.parse_args()

out = subprocess.check_output(["youtube-dl", "--sub-lang", "en", "--write-sub", "--skip-download", args.yturl.partition("&")[0]])

# Find VTT file<
def vtt_file(out):
    for line in out.decode("utf-8").split("\n"):
        if "Writing video subtitles to: " in line:
            return line.partition(":")[2].strip()
    return None

filename = vtt_file(out)
if not filename:
    print(red("Video does not seem to have english subs", bold=True))
    sys.exit(1)

# Read source VTT & convert to HTML
vtt = WebVTT()
vtt.read(filename)

stmp = StringIO()
print("<div>", file=stmp)
for caption in vtt:
    print('<span data-start="{}" data-end="{}">{}</span>'.format(caption.start, caption.end, caption.text), file=stmp)
print("</div>", file=stmp)

# Translate
driver = TranslationDriver(args.lang)
strans = driver.translate(stmp.getvalue())

# Convert translated HTML back to VTT
vtt = WebVTT()

soup = BeautifulSoup(strans, "lxml")
for span in soup.find_all("span"):
    start = span["data-start"]
    end = span["data-end"]
    caption = Caption(start, end, span.text)
    vtt.captions.append(caption)

# Remove the english file
os.remove(filename)

outfile = filename.replace(".en.", ".{}.".format(args.lang));
vtt.save(outfile)
print(green(outfile, bold=True))