# -*- coding: utf-8 -*-
from google.appengine.ext import db

class Entry(db.Model):
  """" Bookmark Entry """
  author = db.UserProperty(required=True, auto_current_user=True)
  title = db.StringProperty(required=True)
  url = db.StringProperty(required=True)
  short_url = db.TextProperty(required=False)
  tags = db.StringListProperty()
  pub_date = db.DateTimeProperty(auto_now_add=True)
  last_update = db.DateTimeProperty(auto_now=True)
  status = db.StringProperty(default='Live', choices=[
    'Draft', 'Live', 'Hidden'])
   
  @property
  def get_absolute_url(self):
    return '/entry/%s' % ( self.key().id(),)

  def to_dict(self):
    """Return a bookmark as Python Dict"""
    return {
      'author':self.author, 
      'title':self.title, 
      'url':self.url, 
      'short_url':self.short_url,
      'tags':self.tags,
      'pub_date':self.pub_date,
      'last_update':self.last_update,
      'status':self.status,
      }

  def to_json(self):
    """JSONify an bookmark"""
    return simplejson.dumps(self.to_dict())


