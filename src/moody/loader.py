"""A caching template loader that allows disk-based templates to be used."""


import os, sys, re
from abc import ABCMeta, abstractmethod
from xml.sax.saxutils import escape

from moody.parser import default_parser, regex_macro, Node, Expression


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
        # Get the parent.
        template_name = self.expression.eval(context)
        loader = context.params["__loader__"]
        template = loader.load(template_name)
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


class Loader:
    
    """A template loader."""
    
    __slots__ = ("_sources", "_parser", "_loader_macros", "_autoescape_functions", "_cache")
    
    def __init__(self, sources, parser=default_parser, loader_macros=DEFAULT_LOADER_MACROS, autoescape_functions=DEFAULT_AUTOESCAPE_FUNCTIONS):
        """
        Initializes the Loader.
        
        When specifying template_dirs on Windows,the forward slash '/' should be used as a path separator.
        """
        self._sources = sources
        self._parser = parser
        self._loader_macros = loader_macros
        self._autoescape_functions = autoescape_functions
        self._cache = {}
    
    def clear_cache(self):
        """Clears the template cache."""
        self._cache.clear()
        
    def load(self, template_name, *fallback_names):        
        """
        Loads and returns the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        if template_name in self._cache:
            return self._cache[template_name]
        all_template_names = (template_name,) + fallback_names
        # Try to load.
        for template_name_item in all_template_names:
            _, extension = os.path.splitext(template_name_item)
            # Set up the default params.
            default_params = {
                "__autoescape__": self._autoescape_functions.get(extension),
                "__loader__": self
            }
            # Try to use one of the template loaders.
            for source in self._sources:
                template_src = source.load_source(template_name_item)
                if template_src is not None:
                    template = self._parser.compile(template_src, template_name_item, default_params, self._loader_macros)
                    self._cache[template_name] = template
                    return template
        # Raise an error.
        raise TemplateDoesNotExist("Could not find a template named {}.".format(", ".join(repr(template_name) for template_name in all_template_names)))
        
    def render(self, *template_names, **params):
        """
        Loads and renders the named template.
        
        If more than one template name is given, then the first template that exists will be used.
        
        On Windows, the forward slash '/' should be used as a path separator.
        """
        return self.load(*template_names).render(**params)
        

# The default template loader, which loads templates from the pythonpath.
default_loader = Loader([DirectorySource(dir) for dir in sys.path])