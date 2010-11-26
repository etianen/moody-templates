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
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% if True %}{% else %}{% elif True %}{% endif %}"))
        self.assertRaises(TemplateSyntaxError, lambda: moody.compile("{% if True %}{% else %}{% else %}{% endif %}"))
        
        
if __name__ == "__main__":
    unittest.main()