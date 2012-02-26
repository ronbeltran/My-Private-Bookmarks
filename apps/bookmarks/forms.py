# -*- coding: utf-8 -*-
from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms

from bookmarks.models import Entry

class EntryForm(djangoforms.ModelForm):
  class Meta:
    model = Entry 
    exclude = ['author','short_url','pub_date','last_update',]

