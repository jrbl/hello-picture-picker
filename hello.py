#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Hello, world: with webscraping

Given a twitter handle, gathers their recent tweets, then does a google image
search for those texts, choosing pictures at random from the results.  Then it
mashes them up, and shows them to the user.  Fun!
"""

import flask                 # http://flask.pocoo.org/
import lxml.html             # http://lxml.de/
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
IP_PORT = 54321

def print_help():
    helpstr = """
python hello.py [-d] [-i <ip_addr>]
    A silly toy for the internet.  Defaults to running on 127.0.0.1:%d.

-d: DEBUG on: turns on full stack traces: do not do with -i!!
-i: specify IP address to bind to.  to serve on the public Internet, use this
    option.  Do not use with -d.
""" % IP_PORT
    print helpstr
    return


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
@app.route("/<path:staticfile>")
def index(staticfile=None):
    """Useful if you want to be able to get things like .css and .js files"""
    if staticfile:
        # this doesn't perform well; should be set up in a proper webserver
        flask.send_from_directory('static', staticfile)
    else:
        return hello()

@app.route("/hello")
@app.route("/hello/")
@app.route("/hello/<name>")
def hello(name=None):
    """Main driver, also serves as index"""
    if not name:
        return flask.render_template('hello_empty.html')
    
    try:
        # mobile twitter is easy to scrape
        handle = urllib2.urlopen(u'http://mobile.twitter.com/'+name)
    except urllib2.HTTPError:
        # TODO: pop up a nice message explaining that their page couldn't be found
        return index()
    txt = '\n'.join(handle.readlines())
    tree = lxml.html.document_fromstring(txt)
    tweetlist = [t.text_content().strip() for t in tree.body.find_class('tweet-content')]
    # XXX: google ajax api is limited to 8 results per hit
    google_api_base = u'https://ajax.googleapis.com/ajax/services/search/images?'
    output = ''

    for tweet in tweetlist:
        search = searchable(u'hilarious ' + tweet)
        try:
            search = google_api_base + urllib.urlencode({'v': 1.0, 'q': search, 
                                                        #'imgsz': 'medium', # restrictions make it worse
                                                         'rsz': 8, 'safe': 'off'})
        except UnicodeEncodeError:
            # XXX: I haven't got my unicode handling right here yet, but we can at least avoid exceptions
            continue
        search_results = simplejson.loads('\n'.join(urllib2.urlopen(search).readlines()))
        search_results = search_results['responseData']['results']
        if len(search_results) == 0:
            continue
        pic_url = random.choice(search_results)['url']
        output += '<div class="tweetdiv"><p class="tweettext">'+linkable(tweet)
        output += '</p>'+'<img class="tweetpic" src='+pic_url+' /></div>'

    return flask.render_template('hello.html', name=name, body=output)


if __name__ == "__main__":
    import sys
    from getopt import getopt

    optvals, args = getopt(sys.argv[1:], 'di:h', ['debug', 'ip', 'help'])
    opts = dict(optvals)

    app.debug = True if opts.has_key('-d') else False
    if opts.has_key('-h'):
        print_help()
        sys.exit()
    if opts.has_key('-i'):
        if app.debug:
            print "Debugging is insecure; don't do it while listening on a public IP."
            sys.exit(187)
        app.run(host=opts['-i'], port=IP_PORT)
    app.run(port=IP_PORT)
