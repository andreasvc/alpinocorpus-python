#!/usr/bin/python
# -*- coding: utf-8 -*-

# server.py - A simple web API for Alpino corpora
#
# Author: Daniël de Kok <me@danieldk.eu>
#
# This is a simple web service that provides an interface to Alpino corpora
# using the alpinocorpus Python module. The only requirement is the web.py
# lightweight web framework.
#
# The API of this server is pretty simple: the following URLS are used:
#
# * /corpora                  : provides a list of corpora, tab separated values
# * /corpora.(js|json|xml)    : provides a list of corpora, javascript, json, xml
# * /<corpus>/entries         : provides a list of entries in the given corpus
# * /<corpus>/entry/<entry>   : retrieve an entry from a corpus
#
# The list of entries can be filtered by providing the 'query' parameter with
# an XPath query.
#
# Nodes matching an XPath query can be marked when retrieving an entry, by
# specifying the following parameters:
#
# * markerQuery : the query to use for marking nodes
# * markerAttr  : marker attribute
# * markerValue : marker value

import json, web

import alpinocorpus

from server_config import corpora

urls = (
      '/corpora(|\\.js|\\.json|\\.xml)', 'Corpora',
      '/([^/]*)/entries/?', 'Entries',
      '/(.*)/entry/(.*)', 'Entry',
      '/(.*)/validate', 'QueryValidation'
)

app = web.application(urls, globals())

def escapeSpecials(txt):
  return txt.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

def escapeXML(txt):
  return txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").encode("ascii", "xmlcharrefreplace")

class Corpora:
  def GET(self, ext):

    if ext == '.xml':

      web.header('Content-Type', 'text/xml')

      yield "<corpusarchive>\n"
      for corpus in sorted(corpora):
        info = corpora[corpus]
        yield """<corpus>
          <filename>%s</filename>
          <filesize>%d</filesize>
          <sentences>%d</sentences>
          <shortdesc>%s</shortdesc>
          <desc>%s</desc>
        </corpus>
""" % (corpus, info['filesize'], info['entries'], escapeXML(info['shortdesc']), escapeXML(info['longdesc']))
      yield "</corpusarchive>\n"

    elif ext == '.js' or ext == '.json':

      if ext == '.js':
        mst = 'javascript'
      else:
        mst = 'json'
      web.header('Content-Type', 'application/%s' % mst)

      if ext == '.js':
        yield "var corpora = "
      c = {}
      for corpus, info in corpora.iteritems():
        c[corpus] = {}
        for i in info:
          if i != "path":
            c[corpus][i] = info[i]
      yield json.dumps(c, sort_keys=True).replace('"}, "', '"},\n "')
      if ext == '.js':
        yield ";\n"
      else:
        yield "\n"

    else:

      web.header('Content-Type', 'text/plain; charset=utf-8')

      for corpus in sorted(corpora):
        info = corpora[corpus]
        yield "%s\t%d\t%s\t%s\n" % (corpus, info['entries'],
                                    escapeSpecials(info['shortdesc']).encode('utf-8'), escapeSpecials(info['longdesc']).encode('utf-8'))


class Entries:
  def GET(self, name):
    web.header('Content-Type', 'text/plain')

    if not corpora.has_key(name):
      yield web.notfound()

    try:
      c = alpinocorpus.CorpusReader(corpora[name]['path'])

      # Was a query provided?
      params = web.input()
      contents = False
      if params.has_key('query'):
        gen = c.query(params['query'].encode('utf-8'))
        if params.has_key('contents') and params.get('contents') == '1':
          contents = True
      else:
        gen = c.entries()

      # Stream (matching) entries
      for e in gen:
        if contents:
          yield "%s\t%s\n" % (e.name(), e.contents())
        else:
          yield "%s\n" % e.name()

    except RuntimeError:
      yield web.internalerror()

  def POST(self, name):
    web.header('Content-Type', 'text/plain')

    if not corpora.has_key(name):
      yield web.notfound()

    try:
      c = alpinocorpus.CorpusReader(corpora[name]['path'])

      params = web.input()

      # Do we want to highlight something?
      if params.has_key('markerQuery') and params.has_key('markerAttr') and params.has_key('markerValue'):
        markerQueries = [alpinocorpus.MarkerQuery(params['markerQuery'].encode('utf-8'),
          params['markerAttr'], params['markerValue'])]
      else:
        markerQueries = []

      # Was a query provided?
      if params.has_key('query'):
        gen = c.queryWithStylesheet(params['query'].encode('utf-8'), web.data(), markerQueries)
      else:
        gen = c.entriesWithStylesheet(web.data(), markerQueries)

      # Stream (matching) entries
      for e in gen:
        yield "%s\t%s\n" % (e.name(), escapeSpecials(e.contents()))

    except RuntimeError:
      yield web.internalerror()

class Entry:
  def GET(self, name, entry):
    web.header('Content-Type', 'text/xml')

    if not corpora.has_key(name):
      return web.notfound()

    params = web.input()
    try:
      c = alpinocorpus.CorpusReader(corpora[name]['path'])

      # Was there a request to mark entries?
      if params.has_key('markerQuery') and params.has_key('markerAttr') and params.has_key('markerValue'):
        queries = [alpinocorpus.MarkerQuery(params['markerQuery'].encode('utf-8'),
          params['markerAttr'], params['markerValue'])]
        data = c.readMarkQueries(entry, queries)
      else:
        data = c.read(entry)

    except RuntimeError:
      return web.notfound()

    return data

class QueryValidation:
  def GET(self, name):
    web.header('Content-Type', 'text/plain')

    if not corpora.has_key(name):
      return web.notfound()

    params = web.input()
    try:
      c = alpinocorpus.CorpusReader(corpora[name]['path'])

      # Was there a request to mark entries?
      if params.has_key('query'):
        query = params.get('query').encode('utf-8')
        if c.validQuery(query):
          return '1'
        else:
          return '0'
      else:
        return web.notfound()

    except RuntimeError:
      return web.notfound()

if __name__ == "__main__":

  app.run()
