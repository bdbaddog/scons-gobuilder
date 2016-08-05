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
from SCons.Builder import Builder
from SCons.Action import Action, _subproc
from SCons.Scanner import Scanner, FindPathDirs
from SCons.Defaults import ObjSourceScan
import os.path
import os
import re
import string
import pdb
import subprocess

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

    if '_test' in file_abspath: process_file = False

    print "check_go_File:%s  Process:%s"%(file_abspath,process_file)


    return process_file

def is_not_go_standard_library(env, packagename):
    """ Check with go if the imported module is part of
    Go's standard library"""

    #TODO: What to do when there's a system package and a package in the project with the same name


    return packagename not in env['GO_SYSTEM_PACKAGES']

def include_go_file(env,file):
    """
    Use file name (and also scan for +build statements in file to determine
    if this file should be compiled and/or added to dependency tree
    :param env: Environment being used to compile this file
    :param file: The file in question
    :return: Boolean indicating if this file should be included
    """

    include_file = True

    if '_test' in file.abspath: include_file = False

    return include_file

def expand_go_packages_to_files(env, gopackage, path):
    """
    Use GOPATH and package name to find directory where package is located and then scan
    the directory for go packages. Return complete list of found files
    TODO: filter found files by normal go file pruning (matching GOOS,GOOARCH,
         and //+build statements in files
    :param env:
    :param gopackage:
    :return:
    """
    go_files = []

    for p in path:
        print "Path:%s/src/%s"%(p,gopackage)
        go_files = p.glob("src/%s/*.go"%gopackage)
        count=0
        for f in go_files:
            print "(%4d) File:%s  Test:%s"%(count,f.abspath,('_test' in f.abspath))
            count += 1
        if len(go_files) > 0:
            # If we found packages files in this path, the don't continue searching GOPATH
            break

    # print "filtering test files"
    # for f in go_files:
    #     print "%s : %s"%(type(f), f)
    try:
        go_files = [ f for f in go_files if include_go_file(env,f)]
    except TypeError as e:
        print "TypeError is %s %s"%(e,f)
    # print "done filtering test files"
    # count = 0
    # for f in go_files:
    #     print "X(%4d) File:%s  Test:%s" % (count, f.abspath, ('_test' in f.abspath))
    #     count += 1

    return go_files

def importedModules(node, env, path):
    """ Find all the imported modules. """

    # Does the node exist yet?
    if not os.path.isfile(str(node)):
        return []

    packages = []
    deps = []

    # print "Paths to search: %s"%path
    # print "Node PATH      : %s"%node.path

    content = node.get_contents()
    for b in m_build.finditer(content):
        if b.group(1):
            print "BUILD:%s"%b.group(1)


    for m in m_import.finditer(content):
        if m.group(1) == '(':
            imports = [ x.strip('"\t') for x in m.group(2).splitlines()]
            print "Import() ", " ".join(imports)
            packages.extend(imports)
        else:
            # single line import statements
            print "Import \"\"", m.group(5)
            packages.append(m.group(5))

    print "packages:%s"%packages

    import_packages = [ gopackage for gopackage in packages if is_not_go_standard_library(env, gopackage)]

    for gopackage in import_packages:
        deps += expand_go_packages_to_files(env,gopackage,path)

    return deps


is_String = SCons.Util.is_String
is_List = SCons.Util.is_List


def _create_env_for_subprocess(env):
    """ Create string-ified environment to pass to subprocess
    This logic is mostly copied from SCons.Action._subproc
    """

    # Ensure that the ENV values are all strings:
    new_env = dict()
    for key, value in env['ENV'].items():
        if is_List(value):
            # If the value is a list, then we assume it is a path list,
            # because that's a pretty common list-like value to stick
            # in an environment variable:
            value = SCons.Util.flatten_sequence(value)
            new_env[key] = os.pathsep.join(map(str, value))
        else:
            # It's either a string or something else.  If it's a string,
            # we still want to call str() because it might be a *Unicode*
            # string, which makes subprocess.Popen() gag.  If it isn't a
            # string or a list, then we just coerce it to a string, which
            # is the proper way to handle Dir and File instances and will
            # produce something reasonable for just about everything else:
            new_env[key] = str(value)
    return new_env


def _get_system_packages(env):

    # use
    subp_env = _create_env_for_subprocess(env)

    all_packages = set(subprocess.check_output([env.subst('$GO'), "list", "..."], env=subp_env).split())

    proj_packages = set(subprocess.check_output([env.subst('$GO'), "list", "./..."], env=subp_env).split())

    # pdb.set_trace()
    system_packages = all_packages - proj_packages

    # print "All PACKAGES: %s" % all_packages
    # print "    PACKAGES: %s" % proj_packages
    # print "GlobPackages: %s" % system_packages
    # print "PACKAGES: %s" % [s for s in stdout]
    env['GO_SYSTEM_PACKAGES'] = list(system_packages)


def _go_emitter(target, source, env):
    if len(source) == 1:
        target.append(str(source).replace('.go',''))
    return target, source

def generate(env):
    go_suffix = '.go'


    go_binaries = ['go','gccgo-go','gccgo']

    # If user as set GO, honor it, otherwise try finding any of the expected go binaries
    env['GO'] = env.get('GO',False) or env.Detect(['go','gccgo-go'])  or "ECHO"

    go_path = env.WhereIs(env['GO'])
    # Typically this would be true, but it shouldn't need to be set if
    # We're using the "go" binary from either google or gcc go.
    # env['ENV']['GOROOT'] = os.path.dirname(os.path.dirname(go_path))
    # GOROOT points to where go environment is setup.
    # Only need to set GOROOT if GO is not in your path..  check if there's a dirsep in the GO path
    # gcc go has implicit GOROOT and it's where --prefix pointed when built.
    # Only honor user provide GOROOT. otherwise don't specify.
    env['ENV']['GOPATH'] = env.get('GOPATH','.')

    # Populate GO_SYSTEM_PACKAGES
    # TODO: Add documentation for GO_SYSTEM_PACKAGES
    _get_system_packages(env)

    goSuffixes = [".go"]

    compileAction = Action("$GOCOM","$GOCOMSTR")

    linkAction = Action("$GOLINK","$GOLINKSTR")

    goScanner = Scanner(function=importedModules,
                        scan_check=check_go_file,
                        name="goScanner",
                        skeys=goSuffixes,
                        path_function=FindPathDirs('GOPATH'),
                        recursive=True)

    goProgram = Builder(action=linkAction,
                        prefix="$PROGPREFIX",
                        suffix="$PROGSUFFIX",
                        source_scanner=goScanner,
                        src_suffix=".go",
                        src_builder="goObject")
    env["BUILDERS"]["goProgram"] = goProgram

    # goLibrary = SCons.Builder.Builder(action=SCons.Defaults.ArAction,
    #                                   prefix="$LIBPREFIX",
    #                                   suffix="$LIBSUFFIX",
    #                                   src_suffix="$OBJSUFFIX",
    #                                   src_builder="goObject")
    # env["BUILDERS"]["goLibrary"] = goLibrary

    # goObject = Builder(action=compileAction,
    #                    # emitter=addgoInterface,
    #                    # emitter=_go_emitter,
    #                    prefix="$OBJPREFIX",
    #                    suffix="$OBJSUFFIX",
    #                    src_suffix=goSuffixes,
    #                    source_scanner=goScanner)
    # env["BUILDERS"]["goObject"] = goObject

    # initialize GOOS and GOARCH
    # TODO: Validate the values of each to make sure they are valid for GO.
    # TODO: Document all the GO variables.
    env["GOOS"] = "$TARGET_OS"
    env["GOARCH"] = "$TARGET_ARCH"
    env["GOFLAGS"] = env['GOFLAGS'] or None
    env['GOCOM'] = '$GO build $GOFLAGS $SOURCES'
    env['GOCOMSTR'] = '$GOCOM'
    env['GOLINK'] = '$GO build -o $TARGET $GOFLAGS $SOURCES'
    env['GOLINKSTR'] = '$GOLINK'

    # import SCons.Tool
    # static_obj, shared_obj = SCons.Tool.createObjBuilders(env)
    # static_obj.add_action(go_suffix, compileAction)
    # shared_obj.add_action(go_suffix, compileAction)
    #
    # static_obj.add_emitter(go_suffix, SCons.Defaults.StaticObjectEmitter)
    # shared_obj.add_emitter(go_suffix, SCons.Defaults.SharedObjectEmitter)



def exists(env):
    return env.Detect("go") or env.Detect("gnugo")
