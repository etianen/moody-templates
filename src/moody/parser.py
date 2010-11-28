"""The main template parser."""

import re
from collections import Sequence
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager


class TemplateError(Exception):
    
    """An error has occured with a template."""
    
    
class TemplateSyntaxError(TemplateError):
    
    """An error has been found in a template's syntax."""


class Context:
    
    """The state of a template during render time."""
    
    __slots__ = ("params", "_buffer",)
    
    def __init__(self, params, buffer):
        """Initializes the Context."""
        self.params = params
        self._buffer = buffer
            
    @contextmanager
    def block(self):
        """
        Creates a new subcontext that is scoped to a block.
        
        Changes to the sub-context will not affect the parent context, although
        the buffer is shared.
        """
        sub_context = Context(self.params.copy(), self._buffer)
        yield sub_context
    
    def read(self):
        """Reads the contents of the buffer as a string."""
        return "".join(self._buffer)


RE_NAME = re.compile("^[a-zA-Z_][a-zA-Z_0-9]*$")        
        
class Name:

    """The parsed name of a template variable."""

    __slots__ = ("lineno", "names", "is_expandable",)

    def __init__(self, lineno, name):
        """Parses the name_string and initializes the Name."""
        self.lineno = lineno
        # Parse the names.
        if "," in name:
            self.names = [name.strip() for name in name.split(",")]
            if not self.names[-1]:
                names.pop()
            self.is_expandable = True
        else:
            self.names = [name]
            self.is_expandable = False
        # Make sure that the names are valid.
        for name in self.names:
            if not RE_NAME.match(name):
                raise TemplateSyntaxError("Line {}: {!r} is not a valid variable name. Only letters, numbers and undescores are allowed.".format(lineno, name))

    def set(self, context, value):
        """Sets the value in the context under this name."""
        if self.is_expandable:
            # Handle variable expansion.
            value = iter(value)
            for name_part in self.names:
                try:
                    context.params[name_part] = next(value)
                except StopIteration:
                    raise ValueError("Line {}: Not enough values to unpack.".format(self.lineno))
            # Make sure there are no more values.
            try:
                next(value)
            except StopIteration:
                pass
            else:
                raise ValueError("Line {}: Need more that {} values to unpack.".format(self.lineno, len(self.names)))
        else:
            context.params[self.names[0]] = value


class Expression:
    
    """A compiled template expression."""
    
    __slots__ = ("compiled_expression",)
    
    def __init__(self, expression):
        """Initiliazes the Expression."""
        self.compiled_expression = compile(expression, "<string>", "eval")
        
    def eval(self, context):
        """Evaluates the expression using the given context, returning the result."""
        return eval(self.compiled_expression, {}, context.params)
        
        
class Node(metaclass=ABCMeta):
    
    """A node in a compiled template."""
    
    __slots__ = ()
    
    @abstractmethod
    def render(self, context):
        """Renders the node using the given context."""
        
        
class StringNode(Node):
    
    """A node containing a static string value."""
    
    __slots__ = ("value",)
    
    def __init__(self, value):
        """Initializes the StringNode."""
        self.value = value
        
    def render(self, context):
        """Renders the StringNode."""
        context._buffer.append(self.value)


class ExpressionNode(Node):
    
    __slots__ = ("expression",)
    
    def __init__(self, expression):
        """Initializes the ExpressionNode."""
        self.expression = Expression(expression)
        
    def render(self, context):
        """Renders the ExpressionNode."""
        value = str(self.expression.eval(context))
        # Apply autoescaping.
        autoescape = context.params.get("__autoescape__")
        if autoescape:
            value = autoescape(value)
        # Write the value.
        context._buffer.append(value)


class TemplateFragment:
    
    """A fragment of a template."""
    
    __slots__ = ("_nodes",)
    
    def __init__(self, nodes):
        """Initializes the TemplateFragment."""
        self._nodes = nodes
        
    def _render_to_context(self, context):
        """Renders the template to the given context."""
        for node in self._nodes:
            node.render(context)
        
        
class Template(TemplateFragment):
    
    """A compiled template."""
    
    __slots__ = ("_nodes", "_default_params",)
    
    def __init__(self, nodes, default_params):
        """Initializes the template."""
        super(Template, self).__init__(nodes)
        self._default_params = default_params
            
    def render(self, **params):
        """Renders the template, returning the string result."""
        # Create the params.
        context_params = self._default_params.copy()
        context_params.update(params)
        # Create the context.
        context = Context(context_params, [])
        # Render the template.
        self._render_to_context(context)
        return context.read()


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
    
    __slots__ = ("tokens", "macros",)
    
    def __init__(self, template, macros):
        """Initializes the ParserRun."""
        self.tokens = tokenize(template)
        self.macros = macros
    
    def parse_template_chunk(self):
        """
        Parses as many nodes as possible until an unknown block is reached.
        
        Returns a tuple of (lineno, macro_token, nodes). If no unknown macro
        token was found, macro_token will be None.
        """
        nodes = []
        for lineno, token_type, token_contents in self.tokens:
            if token_type == "STRING":
                nodes.append(StringNode(token_contents))
            elif token_type == "EXPRESSION":
                nodes.append(ExpressionNode(token_contents))
            elif token_type == "MACRO":
                # Process macros.
                node = None
                for macro in self.macros:
                    node = macro(self, lineno, token_contents)
                    if node:
                        nodes.append(node)
                        break
                if not node:
                    return lineno, token_contents, nodes
            else:
                assert False, "{!r} is not a valid token type.".format(token_type)
        # No match.
        return lineno, None, nodes
        
    def parse_block(self, start_tag, end_tag, regex):
        """
        Parses a block of template, looking for a macro token that matches the
        given regex.
        
        If a match is found, then a tuple of (lineno, match, template_fragment) is
        returned. A TemplateSyntaxError is raised.
        """
        lineno, token_contents, nodes = self.parse_template_chunk()
        if not token_contents:
            raise TemplateSyntaxError("Line {lineno}: {{% {start} %}} tag could not find a corresponding {{% {end} }}.".format(lineno=lineno, start=start_tag, end=end_tag))
        # Attempt to match.
        match = regex.match(token_contents)
        if match:
            return lineno, match, TemplateFragment(nodes)
        # No match, so raise syntax error.
        raise TemplateSyntaxError("Line {lineno}: {{% {token} %}} is not a recognized tag.".format(lineno=lineno, token=token_contents))
            
        
class Parser:
    
    """A template parser."""
    
    __slots__ = ("_macros",)
    
    def __init__(self, macros=()):
        """Initializes the Parser."""
        self._macros = macros
        
    def compile(self, template, default_params=None, extra_macros=()):
        """Compiles the template."""
        # Get the list of macros.
        macros = list(self._macros)
        macros.extend(extra_macros)
        # Get the default params.
        default_params = default_params or {}
        # Render the main block.
        lineno, token_contents, nodes = ParserRun(template, macros).parse_template_chunk()
        if token_contents:
            raise TemplateSyntaxError("Line {lineno}: {{% {token} %}} is not a recognized tag.".format(lineno=lineno, token=token_contents))
        return Template(nodes, default_params)


def regex_macro(regex):
    """A decorator that defines a macro function."""
    regex = re.compile(regex)
    def decorator(func):
        def wrapper(parser, lineno, token):
            match = regex.match(token)
            if match:
                return func(parser, lineno, *match.groups(), **match.groupdict())
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
def if_macro(parser, lineno, expression):
    """A macro that implements an 'if' expression."""
    clauses = []
    else_tag = False
    else_block = None
    while True:
        block_lineno, match, block = parser.parse_block("if", "endif", RE_IF_CLAUSE)
        if else_tag:
            else_block = block
        else:
            clauses.append((Expression(expression), block))
        elif_flag, elif_expression, else_flag, endif_flag = match.groups()
        if elif_flag:
            if else_tag:
                raise TemplateSyntaxError("Line {}: {{% elif %}} tag cannot come after {{% else %}}.".format(block_lineno))
            expression = elif_expression
        elif else_flag:
            if else_tag:
                raise TemplateSyntaxError("Line {}: Only one {{% else %}} tag is allowed per {{% if %}} macro.".format(block_lineno))
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
def for_macro(parser, lineno, name, expression):
    """A macro that implements a 'for' loop."""
    _, match, block = parser.parse_block("for", "endfor", RE_ENDFOR)
    return ForNode(Name(lineno, name), Expression(expression), block)


# The set of default macros.
DEFAULT_MACROS = (if_macro, for_macro,)


# The default parser, using the default set of macros.
default_parser = Parser(DEFAULT_MACROS)