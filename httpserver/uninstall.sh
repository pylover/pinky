#! /usr/bin/env bash


source ./variables.sh


service ${TITLE} stop
systemctl disable ${TITLE}.service 
$PIP uninstall -r requirements.txt
rm ${EXEC}
rm ${CONFIG_FILE}
rm ${SYSTEMD_UNIT}
systemctl daemon-reload

