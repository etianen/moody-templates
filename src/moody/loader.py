"""A caching template loader that allows disk-based templates to be used."""


import os, sys
from xml.sax.saxutils import escape

from moody.parser import default_parser, TemplateError, regex_macro, Node, Expression


class TemplateDoesNotExist(TemplateError):
    
    """A named template could not be found."""


# Default rules for autoescaping templates based on name.
DEFAULT_AUTOESCAPE_FUNCTIONS = {
    ".xml": escape,
    ".xhtml": escape,
    ".html": escape,
    ".htm": escape,
}


class Loader:
    
    """A caching template loader."""
    
    __slots__ = ("_template_dirs", "_template_cache", "_parser", "_loader_macros", "_autoescape_functions",)
    
    def __init__(self, template_dirs=(), parser=default_parser, loader_macros=(), autoescape_functions=DEFAULT_AUTOESCAPE_FUNCTIONS):
        """
        Initializes the loader.
        
        When specifying template_dirs on Windows,the forward slash '/' should be used as a path separator.
        """
        self._template_dirs = template_dirs
        self._template_cache = {}
        self._parser = parser
        self._loader_macros = loader_macros
        self._autoescape_functions = autoescape_functions
        
    def load(self, *template_names):        
        """
        Loads and returns the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        
        # Try to load.
        for template_name in template_names:
            _, extension = os.path.splitext(template_name)
            # Set up the default params.
            default_params = {
                "__autoescape__": self._autoescape_functions.get(extension),
                "__loader__": self
            }
            # Try to use the cache.
            if template_name in self._template_cache:
                return self._template_cache[template_name]
            # Try to use one of the template dirs.
            for template_dir in self._template_dirs:
                template_path = os.path.normpath(os.path.join(template_dir, template_name))
                if os.path.exists(template_path):
                    with open(template_path, "r") as template_file:
                        template = self._parser.compile(template_file.read(), default_params, self._loader_macros)
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


class IncludeNode(Node):
    
    """Node that implements an 'include' expression."""
    
    __slots__ = ("expression",)
    
    def __init__(self, expression):
        """Initializes the IncludeNode."""
        self.expression = expression
        
    def render(self, context):
        """Renders the IncludeNode."""
        template_name = self.expression.eval(context)
        loader = context.params["__loader__"]
        template = loader.load(template_name)
        template._render_to_context(context)


@regex_macro("^include\s+(.+?)$")
def include_macro(parser, lineno, expression):
    """Macro that implements an 'include' expression."""
    return IncludeNode(Expression(expression))


DEFAULT_LOADER_MACROS = (include_macro,)
        

# The default template loader, which loads templates from the pythonpath.
default_loader = Loader(sys.path, loader_macros=DEFAULT_LOADER_MACROS)