#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Hello, world: with webscraping

Given a twitter handle, gathers their recent tweets, then does a google image
search for those texts, choosing pictures at random from the results.  Then it
mashes them up, and shows them to the user.  Fun!
"""

import flask                 # http://http://flask.pocoo.org/
import lxml.html
import os
import random
import re
import simplejson            # http://pypi.python.org/pypi/simplejson/
import urllib
import urllib2

app = flask.Flask(__name__)


COMMON_SHORTENERS = [re.compile('(?P<url>'+rex+')') for rex in 
                                         ['ur1.ca/\S+', 
                                          't.co/\S+', 
                                          'bit.ly/\S+',
                                          'instagr.am/\S+',
                                          'dlvr.it/\S+',
                                          '\w+\.com/\S+',
                                         ]]

def searchable(s):
    """Strip out the junk from s so it's easier to find good pictures"""
    s = s.strip()
    for shortener in COMMON_SHORTENERS:
        s = shortener.sub('', s)
    s = re.sub('@', '', s)
    s = re.sub('#', '', s)
    s = re.sub('Retweeted by \S+', '', s)
    return s

def linkable(s):
    """Turn things that are likely to be URLs into hot links
    
    Also autoheat @usernames and #tags
    """
    s = s.strip()
    for shortener in COMMON_SHORTENERS:
        s = shortener.sub('<a href="http://\g<url>">\g<url></a>', s)
    s = re.sub('@(?P<handle>\S+)', '<a href="https://www.twitter.com/#!/\g<handle>">@\g<handle></a>', s)
    s = re.sub('#(?P<tag>[^!]\S+)', '<a href="https://www.twitter.com/#!/search/%23\g<tag>">#\g<tag></a>', s)
    return s


@app.route("/")
@app.route("/hello")
@app.route("/hello/")
@app.route("/hello/<name>")
def hello(name=None):
    """Main driver, also serves as index"""
    if not name:
        return flask.render_template('hello_empty.html')

    txt = '\n'.join(urllib2.urlopen('http://mobile.twitter.com/'+name).readlines())
    tree = lxml.html.document_fromstring(txt)
    tweetlist = [t.text_content().strip() for t in tree.body.find_class('tweet-content')]
    google_api_base = u'https://ajax.googleapis.com/ajax/services/search/images?'
    output = ''

    for tweet in tweetlist:
        search = searchable(u'funny ' + tweet)
        try:
            search = google_api_base + urllib.urlencode({'v': 1.0, 'q': search, #'imgsz': 'medium',
                                                         'rsz': 8, 'safe': 'off'})
        except UnicodeEncodeError:
            # I haven't got my unicode handling right here yet
            continue
        search_results = simplejson.loads('\n'.join(urllib2.urlopen(search).readlines()))
        search_results = search_results['responseData']['results']
        if len(search_results) == 0:
            continue
        pic_url = random.choice(search_results)['url']
        #pic_url = search_results[0]['url']
        output += '<p>'+linkable(tweet)+'<br />'+'<img src='+pic_url+' /></p>'

    return flask.render_template('hello.html', name=name, body=output)

if __name__ == "__main__":
    import sys
    from getopt import getopt

    optvals, args = getopt(sys.argv[1:], 'di:', ['debug', 'ip'])
    opts = dict(optvals)

    app.debug = True if opts.has_key('-d') else False
    if opts.has_key('-k') and app.debug:
        app.secret_key = opts['-k']
    else:
        app.secret_key = '3edafd5e-0129-11e1-a693-0026b9ce365e'
    if opts.has_key('-i'):
        if app.debug:
            print "Debugging is insecure; don't do it while listening on a public IP."
            sys.exit(187)
        app.run(host=opts['-i'])
    app.run()
