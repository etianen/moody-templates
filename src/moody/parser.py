"""The main template parser."""

import os, re
from xml.sax.saxutils import escape

from moody.errors import TemplateCompileError
from moody.base import Expression, Node, Template, TemplateFragment
from moody.macros import DEFAULT_MACROS

        
class StringNode(Node):
    
    """A node containing a static string value."""
    
    __slots__ = ("value",)
    
    def __init__(self, value):
        """Initializes the StringNode."""
        self.value = value
        
    def render(self, context):
        """Renders the StringNode."""
        context.buffer.append(self.value)


class ExpressionNode(Node):
    
    __slots__ = ("expression",)
    
    def __init__(self, expression):
        """Initializes the ExpressionNode."""
        self.expression = Expression(expression)
        
    def render(self, context):
        """Renders the ExpressionNode."""
        value = str(self.expression.eval(context))
        # Apply autoescaping.
        autoescape = context.meta.get("__autoescape__")
        if autoescape:
            value = autoescape(value)
        # Write the value.
        context.buffer.append(value)


RE_TOKEN = re.compile("{#.+?#}|{{\s*(.*?)\s*}}|{%\s*(.*?)\s*%}")


def tokenize(template):
    """Lexes the given template, returning an iterator or token."""
    for lineno, line in enumerate(template.splitlines(True), 1):
        index = 0
        for match in RE_TOKEN.finditer(line):
            # Process string tokens.
            if match.start() > index:
                yield lineno, "STRING", line[index:match.start()]
            # Process tag tokens.
            expression_token, macro_token = match.groups()
            # Process expression tokens.
            if expression_token:
                yield lineno, "EXPRESSION", expression_token
            elif macro_token:
                yield lineno, "MACRO", macro_token
            # Update the index.
            index = match.end()
        # Yield the final string token.
        yield lineno, "STRING", line[index:]


class ParserRun:
    
    """The state held by a parser during a run."""
    
    __slots__ = ("tokens", "name", "macros",)
    
    def __init__(self, template, name, macros):
        """Initializes the ParserRun."""
        self.tokens = tokenize(template)
        self.name = name
        self.macros = macros
    
    def parse_template_chunk(self, end_chunk_handler):
        """
        Parses as many nodes as possible until an unknown block is reached.
        Returns the result of the end_chunk_handler.
        
        The chunk is ended when there is no more template to parse, or an unknown
        macro is encountered. Once this occurs, the end_chunk_handler is called
        with macro_name and nodes as positional arguments. The end_chunk handler
        must then process the nodes and return a result.
        """
        nodes = []
        for lineno, token_type, token_contents in self.tokens:
            try:
                if token_type == "STRING":
                    node = StringNode(token_contents)
                elif token_type == "EXPRESSION":
                    node = ExpressionNode(token_contents)
                elif token_type == "MACRO":
                    # Process macros.
                    node = None
                    for macro in self.macros:
                        node = macro(self, token_contents)
                        if node:
                            break
                    if not node:
                        return end_chunk_handler(token_contents, nodes)
                else:
                    assert False, "{!r} is not a valid token type.".format(token_type)
                # Set the node line number.
                node.lineno = lineno
                nodes.append(node)
            except TemplateCompileError:
                raise
            except Exception as ex:
                raise TemplateCompileError(str(ex), self.name, lineno) from ex
        # No unknown macro.
        return end_chunk_handler(None, nodes)
        
    def parse_all_nodes(self):
        """Parses all remaining nodes."""
        def end_chunk_handler(token_contents, nodes):
            if token_contents:
                raise SyntaxError("{{% {} %}} is not a recognized tag.".format(token_contents))
            return nodes
        return self.parse_template_chunk(end_chunk_handler)
        
    def parse_block(self, start_tag, end_tag, regex):
        """
        Parses a block of template, looking for a macro token that matches the
        given regex.
        
        If a match is found, then a tuple of (match, template_fragment) is
        returned. A SyntaxError is raised.
        """
        def end_chunk_handler(token_contents, nodes):
            if not token_contents:
                raise SyntaxError("{{% {} %}} tag could not find a corresponding {{% {} %}}.".format(start_tag, end_tag))
            # Attempt to match.
            match = regex.match(token_contents)
            if not match:
                raise SyntaxError("{{% {} %}} is not a recognized tag.".format(token_contents))
            return match, TemplateFragment(nodes, self.name)
        return self.parse_template_chunk(end_chunk_handler)


# Default rules for autoescaping templates based on name.
DEFAULT_AUTOESCAPE_FUNCS = {
    ".xml": escape,
    ".xhtml": escape,
    ".html": escape,
    ".htm": escape,
}


class Parser:
    
    """A template parser."""
    
    __slots__ = ("_macros", "_autoescape_funcs",)
    
    def __init__(self, macros, autoescape_funcs=DEFAULT_AUTOESCAPE_FUNCS):
        """Initializes the Parser."""
        self._macros = macros
        self._autoescape_funcs = autoescape_funcs
        
    def compile(self, template, name="__string__", params=None, meta=None):
        """Compiles the template."""
        # Get the autoescape function.
        _, extension = os.path.splitext(name)
        autoescape = self._autoescape_funcs.get(extension)
        # Compile the meta params.
        default_meta = {
            "__name__": name,
            "__autoescape__": autoescape,
        }
        default_meta.update(meta or {})
        # Get the default params.
        params = params or {}
        # Render the main block.
        nodes = ParserRun(template, name, self._macros).parse_all_nodes()
        return Template(nodes, name, params, default_meta)
        
        
# The default parser, using the default set of macros.
default_parser = Parser(DEFAULT_MACROS)