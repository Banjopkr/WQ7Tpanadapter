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

INSTALL the WQ7Tpanadapter software 

cd ~
git clone https://github.com/Banjopkr/WQ7Tpanadapter.git

If you want to use 7" or other large display

sudo cp -r WQ7Tpanadapter/FreqShow_Large FreqShow_Large
sudo cp -r FreqShow_Large/FreqShow.desktop Desktop/FreqShow.desktop

If you want to use 2.8" or other small display

sudo cp -r WQ7Tpanadapter/FreqShow_Small FreqShow_Small
sudo cp -r FreqShow_Small/FreqShow.desktop Desktop/FreqShow.desktop

Now you should have a launcher file to double click on from the desktop

READ READ READ THE PDF operating manual it will also show you how to save your own deafault parameters!
