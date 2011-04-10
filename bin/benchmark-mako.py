#!/usr/bin/env python3

import os.path, timeit
from mako.lookup import TemplateLookup


def main():
    print("Running benchmarks for mako templates...")
    template_root = os.path.join(os.path.dirname(__file__), "templates_mako")
    lookup = TemplateLookup(
        directories=(template_root,),
        filesystem_checks = False,
    )
    def benchmark(func):
        return min(timeit.repeat(func, repeat=3, number=1000))
    # Test the cached rendering.
    def render_cached():
        lookup.get_template("index.html").render_unicode(
            list_items = list(range(100)),
        )
    render_cached()
    print("Cached rendering:   {time}".format(time=benchmark(render_cached)))
    
    
if __name__ == "__main__":
    main()