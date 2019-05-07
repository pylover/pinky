#! /usr/bin/env bash


TITLE="pinky"
PIP=`which pip3.6`
CONFIG_FILE="/etc/${TITLE}.yml"
EXEC="/usr/local/bin/${TITLE}server.py"
SYSTEMD_UNIT="/etc/systemd/system/${TITLE}.service"


