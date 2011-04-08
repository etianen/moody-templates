#!/usr/bin/env python

import os.path, timeit
from django.conf import settings


def main():
    print("Running benchmarks for django templates...")
    template_root = os.path.join(os.path.dirname(__file__), "templates")
    settings.configure(
        TEMPLATE_DIRS = (template_root,),
        TEMPLATE_LOADERS = (
            ("django.template.loaders.cached.Loader", (
                "django.template.loaders.filesystem.Loader",
            )),
        )
    )
    from django.template import loader
    def benchmark(func):
        return min(timeit.repeat(func, repeat=3, number=500))
    # Test the cached rendering.
    def render_cached():
        loader.render_to_string("index.html", {
            "list_items": list(range(100)),
        })
    print("Cached rendering:   {time}".format(time=benchmark(render_cached)))
    # Test the uncached rendering.
    def render_uncached():
        loader.template_source_loaders[0].template_cache.clear()
        loader.render_to_string("index.html", {
            "list_items": list(range(100)),
        })
    print("Uncached rendering: {time}".format(time=benchmark(render_uncached)))
    
    
if __name__ == "__main__":
    main()