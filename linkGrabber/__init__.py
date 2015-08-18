""" Module that scrapes a web page for hyperlinks """
import re
import types
import collections
import pprint
from urlparse import urlparse, urljoin

import requests

from bs4 import BeautifulSoup

content_allow = ['text/plain', 'text/html']


class Links(object):

    """Grabs links from a web page
    based upon a URL and filters"""

    def __init__(self, href=None, text=None, parser='lxml'):
        """ Create instance of Links class

        :param href: URL to download links from
        :param text: Search through text for links instead of URL
        :param parser: Parser for BeautifulSoup library. [default: lxml]
        """
        if href is not None and not href.startswith('http'):
            raise ValueError("URL must contain http:// or https://")
        elif href is not None:
            self._href = href
            self._response = requests.get(self._href)
            if self._response.status_code != 200:
                raise ValueError('Response FAIL: %s' %
                                 self._response.status_code)

            if not hasattr(self._response, 'headers'):
                raise ValueError('Response has not headers')

            if 'content-type' not in self._response.headers:
                raise ValueError('content-type information is not available')

            self._ctype = self._response.headers['content-type'].rsplit(';')[0]
            if self._ctype not in content_allow:
                raise ValueError(
                    'the content-type %s is not textable' % self._ctype)

            self._text = self._response.text

        elif href is None and text is not None:
            self._text = text
        else:
            raise ValueError("Either href or text must not be empty")

        self._soup = BeautifulSoup(self._text, parser)

    def __repr__(self):
        return "<Links {0}>".format(self._href or self._text[:15] + '...')

    @property
    def text(self):
        return self._text

    @property
    def response(self):
        return self._response

    def find(self, limit=None, reverse=False, sort=None,
             exclude=None, duplicates=True, pretty=False,
             all_same_root=False,  join_domain=False,  **filters):
        """ Using filters and sorts, this finds all hyperlinks
        on a web page

        :param limit: Crop results down to limit specified
        :param reverse: Reverse the list of links, useful for before limiting
        :param exclude: Remove links from list
        :param duplicates: Determines if identical URLs should be displayed
        :param pretty: Quick and pretty formatting using pprint
        :param all_same_root: exclude all links without root domain of it was specified. 
        :param join_domain: return all href with root domain joined if it starts with '/'
        :param filters: All the links to search for """

        exclude = exclude or []
        filters = filters or {}

        search = self._soup.findAll('a', **filters)

        if reverse:
            search.reverse()

        urlsvisited = collections.defaultdict(bool)
        siteinfo = urlparse(self._href)

        links = []
        for anchor in search:
            build_link = anchor.attrs

            if 'href' in anchor.attrs:
                anchor['href'] = anchor['href'].strip()
                if join_domain:
                    anchor['href'] = urljoin(self._href, anchor['href'])
                link = urlparse(anchor['href'])
                if all_same_root and link.netloc != siteinfo.netloc:
                    continue
                build_link[u'seo'] = seoify_hyperlink(anchor['href'])
            elif all_same_root:
                continue

            if u'seo' in build_link:
                build_link[u'text'] = anchor.string or build_link[u'seo']

            ignore_link = False
            for nixd in exclude:
                for key, value in iteritems(nixd):
                    if key in build_link:
                        if (isinstance(build_link[key], collections.Iterable)
                                and not isinstance(build_link[key], types.StringTypes)):
                            for item in build_link[key]:
                                ignore_link = exclude_match(value, item)
                        else:
                            ignore_link = exclude_match(value, build_link[key])

            if not duplicates:
                if anchor.get('href', None):
                    ignore_link = urlsvisited[anchor['href']]

            if not ignore_link:
                urlsvisited[anchor.get('href', None)] = True
                links.append(build_link)

            if limit and len(links) == limit:
                break

        if sort:
            links = sorted(links, key=sort, reverse=reverse)

        if pretty:
            pp = pprint.PrettyPrinter(indent=4)
            return pp.pprint(links)
        else:
            return links


def exclude_match(exclude, link_value):
    """ Check excluded value against the link's current value """
    if hasattr(exclude, "search") and exclude.search(link_value):
        return True

    if exclude == link_value:
        return True

    return False


def seoify_hyperlink(hyperlink):
    """Modify a hyperlink to make it SEO-friendly by replacing
    hyphens with spaces and trimming multiple spaces.

    :param hyperlink: URL to attempt to grab SEO from """
    last_slash = hyperlink.rfind('/')
    return re.sub(r' +|-', ' ', hyperlink[last_slash + 1:])


def iteritems(d):
    """ Factor-out Py2-to-3 differences in dictionary item
    iterator methods """
    try:
        return d.iteritems()
    except AttributeError:
        return d.items()
