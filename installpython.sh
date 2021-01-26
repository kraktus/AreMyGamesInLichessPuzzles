#!/bin/bash
sudo apt-get update -y
sudo apt-get install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update -y
sudo apt-get install python3.8 -y
sudo apt-get install python3-pip -y
sudo apt-get install python3.8-dev -y
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.8 1
sudo update-alternatives --set python /usr/bin/python3.8
