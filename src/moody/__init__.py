"""
The moody templating system.

Fast and extensible. It gets the job done.

Developed by Dave Hall <dave@etianen.com>.
"""

from moody.parser import default_parser, TemplateError


compile = default_parser.compile


def render(template, **params):
    """
    Compiles and renders the given template string with the given parameters.
    
    This is just a shortcut for moody.compile(template).render(**params).
    """
    return compile(template).render(**params)
    

# TODO: template error reporting (filename, lineno)
# TODO: alternative loader sources, such as memory.