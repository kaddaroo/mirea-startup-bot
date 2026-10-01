#/root
systemctl daemon-reload
systemctl enable --now mirea-bot.service
systemctl status mirea-bot.service