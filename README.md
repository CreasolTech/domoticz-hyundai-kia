# Domoticz Hyundai-Kia plugin
Author: Creasol - linux@creasol.it 
Websites: https://www.creasol.it/domotics

For any support request, please write email to linux@creasol.it or enter the Telegram DomBus group https://t.me/DomBus 


# Introduction

This plugin is designed for [Domoticz](https://www.domoticz.com) home automation system and provide a way to get status from Hyunday and Kia cars.

It's based on the [hyundai-kia-connect-api](https://pypi.org/project/hyundai-kia-connect-api/) written by Fuat Akgun](https://www.domoticz.com) home automation system and provide a way to get status from Hyunday and Kia cars.

It's based on the [hyundai-kia-connect-api](https://pypi.org/project/hyundai-kia-connect-api/) written by Fuat Akgun that must be installed using the command  
<code>sudo pip3 install hyundai-kia-connect-api</code>

In this folder you can find the python plugin for Domoticz: **you can install the hardware plugin by using Python Plugin Manager, or typing the following commands from the linux shell**:

```
#install git, if not already installed
which git
if [ $? -ne 0 ]; then sudo apt install git; fi

#change to the domoticz directory / plugins
cd /home/pi/domoticz/plugins 

#fetch the Python Plugin Manager (that can be used to install/upgrade other plugins, including domoticz-hyundai-kia)
git clone https://github.com/ycahome/pp-manager

#fetch Creasol Plugin
git clone https://github.com/CreasolTech/domoticz-hyundai-kia

#restart Domoticz daemon
service domoticz restart
```



