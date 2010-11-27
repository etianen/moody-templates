"""The main template parser."""

import re
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager


class TemplateError(Exception):
    
    pass
    
    
class TemplateSyntaxError(TemplateError):
    
    pass


class Context:
    
    __slots__ = ("params", "buffer",)
    
    def __init__(self, params, buffer):
        self.params = params
        self.buffer = buffer
    
    @contextmanager
    def block(self):
        sub_context = Context(self.params.copy(), self.buffer)
        yield sub_context
        
    def write(self, value):
        # TODO: autoescape
        self.buffer.append(str(value))
        
    def read(self):
        return "".join(self.buffer)


class Expression:
    
    __slots__ = ("compiled_expression",)
    
    def __init__(self, expression):
        self.compiled_expression = compile(expression, "<string>", "eval")
        
    def eval(self, context):
        return eval(self.compiled_expression, {}, context.params)
        
        
class Node(metaclass=ABCMeta):
    
    __slots__ = ()
    
    @abstractmethod
    def render(self, context):
        pass
        
        
class StringNode(Node):
    
    __slots__ = ("value",)
    
    def __init__(self, value):
        self.value = value
        
    def render(self, context):
        context.buffer.append(self.value)


class ExpressionNode(Node):
    
    __slots__ = ("expression",)
    
    def __init__(self, expression):
        self.expression = Expression(expression)
        
    def render(self, context):
        context.write(self.expression.eval(context))
        
        
class Template:
    
    __slots__ = ("_nodes",)
    
    def __init__(self, nodes):
        self._nodes = nodes
        
    def _render_to_context(self, context):
        for node in self._nodes:
            node.render(context)
            
    def render(self, **params):
        context = Context(params, [])
        self._render_to_context(context)
        return context.read()


RE_TOKEN = re.compile("{#.+?#}|{{\s*(.*?)\s*}}|{%\s*(.*?)\s*%}")


def tokenize(template):
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
    
    __slots__ = ("tokens", "macros",)
    
    def __init__(self, template, macros):
        self.tokens = tokenize(template)
        self.macros = macros
        
    def parse_block(self, regex=None):
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
                    if regex:
                        match = regex.match(token_contents)
                        if match:
                            return lineno, match, Template(nodes)
                    raise TemplateSyntaxError("Line {lineno}: {{% {token} %}} is not a recognized tag.".format(lineno=lineno, token=token_contents))
            else:
                assert False, "{!r} is not a valid token type.".format(token_type)
        # No match.
        return lineno, None, Template(nodes)
            
        
class Parser:
    
    __slots__ = ("_macros",)
    
    def __init__(self, macros=()):
        self._macros = macros
        
    def compile(self, template):
        _, _, block = ParserRun(template, list(self._macros)).parse_block()
        return block


def regex_macro(regex):
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
    
    __slots__ = ("clauses", "else_block",)
    
    def __init__(self, clauses, else_block):
        self.clauses = clauses
        self.else_block = else_block
        
    def render(self, context):
        for expression, block in self.clauses:
            if expression.eval(context):
                block._render_to_context(context)
                return
        if self.else_block:
            self.else_block._render_to_context(context)


RE_IF_CLAUSE = re.compile("^(elif) (.+?)$|^(else)$|^(endif)$")

@regex_macro("^if\s+(.+?)$")
def if_macro(parser, lineno, expression):
    clauses = []
    else_tag = False
    else_block = None
    while True:
        block_lineno, match, block = parser.parse_block(RE_IF_CLAUSE)
        if not match:
            raise TemplateSyntaxError("Line {}: {{% if %}} tag cannot find a matching {{% endif %}}.".format(lineno))
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


class WithNode(Node):
    
    __slots__ = ("expression", "name", "block",)
    
    def __init__(self, expression, name, block):
        self.expression = expression
        self.name = name
        self.block = block
        
    def render(self, context):
        value = self.expression.eval(context)
        with context.block() as sub_context:
            sub_context.params[self.name] = value
            self.block._render_to_context(sub_context)


RE_ENDWITH = re.compile("^endwith$")
    
@regex_macro("^with\s+(.+?)\s+as\s+(.+?)$")
def with_macro(parser, lineno, expression, name):
    _, match, block = parser.parse_block(RE_ENDWITH)
    if not match:
        raise TemplateSyntaxError("Line {}: {{% with %}} tag cannot find matching {{% endwith %}}.".format(lineno))
    return WithNode(Expression(expression), name, block)
    

class ForNode(Node):
    
    __slots__ = ("name", "expression", "block",)
    
    def __init__(self, name, expression, block):
        self.name = name
        self.expression = expression
        self.block = block
        
    def render(self, context):
        items = self.expression.eval(context)
        with context.block() as sub_context:
            for item in items:
                sub_context.params[self.name] = item
                self.block._render_to_context(sub_context)


RE_ENDFOR = re.compile("^endfor$")

@regex_macro("^for\s+(.+?)\s+in\s+(.+?)$")
def for_macro(parser, lineno, name, expression):
    _, match, block = parser.parse_block(RE_ENDFOR)
    if not match:
        raise TemplateSyntaxError("Line {}: {{% for %}} tag cannot find matching {{% endfor %}}.".format(lineno))
    return ForNode(name, Expression(expression), block)


DEFAULT_MACROS = (if_macro, with_macro, for_macro,)


default_parser = Parser(DEFAULT_MACROS)