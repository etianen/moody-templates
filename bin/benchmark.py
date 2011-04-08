#!/usr/bin/env python3

import moody, os.path


def main():
    print("Running benchmarks for moody-templates...")
    loader = moody.make_loader(os.path.join(os.path.dirname(__file__), "templates"))
    print(loader.render("index.html",
        list_items = (
            "Foo",
            "Bar",
        )
    ))
    
    
if __name__ == "__main__":
    main()