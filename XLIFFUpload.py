#!/usr/bin/env python3
import requests
import os.path
import subprocess
from io import BytesIO
from xml.sax.saxutils import escape
from UpdateAllFiles import getCrowdinSession

def upload_file(filename, fileid, auto_approve=False, lang="lol", fullauto_account=False, duplicates=False):
    """
    Upload XLIFF to Crowdin
    NOTE: filename may also be BytesIO
    """
    auto_approve = 1 if auto_approve else 0
    url = "https://crowdin.com/project/khanacademy/{}/all/upload?as_xliff=1&import_eq_suggestions=1&qqfile=upload.xliff&ws_hash_user_key=1bdebe3137795fb8e9f72bb4bbfa34aa".format(
        lang)
    if duplicates:
        url += "&import_duplicates=1"
    if auto_approve:
        url += "&auto_approve_imported=1"
    print(url)
    headers = {
        "Referer": "https://crowdin.com/translate/khanacademy/all/enus-de",
        "x-file-name": "upload.xliff",
        "x-requested-with": "XMLHttpRequest",
        "content-type": "application/octet-stream",
    }

    s = getCrowdinSession(fullauto_account=fullauto_account)

    if isinstance(filename, str):
        with open(filename, "rb") as infile:
            response = s.post(url, data=infile.read(), headers=headers)
    else: # Assume byteio
        response = s.post(url, data=filename.read(), headers=headers)
    if response.json()["success"] != True:
        print("Submit failed: {}".format(response.text))
    # {success: true, version: "8"}
    # POST
    # content-type:application/octet-stream
    # x-file-name:test.xliff
    # x-requested-with:XMLHttpRequest

def upload_string(fileid, lang, stringid, engl, translated, approved=False):
    """
    Upload a single string
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
    """.format(fileid, lang, stringid, escape(engl), escape(translated)).strip()
    print(xml)
    bio = BytesIO(xml.encode("utf-8"))
    upload_file(bio, fileid, auto_approve=approved, lang=lang, duplicates=True)


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
