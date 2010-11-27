"""A caching template loader that allows disk-based templates to be used."""


import os, sys
from xml.sax.saxutils import escape

from moody.parser import default_parser, TemplateError


class TemplateDoesNotExist(TemplateError):
    
    """A named template could not be found."""


# Default rules for autoescaping templates based on name/
DEFAULT_AUTOESCAPE_FUNCTIONS = {
    ".xml": escape,
    ".xhtml": escape,
    ".html": escape,
    ".htm": escape,
}


class Loader:
    
    """A caching template loader."""
    
    def __init__(self, template_dirs=(), parser=default_parser, autoescape_functions=DEFAULT_AUTOESCAPE_FUNCTIONS):
        """
        Initializes the loader.
        
        When specifying template_dirs on Windows,the forward slash '/' should be used as a path separator.
        """
        self._template_dirs = template_dirs
        self._template_cache = {}
        self._parser = parser
        self._autoescape_functions = autoescape_functions
        
    def load(self, *template_names):        
        """
        Loads and returns the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        
        # Try to load.
        for template_name in template_names:
            # See if any special template escaping needs to be done.
            default_params = {}
            _, extension = os.path.splitext(template_name)
            default_params["__autoescape__"] = self._autoescape_functions.get(extension)
            # Try to use the cache.
            if template_name in self._template_cache:
                return self._template_cache[template_name]
            # Try to use one of the template dirs.
            for template_dir in self._template_dirs:
                template_path = os.path.normpath(os.path.join(template_dir, template_name))
                if os.path.exists(template_path):
                    with open(template_path, "r") as template_file:
                        template = self._parser.compile(template_file.read(), default_params)
                    self._template_cache[template_name] = template
                    return template
        # Raise an error.
        template_name_string = ", ".join(repr(template_name) for template_name in template_names)
        template_dir_string = ", ".join(repr(template_dir) for template_dir in self._template_dirs)
        raise TemplateDoesNotExist("Could not find a template named {} in any of {}".format(template_name_string, template_dir_string))
        
    def render(self, *template_names, **params):
        """
        Loads and renders the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        return self.load(*template_names).render(**params)
        
        
default_loader = Loader(sys.path)