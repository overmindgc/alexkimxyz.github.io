#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Alexander Kim'
SITENAME = "Alex Kim's Blog"
SITEURL = 'http://alexkimxyz.github.io'

PATH = 'content'

TIMEZONE = 'America/Montreal'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
# LINKS = (
# 			('LinkedIn', 'https://www.linkedin.com/in/alexkimxyz'),
# 			('Github', 'https://github.com/alexkimxyz'),
# 			('Twitter', 'https://twitter.com/alexkimxyz'),
# 		)

# Social widget
SOCIAL = (
			('LinkedIn', 'https://www.linkedin.com/in/alexkimxyz'),
			('Github', 'https://github.com/alexkimxyz'),
			('Twitter', 'https://twitter.com/alexkimxyz'),
		)

DEFAULT_PAGINATION = 3

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True
MARKUP = ('md', 'ipynb')

PLUGIN_PATHS = ['./plugins']
PLUGINS = ['ipynb.markup']

# if you create jupyter files in the content dir, snapshots are saved with the same
# metadata. These need to be ignored. 
IGNORE_FILES = [".ipynb_checkpoints"]  
THEME = './theme/pelican-simplegrey'