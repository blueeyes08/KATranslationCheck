#!/usr/bin/env python3
import requests
import os.path
import subprocess
from UpdateAllFiles import getCrowdinSession

def upload_file(filename, fileid, auto_approve=False, lang="lol", fullauto_account=False, duplicates=False):
    auto_approve = 1 if auto_approve else 0
    basename = os.path.basename(filename)
    url = "https://crowdin.com/project/khanacademy/{}/{}/upload?import_eq_suggestions=1&{}qqfile={}".format(
        lang, fileid, "auto_approve_imported=1&" if auto_approve else "", basename)
    if duplicates:
        url += "&import_duplicates=1"

    s = getCrowdinSession(fullauto_account=fullauto_account)
    with open(filename, "rb") as infile:
        response = s.post(url, data=infile)
    if response.json()["success"] != True:
        print("Submit failed: {}".format(response.text))
    # {success: true, version: "8"}
    # POST
    # content-type:application/octet-stream
    # x-file-name:test.xliff
    # x-requested-with:XMLHttpRequest

def approve_string(filename, fileid, lang, engl, translated):
    """

    """
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
      <file id="38164" original="/2_high_priority_content/learn.math.calculus-home.articles.pot" source-language="en-US" target-language="sv-SE" datatype="plaintext">
        <body>
          <trans-unit id="3884148" identifier="a3d044bd643c30033b53e924a5a8e6da" approved="yes">
            <source>Because part of the region is below the x-axis, we subtract the area of that region from the definite integral.</source>
            <target state="translated">Eftersom en del av regionen ligger under x-axeln subtraherar vi området i den regionen från det bestämda integralet.</target>
          </trans-unit>
        </body>
      </file>
    </xliff>
    """
    # TODO


def update_crowdin_index_files(lang):
    """
    Update the ka-babelfish files on Crowdin
    """
    with open("apikey.txt") as infile:
        apikey = infile.read().strip()
    # Upload ifpatterns source
    out = subprocess.check_output(["curl",
        "-F", "files[ifpatterns.xliff]=@transmap/{}.ifpatterns.xliff".format(lang),
        "https://api.crowdin.com/api/project/ka-babelfish/update-file?key={}".format(apikey)])
    print(out)
    # Upload texttags source
    out = subprocess.check_output(["curl",
        "-F", "files[ifpatterns.xliff]=@transmap/{}.ifpatterns.xliff".format(lang),
        "https://api.crowdin.com/api/project/ka-babelfish/update-file?key={}".format(apikey)])
    print(out)
