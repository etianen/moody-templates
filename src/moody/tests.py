import unittest

import moody
from moody.parser import TemplateCompileError, TemplateRenderError
from moody.loader import default_loader, Loader, TemplateDoesNotExist, MemorySource


class TestRender(unittest.TestCase):
    
    def testCommentTag(self):
        self.assertEqual(moody.render("{# A comment. #}"), "")
        
    def testStringTag(self):
        self.assertEqual(moody.render("Hello world"), "Hello world")
        
    def testExpressionTag(self):
        self.assertEqual(moody.render("{{'Hello world'}}"), "Hello world")
        
    def testIfMacro(self):
        # Test single if.
        template1 = moody.compile("{% if test == 'foo' %}foo{% endif %}")
        self.assertEqual(template1.render(test="foo"), "foo")
        self.assertEqual(template1.render(test="bar"), "")
        # Test if and else.
        template2 = moody.compile("{% if test == 'foo' %}foo{% else %}bar{% endif %}")
        self.assertEqual(template2.render(test="foo"), "foo")
        self.assertEqual(template2.render(test="bar"), "bar")
        # Test if, elif and else.
        template3 = moody.compile("{% if test == 'foo' %}foo{% elif test == 'bar' %}bar{% else %}snafu{% endif %}")
        self.assertEqual(template3.render(test="foo"), "foo")
        self.assertEqual(template3.render(test="bar"), "bar")
        self.assertEqual(template3.render(test="snafu"), "snafu")
        # Test if and elif
        template4 = moody.compile("{% if test == 'foo' %}foo{% elif test == 'bar' %}bar{% elif test == 'snafu' %}snafu{% endif %}")
        self.assertEqual(template4.render(test="foo"), "foo")
        self.assertEqual(template4.render(test="bar"), "bar")
        self.assertEqual(template4.render(test="snafu"), "snafu")
        self.assertEqual(template4.render(test="wibble"), "")
        # Test various syntax errors.
        self.assertRaises(TemplateCompileError, lambda: moody.compile("{% if True %}"))
        self.assertRaises(TemplateCompileError, lambda: moody.compile("{% if True %}{% else %}{% elif True %}{% endif %}"))
        self.assertRaises(TemplateCompileError, lambda: moody.compile("{% if True %}{% else %}{% else %}{% endif %}"))
    
    def testForMacro(self):
        # Test basic functionality.
        template1 = moody.compile("{% for n in range(0, 3) %}{{n}}{% endfor %}")
        self.assertEqual(template1.render(), "012")
        # Test various syntax errors.
        self.assertRaises(TemplateCompileError, lambda: moody.compile("{% for n in range(0, 3) %}"))
        # Test variable expansion.
        template2 = moody.compile("{% for n, m in value %}{{n}}{{m}}{% endfor %}")
        self.assertEqual(template2.render(value=[["foo", "bar"]]), "foobar")
        self.assertRaises(TemplateRenderError, lambda: template2.render(value=[["foo"]]))
        self.assertRaises(TemplateRenderError, lambda: template2.render(value=[["foo", "bar", "foobar"]]))
        
    def testNestedTags(self):
        template1 = moody.compile("""
            {% if test.startswith("foo") %}
                {% if test == "foobar" %}
                    {{test}}
                {% else %}
                    {% for item in range(2) %}{% if True %}{{test}}{% endif %}{% endfor %}
                {% endif %}
            {% else %}
                snafu
            {% endif %}
        """)
        self.assertEqual(template1.render(test="foobar").strip(), "foobar")
        self.assertEqual(template1.render(test="foo").strip(), "foofoo")
        self.assertEqual(template1.render(test="").strip(), "snafu")
        
    def testAutoEscape(self):
        template1 = moody.compile("{{'foo'}}")
        self.assertEqual(template1.render(), "foo")
        self.assertEqual(template1.render(__autoescape__=lambda v: "bar"), "bar")
        
    def testDefaultParams(self):
        template1 = moody.compile("{{test}}", default_params={"test": "foo"})
        self.assertEqual(template1.render(), "foo")
        self.assertEqual(template1.render(test="bar"), "bar")


test_loader = Loader((
    MemorySource({
        "simple.txt": "{{test}}",
    }), MemorySource({
        "simple.html": "{{test}}",
        "include.txt": "{% include 'simple.txt' %}",
        "parent.txt": "Hello {% block name %}world{% endblock %}",
        "child.txt": "{% extends 'parent.txt' %}{% block name %}Dave {% block surname %}Hall{% endblock %}{% endblock %}",
        "grandchild.txt": "{% extends 'child.txt' %}{% block surname %}Foo{% endblock surname %}",
    })
))


class TestLoader(unittest.TestCase):
    
    def setUp(self):
        test_loader.clear_cache()
    
    def testLoad(self):
        self.assertTrue(test_loader.load("simple.txt"))
        
    def testAutoescape(self):
        self.assertEqual(test_loader.render("simple.txt", test="<Hello world>"), "<Hello world>")
        self.assertEqual(test_loader.render("simple.html", test="<Hello world>"), "&lt;Hello world&gt;")
        
    def testNameStacking(self):
        self.assertEqual(test_loader.render("missing.txt", "simple.txt", test="foo"), "foo")
        
    def testTemplateDoesNotExist(self):
        self.assertRaises(TemplateDoesNotExist, lambda: default_loader.load("missing.txt"))
        
    def testIncludeTag(self):
        self.assertEqual(test_loader.render("include.txt", test="foo"), test_loader.render("simple.txt", test="foo"))
        
    def testInheritance(self):
        self.assertEqual(test_loader.render("parent.txt"), "Hello world")
        self.assertEqual(test_loader.render("child.txt"), "Hello Dave Hall")
        self.assertEqual(test_loader.render("grandchild.txt"), "Hello Dave Foo")
        
    def testCache(self):
        self.assertEqual(len(test_loader._cache), 0)
        test_loader.load("simple.txt")
        self.assertEqual(len(test_loader._cache), 1)
        test_loader.load("simple.txt")
        self.assertEqual(len(test_loader._cache), 1)

        
class TestDirectorySource(unittest.TestCase):
    
    def testLoad(self):
        self.assertEqual(default_loader.render("src/moody/__init__.py"), open("src/moody/__init__.py", "r").read())
        
        
if __name__ == "__main__":
    unittest.main()