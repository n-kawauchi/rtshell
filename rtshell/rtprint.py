#!/usr/bin/env python
# -*- Python -*-
# -*- coding: utf-8 -*-

'''rtshell

Copyright (C) 2009-2010
    Geoffrey Biggs
    RT-Synthesis Research Group
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt

Implementation of the command to print data sent by ports to the console.

'''


import OpenRTM_aist
import optparse
import RTC
import rtctree.tree
import rtctree.utils
import sys
import threading
import time
import traceback

import comp_mgmt
import modmgr
import path
import port_types
import rtprint_comp
import rtshell


def read_from_ports(raw_paths, options, tree=None):
    event = threading.Event()

    mm = modmgr.ModuleMgr(verbose=options.verbose)
    mm.load_mods_and_poas(options.modules)
    if options.verbose:
        print >>sys.stderr, \
                'Pre-loaded modules: {0}'.format(mm.loaded_mod_names)
    if options.timeout == -1:
        max = options.max
        if options.verbose:
            print >>sys.stderr, 'Will run {0} times.'.format(max)
    else:
        max = -1
        if options.verbose:
            print >>sys.stderr, 'Will stop after {0}s'.format(options.timeout)

    targets = port_types.parse_targets(raw_paths)
    if not tree:
        paths = [t[0] for t in targets]
        tree = rtctree.tree.create_rtctree(paths=paths, filter=paths)
    port_specs = port_types.make_port_specs(targets, mm, tree)
    port_types.require_all_input(port_specs)
    if options.verbose:
        print >>sys.stderr, \
                'Port specifications: {0}'.format([str(p) for p in port_specs])

    comp_name, mgr = comp_mgmt.make_comp('rtprint_reader', tree,
            rtprint_comp.Reader, port_specs, event=event, rate=options.rate,
            max=max)
    if options.verbose:
        print >>sys.stderr, 'Created component {0}'.format(comp_name)
    comp = comp_mgmt.find_comp_in_mgr(comp_name, mgr)
    comp_mgmt.connect(comp, port_specs, tree)
    comp_mgmt.activate(comp)
    try:
        if options.timeout != -1:
            event.wait(options.timeout)
            comp_mgmt.disconnect(comp)
            comp_mgmt.deactivate(comp)
        elif options.max > -1:
            event.wait()
            comp_mgmt.disconnect(comp)
            comp_mgmt.deactivate(comp)
        else:
            while True:
                raw_input()
            # The manager will catch the Ctrl-C and shut down itself, so don't
            # disconnect/deactivate the component
    except KeyboardInterrupt:
        pass
    except EOFError:
        pass
    tree.give_away_orb()
    del tree
    comp_mgmt.shutdown(mgr)
    return 0


def main(argv=None, tree=None):
    usage = '''Usage: %prog [options] <path1>:<port1> [<path2>:<port2>...]
Print the data being sent by one or more output ports.

By default, only the first value received from one or more ports is printed.
Options are available to print multiple values or print regularly for a
specified length of time. In any one loop of the port checks, if only one port
out of multiple has data available, that is counted as a print.

''' + rtshell.RTSH_PATH_USAGE + '''
A connection will be made to the port using the default connection settings
compatible with the port.'''
    version = rtshell.RTSH_VERSION
    parser = optparse.OptionParser(usage=usage, version=version)
    parser.add_option('-m', '--mod', dest='modules', action='append',
            type='string', default=[],
            help='Extra modules to import. If automatic module loading '\
            'struggles with your data types, try listing the modules here. '\
            'The module and its __POA partner will be imported.')
    parser.add_option('-n', '--number', dest='max', action='store',
            type='int', default='-1',
            help='Specify the number of times to read from any ports. \
[Default: %default]')
    parser.add_option('-r', '--rate', dest='rate', action='store',
            type='float', default=1.0,
            help='Specify the rate in Hertz at which to read and print. \
[Default: %default]')
    parser.add_option('-t', '--timeout', dest='timeout', action='store',
            type='float', default=-1, help='Read data for this many seconds, \
then stop. Specify -1 for no timeout. This option overrides --number. \
[Default: %default]')
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
            default=False,
            help='Output verbose information. [Default: %default]')

    if argv:
        sys.argv = [sys.argv[0]] + argv
    try:
        options, args = parser.parse_args()
    except optparse.OptionError, e:
        print >>sys.stderr, 'OptionError:', e
        return 1

    if len(args) < 1:
        print >>sys.stderr, usage
        return 1

    try:
        result = read_from_ports([path.cmd_path_to_full_path(p) \
                for p in args], options, tree)
    except Exception, e:
        if options.verbose:
            traceback.print_exc()
        print >>sys.stderr, '{0}: {1}'.format(sys.argv[0], e)
        return 1
    return result

