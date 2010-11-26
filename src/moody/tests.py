import unittest

import moody
from moody.parser import TemplateSyntaxError


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
        
    def testWithMacro(self):
        # Test basic functionality.
        template1 = moody.compile("{% with test[3:] as subtest %}{{subtest}}{% endwith %}")
        self.assertEqual(template1.render(test="foobar"), "bar")
        # Test correct scoping.
        template2 = moody.compile("{% with test[3:] as test %}{{test}}{% endwith %}{{test}}")
        self.assertEqual(template2.render(test="foobar"), "barfoobar")
        # Test various syntax errors.
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% with True as foo %}"))
    
    def testForMacro(self):
        # Test basic functionality.
        template1 = moody.compile("{% for n in range(0, 3) %}{{n}}{% endfor %}")
        self.assertEqual(template1.render(), "012")
        # Test correct scoping.
        template2 = moody.compile("{% for n in range(0, 3) %}{{n}}{% endfor %}{{n}}")
        self.assertEqual(template2.render(n="foo"), "012foo")
        # Test various syntax errors.
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% for n in range(0, 3) %}"))
        
    def testNestedTags(self):
        template1 = moody.compile("""
            {% if test %}
                {% with test[3:] as subtest %}
                    {% if subtest %}
                        {{subtest}}
                    {% else %}
                        {% for _ in range(2) %}snafu{% endfor %}
                    {% endif %}
                {% endwith %}
            {% else %}
                {% with "wibble" as test %}
                    {{test}}
                {% endwith %}
            {% endif %}
        """)
        self.assertEqual(template1.render(test="foobar").strip(), "bar")
        self.assertEqual(template1.render(test="foo").strip(), "snafusnafu")
        self.assertEqual(template1.render(test="").strip(), "wibble")
        
        
if __name__ == "__main__":
    unittest.main()