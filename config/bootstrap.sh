#!/bin/bash

# update + upgrade os
sudo apt update && sudo apt upgrade -y

# configure MAX98357A sound card, disable bluetooth
cat config.txt | sudo tee -a /boot/firmware/config.txt > /dev/null

# configure ALSA software mixer
sudo cp asound.conf /etc/asound.conf

# copy services
sudo cp lizard-api.service /etc/systemd/system/
sudo cp lizard-button.service /etc/systemd/system/

# enable services
sudo systemctl enable lizard-api.service
sudo systemctl enable lizard-button.service

# python dependencies
sudo apt install python3-pip python3-venv -y
python3 -m venv --system-site-packages ~/iot-env
source ~/iot-env/bin/activate
pip install fastapi uvicorn python-dotenv
deactivate

echo "Setup complete. Please reboot for changes to take effect."
