from __future__ import with_statement
import sys
import os
import codecs
import urllib
import operator
from hydeengine.siteinfo import ContentNode
from django.conf import settings
from django.template.loader import render_to_string
from hydeengine.file_system import Folder
from siteinfo import SiteNode

"""
    PRE PROCESSORS
    
    Can be launched before the parsing of each templates and
    after the loading of site info.
"""

class Category:
    """
    Plain object
    """
    def __init__(self, name=""):
        self.posts = []
        self.feed_url = None
        self.archive_url = None
        self.name = name

    @property
    def name(self):
        return self.name
    
    @property
    def posts(self):
        return self.posts

    @property
    def feed_url(self):
        return self.feed_url

    @property
    def archive_url(self):
        return self.archive_url
    

class CategoriesManager:   
    """
    Fetch the category(ies) from every post under the given node
    and creates a reference on them in the node.

    By default it generates also listing pages displaying every posts belonging
    to each category. You can turn it off by setting `archiving` param to `False`

       `params` : must contain the `template` key which will be used to render
                  the archive page
                  may contain the `output_folder` key to specify the destination
                  folder of the generated listing pages (by default: 'archives')
    """
    @staticmethod
    def process(folder, params):
        context = settings.CONTEXT
        site = context['site']    
        node = params['node']
        categories = {}
        for post in node.walk_pages():
            if hasattr(post, 'categories') and post.categories != None:
                for category in post.categories:
                    if categories.has_key(category) is False:
                        categories[category] = Category(category)
                    categories[category].posts.append(post)  
                    categories[category].posts.sort(key=operator.attrgetter("created"), reverse=True)
        l = []
        for category in categories.values():
            l.append({"name": category.name,
                      "posts": category.posts,
                      "feed_url": category.feed_url,
                      "post_count": len(category.posts)})

        node.categories = l
        for sub_node in node.walk():
            sub_node.categories = l

        #archiving section
        archiving = 'archiving' in params.keys() and params['archiving'] is False or True

        if archiving:
            categories = l
            #: defining the output folder - customisable
            if hasattr(settings,"CATEGORY_ARCHIVES_DIR"):
                relative_folder = output_folder = settings.CATEGORY_ARCHIVES_DIR
            else:
                relative_folder = output_folder = 'archives'
            if 'output_folder' in params and params['output_folder'] is not None \
                    and len(params['output_folder']) > 0:
                relative_folder = output_folder = params['output_folder']
            output_folder = os.path.join(settings.TMP_DIR, output_folder)
            if not os.path.isdir(output_folder):
                os.makedirs(output_folder)

            #: fetching default archive template
            template = None
            if 'template' in params:
                template = os.path.join(settings.LAYOUT_DIR, params['template'])
            else:
                raise ValueError("No template reference in CategoriesManager's settings")

            for category in categories:
                archive_resource = "%s.html" % urllib.quote_plus(category["name"])
                category["archive_url"] = "/%s/%s" % (relative_folder,
                                                         archive_resource)

            for category in categories:
                name = urllib.quote_plus(category["name"])
                posts = category["posts"]
                archive_resource = "%s.html" % (name)
                settings.CONTEXT.update({'category':category["name"], 
                                         'posts': posts,
                                         'categories': categories})
                output = render_to_string(template, settings.CONTEXT)
                with codecs.open(os.path.join(output_folder, \
                                     archive_resource), \
                                     "w", "utf-8") as file:
                    file.write(output)    

        
class NodeInjector(object):
    """
        Finds the node that represents the given path and injects it with the given     
        variable name into all the posts contained in the current node.
    """
    @staticmethod
    def process(folder, params):
        context = settings.CONTEXT
        site = context['site']
        node = params['node']
        try:
            varName = params['variable']
            path = params['path']
            params['injections'] = { varName: path }
        except KeyError:
            pass
        for varName, path in params['injections'].iteritems():
            nodeFromPathFragment = site.find_node(site.folder.parent.child_folder(path))
            if not nodeFromPathFragment:
                continue
            for post in node.walk_pages():
                setattr(post, varName, nodeFromPathFragment)

