"""Base classes used by the template engine."""


import re
from collections import Sequence
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager

from moody.errors import TemplateRenderError
    
    
class Context:

    """The state of a template during render time."""

    __slots__ = ("params", "meta", "buffer",)

    def __init__(self, params, meta, buffer):
        """Initializes the Context."""
        self.params = params
        self.meta = meta
        self.buffer = buffer

    def read(self):
        """Reads the contents of the buffer as a string."""
        return "".join(self.buffer)


RE_NAME = re.compile("^[a-zA-Z_][a-zA-Z_0-9]*$")        

class Name:

    """The parsed name of a template variable."""

    __slots__ = ("names", "is_expandable",)

    def __init__(self, name):
        """Parses the name_string and initializes the Name."""
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
                raise ValueError("{!r} is not a valid variable name. Only letters, numbers and undescores are allowed.".format(name))

    def set(self, context, value):
        """Sets the value in the context under this name."""
        if self.is_expandable:
            # Handle variable expansion.
            value = iter(value)
            for name_part in self.names:
                try:
                    context.params[name_part] = next(value)
                except StopIteration:
                    raise ValueError("Not enough values to unpack.")
            # Make sure there are no more values.
            try:
                next(value)
            except StopIteration:
                pass
            else:
                raise ValueError("Need more that {} values to unpack.".format(len(self.names)))
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
        return eval(self.compiled_expression, context.meta, context.params)


class Node(metaclass=ABCMeta):

    """A node in a compiled template."""

    __slots__ = ("lineno",)

    @abstractmethod
    def render(self, context):
        """Renders the node using the given context."""


class TemplateFragment:

    """A fragment of a template."""

    __slots__ = ("_nodes", "_name",)

    def __init__(self, nodes, name):
        """Initializes the TemplateFragment."""
        self._nodes = nodes
        self._name = name

    def _render_to_context(self, context):
        """Renders the template to the given context."""
        for node in self._nodes:
            try:
                node.render(context)
            except TemplateRenderError:
                raise
            except Exception as ex:
                raise TemplateRenderError(str(ex), self._name, node.lineno) from ex


class Template(TemplateFragment):

    """A compiled template."""

    __slots__ = ("_params", "_meta",)

    def __init__(self, nodes, name, params, meta):
        """Initializes the template."""
        super(Template, self).__init__(nodes, name)
        self._params = params
        self._meta = meta

    def _render_to_sub_context(self, context, params, meta):
        """Renders the template to the given context."""
        # Generate the params.
        sub_params = self._params.copy()
        sub_params.update(context.params)
        sub_params.update(params)
        # Generate the meta.
        sub_meta = self._meta.copy()
        sub_meta.update(meta)
        # Generate the sub context.
        sub_context = Context(sub_params, sub_meta, context.buffer)
        self._render_to_context(sub_context)

    def render(self, **params):
        """Renders the template, returning the string result."""
        # Create the params.
        context_params = self._params.copy()
        context_params.update(params)
        # Create the context.
        context = Context(context_params, self._meta, [])
        # Render the template.
        self._render_to_context(context)
        return context.read()