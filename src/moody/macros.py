"""The default built-in macros."""

import re, sys

from moody.base import Node, Expression, Name, Template


def regex_macro(regex):
    """A decorator that defines a macro function."""
    regex = re.compile(regex)
    def decorator(func):
        def wrapper(parser, token):
            match = regex.match(token)
            if match:
                return func(parser, *match.groups(), **match.groupdict())
            return None
        return wrapper
    return decorator


class IfNode(Node):
    
    """A node that implements an 'if' expression."""
    
    __slots__ = ("clauses", "else_block",)
    
    def __init__(self, clauses, else_block):
        """Initializes the IfNode."""
        self.clauses = clauses
        self.else_block = else_block
        
    def render(self, context):
        """Renders the IfNode."""
        for expression, block in self.clauses:
            if expression.eval(context):
                block._render_to_context(context)
                return
        if self.else_block:
            self.else_block._render_to_context(context)


RE_IF_CLAUSE = re.compile("^(elif) (.+?)$|^(else)$|^(endif)$")

@regex_macro("^if\s+(.+?)$")
def if_macro(parser, expression):
    """A macro that implements an 'if' expression."""
    clauses = []
    else_tag = False
    else_block = None
    while True:
        match, block = parser.parse_block("if", "endif", RE_IF_CLAUSE)
        if else_tag:
            else_block = block
        else:
            clauses.append((Expression(expression), block))
        elif_flag, elif_expression, else_flag, endif_flag = match.groups()
        if elif_flag:
            if else_tag:
                raise SyntaxError("{{% elif %}} tag cannot come after {{% else %}}.")
            expression = elif_expression
        elif else_flag:
            if else_tag:
                raise SyntaxError("Only one {{% else %}} tag is allowed per {{% if %}} macro.")
            else_tag = True
        elif endif_flag:
            break
    return IfNode(clauses, else_block)
    

class ForNode(Node):
    
    """A node that implements a 'for' loop."""
    
    __slots__ = ("name", "expression", "block",)
    
    def __init__(self, name, expression, block):
        """Initializes the ForNode."""
        self.name = name
        self.expression = expression
        self.block = block
        
    def render(self, context):
        """Renders the ForNode."""
        items = self.expression.eval(context)
        for item in items:
            self.name.set(context, item)
            self.block._render_to_context(context)


RE_ENDFOR = re.compile("^endfor$")

@regex_macro("^for\s+(.+?)\s+in\s+(.+?)$")
def for_macro(parser, name, expression):
    """A macro that implements a 'for' loop."""
    match, block = parser.parse_block("for", "endfor", RE_ENDFOR)
    return ForNode(Name(name), Expression(expression), block)
    
    
def get_template(context, template):
    """
    If template is a str, then looks up the loader and loads the template.

    Otherwise, if template is a template, returns the template.
    """
    if isinstance(template, Template):
        return template
    if isinstance(template, str):
        from moody.loader import default_loader
        loader = context.params.get("__loader__", default_loader)
        return loader.load(template)
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


# The set of default macros.
DEFAULT_MACROS = (if_macro, for_macro, include_macro, block_macro, extends_macro,)