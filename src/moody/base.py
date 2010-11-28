"""Base classes used by the template engine."""


import re
from collections import Sequence
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager

from moody.errors import TemplateRenderError
    
    
class Context:

    """The state of a template during render time."""

    __slots__ = ("params", "buffer",)

    def __init__(self, params, buffer):
        """Initializes the Context."""
        self.params = params
        self.buffer = buffer

    @contextmanager
    def block(self):
        """
        Creates a new subcontext that is scoped to a block.

        Changes to the sub-context will not affect the parent context, although
        the buffer is shared.
        """
        sub_context = Context(self.params.copy(), self.buffer)
        yield sub_context

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
        return eval(self.compiled_expression, {}, context.params)


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
                raise TemplateRenderError(str(ex), self._name, node.lineno)


class Template(TemplateFragment):

    """A compiled template."""

    __slots__ = ("_default_params",)

    def __init__(self, nodes, name, default_params):
        """Initializes the template."""
        super(Template, self).__init__(nodes, name)
        self._name = name
        self._default_params = default_params

    def _render_to_context(self, context):
        """Renders the template to the given context."""
        for name, value in self._default_params.items():
            if name.startswith("__") and name.endswith("__"):
                context.params[name] = value
            else:
                context.params.setdefault(name, value)
        super(Template, self)._render_to_context(context)

    def render(self, **params):
        """Renders the template, returning the string result."""
        # Create the params.
        context_params = self._default_params.copy()
        context_params.update(params)
        # Create the context.
        context = Context(params, [])
        # Render the template.
        self._render_to_context(context)
        return context.read()