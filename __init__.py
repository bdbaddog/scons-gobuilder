# -*- mode:python; coding:utf-8; -*-

#  A SCons tool to enable compilation of go in SCons.
#
# Copyright © 2016 William Deegan
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import SCons.Tool
import SCons.Action
from SCons.Scanner import Scanner
from SCons.Defaults import ObjSourceScan, ArAction
import os.path
import string

# Handle multiline import statements
m_import = re.compile(r'import\s*(\()\s*([^\(]*?)(\))|import\s*(\")(.*?)(\")', re.MULTILINE)

# Handle +build statements
m_build = re.compile(r'\/\/\s*\+build\s(.*)')

# TODO: Determine if lists below include all those supported by both gccgo and google go
#       or just google go.  If just google go, obtain complete list and add to below
#       or perhaps after we determine which compiler we're using use the appropriate list
#       though in theory, this is just to validate settings for the GOOS AND GOARCH environment
#       variables.
# list of valid goos and gooarch from
# https://github.com/golang/go/blob/master/src/go/build/syslist.go
# Need to include license statement from
# https://github.com/golang/go/blob/master/LICENSE
_goosList = "android darwin dragonfly freebsd linux nacl netbsd openbsd plan9 solaris windows".split()
_goarchList = "386 amd64 amd64p32 arm armbe arm64 arm64be ppc64 ppc64le mips mipsle mips64 mips64le mips64p32 mips64p32le ppc s390 s390x sparc sparc64".split()

def check_go_file(node,env):
    """
    Check if the node is either ready to scan now, or should be scanned
    :param node: File/Node to be scanned
    :param env: Environment()
    :return: Boolean value indicated whether to scan this file
    """
    process_file = True

    file_abspath = node.abspath



    return process_file

def importedModules(node, env, path):
    """ Find all the imported modules. """

    # Does the node exist yet?
    if not os.path.isfile(str(node)):
        return []

    deps = []

    for b in m_build.finditer(content):
        if b.group(1):
            print "BUILD:%s"%b.group(1)


    for m in m_import.finditer(content):
        if m.group(1) == '(':
            print "Import() ", " ".join(m.group(2).splitlines())
            deps.extend(m.group(2).splitlines)
        else:
            # single line import statements
            print "Import \"\"", m.group(5)
            deps.append(m.group(5))

    return deps


def generate(env):
    env["go"] = env.Detect("go") or env.Detect("gnugo")

    goSuffixes = [".go"]

    compileAction = SCons.Action.Action("$GOCOM")

    linkAction = SCons.Action.Action("$GOLINK")


    goScanner = Scanner(function=importedModules,
                        scan_check=check_go_file,
                        name="goScanner",
                        skeys=goSuffixes,
                        recursive=False)

    goProgram = SCons.Builder.Builder(action=linkAction,
                                      prefix="$PROGPREFIX",
                                      suffix="$PROGSUFFIX",
                                      src_suffix="$OBJSUFFIX",
                                      src_builder="goObject")
    env["BUILDERS"]["goProgram"] = goProgram

    goLibrary = SCons.Builder.Builder(action=SCons.Defaults.ArAction,
                                      prefix="$LIBPREFIX",
                                      suffix="$LIBSUFFIX",
                                      src_suffix="$OBJSUFFIX",
                                      src_builder="goObject")
    env["BUILDERS"]["goLibrary"] = goLibrary

    goObject = SCons.Builder.Builder(action=compileAction,
                                     emitter=addgoInterface,
                                     prefix="$OBJPREFIX",
                                     suffix="$OBJSUFFIX",
                                     src_suffix=goSuffixes,
                                     source_scanner=goScanner)
    env["BUILDERS"]["goObject"] = goObject

    # initialize GOOS and GOARCH
    # TODO: Validate the values of each to make sure they are valid for GO.
    # TODO: Document all the GO variables.
    env["GOOS"] = "$TARGET_OS"
    env["GOARCH"] = "$TARGET_ARCH"
    env["GOFLAGS"] = None

def exists(env):
    return env.Detect("go") or env.Detect("gnugo")
