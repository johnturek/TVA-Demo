sudo rm /etc/apt/sources.list.d/yarn.list
sudo apt update

corepack enable
yarn --version

curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash