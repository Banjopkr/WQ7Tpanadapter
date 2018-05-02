# WQ7Tpanadapter
A very enhanced panadapter program for the Raspberrypi based on the original FreqShow


INSTALLATION of DEPENDENCIES
!VERY IMPORTANT!

Please note, the enhancements to the original FreqShow by WQ7T require the Python-Scipy
Library in addition to the original dependencies for FreqShow.

Original dependencies required by Adafruit/FreqShow
https://learn.adafruit.com/freq-show-raspberry-pi-rtl-sdr-scanner/installation
install scripts:

sudo apt-get update
sudo apt-get install cmake build-essential python-pip libusb-1.0-0-dev python-numpy git
pandoc

https://www.scipy.org/install.html
install script :

python -m pip install --user numpy scipy matplotlib ipython jupyter pandas sympy nose

OR
alternate install script:

sudo apt-get install python-numpy python-scipy python-matplotlib ipython ipython-notebook
python-pandas python-sympy python-nose
INSTALL RTL-SDR
cd ~
git clone git://git.osmocom.org/rtl-sdr.git
cd rtl-sdr
mkdir build
cd build
cmake ../ -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON
make
sudo make install
sudo ldconfig

sudo pip install pyrtlsdr

git clone https://github.com/Banjopkr/WQ7Tpanadapter.git
