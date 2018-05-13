#!/usr/bin/env python3
import requests
import os.path
import subprocess
import tempfile
from xml.sax.saxutils import escape
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

def upload_string(fileid, lang, stringid, engl, translated, approved=False):
    """

    """
    xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
        <file id="{}" source-language="en-US" target-language="{}" datatype="plaintext">
            <body>
                <trans-unit id="{}">
                    <source>{}</source>
                    <target state="translated">{}</target>
                </trans-unit>
            </body>
        </file>
    </xliff>
    """.format(fileid, lang, stringid, escape(engl), escape(translated))
    print(xml)
    with tempfile.NamedTemporaryFile() as tmpfile:
        upload_file(tmpfile.name, fileid, auto_approve=True, lang=lang)


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
