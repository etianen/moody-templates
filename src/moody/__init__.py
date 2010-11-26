from moody.parser import default_parser


compile = default_parser.compile


def render(template, **params):
    return compile(template).render(**params)