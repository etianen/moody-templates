#!/usr/bin/env python3

import moody, os.path, timeit


def main():
    print("Running benchmarks for moody-templates...")
    template_root = os.path.join(os.path.dirname(__file__), "templates")
    def benchmark(func):
        return min(timeit.repeat(func, repeat=3, number=500))
    # Test the cached rendering.
    loader = moody.make_loader(template_root)
    def render_cached():
        loader.render("index.html", list_items = list(range(100)))
    print("Cached rendering:   {time}".format(time=benchmark(render_cached)))
    # Test the uncached rendering.
    def render_uncached():
        loader._cache.clear()
        loader.render("index.html", list_items = list(range(100)))
    print("Uncached rendering: {time}".format(time=benchmark(render_uncached)))
    
    
if __name__ == "__main__":
    main()