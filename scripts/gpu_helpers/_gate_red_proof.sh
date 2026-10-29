#!/bin/sh
# deliberate SC2046 (warning): unquoted command substitution
echo $(echo hi)
