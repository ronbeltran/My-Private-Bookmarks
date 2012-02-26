# -*- coding: utf-8 -*-
from google.appengine.ext import db


class Entry(db.Model):

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
