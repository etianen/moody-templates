"""A caching template loader that allows disk-based templates to be used."""


import os, sys, re
from abc import ABCMeta, abstractmethod
from xml.sax.saxutils import escape

from moody.parser import default_parser, regex_macro, Node, Expression, Template


class TemplateDoesNotExist(Exception):
    
    """A named template could not be found."""


# Default rules for autoescaping templates based on name.
DEFAULT_AUTOESCAPE_FUNCTIONS = {
    ".xml": escape,
    ".xhtml": escape,
    ".html": escape,
    ".htm": escape,
}


class Source(metaclass=ABCMeta):
    
    """A source of template data."""
    
    __slots__ = ()
    
    @abstractmethod
    def load_source(self, template_name):
        """
        Loads the template source code for the template of the given name.
        
        If no source code can be found, returns None.
        """
        
        
class MemorySource(Source):

    """A template loader that loads from memory."""
    
    __slots__ = ("templates",)
    
    def __init__(self, templates):
        """Initializes the MemorySource from a dict of template source strings."""
        self.templates = templates
        
    def load_source(self, template_name):
        """Loads the source from the memory template dict."""
        return self.templates.get(template_name)
        
    def __str__(self):
        """Returns a string representation."""
        return "<memory>"
        
        
class DirectorySource(Source):
    
    """A template loader that loads from a directory on disk."""
    
    __slots__ = ("dirname")
    
    def __init__(self, dirname):
        """
        Initializes the DirectorySource.
        
        On windows, the dirname should be specified using forward-slashes.
        """
        self.dirname = dirname
        
    def load_source(self, template_name):
        """Loads the source from disk."""
        template_path = os.path.normpath(os.path.join(self.dirname, template_name))
        if os.path.exists(template_path):
            with open(template_path, "r") as template_file:
                return template_file.read()
        return None
        
    def __str__(self):
        """Returns a string representation."""
        return self.dirname


def get_template(context, template):
    """
    If template is a str, then looks up the loader and loads the template.
    
    Otherwise, if template is a template, returns the template.
    """
    if isinstance(template, Template):
        return template
    if isinstance(template, str):
        if "__loader__" in context.params:
            loader = context.params["__loader__"]
            return loader.load(template)
        raise ValueError("Cannot load template named {!r}, as this template was not created by a Loader.".format(template))
    raise TypeError("Expected a Template or a str, found {!r}.".format(template))


class IncludeNode(Node):
    
    """Node that implements an 'include' expression."""
    
    __slots__ = ("expression",)
    
    def __init__(self, expression):
        """Initializes the IncludeNode."""
        self.expression = expression
        
    def render(self, context):
        """Renders the IncludeNode."""
        template = get_template(context, self.expression.eval(context))
        with context.block() as sub_context:
            template._render_to_context(sub_context)


@regex_macro("^include\s+(.+?)$")
def include_macro(parser, expression):
    """Macro that implements an 'include' expression."""
    return IncludeNode(Expression(expression))


class BlockNode(Node):
    
    """A block of inheritable content."""
    
    __slots__ = ("name", "block",)
    
    def __init__(self, name, block):
        """Initializes the BlockNode."""
        self.name = name
        self.block = block
        
    def render(self, context):
        """Renders the BlockNode."""
        # Add my block to the stack.
        stack = context.params.get("__blocks__", {}).get(self.name, [])
        stack.append(self.block)
        # Render the bottommost block.
        with context.block() as sub_context:
            stack[0]._render_to_context(sub_context)


@regex_macro("^block\s+([a-zA-Z_][a-zA-Z_\-0-9]*)$")
def block_macro(parser, name):
    """Macro that implements an inheritable template block."""
    match, block = parser.parse_block("block", "endblock", re.compile("^endblock$|^endblock\s+{}$".format(name)))
    return BlockNode(name, block)
    
    
class ExtendsNode(Node):
    
    """Implements a inherited child template."""
    
    __slots__ = ("expression", "block_nodes",)
    
    def __init__(self, expression, block_nodes):
        """Initializes the ExtendsNode."""
        self.expression = expression
        self.block_nodes = block_nodes
        
    def render(self, context):
        """Renders the ExtendsNode."""
        template = get_template(context, self.expression.eval(context))
        # Get the block information.
        block_info = context.params.setdefault("__blocks__", {})
        for block_node in self.block_nodes:
            block_info.setdefault(block_node.name, []).append(block_node.block)
        # Render the parent template with my blocks.
        with context.block() as sub_context:
            template._render_to_context(sub_context)
    
    
@regex_macro("^extends\s+(.+?)$")
def extends_macro(parser, expression):
    """Macro that implements an inherited child template."""
    # Parse the rest of the template.
    nodes = parser.parse_all_nodes()
    # Go through the nodes, looking for all block tags.
    block_nodes = [node for node in nodes if isinstance(node, BlockNode)]
    return ExtendsNode(Expression(expression), block_nodes)
    

# Default additional macros available to a template loader.    
DEFAULT_LOADER_MACROS = (include_macro, block_macro, extends_macro,)


class DebugLoader:

    """
    A template loader that doesn't cache compiled templates.
    
    Terrible performance, but great for debugging.
    """
    
    __slots__ = ("_sources", "_parser", "_loader_macros", "_autoescape_functions",)
    
    def __init__(self, sources, parser=default_parser, loader_macros=DEFAULT_LOADER_MACROS, autoescape_functions=DEFAULT_AUTOESCAPE_FUNCTIONS):
        """
        Initializes the Loader.
        
        When specifying template_dirs on Windows,the forward slash '/' should be used as a path separator.
        """
        # Initialize the sources.
        self._sources = []
        for source in sources:
            if isinstance(source, Source):
                self._sources.append(source)
            elif isinstance(source, str):
                self._sources.append(DirectorySource(source))
            else:
                raise TypeError("Arguments for source should be a str or a Source instance, not {!r}.".format(source))
        # And the rest.
        self._parser = parser
        self._loader_macros = loader_macros
        self._autoescape_functions = autoescape_functions
    
    def _load_all(self, template_name):
        """Loads and returns all the named templates from the sources."""
        # Get the autoescape function.
        _, extension = os.path.splitext(template_name)
        autoescape = self._autoescape_functions.get(extension)
        # Load from all the template sources.
        templates = []
        for source in self._sources:
            template_src = source.load_source(template_name)
            if template_src is not None:
                default_params = {
                    "__autoescape__": autoescape,
                    "__loader__": self,
                    "__super__": templates and templates[-1] or None,
                }
                templates.append(self._parser.compile(template_src, template_name, default_params, self._loader_macros))
        return templates
    
    def load(self, *template_names):        
        """
        Loads and returns the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        if not template_names:
            raise ValueError("You must specify at least one template name.")
        for template_name in template_names:
            templates = self._load_all(template_name)
            if templates:
                return templates[-1]
        # Raise an error.
        template_name_str = ", ".join(repr(template_name) for template_name in template_names)
        source_name_str = ", ".join(str(source) for source in self._sources)
        raise TemplateDoesNotExist("Could not find a template named {} in any of {}.".format(template_name_str, source_name_str))
        
    def render(self, *template_names, **params):
        """
        Loads and renders the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        return self.load(*template_names).render(**params)


class Loader(DebugLoader):
    
    """
    A template loader.
    
    Compiled templates are cached for performance.
    """
    
    __slots__ = ("_cache",)
    
    def __init__(self, *args, **kwargs):
        """Initializes the loader."""
        super(Loader, self).__init__(*args, **kwargs)
        self._cache = {}
    
    def clear_cache(self, ):
        """Clears the template cache."""
        self._cache.clear()
        
    def _load_all(self, template_name):
        """A caching version of the debug loader's load method."""
        if template_name in self._cache:
            return self._cache[template_name]
        template = super(Loader, self)._load_all(template_name)
        self._cache[template_name] = template
        return template
        

# The default template loader, which loads templates from the pythonpath.
default_loader = Loader(sys.path)