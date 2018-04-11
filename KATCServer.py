#!/usr/bin/env python3
import bottle
from bottle import Bottle, route, run, template, request, response
import simplejson as json
from AutoTranslateCommon import *

app = Bottle()

@app.hook('after_request')
def enable_cors():
    """
    You need to add some headers to each request.
    Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

@app.error(405)
def method_not_allowed(res):
    if request.method == 'OPTIONS':
        new_res = bottle.HTTPResponse()
        new_res.set_header('Access-Control-Allow-Origin', '*')
        new_res.set_header('Access-Control-Allow-Headers', 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token')
        new_res.set_header('Access-Control-Allow-Methods', 'PUT, GET, POST, DELETE, OPTIONS')
        return new_res
    res.headers['Allow'] += ', OPTIONS'
    return request.app.default_error_handler(res)



@app.get('/apiv2/<lang>')
def index():
    pass

@app.get('/apiv2/patterns/<lang>')
def patterns(lang):
    length = request.query.length or 200
    length = int(length)
    data = read_patterns(lang, "ifpatterns")
    response.content_type = 'application/json'
    return json.dumps(data[:length])

@app.get('/apiv2/texttags/<lang>')
def patterns(lang):
    length=request.query.length or 200
    length = int(length)
    data=read_patterns(lang, "texttags")
    response.content_type = 'application/json'
    return json.dumps(data[:length])

def _modify_patterns(lang, pattype, engl, transl):
    # Brute force search-and-replace in patterns
    patterns=read_patterns(lang, pattype)
    n = 0
    for pattern in patterns:
        if pattern["english"] == engl:
            pattern["translated"] = transl
            print("Found", pattern)
            n += 1
    save_patterns(lang, pattype, patterns)
    return n

@app.post('/apiv2/save-pattern/<lang>')
def savePattern(lang):
    response.content_type = 'application/json'
    body = json.load(request.body)
    engl = body["english"]
    transl = body["translated"]
    if not transl:
        print("Error: No translation given")
        return json.dumps({"status": "error", "errorp": "No translation"})
    print(engl, "=>", transl)
    # Read texttags & ifpatterns for that lang
    n = _modify_patterns(lang, "ifpatterns", engl, transl)
    n += _modify_patterns(lang, "texttags", engl, transl)
    # Modify

    return json.dumps({"status": "ok", "count": n})

app.run(host='localhost', port=9921)
