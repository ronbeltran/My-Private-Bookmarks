#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os 
import logging
import webapp2
import filters
import urllib
import hashlib

sys.path.insert(0, 'jinja2.zip')
sys.path.insert(0, 'webapp2_extras.zip')
sys.path.insert(0, 'apps')

from webapp2 import Route
from webapp2 import uri_for 
from webapp2_extras import jinja2

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache

from bookmarks.models import Entry
from bookmarks.forms import EntryForm

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

HOME_MAX_ENTRY = 100
MAX_ENTRY_FETCH = 1000
MY_BMARKS_MAX_ENTRY = 100
GRAVATAR_SIZE = 80
GRAVATAR_DEFAULT_IMAGE = ""


if DEBUG:
  CACHE_EXPIRE_TIME = 0 # dont cache in dev
else:
  CACHE_EXPIRE_TIME = 60 * 5 # minutes


def user_required(handler):
  """
  A decorator to check if user is logged in
  """
  def check_login(self, *args, **kwargs):
    if not users.get_current_user():
      self.redirect(users.create_login_url())
    else:
      return handler(self, *args, **kwargs)
  return check_login


def get_gravatar_url(email):
  gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
  gravatar_url += urllib.urlencode({'d':GRAVATAR_DEFAULT_IMAGE, 's':str(GRAVATAR_SIZE)})
  return gravatar_url


config = {}
config = {
  'site_config': {
    'SITE_TITLE':'My Private Bookmarks',
    'SITE_DESCRIPTION':'Save your private bookmarks',
    'SITE_AUTHOR':'Ronnie Beltran',
    'SITE_URL':'http://myprivatebookmarks.appspot.com',
    'SITE_EMAIL':'rbbeltran.09@gmail.com',
    'URCHIN_ID':'',
    'DISQUS_SHORT_NAME':'',
    'DEBUG': DEBUG,
  }, # end site_config
  'webapp2_extras.sessions': {
    'secret_key': 'change_me',
  }, # webapp2_extras.sessions
  'webapp2_extras.jinja2': {
    'template_path': 'templates',
      'filters': {
        'timesince': filters.timesince,
        'datetimeformat': filters.datetimeformat,
       }, # end filters
      'globals': {
        'uri_for': webapp2.uri_for,
        'get_gravatar_url':get_gravatar_url,
      }, # end globals
    }, # end webapp2_extras.jinja2
}


def handle_500(request, response, exception):
  logging.exception(exception)
  response.write("A server error occurred!")
  response.set_status(500)


class BaseHandler(webapp2.RequestHandler):
  """Implements Google Accounts authentication methods."""
  def get_current_user(self):
    user = users.get_current_user()
    if user: user.administrator = users.is_current_user_admin()
    return user


  def get_login_logout_url(self):
    link = ''
    if self.get_current_user():
      link = users.create_logout_url(self.request.path)
    else:
      link = users.create_login_url(self.request.path)
    return link

  @webapp2.cached_property
  def jinja2(self):
    # Returns a Jinja2 renderer cached in the app registry.
    return jinja2.get_jinja2(app=self.app)

  def render_response(self, _template, **context):
    # Renders a template and writes the result to the response.
    context_variables = {
      'link': self.get_login_logout_url(),
      'user': self.get_current_user(),
    }
    context.update(self.app.config.get('site_config'))
    context.update(context_variables)
    rv = self.jinja2.render_template(_template, **context)
    self.response.write(rv)


class HomeHandler(BaseHandler):
  def get(self):
    variables = {
    }
    self.render_response('home.html', **variables)

class AboutHandler(BaseHandler):
  def get(self):
    self.render_response('about.html')


class MyBookmarksHandler(BaseHandler):
  @user_required
  def get(self):
    # don't cache query for logged in users
    entries = db.Query(Entry).filter('author =', self.get_current_user()).order('-pub_date').fetch(limit=MY_BMARKS_MAX_ENTRY)
    variables = {
      'entries' : entries,
    }
    self.render_response('entry/mybookmarks.html', **variables)

  def get_entries_from_memcache(self):
    # get entries from memcache
    entries = memcache.get('my_pastes_entries')
    if entries is not None:
      return entries
    else:
      # if not found in cache hit the datastore and cache the result
      entries = db.Query(Entry).filter('author =', self.get_current_user()).order('-pub_date').fetch(limit=MY_BMARKS_MAX_ENTRY)
      if not memcache.add(key='my_pastes_entries', value=entries, time=CACHE_EXPIRE_TIME):
        logging.error('Memcached set in MyPastesHandler failed.')
      return entries


class TagHandler(BaseHandler):
  def get(self, tag):
    entries = db.Query(Entry).filter('status =', 'Live').filter('tags =',tag).order('-pub_date').fetch(limit=HOME_MAX_ENTRY)
    if not entries:
      raise webapp2.abort(404)
    variables = {
      'entries' : entries,
      'tag' : tag,
    }
    self.render_response('entry/tag.html', **variables)


class NewEntryHandler(BaseHandler):
  @user_required
  def get(self):
    variables = {
      'form' : EntryForm(),
    }
    return self.render_response('entry/add_entry.html', **variables )

  @user_required
  def post(self):
    variables = {
      'form' : EntryForm(self.request.POST),
    }
    data = EntryForm(data=self.request.POST)
    if data.is_valid():
      entry = data.save(commit=False)
      # limit the tags to 5
      entry.tags = entry.tags[0:5]
      # prettify the tags 
      entry.tags = [str(tag).strip().replace(' ', '_') for tag in entry.tags ]
      entry.author = users.get_current_user()
      entry.put()
      self.redirect('/u/entries')
    else:
      return self.render_response('entry/add_entry.html', **variables )


class EditEntryHandler(BaseHandler):
  @user_required
  def get(self):
    entry_id = int(self.request.get('entry_id'))
    entry = Entry.get(db.Key.from_path('Entry', entry_id))
    if not entry:
      raise webapp2.abort(404)
    if users.get_current_user() != entry.author:
      raise webapp2.abort(403)
    variables = {
      'form' : EntryForm(instance=entry),
      'entry_id': entry_id,
    }
    return self.render_response('entry/edit_entry.html', **variables )

  @user_required
  def post(self):
    entry_id = int(self.request.get('entry_id'))
    entry = Entry.get(db.Key.from_path('Entry', entry_id))
    if not entry:
      raise webapp2.abort(404)
    if users.get_current_user() != entry.author:
      raise webapp2.abort(403)
    data = EntryForm(data=self.request.POST, instance=entry)
    if data.is_valid():
      entry = data.save(commit=False)
      # prettify the tags 
      entry.tags = [str(tag).strip().replace(' ', '_') for tag in entry.tags ]
      entry.author = users.get_current_user()
      entry.put()
      self.redirect('/u/entries')
    else:
      return self.render_response('entry/edit_entry.html', **variables )


routes = [
  Route(r'/', handler=HomeHandler, name='home'),
  Route(r'/about', handler=AboutHandler, name='about'),
  Route(r'/u/entries', handler=MyBookmarksHandler, name='my_bookmarks'),
  Route(r'/entry/new', handler=NewEntryHandler, name='entry_new'),
  Route(r'/entry/edit', handler=EditEntryHandler, name='entry_edit'),
  Route(r'/tags/<tag>', handler=TagHandler, name='entry_tag'),
  ]


app = webapp2.WSGIApplication(routes, config=config, debug=DEBUG)
app.error_handlers[500] = handle_500


def main():
  app.run()


if __name__ == '__main__':
  main()
