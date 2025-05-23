#! /usr/bin/env python

# This file is part of IVRE.
# Copyright 2011 - 2025 Pierre LALET <pierre@droids-corp.org>
#
# IVRE is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IVRE is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
# License for more details.
#
# You should have received a copy of the GNU General Public License
# along with IVRE. If not, see <http://www.gnu.org/licenses/>.


"""This tool can be used to manage IP addresses related data, such as
AS number and country information.

"""


import json
import sys
from argparse import ArgumentParser
from collections.abc import Callable
from typing import Any, cast

from ivre import geoiputils, utils
from ivre.db import DBData, db
from ivre.tags import add_tags, gen_addr_tags


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    torun: list[tuple[Callable, list, dict]] = []
    parser.add_argument("--download", action="store_true", help="Fetch all data files.")
    parser.add_argument(
        "--import-all",
        action="store_true",
        help="Create all CSV files for reverse lookups.",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode.")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON data.")
    parser.add_argument(
        "ip",
        nargs="*",
        metavar="IP",
        help="Display results for specified IP addresses.",
    )
    parser.add_argument(
        "--from-db",
        metavar="DB_URL",
        help="Get data from the provided URL instead of using IVRE's configuration.",
    )
    args = parser.parse_args()
    if args.from_db:
        dbase = DBData.from_url(args.from_db)
        dbase.globaldb = db
    else:
        dbase = db.data
    if args.download:
        geoiputils.download_all(verbose=not args.quiet)
        dbase.reload_files()
    if args.import_all:
        torun.append((cast(Callable, dbase.build_dumps), [], {}))
    for function, fargs, fkargs in torun:
        function(*fargs, **fkargs)
    for addr in args.ip:
        if addr.isdigit():
            addr = utils.int2ip(int(addr))
        if args.json:
            res = {"addr": addr}
            try:
                res.update(dbase.infos_byip(addr) or {})
            except utils.InvalidIPAddress as exc:
                utils.LOGGER.error("Invalid IP address [%r]!", exc.value)
            json.dump(res, sys.stdout)
            print()
        else:
            print(addr)
            try:
                for subinfo in [dbase.as_byip(addr), dbase.location_byip(addr)]:
                    for key, value in (subinfo or {}).items():
                        print("    %s %s" % (key, value))
            except utils.InvalidIPAddress as exc:
                utils.LOGGER.error("Invalid IP address [%r]!", exc.value)
                continue
            info: dict[str, Any] = {}
            add_tags(info, gen_addr_tags(addr))
            for tag in info.get("tags", []):
                if tag.get("info"):
                    print(f"    {tag['value']}: {', '.join(tag['info'])}")
                else:
                    print(f"    {tag['value']}")
