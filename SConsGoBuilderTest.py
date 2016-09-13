import collections

import unittest
import GoBuilder
import TestUnit


class DummyNode(object):
    """
    Dummy test Node object to be passed into various GoBuilder methods
    """
    def __init__(self,  name=None, search_result=(),contents=None):

        self.name = name
        self.search_result = tuple(search_result)
        self.contents = contents
        self.attributes=collections.UserDict()

    def __str__(self):
        return self.name

    # def Rfindalldirs(self, pathlist):
    #     return self.search_result + pathlist

    def get_contents(self):
        return self.contents


class TestImportParsing(unittest.TestCase):

    def test_single_line_imports(self):
        test_node=DummyNode(name='xyz.go',contents="""
package main
import "sli"
        """)

        GoBuilder.parse_file(None, test_node)
        self.assertEqual(test_node.attributes.go_packages,['sli'])

    def test_multi_line_imports(self):
        test_node = DummyNode(name='xyz.go', contents="import (\n\t\"mli\"\n\t)")
        GoBuilder.parse_file(None,test_node)
        self.assertEqual(test_node.attributes.go_packages, ['mli'])

    def test_single_line_namespace_import(self):
        test_node=DummyNode(name='xyz.go',contents="package main\nimport abc \"slni\"\n")

        GoBuilder.parse_file(None, test_node)
        self.assertEqual(test_node.attributes.go_packages,['slni'])

    def test_multi_line_namespace_imports(self):
        test_node = DummyNode(name='xyz.go', contents="import (\n\tabc\"mlni\"\n\t)")
        GoBuilder.parse_file(None, test_node)
        self.assertEqual(test_node.attributes.go_packages, ['mlni'])


def suite():
    suite = unittest.TestSuite()
    tclasses = [
        TestImportParsing,
               ]
    for tclass in tclasses:
        names = unittest.getTestCaseNames(tclass, 'test_')
        suite.addTests(list(map(tclass, names)))
    return suite


if __name__ == "__main__":
    TestUnit.run(suite())
