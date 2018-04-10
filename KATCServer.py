#!/usr/bin/env python3
from bottle import route, run, template, request, response
import simplejson as json
from AutoTranslateCommon import transmap_filename

@route('/apiv2/<lang>')
def index():
    pass

@route('/apiv2/patterns/<lang>')
def patterns(lang):
    with open(transmap_filename(lang, "ifpatterns")) as infile:
        data = json.load(infile)
    response.content_type = 'application/json'
    return json.dumps(data[:200])

@route('/apiv2/texttags/<lang>')
def patterns(lang):
    with open(transmap_filename(lang, "texttags")) as infile:
        data = json.load(infile)
    response.content_type = 'application/json'
    return json.dumps(data[:200])



run(host='localhost', port=9921)
