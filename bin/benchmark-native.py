#!/usr/bin/env python3

import timeit


def main():
    print("Running benchmarks for native rendering...")
    def benchmark(func):
        return min(timeit.repeat(func, repeat=3, number=1000))
    # Test the native rendering.
    def render_native():
        title = "Hello world"
        header = "Hello world"
        list_items = list(range(100))
        if list_items:
            list_str = "<ul>{}</ul>".format("".join("<li>{}</li>".format(n) for n in list_items))
        else:
            list_str = ""
        """
        <!DOCTYPE html>
        <html>

            <head>

                <title>{title}</title>

            </head>

            <body>

                <h1>{header}</h1>

                {list_str}

            </body>

        </html>
        """.format(
            title = title,
            header = header,
            list_str = list_str,
        )
    print("Native rendering:   {time}".format(time=benchmark(render_native)))
    
    
if __name__ == "__main__":
    main()