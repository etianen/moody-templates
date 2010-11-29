"""The default built-in macros."""

import re, sys

import moody
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


class SetNode(Node):
    
    """A node that sets a parameter in the context."""
    
    __slots__ = ("expression", "name",)
    
    def __init__(self, expression, name):
        """Initializes the SetNode."""
        self.expression = expression
        self.name = name
        
    def render(self, context):
        """Renders the SetNode."""
        self.name.set(context, self.expression.eval(context))
        

@regex_macro("^set\s+(.+?)\s+as\s+(.+?)$")
def set_macro(parser, expression, name):
    """Macro that allows setting of a value in the context."""
    return SetNode(Expression(expression), Name(name))
    
    
class RenderNode(Node):
    
    """A node that renders an expression without autoescaping."""
    
    __slots__ = ("expression",)
    
    def __init__(self, expression):
        """Initializes the RenderNode."""
        self.expression = expression
        
    def render(self, context):
        """Renders the RenderNode."""
        context.buffer.append(str(self.expression.eval(context)))
        
        
@regex_macro("^render\s+(.+?)$")
def render_macro(parser, expression):
    """Macro that allows an expression to be rendered without autoescaping."""
    return RenderNode(Expression(expression))


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
        loader = context.meta.get("__loader__", moody.default_loader)
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
        template._render_to_sub_context(context, {})


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
        # Get the block stack.
        block_stack = [(context, self.block)]
        child_context = context
        while "__child__" in child_context.meta:
            child_context = child_context.meta["__child__"]
            if self.name in child_context.meta["__blocks__"]:
                block = child_context.meta["__blocks__"][self.name]
                block_context = child_context
                block_stack.append((block_context, block))
        # Render the topmost block.
        block_context, block = block_stack.pop()
        sub_context = block_context.sub_context(meta={"__parent_blocks__": block_stack})
        block._render_to_context(sub_context)


@regex_macro("^block\s+([a-zA-Z_][a-zA-Z_\-0-9]*)$")
def block_macro(parser, name):
    """Macro that implements an inheritable template block."""
    match, block = parser.parse_block("block", "endblock", re.compile("^endblock$|^endblock\s+{}$".format(name)))
    return BlockNode(name, block)


class SuperNode(Node):
    
    """Nodes that renders the parent block's content."""
    
    __slots__ = ()
    
    def render(self, context):
        """Renders the SuperNode."""
        if "__parent_blocks__" in context.meta:
            block_stack = context.meta["__parent_blocks__"][:]
            block_context, block = block_stack.pop()
            sub_context = block_context.sub_context(meta={"__parent_blocks__": block_stack})
            block._render_to_context(sub_context)
    
    
@regex_macro("^super$")
def super_macro(parser):
    """Macro that renders the parent block's content."""
    return SuperNode()


class ExtendsNode(Node):

    """Implements a inherited child template."""

    __slots__ = ("expression", "block_nodes",)

    def __init__(self, expression, block_nodes):
        """Initializes the ExtendsNode."""
        self.expression = expression
        self.block_nodes = block_nodes

    def render(self, context):
        """Renders the ExtendsNode."""
        # Create a summary of my blocks.
        blocks = {block_node.name: block_node.block for block_node in self.block_nodes}
        context.meta["__blocks__"] = blocks
        # Render the parent template with my blocks.
        template = get_template(context, self.expression.eval(context))
        template._render_to_sub_context(context, {"__child__": context})


@regex_macro("^extends\s+(.+?)$")
def extends_macro(parser, expression):
    """Macro that implements an inherited child template."""
    # Parse the rest of the template.
    nodes = parser.parse_all_nodes()
    # Go through the nodes, looking for all block tags.
    block_nodes = [node for node in nodes if isinstance(node, BlockNode)]
    return ExtendsNode(Expression(expression), block_nodes)


# The set of default macros.
DEFAULT_MACROS = (set_macro, render_macro, if_macro, for_macro, include_macro, block_macro, super_macro, extends_macro,)