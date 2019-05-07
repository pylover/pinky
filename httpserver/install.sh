#! /usr/bin/env bash

set -e

TITLE="pinky"
PIP=`which pip3.6`
CONFIG_FILE="/etc/${TITLE}.yml"
EXEC="/usr/local/bin/${TITLE}server.py"
SYSTEMD_UNIT="/etc/systemd/system/${TITLE}.service"
apt install libev-dev 
$PIP install --upgrade pip setuptools wheel
$PIP install -r requirements.txt
cp pinkyserver.py ${EXEC}

echo "
listen:
  host: 0.0.0.0
  port: 80
 
coolend:
  fan:
    speed: 90
    gpio: 16
    pwm_frequency: 1000

" > ${CONFIG_FILE} 


echo "
[Unit]
Description=Pinky HTTP Server
After=network.target

[Service]
ExecStart=${EXEC} ${CONFIG_FILE}

[Install]
WantedBy=multi-user.target
" > ${SYSTEMD_UNIT}

systemctl daemon-reload
systemctl enable ${TITLE}.service 
service ${TITLE} start

