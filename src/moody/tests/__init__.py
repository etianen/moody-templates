import unittest

import moody
from moody.parser import TemplateSyntaxError
from moody.loader import default_loader, TemplateDoesNotExist


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
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% if True %}"))
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% if True %}{% else %}{% elif True %}{% endif %}"))
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% if True %}{% else %}{% else %}{% endif %}"))
    
    def testForMacro(self):
        # Test basic functionality.
        template1 = moody.compile("{% for n in range(0, 3) %}{{n}}{% endfor %}")
        self.assertEqual(template1.render(), "012")
        # Test various syntax errors.
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% for n in range(0, 3) %}"))
        # Test variable expansion.
        template2 = moody.compile("{% for n, m in value %}{{n}}{{m}}{% endfor %}")
        self.assertEqual(template2.render(value=[["foo", "bar"]]), "foobar")
        self.assertRaises(ValueError, lambda: template2.render(value=[["foo"]]))
        self.assertRaises(ValueError, lambda: template2.render(value=[["foo", "bar", "foobar"]]))
        
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
        
        
class TestLoader(unittest.TestCase):
    
    def setUp(self):
        default_loader._template_cache.clear()
    
    def testLoad(self):
        cache_size = len(default_loader._template_cache)
        self.assertIn("Dave <dave@etianen.com>", default_loader.render("moody/tests/template.txt", name="Dave", email="<dave@etianen.com>"))
        self.assertGreater(len(default_loader._template_cache), cache_size)
        # Test that caching is loading.
        cache_size = len(default_loader._template_cache)
        self.assertIn("Dave <dave@etianen.com>", default_loader.render("moody/tests/template.txt", name="Dave", email="<dave@etianen.com>"))
        self.assertEqual(len(default_loader._template_cache), cache_size)
        
    def testAutoescape(self):
        self.assertIn("Dave &lt;dave@etianen.com&gt;", default_loader.render("moody/tests/template.html", name="Dave", email="<dave@etianen.com>"))
    
    def testNameStacking(self):
        self.assertIn("Dave &lt;dave@etianen.com&gt;", default_loader.render("moody/tests/dummy.html", "moody/tests/template.html", name="Dave", email="<dave@etianen.com>"))
    
    def testTemplateDoesNotExist(self):
        self.assertRaises(TemplateDoesNotExist, lambda: default_loader.load("moody/tests/dummy.html"))
        
    def testIncludeTag(self):
        self.assertEqual(default_loader.render("moody/tests/template.txt", name="Dave", email="<dave@etianen.com>"), default_loader.render("moody/tests/include.txt", name="Dave", email="<dave@etianen.com>"))
    
    def testInheritance(self):
        self.assertEqual(default_loader.render("moody/tests/parent.txt"), "Hello world")
        self.assertEqual(default_loader.render("moody/tests/child.txt"), "Hello Dave Hall")
        self.assertEqual(default_loader.render("moody/tests/grandchild.txt"), "Hello Dave Foo")
        
        
if __name__ == "__main__":
    unittest.main()