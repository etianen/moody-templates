"""
The moody templating system.

Fast and extensible. It gets the job done.

Developed by Dave Hall <dave@etianen.com>.
"""

from moody.parser import default_parser, TemplateError
from moody.loader import default_loader


compile = default_parser.compile


def render(template, **params):
    """
    Compiles and renders the given template string with the given parameters.
    
    This is just a shortcut for moody.compile(template).render(**params).
    """
    return compile(template).render(**params)
    

# TODO: allow inheritance without loader
# TODO: allow include without loader
# TODO: inherit from self
# TODO: render block.super
# TODO: set node (then use to test name expansion properly)
# TODO: import node (two types)
# TODO: render node
# TODO: test error reporting