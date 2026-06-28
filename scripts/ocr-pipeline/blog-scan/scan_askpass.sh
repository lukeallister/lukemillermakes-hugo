#!/bin/sh
# scan_askpass.sh — read the autobot SSH password from the bind-mounted
# /etc/rsyncd.password file. Invoked by ssh via SSH_ASKPASS.
#
# We strip any trailing CR/whitespace because the rsyncd.password file was
# written by hand and may include a trailing newline that some editors add.
exec cat /etc/rsyncd.password