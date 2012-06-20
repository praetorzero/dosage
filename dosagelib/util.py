from __future__ import division

import urllib2, urlparse
import sys
import struct
import array
import os
import cgi
import re
import traceback
import time
from htmlentitydefs import name2codepoint
from math import log, floor

from .output import out
from .configuration import UserAgent, AppName, App, SupportUrl

class NoMatchError(Exception): pass

def getMatchValues(matches):
    return set([match.group(1) for match in matches])

def fetchManyMatches(url, regexes):
    '''Returns a list containing lists of matches for each regular expression, in the same order.'''
    out.write('Matching regex(es) %r multiple times against %s...' % ([rex.pattern for rex in regexes], url), 2)
    page = urlopen(url)
    data = page.read()

    matches = [getMatchValues(regex.finditer(data)) for regex in regexes]
    if matches:
        out.write('...found %r' % (matches,), 2)
    else:
        out.write('...not found!', 2)

    return list(matches)

def fetchMatches(url, regexes):
    out.write('Matching regex(es) %r against %s...' % ([rex.pattern for rex in regexes], url), 2)
    page = urlopen(url)
    data = page.read()

    matches = []
    for regex in regexes:
        match = regex.search(data)
        if match:
            matches.append(match.group(1))

    if matches:
        out.write('...found %r' % (matches,), 2)
    else:
        out.write('...not found!', 2)

    return matches

def fetchMatch(url, regex):
    matches = fetchMatches(url, (regex,))
    if matches:
        return matches[0]
    return None

def fetchUrl(url, regex):
    match = fetchMatch(url, regex)
    if match:
        return urlparse.urljoin(url, match)
    return None

baseSearch = re.compile(r'<base\s+href="([^"]*)"\s+/?>', re.IGNORECASE)
def fetchUrls(url, regexes):
    matches = fetchMatches(url, [baseSearch] + list(regexes))
    baseUrl = matches.pop(0) or url
    return [urlparse.urljoin(baseUrl, match) for match in matches]

def fetchManyUrls(url, regexes):
    matchGroups = fetchManyMatches(url, [baseSearch] + list(regexes))
    baseUrl = matchGroups.pop(0) or [url]
    baseUrl = baseUrl[0]

    xformedGroups = []
    for matchGroup in matchGroups:
        xformedGroups.append([urlparse.urljoin(baseUrl, match) for match in matchGroup])

    return xformedGroups

def _unescape(text):
    """
    Replace HTML entities and character references.
    """
    def _fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    text = unichr(int(text[3:-1], 16))
                else:
                    text = unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        if isinstance(text, unicode):
            text = text.encode('utf-8')
            text = urllib2.quote(text, safe=';/?:@&=+$,')
        return text
    return re.sub("&#?\w+;", _fixup, text)

def normaliseURL(url):
    """
    Removes any leading empty segments to avoid breaking urllib2; also replaces
    HTML entities and character references.
    """
    # XXX: brutal hack
    url = _unescape(url)
    url = url.replace(' ', '%20')

    pu = list(urlparse.urlparse(url))
    segments = pu[2].replace(' ', '%20').split('/')
    while segments and segments[0] == '':
        del segments[0]
    pu[2] = '/' + '/'.join(segments)
    return urlparse.urlunparse(pu)


def urlopen(url, referrer=None, retries=5):
    # Work around urllib2 brokenness
    url = normaliseURL(url)
    req = urllib2.Request(url)
    if referrer:
        req.add_header('Referrer', referrer)
        req.add_header('Referer', referrer)
    req.add_header('User-Agent', UserAgent)

    tries = 0
    while 1:
        try:
            urlobj = urllib2.urlopen(req)
            break
        except IOError:
            out.write('URL retrieval failed, sleeping %d seconds and retrying (%d)' % (2**tries, tries), 2)
            time.sleep(2**tries)
            tries += 1
            if tries >= retries:
                raise

    return urlobj

def getWindowSize():
    try:
        from fcntl import ioctl
        from termios import TIOCGWINSZ
    except ImportError:
        raise NotImplementedError
    st = 'HHHH'
    names = 'ws_row', 'ws_col', 'ws_xpixel', 'ws_ypixel'
    buf = array.array('b', ' ' * struct.calcsize(st))
    try:
        ioctl(sys.stderr, TIOCGWINSZ, buf, True)
    except IOError:
        raise NotImplementedError
    winsize = dict(zip(names, struct.unpack(st, buf.tostring())))
    return winsize['ws_col']

suffixes = ('B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')

def saneDataSize(size):
    if size == 0:
        return 'unk B'
    index = int(floor(log(abs(size), 1024)))
    index = min(index, len(suffixes) - 1)
    index = max(index, 0)
    factor = 1024 ** index
    return '%0.3f %s' % (float(size) / factor, suffixes[index])

def splitpath(path):
    c = []
    head, tail = os.path.split(path)
    while tail:
        c.insert(0, tail)
        head, tail = os.path.split(head)
    return c

def getRelativePath(basepath, path):
    basepath = splitpath(os.path.abspath(basepath))
    path = splitpath(os.path.abspath(path))

    afterCommon = False
    for c in basepath:
        if afterCommon or path[0] != c:
            path.insert(0, os.path.pardir)
            afterCommon = True
        else:
            del path[0]

    return os.path.join(*path)

def getQueryParams(url):
    query = urlparse.urlsplit(url)[3]
    out.write('Extracting query parameters from %r (%r)...' % (url, query), 3)
    return cgi.parse_qs(query)


def internal_error(out=sys.stderr, etype=None, evalue=None, tb=None):
    """Print internal error message (output defaults to stderr)."""
    print >> out, os.linesep
    print >> out, """********** Oops, I did it again. *************

You have found an internal error in %(app)s. Please write a bug report
at %(url)s and include the following information:
- your commandline arguments and any configuration file in ~/.dosage/
- the system information below

Not disclosing some of the information above due to privacy reasons is ok.
I will try to help you nonetheless, but you have to give me something
I can work with ;) .
""" % dict(app=AppName, url=SupportUrl)
    if etype is None:
        etype = sys.exc_info()[0]
    if evalue is None:
        evalue = sys.exc_info()[1]
    print >> out, etype, evalue
    if tb is None:
        tb = sys.exc_info()[2]
    traceback.print_exception(etype, evalue, tb, None, out)
    print_app_info(out=out)
    print_proxy_info(out=out)
    print_locale_info(out=out)
    print >> out, os.linesep, \
            "******** %s internal error, over and out ********" % AppName


def print_env_info(key, out=sys.stderr):
    """If given environment key is defined, print it out."""
    value = os.getenv(key)
    if value is not None:
        print >> out, key, "=", repr(value)


def print_proxy_info(out=sys.stderr):
    """Print proxy info."""
    print_env_info("http_proxy", out=out)


def print_locale_info(out=sys.stderr):
    """Print locale info."""
    for key in ("LANGUAGE", "LC_ALL", "LC_CTYPE", "LANG"):
        print_env_info(key, out=out)


def print_app_info(out=sys.stderr):
    """Print system and application info (output defaults to stderr)."""
    print >> out, "System info:"
    print >> out, App
    print >> out, "Python %(version)s on %(platform)s" % \
                    {"version": sys.version, "platform": sys.platform}
    stime = strtime(time.time())
    print >> out, "Local time:", stime


def strtime(t):
    """Return ISO 8601 formatted time."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + \
           strtimezone()


def strtimezone():
    """Return timezone info, %z on some platforms, but not supported on all.
    """
    if time.daylight:
        zone = time.altzone
    else:
        zone = time.timezone
    return "%+04d" % (-zone//3600)


def tagre(tag, attribute, value):
    """Return a regular expression matching the given HTML tag, attribute
    and value. It matches the tag and attribute names case insensitive,
    and skips arbitrary whitespace and leading HTML attributes.
    Also, it adds a match group for the value.
    @param tag: the tag name
    @ptype tag: string
    @param attribute: the attribute name
    @ptype attribute: string
    @param value: the attribute value
    @ptype value: string
    @return: the generated regular expression suitable for re.compile()
    @rtype: string
    """
    attrs = dict(
        tag=case_insensitive_re(tag),
        attribute=case_insensitive_re(attribute),
        value=value,
    )
    return r'<\s*%(tag)s[^>]*\s+%(attribute)s\s*=\s*"(%(value)s)"' % attrs

def case_insensitive_re(name):
    """Reformat the given name to a case insensitive regular expression string
    without using re.IGNORECASE. This way selective strings can be made case
    insensitive.
    @param name: the name to make case insensitive
    @ptype name: string
    @return: the case insenstive regex
    @rtype: string
    """
    return "".join("[%s%s]" % (c.lower(), c.upper()) for c in name)
