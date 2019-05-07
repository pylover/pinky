#! /usr/bin/env bash

set -e

source ./variables.sh


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

