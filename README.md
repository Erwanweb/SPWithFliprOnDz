# SPWithFliprOnDz
Swimming pool full control using Flipr device for analysing the SP water

install :

cd ~/domoticz/plugins

git clone https://github.com/Erwanweb/SPWithFliprOnDz.git

cd SPWithFliprOnDz

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart

Upgrade :

cd ~/domoticz/plugins/SPWithFliprOnDz

git reset --hard

git pull --force

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart
