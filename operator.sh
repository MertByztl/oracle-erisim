#!/bin/bash
# Operator forced-command — SSH authorized_keys'te command="..." ile baglanir.
# YALNIZCA beyaz-liste islemler. Shell/dosya/genel-root YOK. Yetki yukseltme YOK.
# Her VPS'te ayni script; ilgisiz islemler o makinede sessizce basarisiz olur.
set -o pipefail
CMD="${SSH_ORIGINAL_COMMAND:-$*}"; set -- $CMD; A="$1"
case "$A" in
  status)
    out="{"
    systemctl list-unit-files 2>/dev/null | grep -q cowrie-hybrid && \
      out="$out\"hybrid\":\"$(systemctl is-active cowrie-hybrid 2>/dev/null)\",\"iot\":\"$(systemctl is-active cowrie-iot 2>/dev/null)\","
    [ -x /usr/local/bin/vpn-ctl.sh ] && \
      out="$out\"vpn\":\"$(sudo tailscale status >/dev/null 2>&1 && echo up || echo down)\","
    sudo docker ps --filter name=hermes --format '{{.Status}}' 2>/dev/null | grep -qi up && \
      out="$out\"hermes\":\"up\","
    out="${out%,}}"; [ "$out" = "{}" ] && out='{"durum":"ayakta"}'
    echo "$out" ;;
  hybrid_start) sudo systemctl start cowrie-hybrid && echo '{"ok":true}'  || echo '{"ok":false}' ;;
  hybrid_stop)  sudo systemctl stop  cowrie-hybrid && echo '{"ok":true}'  || echo '{"ok":false}' ;;
  iot_start)    sudo systemctl start cowrie-iot    && echo '{"ok":true}'  || echo '{"ok":false}' ;;
  iot_stop)     sudo systemctl stop  cowrie-iot    && echo '{"ok":true}'  || echo '{"ok":false}' ;;
  up)       sudo /usr/local/bin/vpn-ctl.sh up ;;
  down)     sudo /usr/local/bin/vpn-ctl.sh down ;;
  direct)   sudo /usr/local/bin/vpn-ctl.sh direct ;;
  tor)      sudo /usr/local/bin/vpn-ctl.sh tor ;;
  new_ip)   sudo /usr/local/bin/vpn-ctl.sh new-ip ;;
  exit_ip)  sudo /usr/local/bin/vpn-ctl.sh exit-ip ;;
  doctor_status)  cd /home/ubuntu/venice-hermes && ./venv/bin/python hermes_doctor.py status ;;
  doctor_restart) cd /home/ubuntu/venice-hermes && ./venv/bin/python hermes_doctor.py restart ;;
  *) echo '{"hata":"izinli degil"}' ;;
esac
