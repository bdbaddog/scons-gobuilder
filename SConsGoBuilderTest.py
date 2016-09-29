import collections
import os.path

import unittest
import GoBuilder
import TestUnit


TESTDATA_DIRECTORY = os.path.join(os.path.dirname(__file__),'tests', 'testfiles')


class GoDummyEnv(collections.UserDict):
    def __init__(self,tags=[],goos='linux',goarch='amd64',goversion='1.6'):
        collections.UserDict.__init__(self)
        self['GOTAGS'] = tags
        self['GOOS'] = goos
        self['GOARCH'] = goarch
        self['GOVERSION'] = goversion

    # def subst(self, key):
    #     if key[0] == '$':
    #         return self[key[1:]]
    #     return key

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
        with open(os.path.join(TESTDATA_DIRECTORY,'test_single_line_imports.go'),'r') as sli:
            test_node=DummyNode(name='xyz.go',contents=sli.read())

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


class TestBuildTagParsing(unittest.TestCase):
    def test_single_build_tag(self):
        with open(os.path.join(TESTDATA_DIRECTORY,'test_single_build_tag.go'),'r') as sli:
            test_node=DummyNode(name='xyz.go',contents=sli.read())

            GoBuilder.parse_file(None, test_node)
            self.assertEqual(test_node.attributes.go_build_statements,['wolf'])

            testenv = GoDummyEnv()

            include_file = GoBuilder._eval_build_statements(testenv,test_node)
            self.assertFalse(include_file,'Failed testing negative for build tag wolf')

            testenv['GOTAGS'] = ['wolf']

            include_file = GoBuilder._eval_build_statements(testenv, test_node)
            self.assertTrue(include_file, 'Failed testing positive for build tag wolf')


def suite():
    suite = unittest.TestSuite()
    tclasses = [
        TestImportParsing,
        TestBuildTagParsing,
               ]
    for tclass in tclasses:
        names = unittest.getTestCaseNames(tclass, 'test_')
        suite.addTests(list(map(tclass, names)))
    return suite


if __name__ == "__main__":
    TestUnit.run(suite())
