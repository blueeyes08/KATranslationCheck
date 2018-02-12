#!/usr/bin/env python3
import re

decimal_comma_re = re.compile(r"(-?\d+\}?)\.(-?\d+|\\\\[a-z]+\{\d+)")

def decimal_comma_replace(s):
    return decimal_comma_re.sub(r"\1{,}\2", s)


__all__ = ["decimal_comma_replace"]
